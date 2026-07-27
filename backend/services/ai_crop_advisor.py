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

SOIL_TYPE_DEFAULTS = {
    "gujarat": "Black Cotton Soil (કાળી જમીન)",
    "maharashtra": "Black Cotton Soil (કાળી જમીન)",
    "punjab": "Alluvial Soil (ગોરાડુ/કાંપ જમીન)",
    "haryana": "Alluvial Soil (ગોરાડુ/કાંપ જમીન)",
    "uttar pradesh": "Alluvial Soil (કાંપ જમીન)",
    "rajasthan": "Sandy Loam Soil (રેતાળ જમીન)",
    "madhya pradesh": "Black Cotton Soil (કાળી જમીન)",
    "karnataka": "Red Loamy Soil (લાલ જમીન)",
    "tamil nadu": "Red Clay Soil (લાલ જમીન)",
    "andhra pradesh": "Red Clay Soil (લાલ જમીન)",
}

def detect_default_soil_type(location_name: str) -> str:
    """Auto-detect default regional soil type based on location/state."""
    loc_lower = (location_name or "").lower()
    for state, default_soil in SOIL_TYPE_DEFAULTS.items():
        if state in loc_lower:
            return default_soil
    # Default fallback for Gujarat/Western India agricultural hubs
    return "Black Cotton Soil (કાળી જમીન)"

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
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Geographical AI Crop Recommendation Engine:
    Combines NPK test metrics, Soil Type, 3-Month Weather Forecast, and District location
    using Gemini AI with Google Search Grounding to generate personalized agronomic advice.
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

    prompt = f"""You are AgriSense AI, an expert Senior Agricultural Scientist and Agronomist specializing in Indian farming regions.

FARMER AGRO-CLIMATIC DATA:
- Location (District/State): {location_name}
- Soil Physical Type: {soil_type}
- Soil Chemical Analysis: Nitrogen (N) = {N} kg/ha, Phosphorus (P) = {P} kg/ha, Potassium (K) = {K} kg/ha, Soil pH = {ph}
- Weather & 90-Day Climate Outlook: {season_info}

LANGUAGE REQUIREMENT: {lang_instructions}

TASK: Perform a specialized 4-layer agronomic evaluation (Location suitability + Soil type + NPK deficits + 3-Month Weather) and output a JSON object with these exact fields:

{{
    "detected_soil_type": "{soil_type}",
    "agro_climatic_zone": "Name of agro-climatic region (e.g. Middle Gujarat Zone / Saurashtra / Vidarbha / Malwa)",
    "recommended_crops": [
        {{
            "crop_name": "Name of crop (e.g. Cotton / કપાસ, Paddy / ડાંગર, Groundnut / મગફળી)",
            "recommended_variety": "High yielding regional variety name (e.g. G.Cot-20 / Gujarat Anand Paddy-1)",
            "suitability_score": 94,
            "suitability_reason": "Detailed reason why this crop fits this location, soil type, NPK test, and 90-day rainfall",
            "expected_yield_per_acre": "Expected yield (e.g. 12-15 Quintals/Acre)",
            "season_duration": "Duration (e.g. 110-120 days)",
            "water_requirement": "High / Medium / Low"
        }}
    ],
    "soil_health_assessment": {{
        "nutrient_status": "Summary of N, P, K deficiencies or excesses",
        "ph_evaluation": "Evaluation of pH {ph} and correction advice if alkaline/acidic",
        "organic_carbon_advice": "Practical advice to improve soil organic carbon and health"
    }},
    "custom_fertilizer_plan": {{
        "basal_dose": "Recommended basal fertilizer application per acre before sowing",
        "top_dressing_stage1": "Application at 30 days stage",
        "top_dressing_stage2": "Application at 60 days flowering stage"
    }},
    "intercropping_strategy": {{
        "suggested_intercrop": "Recommended intercrop / companion crop for extra income and soil nitrogen fixation",
        "benefits": "Key agricultural benefits of this combination"
    }},
    "regional_market_notes": "Brief guidance on local market demand, harvesting window, and economic returns in {location_name}"
}}

CRITICAL INSTRUCTIONS:
- Tailor the crop recommendations specifically to crops grown in {location_name} and suitable for {soil_type}.
- Return ONLY the JSON object, no markdown codeblocks or surrounding conversational text."""

    if api_key and HAS_GEMINI:
        try:
            client = genai.Client(api_key=api_key)
            config = None
            try:
                config = types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    temperature=0.3
                )
            except Exception:
                config = None

            models_to_try = ['gemini-flash-latest', 'gemini-pro-latest', 'gemma-4-26b-a4b-it', 'gemini-3.6-flash']
            
            for model_name in models_to_try:
                try:
                    kwargs = {"model": model_name, "contents": prompt}
                    if config:
                        kwargs["config"] = config
                    res = client.models.generate_content(**kwargs)
                    if res and res.text:
                        text_resp = res.text.strip()
                        if text_resp.startswith("```"):
                            lines = text_resp.split("\n")
                            text_resp = "\n".join([l for l in lines if not l.startswith("```")])
                        
                        try:
                            parsed = json.loads(text_resp)
                            return parsed
                        except Exception:
                            # Extract JSON substring
                            import re
                            match = re.search(r'\{[\s\S]*\}', text_resp)
                            if match:
                                return json.loads(match.group())
                except Exception as err:
                    print(f"AI Crop Advisor model {model_name} failed: {err}")
                    continue
        except Exception as global_err:
            print(f"AI Crop Advisor global error: {global_err}")

    # Fallback response if API offline/quota exceeded
    return _build_fallback_advice(location_name, soil_type, N, P, K, ph, lang)

def _build_fallback_advice(location: str, soil_type: str, N: float, P: float, K: float, ph: float, lang: str) -> Dict[str, Any]:
    if lang == "gu":
        return {
            "detected_soil_type": soil_type,
            "agro_climatic_zone": f"મધ્ય-દક્ષિણ પ્રદેશ ({location})",
            "recommended_crops": [
                {
                    "crop_name": "કપાસ (Cotton)",
                    "recommended_variety": "જી.કોટ-૨૦ / હાઇબ્રિડ-૬",
                    "suitability_score": 92,
                    "suitability_reason": f"{soil_type} અને નાઇટ્રોજન સ્તર માટે કપાસનું વાવેતર અનુકૂળ છે.",
                    "expected_yield_per_acre": "૧૨-૧૫ ક્વિન્ટલ/એકર",
                    "season_duration": "૧૫૦-૧૭૦ દિવસ",
                    "water_requirement": "મધ્યમ"
                },
                {
                    "crop_name": "મગફળી (Groundnut)",
                    "recommended_variety": "જી.જી.-૨૦ / જી.જે.જી.-૩૧",
                    "suitability_score": 88,
                    "suitability_reason": "ફોસ્ફરસ અને જમીન બંધારણ સાથે ઉત્તમ અનુકૂળતા.",
                    "expected_yield_per_acre": "૧૦-૧૨ ક્વિન્ટલ/એકર",
                    "season_duration": "૧૧૦-૧૨૦ દિવસ",
                    "water_requirement": "મધ્યમ"
                }
            ],
            "soil_health_assessment": {
                "nutrient_status": f"નાઇટ્રોજન (N={N}), ફોસ્ફરસ (P={P}), પોટાશ (K={K}). નાઇટ્રોજન સ્તર સુધારવાની જરૂર છે.",
                "ph_evaluation": f"જમીનનો pH સ્તર {ph} અનુકૂળ છે.",
                "organic_carbon_advice": "જમીનમાં દેશી છાણિયું ખાતર અથવા વર્મીકમ્પોસ્ટ ઉમેરો."
            },
            "custom_fertilizer_plan": {
                "basal_dose": "વાવણી વખતે ડી.એ.પી. ૫૦ કિગ્રા અને યુરિયા ૨૫ કિગ્રા/એકર",
                "top_dressing_stage1": "૩૦ દિવસે યુરિયા ૨૫ કિગ્રા/એકર",
                "top_dressing_stage2": "૬૦ દિવસે પોટાશ (MOP) ૨૦ કિગ્રા/એકર"
            },
            "intercropping_strategy": {
                "suggested_intercrop": "કપાસ સાથે તુવેર અથવા મગ",
                "benefits": "જમીનમાં નાઇટ્રોજન સ્થિરીકરણ અને વધારાની આવક"
            },
            "regional_market_notes": f"{location} વિસ્તારમાં કપાસ અને મગફળીનું સ્થાનિક મંડળી અને યાર્ડમાં સારું વેચાણ મૂલ્ય મળે છે."
        }
    else:
        return {
            "detected_soil_type": soil_type,
            "agro_climatic_zone": f"Agricultural Zone ({location})",
            "recommended_crops": [
                {
                    "crop_name": "Cotton",
                    "recommended_variety": "G.Cot-20 / Hybrid-6",
                    "suitability_score": 92,
                    "suitability_reason": f"Highly suited for {soil_type} and local climate.",
                    "expected_yield_per_acre": "12-15 Quintal/Acre",
                    "season_duration": "150-170 Days",
                    "water_requirement": "Medium"
                },
                {
                    "crop_name": "Groundnut",
                    "recommended_variety": "GG-20 / GJG-31",
                    "suitability_score": 88,
                    "suitability_reason": "Matches phosphorus levels and loamy texture.",
                    "expected_yield_per_acre": "10-12 Quintal/Acre",
                    "season_duration": "110-120 Days",
                    "water_requirement": "Medium"
                }
            ],
            "soil_health_assessment": {
                "nutrient_status": f"NPK metrics: N={N}, P={P}, K={K}. Moderate nitrogen enhancement required.",
                "ph_evaluation": f"Soil pH is {ph}, which is within normal limits.",
                "organic_carbon_advice": "Apply farmyard manure (FYM) or compost before sowing."
            },
            "custom_fertilizer_plan": {
                "basal_dose": "DAP 50 kg + Urea 25 kg per acre before sowing",
                "top_dressing_stage1": "Urea 25 kg per acre at 30 days",
                "top_dressing_stage2": "MOP (Potash) 20 kg per acre at 60 days"
            },
            "intercropping_strategy": {
                "suggested_intercrop": "Pigeonpea (Tuver) or Mungbean with Cotton",
                "benefits": "Improves soil nitrogen balance and reduces pest pressure"
            },
            "regional_market_notes": f"Strong APMC yard demand and price stability for Cotton and Groundnut in {location} region."
        }
