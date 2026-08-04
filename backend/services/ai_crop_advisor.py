import os
import json
import re
import base64
from typing import Dict, Any, List, Optional

try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

from services.regional_crop_lookup import lookup_district_crops, load_agro_zones

# ─────────────────────────────────────────────────────────────────────────────
# Region Isolation Validation Rules
# ─────────────────────────────────────────────────────────────────────────────
REGION_FORBIDDEN_KEYWORDS: Dict[str, List[str]] = {
    "surat": ["kutch", "kachchh", "saurashtra", "north gujarat", "arid soil", "desert soil", "deesa", "bhuj", "isabgol", "kharek", "porbandar", "rajkot", "jamnagar"],
    "south gujarat": ["kutch", "kachchh", "saurashtra", "north gujarat", "arid soil", "desert soil", "deesa", "bhuj", "isabgol", "porbandar"],
    "navsari": ["kutch", "kachchh", "saurashtra", "north gujarat", "arid soil", "desert soil", "deesa", "bhuj", "porbandar", "rajkot"],
    "valsad": ["kutch", "kachchh", "saurashtra", "north gujarat", "arid soil", "desert soil", "deesa", "bhuj", "porbandar"],
    "bharuch": ["kutch", "kachchh", "saurashtra", "north gujarat", "arid soil", "desert soil", "porbandar", "rajkot"],
    "kutch": ["surat", "south gujarat", "heavy rainfall zone", "vertisol", "ukai canal", "bardoli", "navsari", "porbandar"],
    "kachchh": ["surat", "south gujarat", "heavy rainfall zone", "vertisol", "ukai canal", "bardoli", "navsari"],
    "bhuj": ["surat", "south gujarat", "heavy rainfall zone", "vertisol", "ukai canal", "bardoli", "navsari"],
    "rajkot": ["surat", "south gujarat heavy rainfall zone", "deesa potato hub", "ukai canal", "navsari", "banaskantha"],
    "saurashtra": ["surat", "south gujarat heavy rainfall zone", "deesa potato hub", "navsari", "banaskantha"],
    "anand": ["kutch arid", "saurashtra dry zone", "surat heavy rainfall zone", "porbandar", "deesa potato hub"],
    "vadodara": ["kutch arid", "saurashtra dry zone", "surat heavy rainfall zone", "porbandar"],
    "ahmedabad": ["kutch arid", "south gujarat heavy rainfall zone", "porbandar", "deesa potato hub"],
    "porbandar": ["deesa", "banaskantha", "north gujarat", "kutch desert", "surat heavy rainfall", "navsari", "ukai canal", "south gujarat heavy rainfall", "isabgol"],
    "bhavnagar": ["deesa", "banaskantha", "north gujarat arid", "kutch desert", "surat heavy rainfall", "navsari", "isabgol"],
    "amreli": ["deesa", "banaskantha", "north gujarat arid", "kutch desert", "surat heavy rainfall", "navsari", "isabgol"],
    "surendranagar": ["deesa potato hub", "surat heavy rainfall", "navsari", "south gujarat"],
    "jamnagar": ["deesa potato hub", "surat heavy rainfall", "navsari", "banaskantha", "south gujarat"],
    "morbi": ["deesa potato hub", "surat heavy rainfall", "navsari", "south gujarat"],
    "mehsana": ["surat heavy rainfall", "navsari", "saurashtra", "porbandar", "kutch desert"],
    "gandhinagar": ["kutch arid", "saurashtra dry", "porbandar", "south gujarat heavy rainfall"],
    "dahod": ["kutch", "saurashtra", "porbandar", "south gujarat coastal", "navsari"],
    "narmada": ["kutch", "saurashtra", "porbandar", "north gujarat arid", "deesa"],
    "tapi": ["kutch", "saurashtra", "porbandar", "north gujarat arid", "deesa"]
}

def validate_region_isolation(advice: Dict[str, Any], target_location: str) -> tuple[bool, str, str]:
    """
    Validation Guard: Scans generated AI JSON fields for foreign region keywords.
    Returns (is_valid, matched_keyword, field_name).
    """
    loc_lower = target_location.lower()
    forbidden: List[str] = []

    for reg_key, words in REGION_FORBIDDEN_KEYWORDS.items():
        if reg_key in loc_lower:
            forbidden.extend(words)

    if not forbidden:
        # Default fallback forbidden list if location is Surat/South Gujarat
        if "surat" in loc_lower or "south" in loc_lower:
            forbidden = ["kutch", "kachchh", "saurashtra", "north gujarat", "arid soil", "isabgol"]

    if not forbidden:
        return True, "", ""

    # Flatten text in advice dict to search
    text_to_check: List[tuple[str, str]] = []

    if isinstance(advice.get("agro_climatic_zone"), str):
        text_to_check.append(("agro_climatic_zone", advice["agro_climatic_zone"]))

    if isinstance(advice.get("regional_market_notes"), str):
        text_to_check.append(("regional_market_notes", advice["regional_market_notes"]))

    if isinstance(advice.get("recommended_crops"), list):
        for idx, crop in enumerate(advice["recommended_crops"]):
            if isinstance(crop, dict):
                reason = crop.get("suitability_reason", "")
                text_to_check.append((f"recommended_crops[{idx}].suitability_reason", reason))

    if isinstance(advice.get("soil_health_assessment"), dict):
        for field, val in advice["soil_health_assessment"].items():
            if isinstance(val, str):
                text_to_check.append((f"soil_health_assessment.{field}", val))

    for field_name, text in text_to_check:
        t_lower = text.lower()
        for kw in forbidden:
            # Check for forbidden keyword as word match
            if re.search(r'\b' + re.escape(kw) + r'\b', t_lower):
                print(f"[VALIDATION GUARD FAILURE] Detected forbidden region '{kw}' in field '{field_name}' for target location '{target_location}'")
                return False, kw, field_name

    return True, "", ""


def detect_default_soil_type(location_name: str) -> str:
    """Auto-detect soil type using gujarat_agro_zones.json dataset."""
    db_match = lookup_district_crops(location_name, "Gujarat", display_name=location_name)
    if db_match and db_match.get("soil"):
        return db_match["soil"]
    return "Medium Black Cotton Soil (Auto-detected)"


def _get_soil_key(soil_type: str) -> str:
    """Map a soil type string to the crop pool key."""
    s = (soil_type or "").lower()
    if "deep black" in s or "clay" in s or "vertisol" in s or ("black" in s and "sandy" not in s) or "kaali" in s:
        return "black cotton"
    if "arid" in s or "desert" in s or "sukhi" in s or "retaad" in s:
        return "sandy arid"
    if "coastal sandy" in s:
        return "coastal sandy"
    if "later" in s:
        return "laterite"
    if "alluvial" in s or "kamp" in s:
        return "alluvial"
    if "sandy" in s or "goradu" in s or "retaal" in s:
        return "sandy loam"
    if "red" in s or "lal" in s:
        return "red loamy"
    return "black cotton"


def generate_geographical_crop_advice(
    location_name: str,
    soil_type: str,
    N: float,
    P: float,
    K: float,
    ph: float,
    temperature: float,
    humidity: float,
    rainfall: float,
    seasonal_weather: Optional[Dict[str, Any]] = None,
    lang: str = "en",
    api_key: Optional[str] = None,
    regional_crops: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Grounded Geographical AI Crop Recommendation Engine with Validation Guard.
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")

    # Step 1: Resolve location & agro-climatic zone data
    if not regional_crops or not regional_crops.get("soil_type_regional"):
        db_data = lookup_district_crops(location_name, "Gujarat", display_name=location_name)
        if db_data:
            regional_crops = db_data

    # Determine if Auto-Detect mode is active
    is_auto_detect = (not soil_type or soil_type == "Auto-Detect")

    # Use dataset soil if Auto-Detect
    if is_auto_detect:
        if regional_crops and regional_crops.get("soil_type_regional"):
            soil_type = regional_crops["soil_type_regional"]
        else:
            soil_type = detect_default_soil_type(location_name)

    # Use dataset NPK baseline:
    # In Auto-Detect mode: ALWAYS override with zone-accurate values (not stale mobile defaults)
    # In manual mode: only override if user input is 0 or negative
    typical_npk = {}
    if regional_crops:
        typical_npk = regional_crops.get("typical_npk", {})
        if is_auto_detect:
            # Auto-Detect: always use zone-accurate NPK (user didn't manually enter soil-test data)
            if typical_npk.get("N"):
                N = typical_npk["N"]
            if typical_npk.get("P"):
                P = typical_npk["P"]
            if typical_npk.get("K"):
                K = typical_npk["K"]
            if typical_npk.get("pH"):
                ph = typical_npk["pH"]
            print(f"[AUTO-DETECT NPK] Overriding with zone baseline: N={N}, P={P}, K={K}, pH={ph}")
        else:
            # Manual soil selection: only fill if user left values empty/zero
            if N <= 0 and typical_npk.get("N"):
                N = typical_npk["N"]
            if P <= 0 and typical_npk.get("P"):
                P = typical_npk["P"]
            if K <= 0 and typical_npk.get("K"):
                K = typical_npk["K"]
            if ph <= 0 and typical_npk.get("pH"):
                ph = typical_npk["pH"]

    zone_name = regional_crops.get("agro_climatic_zone_name", "Local Agro-Climatic Zone") if regional_crops else "Local Agro-Climatic Zone"
    avg_rainfall = regional_crops.get("avg_annual_rainfall_mm", 800) if regional_crops else 800

    # Build verified crops list
    verified_crops_str = ""
    if regional_crops and regional_crops.get("kharif_crops"):
        k_list = ", ".join(regional_crops.get("kharif_crops", [])[:6])
        r_list = ", ".join(regional_crops.get("rabi_crops", [])[:5])
        p_list = ", ".join(regional_crops.get("perennial_crops", [])[:4])
        apmc_note = regional_crops.get("apmc_note", "")
        verified_crops_str = f"""
VERIFIED GROUNDED CROPS FOR THIS ZONE ({zone_name}):
- Kharif Crops ACTUALLY GROWN: {k_list}
- Rabi Crops ACTUALLY GROWN: {r_list}
- Perennial / Horticulture Crops: {p_list}
- APMC Market Insight: {apmc_note}"""

    # Language instruction
    lang_instructions = {
        "gu": "CRITICAL LANGUAGE REQUIREMENT: You MUST respond ENTIRELY in GUJARATI (ગુજરાતી). Write ALL crop names (e.g. મગફળી, કપાસ, ડાંગર, બાજરી, ઘઉં, તલ), varieties, suitability reasons, fertilizer schedule steps, and intercropping tips in fluent, natural Gujarati. DO NOT use English for crop names or reasons.",
        "hi": "CRITICAL LANGUAGE REQUIREMENT: You MUST respond ENTIRELY in HINDI (हिंदी). Write ALL crop names (e.g. मूंगफली, कपास, धान, बाजरा, गेहूं), varieties, suitability reasons, and fertilizer schedules in fluent, natural Hindi. DO NOT use English.",
        "en": "Respond in English using practical Indian agricultural terminology."
    }.get(lang, "Respond in English.")

    def construct_prompt(retry_warning: str = "") -> str:
        return f"""{retry_warning}You are AgriSense AI, a Senior Agronomist specializing in Indian Agro-Climatic Zones.

GROUNDED REGIONAL & FARMER DATA:
- Location / District: {location_name}
- Agro-Climatic Zone: {zone_name}
- Average Annual Rainfall: {avg_rainfall} mm
- Actual Soil Type: {soil_type}
- Farmer Soil Test Values: Nitrogen (N) = {N} kg/ha, Phosphorus (P) = {P} kg/ha, Potassium (K) = {K} kg/ha, Soil pH = {ph}
- Typical Zone Baseline Soil Values: N={typical_npk.get('N', 120)} kg/ha, P={typical_npk.get('P', 35)} kg/ha, K={typical_npk.get('K', 200)} kg/ha, pH={typical_npk.get('pH', 7.5)}
- Current Climate Outlook: Temperature = {temperature}°C, Humidity = {humidity}%, Season Rainfall = {rainfall}mm.{verified_crops_str}

LANGUAGE REQUIREMENT: {lang_instructions}

STRICT REGION ISOLATION DIRECTIVE:
- Focus EXCLUSIVELY on {location_name} and the {zone_name}.
- ABSOLUTELY DO NOT reference, cite, or mention other outside agricultural regions (such as Kutch, Saurashtra, North Gujarat, Vidarbha, or Malwa) unless {location_name} IS explicitly in that exact region.
- ONLY recommend crops appropriate to {soil_type} and {avg_rainfall}mm annual rainfall.

STRICT CONFLICT DETECTION DIRECTIVE:
- Under "soil_health_assessment", evaluate if the farmer's soil inputs (N={N}, P={P}, K={K}, pH={ph}) conflict with the known zone baseline (N={typical_npk.get('N')}, P={typical_npk.get('P')}, K={typical_npk.get('K')}, pH={typical_npk.get('pH')}).
- If there is a conflict (e.g., severe N deficiency or acidic pH in an alkaline clay zone), EXPLICITLY flag the conflict in nutrient_status or ph_evaluation.

RECOMMENDATION REQUIREMENTS:
- Recommend EXACTLY 5 DIFFERENT, DIVERSE crops best suited to {location_name} ({zone_name}).
- Prioritize crops from the VERIFIED GROUNDED CROPS list above.

Output ONLY a JSON object with this exact structure:
{{
    "detected_soil_type": "{soil_type}",
    "agro_climatic_zone": "{zone_name}",
    "recommended_crops": [
        {{
            "crop_name": "Crop Name",
            "recommended_variety": "High-yielding regional variety",
            "suitability_score": 95,
            "suitability_reason": "2-sentence specific reason why this crop suits {location_name}'s {soil_type} and {avg_rainfall}mm rainfall",
            "expected_yield_per_acre": "Yield/Acre",
            "season_duration": "Duration in Days/Months",
            "water_requirement": "High / Medium / Low"
        }}
    ],
    "soil_health_assessment": {{
        "nutrient_status": "Analysis of N={N}, P={P}, K={K}. Explicitly flag any conflict with zone baseline N={typical_npk.get('N')}, P={typical_npk.get('P')}, K={typical_npk.get('K')}.",
        "ph_evaluation": "Analysis of pH {ph}. Flag any conflict if pH deviates from zone norm pH={typical_npk.get('pH')}.",
        "organic_carbon_advice": "Organic matter and manure advice for {soil_type}"
    }},
    "custom_fertilizer_plan": {{
        "basal_dose": "Basal dose per acre based on actual NPK values",
        "top_dressing_stage1": "30-day stage dose",
        "top_dressing_stage2": "60-day flowering dose"
    }},
    "intercropping_strategy": {{
        "suggested_intercrop": "Best intercrop pair for primary crop in {soil_type}",
        "benefits": "Agronomic & economic benefits"
    }},
    "regional_market_notes": "APMC market insight and harvest window for {location_name}"
}}

CRITICAL: Return ONLY raw JSON. recommended_crops MUST contain exactly 5 crops."""

    result = None
    if api_key and HAS_GEMINI:
        try:
            client = genai.Client(api_key=api_key)
            models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-flash-latest']

            for attempt in range(2):  # Main attempt + 1 Validation Retry
                retry_warn = ""
                if attempt == 1:
                    retry_warn = f"CRITICAL RE-GEN WARNING: Your previous output contained a region mismatch hallucination! DO NOT mention outside regions. Focus ONLY on {location_name} and {zone_name}.\n\n"

                prompt_str = construct_prompt(retry_warn)

                for model_name in models_to_try:
                    try:
                        res = client.models.generate_content(
                            model=model_name,
                            contents=prompt_str,
                            config=types.GenerateContentConfig(temperature=0.2)
                        )
                        if res and res.text:
                            text_resp = res.text.strip()
                            if text_resp.startswith("```"):
                                lines = text_resp.split("\n")
                                text_resp = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
                            parsed = json.loads(text_resp)

                            # Validate Region Isolation Guard
                            is_valid, bad_kw, bad_field = validate_region_isolation(parsed, location_name)
                            if is_valid or attempt == 1:
                                result = parsed
                                break
                    except Exception as e:
                        print(f"Gemini generation error ({model_name}): {e}")
                        continue
        except Exception as global_err:
            print(f"Global Gemini advisor error: {global_err}")

    # Fallback to rule-based system if Gemini unavailable or failed
    if not result:
        result = _build_smart_fallback(location_name, soil_type, N, P, K, ph, temperature, rainfall, lang, regional_crops)

    # Post-process translate crop names and durations into Gujarati / Hindi
    return translate_advice_to_lang(result, lang)


def translate_advice_to_lang(advice: Dict[str, Any], lang: str) -> Dict[str, Any]:
    """Translate key advice fields into Gujarati or Hindi. Returns advice unchanged for English."""
    if lang not in ('gu', 'hi') or not isinstance(advice, dict):
        return advice

    # ── Label maps ──────────────────────────────────────────────────────────
    water_map = {
        'gu': {'Low': 'ઓછું', 'Medium': 'મધ્યમ', 'High': 'વધારે',
               'Very High': 'ઘણું વધારે', 'low': 'ઓછું', 'medium': 'મધ્યમ', 'high': 'વધારે'},
        'hi': {'Low': 'कम', 'Medium': 'मध्यम', 'High': 'अधिक',
               'Very High': 'बहुत अधिक', 'low': 'कम', 'medium': 'मध्यम', 'high': 'अधिक'},
    }
    season_map = {
        'gu': {'Kharif': 'ખરીફ', 'Rabi': 'રવિ', 'Summer': 'ઉનાળો', 'Zaid': 'ઝાઇદ',
               'kharif': 'ખરીફ', 'rabi': 'રવિ', 'summer': 'ઉનાળો'},
        'hi': {'Kharif': 'खरीफ', 'Rabi': 'रबी', 'Summer': 'ग्रीष्म', 'Zaid': 'जायद',
               'kharif': 'खरीफ', 'rabi': 'रबी', 'summer': 'ग्रीष्म'},
    }
    crop_name_map = {
        'gu': {
            'Groundnut': 'મગફળી', 'Cotton': 'કપાસ', 'Wheat': 'ઘઉં', 'Rice': 'ડાંગર',
            'Bajra': 'બાજરી', 'Maize': 'મકાઈ', 'Sugarcane': 'શેરડી', 'Soybean': 'સોયાબીન',
            'Onion': 'ડુંગળી', 'Potato': 'બટાકા', 'Tomato': 'ટામેટા', 'Banana': 'કેળા',
            'Mango': 'કેરી', 'Cumin': 'જીરૂ', 'Fennel': 'વરિયાળી', 'Garlic': 'લસણ',
            'Mustard': 'રાઈ', 'Castor': 'એરંડા', 'Sesame': 'તલ', 'Moong': 'મગ',
            'Tur': 'તુવેર', 'Chickpea': 'ચણા', 'Lentil': 'મસૂર', 'Jowar': 'જુવાર',
        },
        'hi': {
            'Groundnut': 'मूंगफली', 'Cotton': 'कपास', 'Wheat': 'गेहूं', 'Rice': 'चावल',
            'Bajra': 'बाजरा', 'Maize': 'मक्का', 'Sugarcane': 'गन्ना', 'Soybean': 'सोयाबीन',
            'Onion': 'प्याज', 'Potato': 'आलू', 'Tomato': 'टमाटर', 'Banana': 'केला',
            'Mango': 'आम', 'Cumin': 'जीरा', 'Fennel': 'सौंफ', 'Garlic': 'लहसुन',
            'Mustard': 'सरसों', 'Castor': 'अरंडी', 'Sesame': 'तिल', 'Moong': 'मूंग',
            'Tur': 'अरहर', 'Chickpea': 'चना', 'Lentil': 'मसूर', 'Jowar': 'ज्वार',
        },
    }

    w_map = water_map.get(lang, {})
    s_map = season_map.get(lang, {})
    c_map = crop_name_map.get(lang, {})

    # ── Translate recommended_crops list ────────────────────────────────────
    translated_crops = []
    for crop in advice.get('recommended_crops', []):
        c = dict(crop)
        # Translate crop name
        c['crop_name'] = c_map.get(c.get('crop_name', ''), c.get('crop_name', ''))
        # Translate water requirement
        wr = c.get('water_requirement', '')
        c['water_requirement'] = w_map.get(wr, wr)
        # Translate season hints inside duration/reason if present
        for season_en, season_tr in s_map.items():
            if 'suitability_reason' in c:
                c['suitability_reason'] = c['suitability_reason'].replace(season_en, season_tr)
        translated_crops.append(c)

    advice['recommended_crops'] = translated_crops

    # ── Translate detected_soil_type label ──────────────────────────────────
    soil_tr = {
        'gu': {'Loamy Soil': 'ગોરાડુ જમીન', 'Black Cotton Soil': 'કાળી જમીન',
               'Sandy Soil': 'રેતાળ જમીન', 'Alluvial Soil': 'કાંપ જમીન',
               'Red Soil': 'લાલ જમીન', 'Clay Soil': 'ચીકણી જમીન'},
        'hi': {'Loamy Soil': 'दोमट मिट्टी', 'Black Cotton Soil': 'काली मिट्टी',
               'Sandy Soil': 'रेतीली मिट्टी', 'Alluvial Soil': 'जलोढ़ मिट्टी',
               'Red Soil': 'लाल मिट्टी', 'Clay Soil': 'चिकनी मिट्टी'},
    }
    soil_label = advice.get('detected_soil_type', '')
    advice['detected_soil_type'] = soil_tr.get(lang, {}).get(soil_label, soil_label)

    return advice



def _build_smart_fallback(
    location: str, soil_type: str, N: float, P: float, K: float,
    ph: float, temp: float, rain: float, lang: str,
    regional_crops: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Smart rule-based fallback grounded in gujarat_agro_zones.json."""
    zone_name = regional_crops.get("agro_climatic_zone_name", "Local Zone") if regional_crops else "Local Zone"
    avg_rain = regional_crops.get("avg_annual_rainfall_mm", 800) if regional_crops else 800
    typical_npk = regional_crops.get("typical_npk", {}) if regional_crops else {}

    crops_grounded = []
    if regional_crops and regional_crops.get("suitable_crops_full"):
        for c in regional_crops["suitable_crops_full"]:
            crops_grounded.append({
                "crop_name": c["crop_name"],
                "recommended_variety": c.get("recommended_variety", "High Yield Variety"),
                "suitability_score": c.get("suitability_score", 90),
                "suitability_reason": c.get("suitability_reason", f"Grounded crop for {location}'s {soil_type}."),
                "expected_yield_per_acre": c.get("expected_yield_per_acre", "12-15 Quintal/Acre"),
                "season_duration": c.get("season_duration", "110-120 Days"),
                "water_requirement": c.get("water_requirement", "Medium")
            })

    if len(crops_grounded) < 5:
        # Fill from default pools
        crops_grounded.append({
            "crop_name": "Wheat", "recommended_variety": "GW-322 / Lok-1",
            "suitability_score": 85, "suitability_reason": f"Reliable rabi crop suited to {soil_type}.",
            "expected_yield_per_acre": "18-24 Quintal/Acre", "season_duration": "115-125 Days", "water_requirement": "Medium"
        })

    # Build conflict text if farmer NPK differs significantly from zone norm
    npk_conflict_text = f"Nutrient status for N={N}, P={P}, K={K}."
    if typical_npk:
        typ_n = typical_npk.get("N", 120)
        if N < typ_n * 0.6:
            npk_conflict_text += f" CONFLICT FLAGGED: Farmer N={N} kg/ha is significantly lower than zone average N={typ_n} kg/ha. Nitrogen supplementation required."
        elif N > typ_n * 1.5:
            npk_conflict_text += f" CONFLICT FLAGGED: Farmer N={N} kg/ha exceeds typical zone norm N={typ_n} kg/ha. Avoid excessive urea."

    ph_conflict_text = f"pH value {ph} analyzed."
    if typical_npk.get("pH"):
        typ_ph = typical_npk["pH"]
        if abs(ph - typ_ph) > 0.8:
            ph_conflict_text += f" CONFLICT FLAGGED: Soil pH {ph} deviates from typical zone baseline pH {typ_ph}."

    return {
        "detected_soil_type": soil_type,
        "agro_climatic_zone": zone_name,
        "recommended_crops": crops_grounded[:5],
        "soil_health_assessment": {
            "nutrient_status": npk_conflict_text,
            "ph_evaluation": ph_conflict_text,
            "organic_carbon_advice": f"Apply 3-4 tonnes FYM/compost per acre to improve organic matter in {soil_type}."
        },
        "custom_fertilizer_plan": {
            "basal_dose": f"50 kg DAP + 25 kg MOP per acre before sowing for {soil_type}.",
            "top_dressing_stage1": "30-35 kg Urea per acre at 30 days after sowing.",
            "top_dressing_stage2": "25 kg Urea per acre at flowering stage."
        },
        "intercropping_strategy": {
            "suggested_intercrop": f"Pulse intercropping suited to {soil_type}.",
            "benefits": "Fixes atmospheric nitrogen and improves overall soil organic carbon."
        },
        "regional_market_notes": regional_crops.get("apmc_note", f"High market demand in local APMC for {location}.") if regional_crops else f"High demand in local APMC for {location}."
    }
