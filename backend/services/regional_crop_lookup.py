"""
regional_crop_lookup.py  v4.0
Fetches REAL crops, CORRECT SOIL TYPE, RAINFALL, and AGRO-CLIMATIC ZONE DATA using:
1. gujarat_agro_zones.json — Authoritative grounding dataset for Gujarat districts (with lat/lon)
2. Haversine geo-distance matching — Maps ANY rural GPS coordinate to nearest known district/APMC
3. Nominatim reverse geocoding — GPS location identification
4. Gemini + Google Search grounding — fallback for non-mapped regions
"""
import os
import json
import re
import math
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


# ─────────────────────────────────────────────────────────────────────────────
# Haversine Distance Calculator — maps any rural GPS to nearest district/APMC
# ─────────────────────────────────────────────────────────────────────────────
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in km between two GPS coordinates using Haversine formula."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearest_district_by_gps(lat: float, lon: float, max_distance_km: float = 120.0) -> Optional[Dict[str, Any]]:
    """
    Find the nearest district from gujarat_agro_zones.json using GPS coordinates.
    This is the PRIMARY lookup method — works for any rural village, farm, or taluka.
    Returns the full zone entry or None if no district is within max_distance_km.
    """
    if not AGRO_ZONES_DATA:
        load_agro_zones()

    best_match = None
    best_distance = float('inf')

    for zone_entry in AGRO_ZONES_DATA:
        center_lat = zone_entry.get("center_lat")
        center_lon = zone_entry.get("center_lon")
        if center_lat is None or center_lon is None:
            continue

        dist_km = _haversine_km(lat, lon, center_lat, center_lon)
        if dist_km < best_distance:
            best_distance = dist_km
            best_match = zone_entry

    if best_match and best_distance <= max_distance_km:
        print(f"[GEO-MATCH] GPS ({lat:.4f}, {lon:.4f}) -> Nearest district: {best_match['district_name']} (distance: {best_distance:.1f} km)")
        return best_match, best_distance

    print(f"[GEO-MATCH] GPS ({lat:.4f}, {lon:.4f}) -> No district within {max_distance_km} km")
    return None, best_distance


# ─────────────────────────────────────────────────────────────────────────────
# Text-Based District Lookup (secondary — for when user types a name)
# ─────────────────────────────────────────────────────────────────────────────
def reverse_geocode_district(lat: float, lon: float) -> Dict[str, str]:
    """Use Nominatim OpenStreetMap to get district/taluka/state from GPS coordinates."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=8&accept-language=en"
        headers = {"User-Agent": "AgriSense-App/4.0 (agricultural crop recommendation, contact@agrisense.in)"}
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
            return _zone_entry_to_result(zone_entry)

    return None


def _zone_entry_to_result(zone_entry: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a zone entry from JSON into the standardized result format."""
    crops = zone_entry.get("suitable_crops", [])
    kharif = [c["crop_name"] for c in crops if c.get("crop_name")]
    return {
        "district": zone_entry["district_name"],
        "state": "Gujarat",
        "soil": zone_entry["soil_type"],
        "soil_key": zone_entry.get("soil_key", "black cotton"),
        "soil_type_regional": zone_entry["soil_type"],
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


def fetch_real_crops_for_location(
    lat: float,
    lon: float,
    location_name: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main function: fetches actual crops + GROUNDED AGRO-ZONE DATA for location.
    Uses 3-tier lookup: (1) GPS haversine nearest-district, (2) text alias match, (3) Gemini fallback
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
        "apmc_note": "",
        "geo_distance_km": None
    }

    # ─── TIER 1: GPS Haversine Nearest-District Match ───
    # This is the PRIMARY method — works for ANY rural village/farm in Gujarat
    geo_match, geo_dist = find_nearest_district_by_gps(lat, lon)
    if geo_match:
        db_data = _zone_entry_to_result(geo_match)
        result["district"] = db_data.get("district", "")
        result["kharif_crops"] = db_data.get("kharif", [])
        result["rabi_crops"] = db_data.get("rabi", [])
        result["perennial_crops"] = db_data.get("perennial", [])
        result["major_crops"] = db_data.get("major_crops", [])
        result["soil_type_regional"] = db_data.get("soil_type_regional", "")
        result["soil_key"] = db_data.get("soil_key", "")
        result["agro_climatic_zone_name"] = db_data.get("agro_climatic_zone_name", "")
        result["avg_annual_rainfall_mm"] = db_data.get("avg_annual_rainfall_mm", 800)
        result["typical_npk"] = db_data.get("typical_npk", {})
        result["suitable_crops_full"] = db_data.get("suitable_crops_full", [])
        result["apmc_note"] = db_data.get("apmc_note", "")
        result["source"] = f"geo_match ({geo_dist:.0f}km)"
        result["geo_distance_km"] = round(geo_dist, 1)
        print(f"[TIER-1 GEO] Matched: {result['district']} -> Zone: {result['agro_climatic_zone_name']} | Soil: {result['soil_type_regional']} | Distance: {geo_dist:.1f}km")
        return result

    # ─── TIER 2: Reverse Geocode + Text Alias Match ───
    geo = reverse_geocode_district(lat, lon)
    result["district"] = geo.get("district", "")
    result["state"] = geo.get("state", "")

    db_data = lookup_district_crops(result["district"], result["state"], display_name=f"{location_name} {geo.get('display_name','')}")
    if db_data:
        result["district"] = db_data.get("district", result["district"])
        result["kharif_crops"] = db_data.get("kharif", [])
        result["rabi_crops"] = db_data.get("rabi", [])
        result["perennial_crops"] = db_data.get("perennial", [])
        result["major_crops"] = db_data.get("major_crops", [])
        result["soil_type_regional"] = db_data.get("soil_type_regional", "")
        result["soil_key"] = db_data.get("soil_key", "")
        result["agro_climatic_zone_name"] = db_data.get("agro_climatic_zone_name", "")
        result["avg_annual_rainfall_mm"] = db_data.get("avg_annual_rainfall_mm", 800)
        result["typical_npk"] = db_data.get("typical_npk", {})
        result["suitable_crops_full"] = db_data.get("suitable_crops_full", [])
        result["apmc_note"] = db_data.get("apmc_note", "")
        result["source"] = db_data.get("source", "gujarat_agro_zones.json")
        print(f"[TIER-2 TEXT] Matched: {result['district']} -> Zone: {result['agro_climatic_zone_name']} | Soil: {result['soil_type_regional']}")
        return result

    # ─── TIER 3: Gemini Search Fallback ───
    if api_key and HAS_GEMINI:
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
    "typical_npk": {{ "N": 120.0, "P": 35.0, "K": 200.0, "pH": 7.5 }},
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
                            if parsed.get("typical_npk"):
                                result["typical_npk"] = parsed["typical_npk"]
                            if parsed.get("kharif_crops"):
                                result["kharif_crops"] = parsed["kharif_crops"]
                            if parsed.get("rabi_crops"):
                                result["rabi_crops"] = parsed["rabi_crops"]
                            if parsed.get("major_cash_crops_by_production"):
                                result["major_crops"] = parsed["major_cash_crops_by_production"]
                            if parsed.get("district_name"):
                                result["district"] = parsed["district_name"]
                            if parsed.get("local_apmc_insight"):
                                result["apmc_note"] = parsed["local_apmc_insight"]
                            result["source"] = f"gemini_search ({model})"
                            break
                except Exception as e:
                    print(f"Gemini fallback failed ({model}): {e}")
        except Exception as e:
            print(f"Gemini fallback global error: {e}")

    return result
