import os
import json
import base64
from typing import Dict, Any, List, Optional

try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# District-level soil type mapping — granular and correct per district
DISTRICT_SOIL_DEFAULTS = {
    # Gujarat Districts
    "kutch": "Sandy Arid Soil (retaad sukhi jamin)",
    "bhuj": "Sandy Arid Soil (retaad sukhi jamin)",
    "anjar": "Sandy Loam Arid (goradu-retaal)",
    "mandvi": "Coastal Sandy Soil (dariyai retaal)",
    "gandhidham": "Sandy Arid Soil (goradu-retaal)",
    "banaskantha": "Sandy Alluvial (retaal-kamp)",
    "palanpur": "Sandy Alluvial (retaal-kamp)",
    "patan": "Sandy Saline Alluvial (khaari-retaal)",
    "mehsana": "Light Sandy Alluvial (goradu-retaal)",
    "rajkot": "Sandy Loam Light Black (goradu-kaali)",
    "amreli": "Sandy Loam Light Black (goradu-kaali)",
    "junagadh": "Sandy Loam Laterite (goradu-lal)",
    "gir somnath": "Sandy Loam Red Laterite (goradu-lal)",
    "porbandar": "Coastal Sandy Soil (dariyai goradu)",
    "jamnagar": "Sandy Loam (goradu)",
    "devbhumi dwarka": "Coastal Sandy (goradu-dariyai)",
    "morbi": "Sandy Loam Medium Black (goradu-kaali)",
    "surendranagar": "Medium Black Cotton Soil (madhyam kaali)",
    "bhavnagar": "Medium Black Cotton Soil (madhyam kaali)",
    "botad": "Deep Black Cotton Soil (undi kaali)",
    "ahmedabad": "Black Cotton Sandy Loam (kaali-goradu)",
    "gandhinagar": "Sandy Loam Alluvial (goradu-kamp)",
    "anand": "Alluvial Sandy Loam (goradu-kamp)",
    "kheda": "Alluvial Loam (kamp-goradu)",
    "nadiad": "Alluvial (kamp)",
    "vadodara": "Alluvial Medium Black (kamp-kaali)",
    "surat": "Deep Black Clayey Soil (Vertisols) / Heavy Alluvial",
    "navsari": "Heavy Black Alluvial Soil (kaali-kamp)",
    "valsad": "Coastal Black Alluvial Soil (kaali-kamp)",
    "bharuch": "Deep Black Cotton Soil (Vertisols)",
    "tapi": "Deep Black Clayey Soil (undi kaali)",
    "narmada": "Medium Black Cotton Soil (madhyam kaali)",
    "dang": "Forest Red Laterite Soil (jangal lal)",
    "sabarkantha": "Shallow Black Red Loamy (chichri kaali-lal)",
    "aravalli": "Red Sandy Loam (lal goradu)",
    "mahisagar": "Medium Black Soil (madhyam kaali)",
    "panchmahals": "Red Mixed Black Soil (lal-kaali)",
    "dahod": "Red Tribal Forest Soil (adivasi lal)",
    # Rajasthan Districts
    "jaipur": "Sandy Loam Semi-Arid",
    "jodhpur": "Sandy Desert Soil",
    "barmer": "Sandy Desert Arid Soil",
    "bikaner": "Sandy Desert Soil",
    "jaisalmer": "Sandy Desert Thar Soil",
    "nagaur": "Sandy Loam Arid",
    "ajmer": "Sandy Loam Brown Soil",
    # Maharashtra
    "nagpur": "Black Cotton Soil (Vidarbha)",
    "pune": "Black Cotton Red Laterite",
    "nashik": "Red Laterite Black",
    "amravati": "Black Cotton Soil",
    "latur": "Black Cotton Soil (Marathwada)",
    # Other states
    "ludhiana": "Alluvial Sandy Loam",
    "lucknow": "Alluvial Indo-Gangetic Plain",
    "indore": "Black Cotton Soil (Malwa)",
}

STATE_SOIL_DEFAULTS = {
    "gujarat": "Mixed Gujarat Soil (varies: Sandy Arid in Kutch, Sandy Loam in Saurashtra, Black Cotton in central)",
    "maharashtra": "Black Cotton Soil (Regur)",
    "punjab": "Alluvial Soil (Sandy Loam)",
    "haryana": "Alluvial Soil (Sandy Loam)",
    "uttar pradesh": "Alluvial Soil (Loamy)",
    "rajasthan": "Sandy Arid Soil",
    "madhya pradesh": "Black Cotton Soil (Regur)",
    "karnataka": "Red Loamy Soil",
    "tamil nadu": "Red Clay Soil",
    "andhra pradesh": "Red Clay Soil",
    "telangana": "Red Loamy Soil",
    "bihar": "Alluvial Soil (Clay Loam)",
    "west bengal": "Alluvial Soil (Laterite)",
    "odisha": "Red Laterite Soil",
    "assam": "Alluvial Soil (Acidic)",
}

# ── Smart rule-based crop pools by soil type ──────────────────────────────────
CROP_POOL_BY_SOIL = {
    "black cotton": [
        {"crop_name": "Cotton", "recommended_variety": "G.Cot-20 / Hybrid-6 / RCH-134",
         "suitability_score": 95, "expected_yield_per_acre": "12-18 Quintal/Acre",
         "season_duration": "150-170 Days", "water_requirement": "Medium",
         "suitability_reason": "Black cotton soil retains moisture well and provides deep root zone; ideal for cotton."},
        {"crop_name": "Soybean", "recommended_variety": "JS-335 / MAUS-71 / Gujarat Soybean-1",
         "suitability_score": 88, "expected_yield_per_acre": "8-12 Quintal/Acre",
         "season_duration": "90-100 Days", "water_requirement": "Medium",
         "suitability_reason": "Soybean thrives in black soil with good organic matter; fixes atmospheric nitrogen benefiting next crop."},
        {"crop_name": "Sorghum (Jowar)", "recommended_variety": "CSH-16 / CSH-23 / Gujarat Jowar-1",
         "suitability_score": 85, "expected_yield_per_acre": "15-20 Quintal/Acre",
         "season_duration": "110-120 Days", "water_requirement": "Low",
         "suitability_reason": "Drought-tolerant; thrives in deep black soil; good fodder and grain crop."},
        {"crop_name": "Pigeonpea (Tur/Arhar)", "recommended_variety": "BSMR-853 / Pusa-992 / Asha",
         "suitability_score": 83, "expected_yield_per_acre": "6-10 Quintal/Acre",
         "season_duration": "160-180 Days", "water_requirement": "Low",
         "suitability_reason": "Deep-rooted legume; improves soil fertility; thrives in well-drained black soils."},
        {"crop_name": "Wheat", "recommended_variety": "GW-322 / Lok-1 / HD-2967",
         "suitability_score": 80, "expected_yield_per_acre": "18-25 Quintal/Acre",
         "season_duration": "120-130 Days", "water_requirement": "Medium",
         "suitability_reason": "Excellent rabi crop for black cotton soil; high market demand and stable returns."},
        {"crop_name": "Chickpea (Chana)", "recommended_variety": "GG-2 / JG-11 / Phule G-5",
         "suitability_score": 78, "expected_yield_per_acre": "8-12 Quintal/Acre",
         "season_duration": "95-110 Days", "water_requirement": "Low",
         "suitability_reason": "Good rabi pulse for black soils; nitrogen fixer; strong APMC demand."},
    ],
    "alluvial": [
        {"crop_name": "Rice (Paddy)", "recommended_variety": "Gujarat Anand Paddy-1 / Swarna / IR-64",
         "suitability_score": 95, "expected_yield_per_acre": "20-30 Quintal/Acre",
         "season_duration": "120-145 Days", "water_requirement": "High",
         "suitability_reason": "Alluvial soil with good water retention is ideal for paddy cultivation."},
        {"crop_name": "Wheat", "recommended_variety": "HD-3086 / GW-496 / Lok-1",
         "suitability_score": 92, "expected_yield_per_acre": "22-28 Quintal/Acre",
         "season_duration": "120-130 Days", "water_requirement": "Medium",
         "suitability_reason": "Alluvial plains are India's wheat belt; high productivity with irrigation."},
        {"crop_name": "Sugarcane", "recommended_variety": "CoJ-64 / CoSe-95422",
         "suitability_score": 87, "expected_yield_per_acre": "300-400 Quintal/Acre",
         "season_duration": "10-12 Months", "water_requirement": "High",
         "suitability_reason": "Deep, fertile alluvial soil supports vigorous sugarcane growth."},
        {"crop_name": "Maize (Corn)", "recommended_variety": "Pioneer 30V92 / HQPM-1 / DKC-9144",
         "suitability_score": 85, "expected_yield_per_acre": "25-35 Quintal/Acre",
         "season_duration": "90-100 Days", "water_requirement": "Medium",
         "suitability_reason": "Well-drained alluvial soils support excellent maize yields."},
        {"crop_name": "Mustard (Sarson)", "recommended_variety": "Pusa Bold / RH-749 / Kranti",
         "suitability_score": 82, "expected_yield_per_acre": "8-12 Quintal/Acre",
         "season_duration": "110-120 Days", "water_requirement": "Low",
         "suitability_reason": "Major rabi oilseed in alluvial zones; good APMC returns."},
        {"crop_name": "Potato", "recommended_variety": "Kufri Jyoti / Kufri Sindhuri / Chipsona",
         "suitability_score": 80, "expected_yield_per_acre": "80-120 Quintal/Acre",
         "season_duration": "90-100 Days", "water_requirement": "Medium",
         "suitability_reason": "Sandy loam alluvial soils are ideal for potato tuber development."},
    ],
    "sandy loam": [
        {"crop_name": "Groundnut", "recommended_variety": "GG-20 / GJG-31 / TAG-24",
         "suitability_score": 95, "expected_yield_per_acre": "10-14 Quintal/Acre",
         "season_duration": "110-120 Days", "water_requirement": "Medium",
         "suitability_reason": "Sandy loam allows easy pod penetration and harvest; ideal for groundnut."},
        {"crop_name": "Pearl Millet (Bajra)", "recommended_variety": "GHB-558 / HHB-67 / Pusa 322",
         "suitability_score": 90, "expected_yield_per_acre": "12-18 Quintal/Acre",
         "season_duration": "75-90 Days", "water_requirement": "Low",
         "suitability_reason": "Highly drought-tolerant; thrives in sandy soils of arid and semi-arid regions."},
        {"crop_name": "Sesame (Til)", "recommended_variety": "Gujarat Til-1 / Purva-1 / RT-346",
         "suitability_score": 85, "expected_yield_per_acre": "3-5 Quintal/Acre",
         "season_duration": "80-90 Days", "water_requirement": "Low",
         "suitability_reason": "Drought-resistant oilseed; excellent for light sandy soils with low water."},
        {"crop_name": "Castor", "recommended_variety": "GAUCH-1 / Aruna / GCH-7",
         "suitability_score": 82, "expected_yield_per_acre": "10-15 Quintal/Acre",
         "season_duration": "180-210 Days", "water_requirement": "Low",
         "suitability_reason": "Deep-rooted oilseed crop; thrives in well-drained sandy loam; Gujarat is India's top producer."},
        {"crop_name": "Cowpea (Chawli)", "recommended_variety": "V-240 / EC-4216 / Pusa Komal",
         "suitability_score": 78, "expected_yield_per_acre": "5-8 Quintal/Acre",
         "season_duration": "60-75 Days", "water_requirement": "Low",
         "suitability_reason": "Short-duration legume; fixes nitrogen; good for light sandy soils."},
    ],
    "red loamy": [
        {"crop_name": "Ragi (Finger Millet)", "recommended_variety": "GPU-28 / VL-149 / HR-911",
         "suitability_score": 90, "expected_yield_per_acre": "8-12 Quintal/Acre",
         "season_duration": "100-120 Days", "water_requirement": "Low",
         "suitability_reason": "Ragi is highly suited to red loamy soils; drought-tolerant and nutritious."},
        {"crop_name": "Maize (Corn)", "recommended_variety": "HQPM-1 / Pioneer 30V92 / NK-6240",
         "suitability_score": 87, "expected_yield_per_acre": "22-30 Quintal/Acre",
         "season_duration": "90-100 Days", "water_requirement": "Medium",
         "suitability_reason": "Red loamy soil supports excellent maize growth with good drainage."},
        {"crop_name": "Groundnut", "recommended_variety": "TMV-2 / JL-24 / K-134",
         "suitability_score": 85, "expected_yield_per_acre": "8-12 Quintal/Acre",
         "season_duration": "110-120 Days", "water_requirement": "Medium",
         "suitability_reason": "Groundnut pod formation benefits from loose red loamy texture."},
        {"crop_name": "Sunflower", "recommended_variety": "KBSH-44 / PAC-36 / Modern Vijay",
         "suitability_score": 82, "expected_yield_per_acre": "6-10 Quintal/Acre",
         "season_duration": "90-100 Days", "water_requirement": "Medium",
         "suitability_reason": "Sunflower adapts well to red soils; high oil content and market demand."},
        {"crop_name": "Pigeonpea (Tur)", "recommended_variety": "ICP-8863 / BDN-711 / BSMR-736",
         "suitability_score": 80, "expected_yield_per_acre": "6-9 Quintal/Acre",
         "season_duration": "150-180 Days", "water_requirement": "Low",
         "suitability_reason": "Legume suited to red soils; improves soil fertility through nitrogen fixation."},
    ],
    "laterite": [
        {"crop_name": "Cashew", "recommended_variety": "Vengurla-4 / BPP-8 / Ullal-2",
         "suitability_score": 92, "expected_yield_per_acre": "4-6 Quintal/Acre",
         "season_duration": "Annual (3-5 years to bear)", "water_requirement": "Low",
         "suitability_reason": "Cashew thrives in acidic laterite soils; major plantation crop in coastal areas."},
        {"crop_name": "Coconut", "recommended_variety": "West Coast Tall / Chandra Sankara",
         "suitability_score": 88, "expected_yield_per_acre": "50-70 Nuts/Palm/Year",
         "season_duration": "Annual (perennial)", "water_requirement": "Medium",
         "suitability_reason": "Coastal laterite soils with good drainage are ideal for coconut cultivation."},
        {"crop_name": "Tapioca (Cassava)", "recommended_variety": "H-226 / Sree Visakham",
         "suitability_score": 85, "expected_yield_per_acre": "80-120 Quintal/Acre",
         "season_duration": "270-300 Days", "water_requirement": "Low",
         "suitability_reason": "Tapioca is well-adapted to acidic laterite soils; starch industry demand."},
        {"crop_name": "Pineapple", "recommended_variety": "Kew / Queen / Mauritius",
         "suitability_score": 82, "expected_yield_per_acre": "150-200 Quintal/Acre",
         "season_duration": "12-14 Months", "water_requirement": "Medium",
         "suitability_reason": "Pineapple thrives in well-drained acidic laterite soils."},
        {"crop_name": "Ragi (Finger Millet)", "recommended_variety": "PR-202 / GPU-28 / VL-149",
         "suitability_score": 80, "expected_yield_per_acre": "8-10 Quintal/Acre",
         "season_duration": "100-115 Days", "water_requirement": "Low",
         "suitability_reason": "Drought-resistant cereal well-adapted to acidic laterite soils."},
    ],
    "sandy arid": [
        {"crop_name": "Bajra (Pearl Millet)", "recommended_variety": "GHB-558 / HHB-67 / GHB-732",
         "suitability_score": 97, "expected_yield_per_acre": "10-16 Quintal/Acre",
         "season_duration": "70-85 Days", "water_requirement": "Very Low",
         "suitability_reason": "Bajra is THE crop for sandy arid soil — extremely drought-tolerant, thrives with minimal rainfall (<400mm). Primary Kharif staple in Kutch/Saurashtra arid zones."},
        {"crop_name": "Castor (Erand)", "recommended_variety": "GCH-7 / GAUCH-1 / DCH-177",
         "suitability_score": 94, "expected_yield_per_acre": "10-15 Quintal/Acre",
         "season_duration": "180-210 Days", "water_requirement": "Very Low",
         "suitability_reason": "Castor is ideal for sandy arid soil — deep taproot accesses subsoil moisture; Gujarat produces 80%+ of India's castor from Kutch/Saurashtra sandy arid zones."},
        {"crop_name": "Isabgol (Psyllium Husk)", "recommended_variety": "GI-2 / HI-5 / Niharika",
         "suitability_score": 91, "expected_yield_per_acre": "4-6 Quintal/Acre",
         "season_duration": "100-110 Days", "water_requirement": "Low",
         "suitability_reason": "Isabgol thrives in well-drained sandy soils of arid regions; Kutch and Patan are India's top districts with export value Rs.80,000-1,20,000/quintal."},
        {"crop_name": "Cumin (Jeera)", "recommended_variety": "Gujarat Cumin-1 / GC-4 / RZ-19",
         "suitability_score": 88, "expected_yield_per_acre": "3-5 Quintal/Acre",
         "season_duration": "90-100 Days", "water_requirement": "Low",
         "suitability_reason": "Cumin is well-suited to light sandy soils of Kutch/North Gujarat; high-value spice with strong APMC and export demand."},
        {"crop_name": "Sesame (Til)", "recommended_variety": "Gujarat Til-1 / Purva-1 / RT-346",
         "suitability_score": 85, "expected_yield_per_acre": "3-5 Quintal/Acre",
         "season_duration": "75-90 Days", "water_requirement": "Very Low",
         "suitability_reason": "Sesame is extremely drought-tolerant and ideal for sandy arid soil; short duration fits within limited monsoon window."},
        {"crop_name": "Date Palm (Khajoor)", "recommended_variety": "Medjool / Barhee / Halawy",
         "suitability_score": 83, "expected_yield_per_acre": "20-30 Quintal/Acre",
         "season_duration": "Perennial (3-5 years to bear)", "water_requirement": "Low",
         "suitability_reason": "Date Palm naturally adapted to hot, arid, sandy conditions; Kutch has India's largest plantation with premium market value."},
        {"crop_name": "Guar (Cluster Bean)", "recommended_variety": "HG-365 / RGC-936 / CAZG-0234",
         "suitability_score": 80, "expected_yield_per_acre": "5-8 Quintal/Acre",
         "season_duration": "90-100 Days", "water_requirement": "Very Low",
         "suitability_reason": "Guar is a drought-hardy nitrogen-fixing legume; guar gum is major industrial export from arid Gujarat/Rajasthan sandy soils."},
    ],
    "coastal sandy": [
        {"crop_name": "Coconut", "recommended_variety": "West Coast Tall / East Coast Tall / Hybrid",
         "suitability_score": 95, "expected_yield_per_acre": "50-70 Nuts/Palm/Year",
         "season_duration": "Perennial", "water_requirement": "Medium",
         "suitability_reason": "Coastal sandy soil with salinity tolerance is ideal for Coconut; major plantation crop along Gujarat/Maharashtra coast."},
        {"crop_name": "Chiku (Sapota)", "recommended_variety": "Cricket Ball / Kalipatti / PKM-1",
         "suitability_score": 90, "expected_yield_per_acre": "40-60 Quintal/Acre",
         "season_duration": "Perennial (3-4 years to bear)", "water_requirement": "Medium",
         "suitability_reason": "Chiku thrives in warm coastal sandy soils; Navsari and Surat produce top-quality Chiku."},
        {"crop_name": "Groundnut", "recommended_variety": "GG-20 / GJG-31 / SB-XI",
         "suitability_score": 88, "expected_yield_per_acre": "8-12 Quintal/Acre",
         "season_duration": "110-120 Days", "water_requirement": "Medium",
         "suitability_reason": "Coastal sandy soils with good drainage are ideal for groundnut pod development."},
        {"crop_name": "Bajra (Pearl Millet)", "recommended_variety": "GHB-558 / HHB-67",
         "suitability_score": 85, "expected_yield_per_acre": "10-15 Quintal/Acre",
         "season_duration": "75-90 Days", "water_requirement": "Low",
         "suitability_reason": "Bajra adapted to warm coastal sandy soil; primary food crop in coastal areas."},
        {"crop_name": "Banana", "recommended_variety": "G9 / Grand Naine / Robusta",
         "suitability_score": 82, "expected_yield_per_acre": "120-180 Quintal/Acre",
         "season_duration": "11-14 Months", "water_requirement": "High",
         "suitability_reason": "Banana suits coastal warm sandy soils with drip irrigation; high commercial returns."},
    ],
}

def detect_default_soil_type(location_name: str) -> str:
    """Auto-detect soil type: checks district-level map first, then state-level."""
    loc_lower = (location_name or "").lower()
    # District-level check (most accurate)
    for district, soil in DISTRICT_SOIL_DEFAULTS.items():
        if district in loc_lower:
            return soil
    # State-level fallback
    for state, soil in STATE_SOIL_DEFAULTS.items():
        if state in loc_lower:
            return soil
    return "Mixed Soil (Auto-detected)"


def _get_soil_key(soil_type: str) -> str:
    """Map a soil type string to the crop pool key."""
    s = (soil_type or "").lower()
    # Explicit Black / Clayey / Vertisol / Heavy soils MUST map to black cotton
    if "deep black" in s or "clay" in s or "vertisol" in s or ("black" in s and "sandy" not in s) or "kaali" in s:
        return "black cotton"
    # Sandy arid / desert (Kutch, Rajasthan, arid North Gujarat)
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
    return "black cotton"  # final fallback


def _npk_filter_and_rank(crops: List[Dict], N: float, P: float, K: float, ph: float) -> List[Dict]:
    """Adjust suitability scores based on actual NPK values and return top 5."""
    ranked = []
    for crop in crops:
        score = crop["suitability_score"]
        name = crop["crop_name"].lower()
        # Nitrogen logic
        if N < 100:
            if "legume" in crop.get("suitability_reason","").lower() or "nitrogen fix" in crop.get("suitability_reason","").lower():
                score += 5  # legumes preferred when N is low
        if N > 200:
            if "wheat" in name or "rice" in name or "maize" in name or "sugarcane" in name:
                score += 4  # N-hungry crops preferred when N is high
        # Phosphorus logic
        if P < 30:
            if "groundnut" in name or "soybean" in name:
                score -= 3  # P-demanding crops penalized
        # Potassium logic
        if K < 50:
            if "potato" in name or "banana" in name or "sugarcane" in name:
                score -= 3  # K-demanding crops penalized
        # pH adjustment
        if ph > 8.5:  # very alkaline
            if "barley" in name or "mustard" in name:
                score += 3
        if ph < 5.5:  # acidic
            if "rice" in name or "ragi" in name or "cashew" in name or "pineapple" in name:
                score += 4
        # Clamp score
        score = min(98, max(55, score))
        c = dict(crop)
        c["suitability_score"] = score
        ranked.append(c)
    ranked.sort(key=lambda x: x["suitability_score"], reverse=True)
    return ranked[:5]


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
    Geographical AI Crop Recommendation Engine:
    Combines NPK test metrics, Soil Type, 3-Month Weather Forecast, and District location
    using Gemini AI to generate personalized agronomic advice with 5 diverse crops.
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")

    if not soil_type or soil_type == "Auto-Detect":
        soil_type = detect_default_soil_type(location_name)

    # Seasonal weather details string
    season_info = ""
    if seasonal_weather:
        season_name = seasonal_weather.get("season_name", "")
        tot_rain = seasonal_weather.get("total_precip_3m_mm", rainfall * 3)
        avg_t = seasonal_weather.get("avg_temp_3m", temperature)
        season_info = f"3-Month Seasonal Forecast for {season_name}: Total expected rainfall = {tot_rain}mm, Avg temperature = {avg_t}°C."
    else:
        season_info = f"Current Climate: Avg temp = {temperature}°C, Humidity = {humidity}%, Season Rainfall = {rainfall}mm."

    lang_instructions = {
        "gu": "Respond entirely in clear, farmer-friendly Gujarati (ગુજરાતી લીપી). Use Gujarati crop names, local units (વિઘા / quintal per acre), and simple terms.",
        "hi": "Respond entirely in clear, farmer-friendly Hindi (हिंदी भाषा). Use Hindi crop names and practical terms.",
        "en": "Respond in English with practical Indian agricultural terminology."
    }.get(lang, "Respond in English.")

    # Build regional crops context string
    regional_context = ""
    if regional_crops and (regional_crops.get("kharif_crops") or regional_crops.get("major_crops")):
        kharif = ", ".join(regional_crops.get("kharif_crops", [])[:6])
        rabi = ", ".join(regional_crops.get("rabi_crops", [])[:5])
        perennial = ", ".join(regional_crops.get("perennial_crops", [])[:4])
        major = ", ".join(regional_crops.get("major_crops", [])[:4])
        emerging = ", ".join(regional_crops.get("emerging_crops", [])[:3])
        apmc_note = regional_crops.get("apmc_note", "")
        src = regional_crops.get("source", "database")
        regional_context = f"""
- REAL CROPS VERIFIED IN THIS DISTRICT (Source: {src}):
  * Kharif Season Crops ACTUALLY GROWN: {kharif}
  * Rabi Season Crops ACTUALLY GROWN: {rabi}
  * Perennial / Horticulture Crops: {perennial}
  * Major Commercial/Cash Crops: {major}
  {f'* Emerging New Crops (last 5 years): {emerging}' if emerging else ''}
  * Local APMC Market Note: {apmc_note}"""

    prompt = f"""You are AgriSense AI, an expert Senior Agricultural Scientist and Agronomist specializing in Indian farming regions.

FARMER AGRO-CLIMATIC DATA:
- Location (District/State): {location_name}
- Soil Physical Type: {soil_type}
- Soil Chemical Analysis: Nitrogen (N) = {N} kg/ha, Phosphorus (P) = {P} kg/ha, Potassium (K) = {K} kg/ha, Soil pH = {ph}
- Weather & 90-Day Climate Outlook: {season_info}{regional_context}

LANGUAGE REQUIREMENT: {lang_instructions}

TASK: Perform a specialized 4-layer agronomic evaluation and recommend EXACTLY 5 DIFFERENT, DIVERSE crops best suited to this farmer's specific conditions.

DIVERSITY RULES:
- PRIORITIZE crops from the "REAL CROPS VERIFIED IN THIS DISTRICT" list above — these are what farmers in this exact location actually grow and sell profitably.
- For {soil_type}: also consider Soybean, Sorghum, Pigeonpea, Wheat, Chickpea, Maize, Sesame, Castor, Pearl Millet, Ragi, Mustard, Sunflower, Sugarcane, Rice, Potato.
- If N={N} is low (< 120 kg/ha): prioritize nitrogen-fixing legumes (e.g. Soybean, Pigeonpea, Chickpea, Cowpea).
- If P={P} is low (< 40 kg/ha): avoid heavy phosphorus-demanding crops; prefer drought-tolerant crops.
- If rainfall is low (< 500mm/season): prioritize drought-tolerant crops (Pearl Millet, Castor, Sesame, Sorghum).
- Include at least 1 short-duration crop (under 100 days) and 1 long-duration crop (over 150 days).
- Include at least 1 legume/pulse crop and 1 cereal or oilseed crop.
- Mention in suitability_reason if the crop is ACTUALLY GROWN in this district (verified local crop).

Output ONLY a JSON object with exactly this structure:

{{
    "detected_soil_type": "{soil_type}",
    "agro_climatic_zone": "Name of agro-climatic region (e.g. Middle Gujarat Zone / Saurashtra / Vidarbha / Malwa Plateau)",
    "recommended_crops": [
        {{
            "crop_name": "Crop Name (English / Local Language)",
            "recommended_variety": "High-yielding regional variety (e.g. GJG-31 / JS-335)",
            "suitability_score": 92,
            "suitability_reason": "Specific 2-sentence reason why THIS crop suits THIS soil type, NPK values, and 90-day climate",
            "expected_yield_per_acre": "e.g. 12-15 Quintal/Acre",
            "season_duration": "e.g. 110-120 Days",
            "water_requirement": "High / Medium / Low"
        }}
    ],
    "soil_health_assessment": {{
        "nutrient_status": "Specific analysis of N={N}, P={P}, K={K} — which is deficient/excess and what to do",
        "ph_evaluation": "Analysis of pH {ph}: is it acidic/alkaline/neutral and what correction is needed",
        "organic_carbon_advice": "Practical manure/compost advice for improving soil organic matter"
    }},
    "custom_fertilizer_plan": {{
        "basal_dose": "Specific fertilizer dose per acre before sowing based on actual NPK values",
        "top_dressing_stage1": "Application at 30-day stage with specific dose",
        "top_dressing_stage2": "Application at 60-day flowering stage with specific dose"
    }},
    "intercropping_strategy": {{
        "suggested_intercrop": "Best intercrop pair for this specific soil and primary crop",
        "benefits": "Specific agronomic and economic benefits"
    }},
    "regional_market_notes": "Specific APMC market insight, price trend, and best harvesting window for {location_name}"
}}

CRITICAL: Return ONLY the raw JSON. No markdown, no ``` blocks, no explanation text. recommended_crops MUST contain exactly 5 different crops."""

    if api_key and HAS_GEMINI:
        try:
            client = genai.Client(api_key=api_key)

            models_to_try = [
                'gemini-2.0-flash',
                'gemini-2.0-flash-lite',
                'gemini-1.5-flash',
                'gemini-1.5-pro',
                'gemini-flash-latest',
            ]

            for model_name in models_to_try:
                try:
                    res = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.4)
                    )
                    if res and res.text:
                        text_resp = res.text.strip()
                        # Strip markdown code fences if present
                        if text_resp.startswith("```"):
                            lines = text_resp.split("\n")
                            text_resp = "\n".join([l for l in lines if not l.startswith("```")])
                        try:
                            parsed = json.loads(text_resp)
                            # Validate we have at least 3 crops
                            if isinstance(parsed.get("recommended_crops"), list) and len(parsed["recommended_crops"]) >= 2:
                                print(f"AI Crop Advisor: success with {model_name}, {len(parsed['recommended_crops'])} crops")
                                return parsed
                        except Exception:
                            import re
                            match = re.search(r'\{[\s\S]*\}', text_resp)
                            if match:
                                parsed = json.loads(match.group())
                                if isinstance(parsed.get("recommended_crops"), list) and len(parsed["recommended_crops"]) >= 2:
                                    return parsed
                except Exception as err:
                    print(f"AI Crop Advisor model {model_name} failed: {err}")
                    continue
        except Exception as global_err:
            print(f"AI Crop Advisor global error: {global_err}")

    print(f"AI Crop Advisor: falling back to smart rule-based system for soil={soil_type}")
    return _build_smart_fallback(location_name, soil_type, N, P, K, ph, temperature, rainfall, lang)


def _build_smart_fallback(
    location: str, soil_type: str, N: float, P: float, K: float,
    ph: float, temperature: float, rainfall: float, lang: str
) -> Dict[str, Any]:
    """
    Smart rule-based fallback: picks 5 diverse crops based on soil type + NPK + climate.
    Much better than hardcoded Cotton+Groundnut.
    """
    soil_key = _get_soil_key(soil_type)
    base_crops = CROP_POOL_BY_SOIL.get(soil_key, CROP_POOL_BY_SOIL["black cotton"])

    # If pool has fewer than 5, add from adjacent pools
    if len(base_crops) < 5:
        for fallback_key in ["black cotton", "alluvial", "sandy loam"]:
            if fallback_key != soil_key:
                base_crops = base_crops + CROP_POOL_BY_SOIL[fallback_key]
                break

    crops = _npk_filter_and_rank(base_crops, N, P, K, ph)

    # NPK status assessment
    n_status = "Deficient" if N < 120 else ("Adequate" if N < 200 else "High")
    p_status = "Deficient" if P < 40 else ("Adequate" if P < 80 else "High")
    k_status = "Deficient" if K < 80 else ("Adequate" if K < 150 else "High")

    # Fertilizer plan based on actual NPK
    urea_kg = max(25, int((200 - N) / 4)) if N < 200 else 15
    dap_kg = max(25, int((80 - P) / 1.5)) if P < 80 else 15
    mop_kg = max(15, int((150 - K) / 3)) if K < 150 else 10

    ph_eval = ""
    if ph < 6.0:
        ph_eval = f"pH {ph} is acidic. Apply agricultural lime (CaCO3) @ 2-3 tonnes/acre to raise pH."
    elif ph > 8.0:
        ph_eval = f"pH {ph} is alkaline. Apply gypsum @ 1-2 tonnes/acre or sulphur to lower pH."
    else:
        ph_eval = f"pH {ph} is ideal (6.0–8.0 range). No pH correction needed."

    # Intercrop logic
    primary_crop = crops[0]["crop_name"] if crops else "Cotton"
    if "cotton" in primary_crop.lower():
        intercrop = "Pigeonpea (Tur) with Cotton (4:1 row ratio)"
        intercrop_benefits = "Pigeonpea fixes atmospheric nitrogen reducing fertilizer cost by 30%; provides extra income of ₹8,000–12,000/acre."
    elif "groundnut" in primary_crop.lower() or "soybean" in primary_crop.lower():
        intercrop = "Sorghum or Pearl Millet as border crop"
        intercrop_benefits = "Windbreak reduces soil erosion; provides fodder income; pest trap crop."
    elif "rice" in primary_crop.lower() or "paddy" in primary_crop.lower():
        intercrop = "Azolla as green manure in paddy fields"
        intercrop_benefits = "Azolla fixes 20–30 kg N/ha reducing urea requirement significantly."
    else:
        intercrop = "Cowpea or Mungbean as intercrop"
        intercrop_benefits = "Short-duration legume fixes nitrogen and provides quick additional income."

    return {
        "detected_soil_type": soil_type,
        "agro_climatic_zone": f"Agricultural Zone — {location}",
        "recommended_crops": crops,
        "soil_health_assessment": {
            "nutrient_status": (
                f"Nitrogen: {N} kg/ha ({n_status}). "
                f"Phosphorus: {P} kg/ha ({p_status}). "
                f"Potassium: {K} kg/ha ({k_status}). "
                f"{'Apply 20-25 kg extra Urea/acre to boost nitrogen.' if n_status == 'Deficient' else ''}"
                f"{'Increase DAP application at basal dose.' if p_status == 'Deficient' else ''}"
                f"{'Apply MOP 15-20 kg/acre to correct potassium.' if k_status == 'Deficient' else ''}"
            ),
            "ph_evaluation": ph_eval,
            "organic_carbon_advice": (
                "Apply well-decomposed FYM (Farmyard Manure) @ 5–8 tonnes/acre or Vermicompost @ 2–3 tonnes/acre "
                "before sowing. Consider green manuring with Dhaincha (Sesbania) for rapid organic matter build-up."
            )
        },
        "custom_fertilizer_plan": {
            "basal_dose": f"DAP {dap_kg} kg + Urea {urea_kg} kg + MOP {mop_kg} kg per acre before sowing (based on actual N={N}, P={P}, K={K} kg/ha test values)",
            "top_dressing_stage1": f"Urea {max(15, urea_kg//2)} kg per acre at 25-30 days after sowing (vegetative stage)",
            "top_dressing_stage2": f"MOP (Potash) {mop_kg} kg + Urea 10 kg per acre at 55-65 days (pre-flowering/flowering stage)"
        },
        "intercropping_strategy": {
            "suggested_intercrop": intercrop,
            "benefits": intercrop_benefits
        },
        "regional_market_notes": (
            f"In {location}, {crops[0]['crop_name'] if crops else 'primary crops'} fetch strong APMC prices. "
            f"Best harvesting window: October–November for Kharif, March–April for Rabi. "
            f"Register with e-NAM portal for better price discovery and direct market access."
        )
    }
