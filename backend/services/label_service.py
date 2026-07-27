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


def _analyze_with_gemini_vision(api_key: str, image_bytes: bytes, products: list, lang: str) -> Dict[str, Any]:
    """
    Send image to Gemini Vision API with:
    1. Google Search Grounding for live brand & web product matching (Option 1)
    2. High-resolution PIL preprocessing + EXIF orientation correction (Option 2)
    """
    client = genai.Client(api_key=api_key)

    # ─── OPTION 2: Image Quality & Preprocessing ───
    mime_type = "image/jpeg"
    processed_bytes = image_bytes
    if HAS_PIL:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            # Correct orientation from camera EXIF tags
            img = ImageOps.exif_transpose(img)
            # Ensure RGB color mode for JPEG export
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Maintain high resolution for OCR (max dimension 2048px)
            max_dim = 2048
            if max(img.width, img.height) > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
            output_io = io.BytesIO()
            img.save(output_io, format="JPEG", quality=92, optimize=True)
            processed_bytes = output_io.getvalue()
            mime_type = "image/jpeg"
        except Exception as img_err:
            print(f"Image preprocessing note: {img_err}")
            processed_bytes = image_bytes

    b64_image = base64.b64encode(processed_bytes).decode('utf-8')

    # Build product names list for local cross-reference
    product_names = [p.get('name', '') for p in products] if products else []
    product_list_str = ", ".join(product_names[:30]) if product_names else "No local database available"

    prompt = f"""You are AgriSense, an expert agricultural, seed, crop input, and food product identification AI.

Analyze this photo carefully. Perform step-by-step visual parsing:
1. OCR Step: Read ALL visible text from the photo, including brand names, product titles, slogans, bullet points, certification logos (e.g. USDA ORGANIC, India Organic), and ingredients.
2. Search & Identification Step: Match the item, brand logo (e.g. EYWA Seeds & Exports, IFFCO, Bayer), windmill/graphic illustrations, and text details to identify the product accurately.

Provide your analysis as a JSON object with these exact fields:
{{
    "product_name": "Full product name as written on the label (e.g. EYWA Sunflower Seeds, Neem Shield, etc.)",
    "brand": "Manufacturer or Brand name (e.g. EYWA Seeds & Exports, IFFCO, Bayer, etc.)",
    "active_ingredient": "Active ingredient / seed variety / nutritional highlights / key contents",
    "type": "seeds/organic product/pesticide/fertilizer/herbicide/fungicide/insecticide/plant growth regulator/bio-fertilizer",
    "target_pests": ["target pests/diseases OR key health benefits / nutritional highlights"],
    "suitable_crops": ["suitable crops / consumption guidelines / target crops"],
    "dosage": "Recommended dosage / seed sowing rate / usage directions",
    "precautions": "Key safety precautions / storage instructions",
    "confidence": 92,
    "identification_notes": "Detailed visual observations explaining how you identified this product (logos, text, color, packaging)"
}}

Known products in our local database for cross-reference: {product_list_str}

IMPORTANT:
- Read all text accurately from the photo (e.g. EYWA SEEDS & EXPORTS, SUNFLOWER SEEDS, USDA ORGANIC, BETTER EPIDERMAL HEALTH, Vitamin E).
- If it is a seed packet, organic produce, or food item, set type to 'seeds' or 'organic product' and fill nutritional/health benefits into target_pests or usage fields.
- Set confidence between 85% and 98% if readable.
- Return ONLY the JSON object, no markdown codeblocks or extra text."""

    # ─── OPTION 1: Google Search Grounding Tool Config ───
    config = None
    try:
        config = types.GenerateContentConfig(
            tools=[{"google_search": {}}],
            temperature=0.2
        )
    except Exception as cfg_err:
        print(f"Search grounding config fallback: {cfg_err}")

    models_to_try = ['gemini-flash-latest', 'gemini-pro-latest', 'gemma-4-26b-a4b-it', 'gemini-3.6-flash', 'gemini-3.5-flash']
    response = None

    for model_name in models_to_try:
        try:
            contents_payload = [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_image
                            }
                        }
                    ]
                }
            ]
            
            if config:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents_payload,
                    config=config
                )
            else:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents_payload
                )

            if response and response.text:
                break
        except Exception as e:
            print(f"Gemini model {model_name} failed: {e}")
            continue

    if not response or not response.text:
        return None

    # Parse JSON from response (handle markdown code blocks)
    response_text = response.text.strip()
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        json_lines = [l for l in lines if not l.startswith("```")]
        response_text = "\n".join(json_lines)

    try:
        ai_result = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            ai_result = json.loads(json_match.group())
        else:
            return None

    # Cross-reference with local database
    local_match = None
    local_score = 0
    if HAS_RAPIDFUZZ and products and ai_result.get("product_name"):
        names = [f"{p['name']} {p.get('brand', '')} {p.get('active_ingredient', '')}" for p in products]
        match_result = process.extractOne(ai_result["product_name"], names, scorer=fuzz.token_set_ratio)
        if match_result and match_result[1] > 50:
            local_match = products[match_result[2]]
            local_score = match_result[1]

    # Build matched_product from AI result
    matched_product = {
        "name": ai_result.get("product_name", "Unknown Product"),
        "brand": ai_result.get("brand", "Unknown Brand"),
        "active_ingredient": ai_result.get("active_ingredient", "Not identified"),
        "type": ai_result.get("type", "agricultural product"),
        "target_pests": ai_result.get("target_pests", []),
        "suitable_crops": ai_result.get("suitable_crops", []),
        "dosage": ai_result.get("dosage", "See label for dosage"),
        "precautions": ai_result.get("precautions", "Follow safety guidelines on label"),
        "usage_notes": ai_result.get("identification_notes", "")
    }

    # If we found a strong local match, merge the local data for completeness
    if local_match and local_score > 70:
        for key in ['dosage', 'precautions', 'usage_notes', 'suitable_crops', 'target_pests']:
            if local_match.get(key) and not matched_product.get(key):
                matched_product[key] = local_match[key]

    confidence = ai_result.get("confidence", 75)

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

            for summary_model in ['gemini-flash-latest', 'gemini-pro-latest', 'gemma-4-26b-a4b-it', 'gemini-3.6-flash']:
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
