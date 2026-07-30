"""
regional_crop_lookup.py  v3.0
Fetches REAL crops, CORRECT SOIL TYPE, RAINFALL, and AGRO-CLIMATIC ZONE DATA using:
1. gujarat_agro_zones.json — Authoritative grounding dataset for Gujarat districts
2. Nominatim reverse geocoding — GPS location identification
3. Gemini + Google Search grounding — fallback for non-mapped regions
"""
import os
import json
import re
import requests
from typing import Dict, List, Optional, Any

try:
    from google import genai
    from google.genai import types
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# ─────────────────────────────────────────────────────────────────────────────
# Load Authoritative Agro-Climatic Dataset
# ─────────────────────────────────────────────────────────────────────────────
AGRO_ZONES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "gujarat_agro_zones.json")

AGRO_ZONES_DATA: List[Dict[str, Any]] = []

def load_agro_zones():
    global AGRO_ZONES_DATA
    if os.path.exists(AGRO_ZONES_FILE):
        try:
            with open(AGRO_ZONES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                AGRO_ZONES_DATA = data.get("districts", [])
                print(f"Loaded {len(AGRO_ZONES_DATA)} district agro-zones from gujarat_agro_zones.json")
        except Exception as e:
            print(f"Error loading gujarat_agro_zones.json: {e}")
            AGRO_ZONES_DATA = []

load_agro_zones()

def reverse_geocode_district(lat: float, lon: float) -> Dict[str, str]:
    """Use Nominatim OpenStreetMap to get district/taluka/state from GPS coordinates."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=8&accept-language=en"
        headers = {"User-Agent": "AgriSense-App/3.0 (agricultural crop recommendation, contact@agrisense.in)"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address", {})
            district = (
                addr.get("county") or
                addr.get("district") or
                addr.get("city_district") or
                addr.get("city") or
                addr.get("town") or ""
            ).lower().strip()
            state = (addr.get("state") or "").lower().strip()
            return {
                "district": district,
                "state": state,
                "country": addr.get("country_code", "in"),
                "display_name": data.get("display_name", ""),
                "raw_address": addr
            }
    except Exception as e:
        print(f"Reverse geocode error: {e}")
    return {"district": "", "state": "", "country": "in", "display_name": "", "raw_address": {}}


def lookup_district_crops(district: str, state: str, display_name: str = "") -> Optional[Dict[str, Any]]:
    """
    Look up district in gujarat_agro_zones.json matching district_name or aliases.
    """
    d = (district or "").lower().strip()
    s = (state or "").lower().strip()
    disp = (display_name or "").lower().strip()
    search_text = f"{d} {disp}"

    if not AGRO_ZONES_DATA:
        load_agro_zones()

    # Search in loaded agro-zones dataset first
    for zone_entry in AGRO_ZONES_DATA:
        dist_name = zone_entry["district_name"].lower()
        aliases = [a.lower() for a in zone_entry.get("aliases", [])]

        # Check exact or partial match
        matched = False
        if dist_name in search_text or any(alias in search_text for alias in aliases):
            matched = True
        elif d and any(d in alias or alias in d for alias in aliases):
            matched = True

        if matched:
            crops = zone_entry.get("suitable_crops", [])
            kharif = [c["crop_name"] for c in crops if c.get("crop_name")]
            return {
                "district": zone_entry["district_name"],
                "state": "Gujarat",
                "soil": zone_entry["soil_type"],
                "soil_key": zone_entry.get("soil_key", "black cotton"),
                "agro_climatic_zone_name": zone_entry["agro_climatic_zone_name"],
                "avg_annual_rainfall_mm": zone_entry["avg_annual_rainfall_mm"],
                "typical_npk": zone_entry.get("typical_npk", {}),
                "kharif": kharif,
                "rabi": [c["crop_name"] for c in crops if "Rabi" in c.get("suitability_reason", "") or "rabi" in c.get("suitability_reason", "").lower()],
                "perennial": [c["crop_name"] for c in crops if c.get("season_duration", "").lower().startswith("perennial") or "11-" in c.get("season_duration", "")],
                "major_crops": kharif[:4],
                "suitable_crops_full": crops,
                "apmc_note": zone_entry.get("apmc_insight", ""),
                "source": "gujarat_agro_zones.json"
            }

    return None


def fetch_real_crops_for_location(
    lat: float,
    lon: float,
    location_name: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main function: fetches actual crops + GROUNDED AGRO-ZONE DATA for location.
    """
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")

    result = {
        "district": "",
        "state": "",
        "kharif_crops": [],
        "rabi_crops": [],
        "perennial_crops": [],
        "major_crops": [],
        "emerging_crops": [],
        "soil_type_regional": "",
        "soil_key": "",
        "agro_climatic_zone_name": "",
        "avg_annual_rainfall_mm": 800,
        "typical_npk": {},
        "suitable_crops_full": [],
        "source": "none",
        "apmc_note": ""
    }

    # Step 1: Reverse geocode GPS -> district
    geo = reverse_geocode_district(lat, lon)
    result["district"] = geo.get("district", "")
    result["state"] = geo.get("state", "")

    # Step 2: Grounding Dataset Lookup (gujarat_agro_zones.json)
    db_data = lookup_district_crops(result["district"], result["state"], display_name=f"{location_name} {geo.get('display_name','')}")
    if db_data:
        result["district"] = db_data.get("district", result["district"])
        result["kharif_crops"] = db_data.get("kharif", [])
        result["rabi_crops"] = db_data.get("rabi", [])
        result["perennial_crops"] = db_data.get("perennial", [])
        result["major_crops"] = db_data.get("major_crops", [])
        result["soil_type_regional"] = db_data.get("soil", "")
        result["soil_key"] = db_data.get("soil_key", "")
        result["agro_climatic_zone_name"] = db_data.get("agro_climatic_zone_name", "")
        result["avg_annual_rainfall_mm"] = db_data.get("avg_annual_rainfall_mm", 800)
        result["typical_npk"] = db_data.get("typical_npk", {})
        result["suitable_crops_full"] = db_data.get("suitable_crops_full", [])
        result["apmc_note"] = db_data.get("apmc_note", "")
        result["source"] = db_data.get("source", "gujarat_agro_zones.json")
        print(f"Grounded Dataset Match: {result['district']} -> Zone: {result['agro_climatic_zone_name']} | Soil: {result['soil_type_regional']}")

    # Step 3: Gemini Search fallback if not found in dataset
    if (not db_data or not result["soil_type_regional"]) and api_key and HAS_GEMINI:
        try:
            loc_query = location_name or f"{result['district']}, {result['state']}, India"
            search_prompt = f"""You are an Indian agricultural data expert.

For GPS location: {lat:.4f}°N, {lon:.4f}°E ({loc_query})

1. What is the EXACT DOMINANT SOIL TYPE in this specific district?
2. What is the AGRO-CLIMATIC ZONE name and avg annual rainfall (mm)?
3. What crops do farmers ACTUALLY GROW and SELL at the local APMC in this area?

Return ONLY JSON:
{{
    "district_name": "exact district name",
    "state_name": "state name",
    "actual_soil_type": "Specific soil type",
    "agro_climatic_zone_name": "Agro-climatic zone name",
    "avg_annual_rainfall_mm": 1000,
    "kharif_crops": ["crop1", "crop2", "crop3"],
    "rabi_crops": ["crop1", "crop2"],
    "perennial_or_horticulture": ["fruit1", "fruit2"],
    "major_cash_crops_by_production": ["crop1", "crop2"],
    "local_apmc_insight": "APMC market insight"
}}"""

            client = genai.Client(api_key=api_key)
            for model in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    res = client.models.generate_content(
                        model=model, contents=search_prompt,
                        config=types.GenerateContentConfig(temperature=0.1)
                    )
                    if res and res.text:
                        text = re.sub(r"^```[a-z]*\n?", "", res.text.strip())
                        text = re.sub(r"\n?```$", "", text)
                        match = re.search(r'\{[\s\S]*\}', text)
                        if match:
                            parsed = json.loads(match.group())
                            if parsed.get("actual_soil_type"):
                                result["soil_type_regional"] = parsed["actual_soil_type"]
                            if parsed.get("agro_climatic_zone_name"):
                                result["agro_climatic_zone_name"] = parsed["agro_climatic_zone_name"]
                            if parsed.get("avg_annual_rainfall_mm"):
                                result["avg_annual_rainfall_mm"] = parsed["avg_annual_rainfall_mm"]
                            if parsed.get("kharif_crops"):
                                result["kharif_crops"] = parsed["kharif_crops"]
                            if parsed.get("rabi_crops"):
                                result["rabi_crops"] = parsed["rabi_crops"]
                            if parsed.get("major_cash_crops_by_production"):
                                result["major_crops"] = parsed["major_cash_crops_by_production"]
                            if parsed.get("district_name"):
                                result["district"] = parsed["district_name"]
                            result["source"] = f"gemini_search ({model})"
                            break
                except Exception as e:
                    print(f"Gemini fallback failed ({model}): {e}")
        except Exception as e:
            print(f"Gemini fallback global error: {e}")

    return result
