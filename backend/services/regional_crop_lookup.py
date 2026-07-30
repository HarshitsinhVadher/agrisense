"""
regional_crop_lookup.py
Fetches REAL crops grown in a GPS location using:
1. District-level crop database (India) — instant offline lookup
2. Gemini + Google Search grounding — live real-world data
3. Open-Meteo Agro / Nominatim reverse geocoding for district identification
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
# District-Level Real Crop Database for India
# Source: ICAR, ICRISAT, State Agriculture Departments, APMC records
# ─────────────────────────────────────────────────────────────────────────────
DISTRICT_CROP_DB: Dict[str, Dict] = {
    # GUJARAT DISTRICTS
    "ahmedabad": {
        "state": "Gujarat", "soil": "Black Cotton Soil",
        "kharif": ["Cotton", "Groundnut", "Bajra", "Castor", "Soybean"],
        "rabi":   ["Wheat", "Chickpea", "Mustard", "Cumin", "Fennel"],
        "perennial": ["Mango", "Banana", "Vegetables"],
        "major_crops": ["Cotton", "Wheat", "Groundnut"],
        "apmc_note": "Ahmedabad APMC is one of the largest in Gujarat; Cotton, Castor and Cumin fetch premium prices."
    },
    "anand": {
        "state": "Gujarat", "soil": "Alluvial / Sandy Loam",
        "kharif": ["Paddy", "Groundnut", "Maize", "Bajra", "Cotton"],
        "rabi":   ["Wheat", "Potato", "Mustard", "Chickpea", "Garlic"],
        "perennial": ["Banana", "Mango", "Tobacco", "Vegetables"],
        "major_crops": ["Paddy", "Wheat", "Groundnut", "Tobacco"],
        "apmc_note": "Anand is famous for dairy; Tobacco and Paddy are key Kharif crops. Wheat dominates Rabi."
    },
    "vadodara": {
        "state": "Gujarat", "soil": "Alluvial / Black Cotton",
        "kharif": ["Cotton", "Paddy", "Groundnut", "Soybean", "Maize"],
        "rabi":   ["Wheat", "Chickpea", "Mustard", "Vegetables"],
        "perennial": ["Mango", "Banana", "Sugarcane"],
        "major_crops": ["Cotton", "Wheat", "Paddy"],
        "apmc_note": "Vadodara APMC sees strong demand for Cotton and Paddy. Kesar Mango is premium fruit crop."
    },
    "surat": {
        "state": "Gujarat", "soil": "Alluvial / Coastal Sandy",
        "kharif": ["Paddy", "Sugarcane", "Vegetables", "Banana"],
        "rabi":   ["Wheat", "Vegetables", "Chickpea"],
        "perennial": ["Sugarcane", "Banana", "Mango", "Chickoo (Sapota)"],
        "major_crops": ["Paddy", "Sugarcane", "Banana"],
        "apmc_note": "Surat region: Sugarcane, Paddy and coastal vegetables. Alphonso/Kesar mango in adjacent talukas."
    },
    "rajkot": {
        "state": "Gujarat", "soil": "Sandy Loam / Black Cotton",
        "kharif": ["Groundnut", "Cotton", "Bajra", "Castor", "Sesame"],
        "rabi":   ["Wheat", "Chickpea", "Cumin", "Mustard"],
        "perennial": ["Pomegranate", "Lime", "Vegetables"],
        "major_crops": ["Groundnut", "Cotton", "Cumin"],
        "apmc_note": "Rajkot is Saurashtra's groundnut belt; Cumin and Castor fetch excellent APMC prices."
    },
    "amreli": {
        "state": "Gujarat", "soil": "Sandy Loam / Light Black",
        "kharif": ["Groundnut", "Cotton", "Bajra", "Castor"],
        "rabi":   ["Wheat", "Chickpea", "Cumin"],
        "perennial": ["Mango", "Lime", "Coconut"],
        "major_crops": ["Groundnut", "Cotton"],
        "apmc_note": "Amreli is prime groundnut district of Saurashtra. High oil content groundnut varieties."
    },
    "bhavnagar": {
        "state": "Gujarat", "soil": "Black Cotton / Sandy Loam",
        "kharif": ["Groundnut", "Cotton", "Bajra", "Sesame"],
        "rabi":   ["Wheat", "Chickpea", "Mustard", "Cumin"],
        "perennial": ["Mango", "Date Palm", "Vegetables"],
        "major_crops": ["Groundnut", "Cotton", "Wheat"],
        "apmc_note": "Bhavnagar coastal zone: Groundnut oil is major output. Cotton and Wheat both have strong demand."
    },
    "junagadh": {
        "state": "Gujarat", "soil": "Sandy Loam / Laterite",
        "kharif": ["Groundnut", "Bajra", "Cotton", "Castor"],
        "rabi":   ["Wheat", "Chickpea", "Cumin", "Fennel"],
        "perennial": ["Kesar Mango", "Banana", "Chiku (Sapota)", "Lime"],
        "major_crops": ["Groundnut", "Kesar Mango", "Banana"],
        "apmc_note": "Junagadh: World-famous Kesar Mango (GI tag). Groundnut is main Kharif crop. Strong fruit export market."
    },
    "kutch": {
        "state": "Gujarat", "soil": "Sandy / Arid Loam",
        "kharif": ["Bajra", "Castor", "Cotton", "Groundnut"],
        "rabi":   ["Wheat", "Chickpea", "Cumin", "Isabgol"],
        "perennial": ["Date Palm", "Pomegranate", "Ber"],
        "major_crops": ["Bajra", "Castor", "Isabgol", "Date Palm"],
        "apmc_note": "Kutch arid zone: Isabgol (Psyllium Husk) has high export value. Date Palm and Castor are key perennials."
    },
    "mehsana": {
        "state": "Gujarat", "soil": "Alluvial / Sandy Loam",
        "kharif": ["Bajra", "Castor", "Cotton", "Groundnut"],
        "rabi":   ["Wheat", "Mustard", "Cumin", "Fennel", "Potato"],
        "perennial": ["Tobacco", "Vegetables"],
        "major_crops": ["Tobacco", "Bajra", "Fennel", "Castor"],
        "apmc_note": "Mehsana is famous for Tobacco and North Gujarat's spice belt (Cumin, Fennel). Fennel fetches high export value."
    },
    "banaskantha": {
        "state": "Gujarat", "soil": "Sandy / Alluvial",
        "kharif": ["Bajra", "Castor", "Groundnut", "Cotton"],
        "rabi":   ["Wheat", "Mustard", "Cumin", "Potato", "Garlic"],
        "perennial": ["Banana", "Vegetables"],
        "major_crops": ["Potato", "Bajra", "Cumin", "Castor"],
        "apmc_note": "Banaskantha: India's leading Potato producing district. Cumin and Castor also have strong APMC returns."
    },
    "patan": {
        "state": "Gujarat", "soil": "Sandy / Saline",
        "kharif": ["Bajra", "Cotton", "Groundnut", "Castor"],
        "rabi":   ["Wheat", "Mustard", "Isabgol", "Cumin"],
        "perennial": ["Date Palm"],
        "major_crops": ["Bajra", "Isabgol", "Cumin"],
        "apmc_note": "Patan: Isabgol (psyllium) is export-quality spice crop. Bajra thrives in sandy soils."
    },
    "gandhinagar": {
        "state": "Gujarat", "soil": "Sandy Loam / Alluvial",
        "kharif": ["Bajra", "Groundnut", "Cotton", "Vegetables"],
        "rabi":   ["Wheat", "Mustard", "Chickpea", "Vegetables"],
        "perennial": ["Mango", "Banana", "Flowers"],
        "major_crops": ["Wheat", "Vegetables", "Bajra"],
        "apmc_note": "Gandhinagar peri-urban zone: High-value vegetables and flowers. Urban proximity enables direct farm-to-market."
    },
    # MAHARASHTRA
    "pune": {
        "state": "Maharashtra", "soil": "Black Cotton / Red Laterite",
        "kharif": ["Soybean", "Bajra", "Maize", "Onion", "Cotton"],
        "rabi":   ["Wheat", "Chickpea", "Onion", "Potato"],
        "perennial": ["Grapes", "Pomegranate", "Sugarcane", "Tomato"],
        "major_crops": ["Grapes", "Soybean", "Onion", "Sugarcane"],
        "apmc_note": "Pune: Premium Grape wine region (Nashik proximity). Onion export hub. Soybean dominant Kharif oilseed."
    },
    "nashik": {
        "state": "Maharashtra", "soil": "Red Laterite / Black",
        "kharif": ["Onion", "Soybean", "Cotton", "Bajra"],
        "rabi":   ["Wheat", "Chickpea", "Onion", "Garlic"],
        "perennial": ["Grapes", "Pomegranate", "Tomato", "Strawberry"],
        "major_crops": ["Grapes", "Onion", "Tomato"],
        "apmc_note": "Nashik: India's wine and grape capital. Onion is #1 Kharif-Rabi crop. Strong export demand."
    },
    "nagpur": {
        "state": "Maharashtra", "soil": "Black Cotton Soil (Vidarbha)",
        "kharif": ["Cotton", "Soybean", "Paddy", "Tuar (Pigeonpea)"],
        "rabi":   ["Wheat", "Chickpea", "Linseed"],
        "perennial": ["Nagpur Mandarin Orange", "Mango"],
        "major_crops": ["Cotton", "Soybean", "Nagpur Orange"],
        "apmc_note": "Nagpur: Famous for GI-tagged Nagpur Mandarin. Vidarbha's Cotton belt — highest MSP benefit."
    },
    # PUNJAB
    "ludhiana": {
        "state": "Punjab", "soil": "Alluvial (Sandy Loam)",
        "kharif": ["Paddy", "Maize", "Cotton", "Bajra"],
        "rabi":   ["Wheat", "Mustard", "Potato", "Chickpea"],
        "perennial": ["Sugarcane", "Vegetables"],
        "major_crops": ["Paddy", "Wheat"],
        "apmc_note": "Ludhiana: Core of Punjab's Green Revolution wheat-paddy belt. Wheat MSP procurement is strong."
    },
    # RAJASTHAN
    "jaipur": {
        "state": "Rajasthan", "soil": "Sandy Loam / Arid",
        "kharif": ["Bajra", "Groundnut", "Maize", "Sorghum"],
        "rabi":   ["Wheat", "Mustard", "Chickpea", "Barley", "Cumin"],
        "perennial": ["Ber (Jujube)", "Pomegranate", "Guava"],
        "major_crops": ["Bajra", "Mustard", "Wheat", "Cumin"],
        "apmc_note": "Jaipur: Rajasthan's Mustard belt. Bajra is drought-resilient Kharif crop. Cumin is high-value export spice."
    },
    # UTTAR PRADESH
    "lucknow": {
        "state": "Uttar Pradesh", "soil": "Alluvial (Indo-Gangetic Plain)",
        "kharif": ["Paddy", "Maize", "Sugarcane", "Arhar"],
        "rabi":   ["Wheat", "Mustard", "Potato", "Pea", "Lentil"],
        "perennial": ["Mango (Dasheri/Langra)", "Guava", "Banana"],
        "major_crops": ["Wheat", "Paddy", "Sugarcane", "Mango"],
        "apmc_note": "Lucknow: World-famous Dasheri Mango (GI). Wheat-Paddy rotation dominates. Sugarcane for UP sugar mills."
    },
}

# State-level fallback when district not found
STATE_CROP_FALLBACK: Dict[str, Dict] = {
    "gujarat": {
        "kharif": ["Cotton", "Groundnut", "Bajra", "Castor", "Soybean", "Paddy"],
        "rabi": ["Wheat", "Chickpea", "Mustard", "Cumin", "Fennel", "Potato"],
        "perennial": ["Mango", "Banana", "Kesar Mango", "Chiku"],
        "note": "Gujarat agriculture: Groundnut, Cotton and Spices dominate. Strong APMC network."
    },
    "maharashtra": {
        "kharif": ["Cotton", "Soybean", "Paddy", "Bajra", "Onion"],
        "rabi": ["Wheat", "Chickpea", "Onion", "Garlic"],
        "perennial": ["Sugarcane", "Grapes", "Pomegranate", "Orange"],
        "note": "Maharashtra: Vidarbha Cotton belt, Western Maharashtra fruit hub, Marathwada pulses."
    },
    "punjab": {
        "kharif": ["Paddy", "Maize", "Cotton"],
        "rabi": ["Wheat", "Mustard", "Potato"],
        "perennial": ["Sugarcane"],
        "note": "Punjab: Wheat-Paddy rotation is dominant. Green Revolution heartland."
    },
    "rajasthan": {
        "kharif": ["Bajra", "Groundnut", "Sorghum", "Maize"],
        "rabi": ["Wheat", "Mustard", "Chickpea", "Barley", "Cumin", "Coriander"],
        "perennial": ["Ber", "Pomegranate"],
        "note": "Rajasthan: Arid agriculture; Cumin, Mustard and Bajra are key crops."
    },
    "uttar pradesh": {
        "kharif": ["Paddy", "Maize", "Sugarcane", "Soybean"],
        "rabi": ["Wheat", "Mustard", "Potato", "Pea", "Lentil"],
        "perennial": ["Mango", "Guava", "Banana"],
        "note": "UP: Wheat-Paddy belt. Sugarcane for sugar industry. Mango orchards in Malihabad."
    },
    "madhya pradesh": {
        "kharif": ["Soybean", "Cotton", "Maize", "Sorghum", "Paddy"],
        "rabi": ["Wheat", "Chickpea", "Lentil", "Mustard"],
        "perennial": ["Orange", "Banana"],
        "note": "MP: Soybean capital of India. Wheat-Chickpea rabi rotation is dominant."
    },
    "karnataka": {
        "kharif": ["Maize", "Paddy", "Cotton", "Ragi", "Bajra", "Sunflower"],
        "rabi": ["Wheat", "Chickpea", "Lentil", "Safflower"],
        "perennial": ["Coffee", "Arecanut", "Coconut", "Pomegranate", "Grapes"],
        "note": "Karnataka: Coffee, Ragi and Maize dominant. North Karnataka is Pulses belt."
    },
}


def reverse_geocode_district(lat: float, lon: float) -> Dict[str, str]:
    """Use Nominatim OpenStreetMap to get district/state from GPS coordinates."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=10"
        headers = {"User-Agent": "AgriSense-App/3.0 (agricultural crop recommendation)"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address", {})
            return {
                "district": (addr.get("county") or addr.get("district") or addr.get("city") or "").lower().strip(),
                "state": (addr.get("state") or "").lower().strip(),
                "country": addr.get("country_code", "in"),
                "display_name": data.get("display_name", "")
            }
    except Exception as e:
        print(f"Reverse geocode error: {e}")
    return {"district": "", "state": "", "country": "in", "display_name": ""}


def lookup_district_crops(district: str, state: str) -> Optional[Dict]:
    """Look up crops from the district crop database."""
    # Try exact district match
    d = district.lower().strip()
    for key in DISTRICT_CROP_DB:
        if key in d or d in key:
            return DISTRICT_CROP_DB[key]
    # Try state fallback
    s = state.lower().strip()
    for key in STATE_CROP_FALLBACK:
        if key in s or s in key:
            return {**STATE_CROP_FALLBACK[key], "district": district, "soil": "Regional"}
    return None


def fetch_real_crops_for_location(
    lat: float,
    lon: float,
    location_name: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main function: fetches actual crops grown at GPS coordinates.
    Returns a dict with kharif_crops, rabi_crops, perennial_crops, district_info, source.
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
        "source": "none",
        "apmc_note": "",
        "soil_type_regional": ""
    }

    # Step 1: Reverse geocode GPS to district
    geo = reverse_geocode_district(lat, lon)
    result["district"] = geo.get("district", "")
    result["state"] = geo.get("state", "")

    # Step 2: Database lookup
    db_data = lookup_district_crops(result["district"], result["state"])
    if db_data:
        result["kharif_crops"] = db_data.get("kharif", [])
        result["rabi_crops"] = db_data.get("rabi", [])
        result["perennial_crops"] = db_data.get("perennial", [])
        result["major_crops"] = db_data.get("major_crops", [])
        result["apmc_note"] = db_data.get("apmc_note", "") or db_data.get("note", "")
        result["soil_type_regional"] = db_data.get("soil", "")
        result["source"] = "district_database"
        print(f"Regional Crop Lookup: Found {result['district']}/{result['state']} in database")

    # Step 3: Gemini + Google Search for live real-world crop data
    if api_key and HAS_GEMINI:
        try:
            loc_query = location_name or f"{result['district']}, {result['state']}, India"
            search_prompt = f"""You are an Indian agricultural data expert.

For the location: {loc_query} (GPS: {lat:.4f}°N, {lon:.4f}°E)

Search for and list the ACTUAL CROPS currently grown by farmers in this specific district/taluka/region.
Include crops from government agriculture department records, APMC data, ICAR/ICRISAT data, and local farming practices.

Return ONLY a JSON object with this exact structure:
{{
    "district_name": "actual district name",
    "state_name": "state name",
    "kharif_crops": ["crop1", "crop2", "crop3", "crop4", "crop5"],
    "rabi_crops": ["crop1", "crop2", "crop3", "crop4"],
    "perennial_or_horticulture": ["fruit1", "vegetable1", "plantation1"],
    "major_cash_crops": ["most commercially important crops"],
    "emerging_crops": ["new or growing crops in the area in last 5 years"],
    "local_soil_type": "dominant soil type in this region",
    "crop_season_note": "brief note about local farming calendar and APMC/mandi insights"
}}

Return ONLY JSON, no markdown, no explanation."""

            client = genai.Client(api_key=api_key)

            # Try with Google Search grounding first
            for model in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
                try:
                    try:
                        res = client.models.generate_content(
                            model=model,
                            contents=search_prompt,
                            config=types.GenerateContentConfig(
                                tools=[{"google_search": {}}],
                                temperature=0.2
                            )
                        )
                    except Exception:
                        res = client.models.generate_content(
                            model=model,
                            contents=search_prompt,
                            config=types.GenerateContentConfig(temperature=0.2)
                        )

                    if res and res.text:
                        text = res.text.strip()
                        # Strip markdown fences
                        text = re.sub(r"^```[a-z]*\n?", "", text)
                        text = re.sub(r"\n?```$", "", text)
                        match = re.search(r'\{[\s\S]*\}', text)
                        if match:
                            parsed = json.loads(match.group())
                            # Merge Gemini data (override database if we got richer data)
                            if parsed.get("kharif_crops"):
                                result["kharif_crops"] = parsed["kharif_crops"]
                            if parsed.get("rabi_crops"):
                                result["rabi_crops"] = parsed["rabi_crops"]
                            if parsed.get("perennial_or_horticulture"):
                                result["perennial_crops"] = parsed["perennial_or_horticulture"]
                            if parsed.get("major_cash_crops"):
                                result["major_crops"] = parsed["major_cash_crops"]
                            if parsed.get("emerging_crops"):
                                result["emerging_crops"] = parsed["emerging_crops"]
                            if parsed.get("local_soil_type") and not result["soil_type_regional"]:
                                result["soil_type_regional"] = parsed["local_soil_type"]
                            if parsed.get("crop_season_note"):
                                result["apmc_note"] = parsed["crop_season_note"]
                            if parsed.get("district_name"):
                                result["district"] = parsed["district_name"]
                            if parsed.get("state_name"):
                                result["state"] = parsed["state_name"]
                            result["source"] = f"gemini_search ({model})"
                            print(f"Regional Crop Lookup: Gemini found crops for {loc_query}")
                            break
                except Exception as e:
                    print(f"Gemini regional crop lookup failed ({model}): {e}")
                    continue
        except Exception as e:
            print(f"Gemini regional crop lookup global error: {e}")

    return result
