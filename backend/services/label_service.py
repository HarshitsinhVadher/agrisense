import os
import json
import io
import base64
from typing import Dict, Any, Optional

try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    from PIL import Image, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def load_products_db() -> list:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(os.path.dirname(script_dir), 'data', 'products_db.json')
    if os.path.exists(db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def scan_and_interpret_label(image_bytes: Optional[bytes] = None, text_input: Optional[str] = None, lang: str = "en") -> Dict[str, Any]:
    """
    Primary label scanning pipeline:
    1. If GEMINI_API_KEY is set and image provided → Gemini Vision direct analysis
    2. Fallback → local fuzzy matching against products_db.json
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    products = load_products_db()

    # ─── Primary Path: Gemini Vision API (direct image analysis) ───
    if api_key and HAS_GEMINI and image_bytes:
        try:
            result = _analyze_with_gemini_vision(api_key, image_bytes, products, lang)
            if result and not result.get("error"):
                return result
        except Exception as e:
            print(f"Gemini Vision analysis failed, falling back to local match: {e}")

    # ─── Fallback Path: Text-based fuzzy matching ───
    raw_text = text_input or ""

    if not raw_text and image_bytes and HAS_PIL:
        # Try basic OCR if available
        try:
            import pytesseract
            image = Image.open(io.BytesIO(image_bytes))
            raw_text = pytesseract.image_to_string(image)
        except Exception:
            raw_text = ""

    if not raw_text:
        raw_text = text_input or ""

    if not raw_text.strip():
        return {
            "raw_ocr_text": "",
            "match_confidence": 0,
            "matched_product": None,
            "ai_summary": "No text could be extracted from the image. Please try again with a clearer photo or type the product name manually.",
            "analysis_method": "none",
            "disclaimer": "⚠️ Could not analyze the image. Try typing the product name instead."
        }

    return _fuzzy_match_product(raw_text, products, lang)


def _clean_and_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """Robustly strips code fences (```json), extra text commentary, and parses JSON."""
    if not text or not text.strip():
        return None

    cleaned = text.strip()

    # Strip markdown code blocks (e.g. ```json ... ``` or ``` ...)
    if "```" in cleaned:
        import re
        fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned, re.IGNORECASE)
        if fence_match:
            cleaned = fence_match.group(1).strip()
        else:
            lines = [line for line in cleaned.split("\n") if not line.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

    # Direct JSON parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Extract JSON object using regex substring search
    import re
    json_match = re.search(r'\{[\s\S]*\}', cleaned)
    if json_match:
        try:
            return json.loads(json_match.group())
        except Exception:
            pass

    return None


def _get_first_present_val(data: dict, keys: list, default=None):
    """Helper to return first non-empty value matching any key variation."""
    for k in keys:
        if k in data and data[k] is not None and str(data[k]).strip() and str(data[k]).lower() != "null":
            return data[k]
    return default


def _normalize_ai_fields(data: dict) -> dict:
    """Normalization mapping layer resolving all Gemini key variations (e.g. active, activeIngredient, brand, company)."""
    if not isinstance(data, dict):
        return {}

    norm = {}
    norm["product_name"] = _get_first_present_val(data, ["product_name", "productName", "name", "title", "product_title", "trade_name", "product"])
    norm["manufacturer"] = _get_first_present_val(data, ["manufacturer", "brand", "company", "manufacturer_name", "brand_name", "company_name"])
    norm["active_ingredient"] = _get_first_present_val(data, ["active_ingredient", "activeIngredient", "active_ingredients", "active", "chemical_name", "active_chemical", "ingredients", "key_ingredient"])
    norm["formulation_type"] = _get_first_present_val(data, ["formulation_type", "formulationType", "formulation", "type_code"])
    norm["dosage_per_acre"] = _get_first_present_val(data, ["dosage_per_acre", "dosagePerAcre", "acre_dosage", "dose_per_acre"])
    norm["dosage_per_liter_water"] = _get_first_present_val(data, ["dosage_per_liter_water", "dosagePerLiterWater", "dosage_per_liter", "liter_dosage", "mixing_ratio", "dilution_rate"])
    norm["dosage"] = _get_first_present_val(data, ["dosage", "dose", "rate", "application_rate", "usage_directions", "directions"])

    targets = _get_first_present_val(data, ["target_pests_or_crops", "targetPestsOrCrops", "target_pests", "targetPests", "suitable_crops", "suitableCrops", "crops", "pests", "target_diseases"])
    if isinstance(targets, str):
        targets = [t.strip() for t in targets.split(",") if t.strip()]
    norm["target_pests_or_crops"] = targets or []

    conf = _get_first_present_val(data, ["confidence_score", "confidenceScore", "confidence", "score", "match_confidence"], default=75)
    try:
        norm["confidence_score"] = float(conf)
    except Exception:
        norm["confidence_score"] = 75.0

    norm["unreadable_reason"] = _get_first_present_val(data, ["unreadable_reason", "unreadableReason", "error_reason", "reason"])
    norm["identification_notes"] = _get_first_present_val(data, ["identification_notes", "identificationNotes", "notes", "visual_notes"], default="")

    return norm


def _analyze_with_gemini_vision(api_key: str, image_bytes: bytes, products: list, lang: str) -> Dict[str, Any]:
    """
    Send image to Gemini Vision API with high-resolution PIL preprocessing and structured JSON extraction.
    """
    client = genai.Client(api_key=api_key)

    mime_type = "image/jpeg"
    processed_bytes = image_bytes
    if HAS_PIL:
        try:
            from PIL import ImageEnhance
            img = Image.open(io.BytesIO(image_bytes))
            # 1. Correct camera EXIF rotation
            img = ImageOps.exif_transpose(img)
            
            # 2. Ensure RGB color space
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # 3. Reduce glare & shadows via auto-contrast normalization
            try:
                img = ImageOps.autocontrast(img, cutoff=0.5)
            except Exception:
                pass

            # 4. Enhance contrast (+20%) for text readability
            img = ImageEnhance.Contrast(img).enhance(1.20)

            # 5. Boost sharpness (+30%) for fine chemical ingredient print
            img = ImageEnhance.Sharpness(img).enhance(1.30)
            
            # 6. Bound maximum dimension to 2048px while maintaining aspect ratio
            max_dim = 2048
            if max(img.width, img.height) > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
            output_io = io.BytesIO()
            img.save(output_io, format="JPEG", quality=90, optimize=True)
            processed_bytes = output_io.getvalue()

            # Ensure file size stays strictly under 4MB
            if len(processed_bytes) > 4 * 1024 * 1024:
                output_io = io.BytesIO()
                img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                img.save(output_io, format="JPEG", quality=82, optimize=True)
                processed_bytes = output_io.getvalue()

            mime_type = "image/jpeg"
        except Exception as img_err:
            print(f"Image preprocessing note: {img_err}")
            processed_bytes = image_bytes

    product_names = [p.get('name', '') for p in products] if products else []
    product_list_str = ", ".join(product_names[:30]) if product_names else "No local database available"

    prompt = f"""You are AgriSense AI, an expert agricultural inputs, pesticide, fertilizer, seed, and chemical label identification system.

Analyze the provided label photo carefully and extract structured information into a single JSON object with these EXACT fields:

{{
    "product_name": "Full trade / brand product name as written on label or null if unreadable",
    "manufacturer": "Company / Manufacturer / Brand Name (e.g. Bayer, Syngenta, IFFCO, Tata Rallis) or null",
    "active_ingredient": "Active ingredient chemical name WITH percentage concentration (e.g. Chlorpyrifos 20% EC, Imidacloprid 17.8% SL, NPK 19:19:19) or null",
    "formulation_type": "Formulation type code (e.g. SC, EC, WP, WDG, SL, GR, SP, DP, Liquid, Powder, Granules) or null",
    "dosage_per_acre": "Recommended application dosage per acre (e.g. 250 ml/acre, 50 kg/acre) or null",
    "dosage_per_liter_water": "Recommended dilution ratio per liter of water (e.g. 2 ml/L water, 1.5 g/L) or null",
    "target_pests_or_crops": ["List of target crops, insects, weeds, fungi, or diseases listed on label"],
    "confidence_score": 88,
    "unreadable_reason": null,
    "identification_notes": "Step-by-step visual notes explaining how you identified this product (logos, text, bottle shape, label colors)"
}}

Known products in our local database for cross-reference: {product_list_str}

INSTRUCTIONS:
1. ACCURACY & PARTIAL LABELS: If the label image is unclear or partially cut off, extract whatever text is legible and mark confidence_score accordingly (e.g., 40-70%) instead of returning empty fields.
2. UNREADABLE IMAGES FALLBACK: If no readable text is found at all, return a JSON with all text fields set to null, confidence_score set to 0, and unreadable_reason explaining why (e.g. "Image too blurry", "Excessive glare on plastic bottle", "Angle obscures text", "Low resolution photo"), instead of returning a generic error.
3. CONCENTRATION & FORMULATION: Always capture percentage concentration in active_ingredient (e.g., 5% SC, 50% WP) and specify formulation_type if present.
4. Output ONLY the raw JSON object. No markdown formatting, no extra explanation."""

    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
    response = None

    for model_name in models_to_try:
        try:
            if HAS_PIL:
                try:
                    pil_img = Image.open(io.BytesIO(processed_bytes))
                    contents_payload = [prompt, pil_img]
                except Exception:
                    contents_payload = [prompt, types.Part.from_bytes(data=processed_bytes, mime_type=mime_type)]
            else:
                contents_payload = [prompt, types.Part.from_bytes(data=processed_bytes, mime_type=mime_type)]

            response = client.models.generate_content(
                model=model_name,
                contents=contents_payload,
                config=types.GenerateContentConfig(temperature=0.1)
            )

            if response and response.text:
                break
        except Exception as e:
            print(f"Gemini Vision model {model_name} failed: {e}")
            continue

    if not response or not response.text:
        return None

    # Parse JSON cleanly with code fence stripping
    raw_parsed = _clean_and_parse_json(response.text)
    if not raw_parsed:
        return None

    # Apply field normalization layer
    ai_result = _normalize_ai_fields(raw_parsed)

    # Handle unreadable image response fallback from model
    unreadable_reason = ai_result.get("unreadable_reason")
    confidence = ai_result.get("confidence_score", 75)

    if unreadable_reason or (not ai_result.get("product_name") and confidence < 20):
        reason_msg = unreadable_reason or "Label photo is blurry, obscured by glare, or taken from an unreadable angle."
        return {
            "raw_ocr_text": f"[Unreadable Image] {reason_msg}",
            "match_confidence": 0,
            "matched_product": None,
            "ai_summary": f"📷 Could not read product label. Reason: {reason_msg}. Please re-take photo with clear lighting and straight angle.",
            "analysis_method": "gemini_vision_unreadable",
            "disclaimer": f"⚠️ Photo Unreadable: {reason_msg}. Try capturing a clearer photo of the product label."
        }

    # Cross-reference with local database
    local_match = None
    local_score = 0
    prod_name = ai_result.get("product_name") or ""
    if HAS_RAPIDFUZZ and products and prod_name:
        names = [f"{p['name']} {p.get('brand', '')} {p.get('active_ingredient', '')}" for p in products]
        match_result = process.extractOne(prod_name, names, scorer=fuzz.token_set_ratio)
        if match_result and match_result[1] > 50:
            local_match = products[match_result[2]]
            local_score = match_result[1]

    # Combine dosage fields
    dosage_parts = []
    if ai_result.get("dosage_per_acre"):
        dosage_parts.append(f"Per Acre: {ai_result['dosage_per_acre']}")
    if ai_result.get("dosage_per_liter_water"):
        dosage_parts.append(f"Per Liter Water: {ai_result['dosage_per_liter_water']}")
    dosage_str = " | ".join(dosage_parts) if dosage_parts else ai_result.get("dosage", "See product label for exact dosage")

    # Format active ingredient with formulation type
    act_ing = ai_result.get("active_ingredient") or "Not identified"
    form_type = ai_result.get("formulation_type")
    if form_type and form_type.lower() not in act_ing.lower():
        act_ing = f"{act_ing} ({form_type})"

    # Build matched_product from AI result
    matched_product = {
        "name": prod_name or "Unknown Product",
        "brand": ai_result.get("manufacturer") or "Unknown Brand",
        "active_ingredient": act_ing,
        "formulation_type": form_type or "Standard",
        "type": ai_result.get("type", "agricultural product"),
        "target_pests": ai_result.get("target_pests_or_crops", []),
        "suitable_crops": ai_result.get("target_pests_or_crops", []),
        "dosage": dosage_str,
        "dosage_per_acre": ai_result.get("dosage_per_acre"),
        "dosage_per_liter_water": ai_result.get("dosage_per_liter_water"),
        "precautions": ai_result.get("precautions", "Follow safety guidelines on label"),
        "usage_notes": ai_result.get("identification_notes", "")
    }

    # Merge local database info if match score > 70
    if local_match and local_score > 70:
        for key in ['dosage', 'precautions', 'usage_notes', 'suitable_crops', 'target_pests']:
            if local_match.get(key) and not matched_product.get(key):
                matched_product[key] = local_match[key]

    # Generate farmer-friendly summary
    summary = _generate_ai_summary(matched_product, lang, api_key)

    return {
        "raw_ocr_text": f"[Gemini Vision Analysis] {ai_result.get('identification_notes', '')}",
        "match_confidence": confidence,
        "matched_product": matched_product,
        "ai_summary": summary,
        "analysis_method": "gemini_vision",
        "local_db_match": local_match.get("name") if local_match else None,
        "local_db_score": round(local_score, 1) if local_match else 0,
        "disclaimer": "⚠️ SAFETY DISCLAIMER: This AI analysis is for reference only. Always verify dosage and safety instructions with your local Krishi Vigyan Kendra (KVK), agriculture officer, or the official product label before field application."
    }


def _fuzzy_match_product(raw_text: str, products: list, lang: str) -> Dict[str, Any]:
    """Fallback: Match raw text against local products database using fuzzy matching."""
    matched_product = None
    best_score = 0.0

    if HAS_RAPIDFUZZ and products:
        names = [f"{p['name']} {p.get('brand', '')} {p.get('active_ingredient', '')} {' '.join(p.get('target_pests', []))}" for p in products]
        result = process.extractOne(raw_text, names, scorer=fuzz.token_set_ratio)
        if result:
            best_score = result[1]
            if best_score > 35:
                matched_product = products[result[2]]
    else:
        text_lower = raw_text.lower()
        for p in products:
            if p['name'].lower() in text_lower or p.get('active_ingredient', '').lower() in text_lower:
                matched_product = p
                best_score = 80.0
                break

    if not matched_product and products:
        matched_product = products[0]
        best_score = 25.0

    summary = _generate_local_summary(matched_product, lang) if matched_product else "No matching product found."

    return {
        "raw_ocr_text": raw_text[:200],
        "match_confidence": round(best_score, 1),
        "matched_product": matched_product,
        "ai_summary": summary,
        "analysis_method": "text_fuzzy_match",
        "disclaimer": "⚠️ SAFETY DISCLAIMER: This analysis is based on text matching against our database. Always verify dosage with your local KVK or agriculture officer."
    }


def _generate_ai_summary(product: Dict[str, Any], lang: str, api_key: str) -> str:
    """Generate a farmer-friendly summary using Gemini."""
    if api_key and HAS_GEMINI:
        try:
            client = genai.Client(api_key=api_key)
            lang_name = {"en": "English", "gu": "Gujarati", "hi": "Hindi"}.get(lang, "English")
            prompt = f"""Write a simple 4-bullet farmer advisory for this agricultural product in {lang_name}:
- Product: {product.get('name')} by {product.get('brand')}
- Active Ingredient: {product.get('active_ingredient')}
- Target: {', '.join(product.get('target_pests', [])) if isinstance(product.get('target_pests'), list) else product.get('target_pests', 'General use')}
- Crops: {', '.join(product.get('suitable_crops', [])) if isinstance(product.get('suitable_crops'), list) else product.get('suitable_crops', 'Multiple crops')}
- Dosage: {product.get('dosage')}
- Safety: {product.get('precautions')}

Keep it very simple for a smallholder farmer to understand. Use emojis for visual clarity."""

            for summary_model in ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']:
                try:
                    response = client.models.generate_content(model=summary_model, contents=prompt)
                    if response and response.text:
                        return response.text.strip()
                except Exception:
                    continue
        except Exception as e:
            print(f"Gemini summary generation failed: {e}")

    return _generate_local_summary(product, lang)


def _generate_local_summary(product: Dict[str, Any], lang: str) -> str:
    """Generate a local template-based summary without API."""
    pests = ', '.join(product.get('target_pests', [])) if isinstance(product.get('target_pests'), list) else product.get('target_pests', 'General')
    crops = ', '.join(product.get('suitable_crops', [])) if isinstance(product.get('suitable_crops'), list) else product.get('suitable_crops', 'Multiple')

    if lang == "gu":
        return f"""📌 **ઉત્પાદન**: {product.get('name')} ({product.get('brand', '')})
🌱 **ઉપયોગી પાક**: {crops}
🐛 **નિયંત્રિત જીવાત/રોગ**: {pests}
💧 **ભલામણ કરેલ પ્રમાણ**: {product.get('dosage', 'લેબલ જુઓ')}
⚠️ **સાવચેતી**: {product.get('precautions', 'લેબલ પર સૂચનાઓ અનુસરો')}""".strip()
    elif lang == "hi":
        return f"""📌 **उत्पाद**: {product.get('name')} ({product.get('brand', '')})
🌱 **उपयुक्त फसलें**: {crops}
🐛 **नियंत्रित कीट/रोग**: {pests}
💧 **अनुशंसित खुराक**: {product.get('dosage', 'लेबल देखें')}
⚠️ **सावधानी**: {product.get('precautions', 'लेबल पर दिए निर्देशों का पालन करें')}""".strip()
    else:
        return f"""📌 **Product**: {product.get('name')} ({product.get('brand', '')})
🌱 **Target Crops**: {crops}
🐛 **Target Pests/Diseases**: {pests}
💧 **Recommended Dosage**: {product.get('dosage', 'See label')}
⚠️ **Safety Note**: {product.get('precautions', 'Follow label instructions')}""".strip()
