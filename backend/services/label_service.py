import os
import json
import io
from typing import Dict, Any, Optional
from PIL import Image

try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

try:
    from google import genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

def load_products_db() -> list:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(os.path.dirname(script_dir), 'data', 'products_db.json')
    if os.path.exists(db_path):
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def scan_and_interpret_label(image_bytes: Optional[bytes] = None, text_input: Optional[str] = None, lang: str = "en") -> Dict[str, Any]:
    raw_ocr_text = ""
    
    if image_bytes:
        try:
            image = Image.open(io.BytesIO(image_bytes))
            if HAS_TESSERACT:
                try:
                    raw_ocr_text = pytesseract.image_to_string(image)
                except Exception as e:
                    print(f"Label OCR error: {e}")
                    raw_ocr_text = ""
        except Exception as e:
            print(f"Label image load error: {e}")

    if not raw_ocr_text and text_input:
        raw_ocr_text = text_input

    if not raw_ocr_text:
        # Default mock scan input for demonstration
        raw_ocr_text = "Neem Shield Bio Pesticide Azadirachtin 10000 PPM 1% EC GreenAgri Aphids Thrips Whiteflies"

    products = load_products_db()
    matched_product = None
    best_score = 0.0

    # Match raw OCR text against products in database using rapidfuzz or string matching
    if HAS_RAPIDFUZZ and products:
        names = [f"{p['name']} {p['brand']} {p['active_ingredient']} {' '.join(p['target_pests'])}" for p in products]
        result = process.extractOne(raw_ocr_text, names, scorer=fuzz.token_set_ratio)
        if result:
            matched_idx = result[2]
            best_score = result[1]
            if best_score > 35:
                matched_product = products[matched_idx]
    else:
        # Fallback simple search
        text_lower = raw_ocr_text.lower()
        for p in products:
            if p['name'].lower() in text_lower or p['active_ingredient'].lower() in text_lower:
                matched_product = p
                best_score = 80.0
                break

    if not matched_product and products:
        matched_product = products[0] # Default fallback match
        best_score = 50.0

    # Generate grounded summary via Gemini API or local template
    summary = generate_grounded_summary(matched_product, raw_ocr_text, lang)

    return {
        "raw_ocr_text": raw_ocr_text[:200],
        "match_confidence": round(best_score, 1),
        "matched_product": matched_product,
        "ai_summary": summary,
        "disclaimer": "⚠️ SAFETY DISCLAIMER: This AI analysis is based on official label details. Always verify dosage with your local Krishi Vigyan Kendra (KVK), agriculture officer, or package label before field application."
    }

def generate_grounded_summary(product: Dict[str, Any], raw_ocr: str, lang: str = "en") -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if api_key and HAS_GEMINI:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""
            You are AgriSense, an expert agricultural assistant in India.
            A farmer scanned a product label with OCR text: "{raw_ocr}".
            It was matched to the following verified Database Record:
            - Product Name: {product.get('name')}
            - Type: {product.get('type')}
            - Active Ingredient: {product.get('active_ingredient')}
            - Target Pests/Diseases: {', '.join(product.get('target_pests', []))}
            - Suitable Crops: {', '.join(product.get('suitable_crops', []))}
            - Recommended Dosage: {product.get('dosage')}
            - Usage Notes: {product.get('usage_notes')}
            - Safety Precautions: {product.get('precautions')}

            Provide a clear, simple, 4-bullet farmer summary in language '{lang}' (en = English, gu = Gujarati, hi = Hindi).
            STRICT REQUIREMENT: Rely ONLY on the provided Database Record facts. Do NOT invent new dosage numbers or chemical claims. Keep language easy for a smallholder farmer to understand.
            """
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Gemini API call failed: {e}")

    # Smart local grounded summary fallback if Gemini API key is missing or call fails
    if lang == "gu":
        return f"""
        📌 **ઉત્પાદન વિગત**: {product.get('name')} ({product.get('brand')})
        🌱 **ઉપયોગી પાક**: {', '.join(product.get('suitable_crops', []))}
        🐛 **નિયંત્રિત જીવાત/રોગ**: {', '.join(product.get('target_pests', [])) if product.get('target_pests') else 'પોષણ પૂર્તિ (ખાતર)'}
        💧 **ભલામણ કરેલ પ્રમાણ**: {product.get('dosage')}
        ⚠️ **સાવચેતી**: {product.get('precautions')}
        """.strip()
    elif lang == "hi":
        return f"""
        📌 **उत्पाद विवरण**: {product.get('name')} ({product.get('brand')})
        🌱 **उपयुक्त फसलें**: {', '.join(product.get('suitable_crops', []))}
        🐛 **नियंत्रित कीट/रोग**: {', '.join(product.get('target_pests', [])) if product.get('target_pests') else 'पोषण पूर्ति (उर्वरक)'}
        💧 **अनुशंसित खुराक**: {product.get('dosage')}
        ⚠️ **सावधानी**: {product.get('precautions')}
        """.strip()
    else:
        return f"""
        📌 **Product Summary**: {product.get('name')} ({product.get('brand')})
        🌱 **Target Crops**: {', '.join(product.get('suitable_crops', []))}
        🐛 **Target Pests/Diseases**: {', '.join(product.get('target_pests', [])) if product.get('target_pests') else 'Nutrient Supplement'}
        💧 **Recommended Dosage**: {product.get('dosage')}
        ⚠️ **Safety Note**: {product.get('precautions')}
        """.strip()
