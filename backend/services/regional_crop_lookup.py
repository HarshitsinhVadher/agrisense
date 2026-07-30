"""
regional_crop_lookup.py  v2.0
Fetches REAL crops AND CORRECT SOIL TYPE for a GPS location using:
1. District-level crop + soil database (India) — granular offline lookup
2. Nominatim reverse geocoding — district identification from GPS
3. Gemini + Google Search grounding — live production data for unknown districts
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
# DISTRICT-LEVEL DATABASE: Correct soil + real crops based on actual production
# Source: ICAR, NBSS&LUP, State Agri Depts, APMC records, ICRISAT DDP
# ─────────────────────────────────────────────────────────────────────────────
DISTRICT_CROP_DB: Dict[str, Dict] = {

    # ══════════ GUJARAT ══════════

    "kutch": {
        "state": "Gujarat",
        "soil": "Sandy Arid Soil (રેતાળ સૂકી જમીન)",
        "soil_key": "sandy arid",
        "kharif": ["Bajra (Pearl Millet)", "Castor", "Cotton", "Groundnut", "Dates (Khajoor)"],
        "rabi":   ["Wheat", "Chickpea (Chana)", "Cumin (Jeera)", "Isabgol (Psyllium)", "Mustard"],
        "perennial": ["Date Palm", "Pomegranate", "Ber (Jujube)", "Custard Apple"],
        "major_crops": ["Bajra", "Castor", "Isabgol", "Date Palm", "Cumin"],
        "emerging_crops": ["Dragon Fruit", "Pomegranate", "Senna"],
        "apmc_note": "Kutch is arid zone — Isabgol (Psyllium Husk) has premium export value. Bajra and Castor suit sandy soil. Date Palm is major perennial cash crop. Bhuj APMC has strong Castor and Cumin prices."
    },
    "bhuj": {  # Bhuj is main city of Kutch
        "state": "Gujarat",
        "soil": "Sandy Arid Soil (રેતાળ સૂકી જમીન)",
        "soil_key": "sandy arid",
        "kharif": ["Bajra (Pearl Millet)", "Castor", "Groundnut", "Sorghum (Jowar)", "Sesame (Til)"],
        "rabi":   ["Wheat", "Chickpea", "Cumin", "Isabgol", "Mustard"],
        "perennial": ["Date Palm", "Pomegranate", "Ber", "Custard Apple"],
        "major_crops": ["Bajra", "Castor", "Isabgol", "Date Palm"],
        "emerging_crops": ["Dragon Fruit", "Senna Leaf", "Millets"],
        "apmc_note": "Bhuj (Kutch district): Arid sandy soil. Bajra is primary Kharif crop. Isabgol/Psyllium is high-value export crop. Date Palm plantation is profitable perennial."
    },
    "anjar": {
        "state": "Gujarat",
        "soil": "Sandy Loam / Arid (રેતાળ-ગોરાડુ જમીન)",
        "soil_key": "sandy loam",
        "kharif": ["Bajra", "Castor", "Cotton", "Groundnut"],
        "rabi":   ["Wheat", "Cumin", "Isabgol", "Chickpea"],
        "perennial": ["Date Palm", "Ber"],
        "major_crops": ["Bajra", "Castor", "Cumin"],
        "apmc_note": "Anjar (Kutch): Sandy loam soil. Castor and Bajra dominant. Cumin is high-value winter crop."
    },
    "mandvi": {
        "state": "Gujarat",
        "soil": "Coastal Sandy Soil (દરિયાઈ રેતાળ જમીન)",
        "soil_key": "coastal sandy",
        "kharif": ["Bajra", "Groundnut", "Vegetables", "Coconut"],
        "rabi":   ["Wheat", "Vegetables", "Onion"],
        "perennial": ["Coconut", "Chiku (Sapota)", "Mango"],
        "major_crops": ["Coconut", "Groundnut", "Vegetables"],
        "apmc_note": "Mandvi coastal area: Coconut and Groundnut are primary crops. Coastal sandy soil suits Chiku and Mango."
    },
    "rajkot": {
        "state": "Gujarat",
        "soil": "Sandy Loam / Light Black (ગોરાડુ-કાળી જમીન)",
        "soil_key": "sandy loam",
        "kharif": ["Groundnut", "Cotton", "Bajra", "Castor", "Sesame (Til)"],
        "rabi":   ["Wheat", "Chickpea", "Cumin", "Mustard", "Coriander"],
        "perennial": ["Pomegranate", "Lime (Kagdi Limbu)", "Vegetables"],
        "major_crops": ["Groundnut", "Cotton", "Cumin", "Castor"],
        "emerging_crops": ["Dragon Fruit", "Strawberry", "Guava"],
        "apmc_note": "Rajkot: Core Saurashtra groundnut belt. Groundnut oil is major output. Cumin and Castor fetch excellent APMC prices. Pomegranate expanding in Gondal taluka."
    },
    "amreli": {
        "state": "Gujarat",
        "soil": "Sandy Loam / Light Black (ગોરાડુ-કાળી)",
        "soil_key": "sandy loam",
        "kharif": ["Groundnut", "Cotton", "Bajra", "Castor", "Soybean"],
        "rabi":   ["Wheat", "Chickpea", "Cumin", "Mustard"],
        "perennial": ["Mango", "Lime", "Coconut"],
        "major_crops": ["Groundnut", "Cotton", "Castor"],
        "apmc_note": "Amreli: Premium groundnut district of Saurashtra. High oil content (48%+) varieties. Cotton is 2nd major Kharif crop."
    },
    "bhavnagar": {
        "state": "Gujarat",
        "soil": "Medium Black Cotton Soil (મધ્યમ કાળી જમીન)",
        "soil_key": "black cotton",
        "kharif": ["Cotton", "Groundnut", "Bajra", "Sesame", "Castor"],
        "rabi":   ["Wheat", "Chickpea", "Mustard", "Cumin"],
        "perennial": ["Mango", "Date Palm", "Vegetables"],
        "major_crops": ["Cotton", "Groundnut", "Wheat"],
        "apmc_note": "Bhavnagar: Medium black soils support Cotton and Groundnut. Coastal area has Date Palm."
    },
    "junagadh": {
        "state": "Gujarat",
        "soil": "Sandy Loam / Laterite (ગોરાડુ-લાલ જમીન)",
        "soil_key": "sandy loam",
        "kharif": ["Groundnut", "Bajra", "Cotton", "Castor", "Mango"],
        "rabi":   ["Wheat", "Chickpea", "Cumin", "Fennel (Variyali)"],
        "perennial": ["Kesar Mango", "Banana", "Chiku (Sapota)", "Lime", "Coconut"],
        "major_crops": ["Groundnut", "Kesar Mango", "Banana", "Chiku"],
        "emerging_crops": ["Avocado", "Dragon Fruit", "Guava"],
        "apmc_note": "Junagadh: World-famous Kesar Mango (GI tag) from Gir region. Groundnut is main Kharif crop. Strong horticulture economy."
    },
    "gir somnath": {
        "state": "Gujarat",
        "soil": "Sandy Loam / Red Laterite (ગોરાડુ-લાલ)",
        "soil_key": "sandy loam",
        "kharif": ["Groundnut", "Cotton", "Bajra", "Mango (Kesar)"],
        "rabi":   ["Wheat", "Chickpea", "Vegetables"],
        "perennial": ["Kesar Mango", "Chiku", "Coconut", "Banana"],
        "major_crops": ["Kesar Mango", "Groundnut", "Coconut"],
        "apmc_note": "Gir Somnath: Kesar Mango and Chiku belt. Coconut plantation in coastal talukas."
    },
    "anand": {
        "state": "Gujarat",
        "soil": "Alluvial Sandy Loam (ગોરાડુ-કાંપ જમીન)",
        "soil_key": "alluvial",
        "kharif": ["Paddy (Rice)", "Groundnut", "Maize", "Bajra", "Cotton", "Tobacco"],
        "rabi":   ["Wheat", "Potato", "Mustard", "Chickpea", "Garlic"],
        "perennial": ["Banana", "Mango", "Tobacco", "Vegetables"],
        "major_crops": ["Paddy", "Wheat", "Groundnut", "Tobacco"],
        "emerging_crops": ["Sweet Corn", "Baby Corn", "Bt Cotton"],
        "apmc_note": "Anand: Famous for dairy (Amul). Tobacco and Paddy are key Kharif crops. Potato and Garlic in Rabi. Wheat dominates winter season."
    },
    "kheda": {
        "state": "Gujarat",
        "soil": "Alluvial Loam (કાંપ-ગોરાડુ જમીન)",
        "soil_key": "alluvial",
        "kharif": ["Paddy", "Tobacco", "Bajra", "Maize", "Cotton"],
        "rabi":   ["Wheat", "Potato", "Garlic", "Onion", "Mustard"],
        "perennial": ["Banana", "Mango", "Vegetables"],
        "major_crops": ["Tobacco", "Paddy", "Potato"],
        "apmc_note": "Kheda: Major Tobacco producing district. Paddy-Wheat rotation common. Potato and Garlic have strong Rabi returns."
    },
    "ahmedabad": {
        "state": "Gujarat",
        "soil": "Black Cotton / Sandy Loam (કાળી-ગોરાડુ)",
        "soil_key": "black cotton",
        "kharif": ["Cotton", "Groundnut", "Bajra", "Castor", "Soybean"],
        "rabi":   ["Wheat", "Chickpea", "Mustard", "Cumin", "Fennel"],
        "perennial": ["Mango", "Banana", "Vegetables"],
        "major_crops": ["Cotton", "Wheat", "Groundnut"],
        "apmc_note": "Ahmedabad: Largest APMC in Gujarat. Cotton, Castor and Cumin fetch premium prices."
    },
    "gandhinagar": {
        "state": "Gujarat",
        "soil": "Sandy Loam / Alluvial (ગોરાડુ-કાંપ)",
        "soil_key": "alluvial",
        "kharif": ["Bajra", "Groundnut", "Cotton", "Vegetables"],
        "rabi":   ["Wheat", "Mustard", "Chickpea", "Vegetables"],
        "perennial": ["Mango", "Banana", "Flowers"],
        "major_crops": ["Wheat", "Vegetables", "Bajra"],
        "apmc_note": "Gandhinagar peri-urban: High-value vegetables and flowers. Urban proximity enables direct farm-to-market."
    },
    "mehsana": {
        "state": "Gujarat",
        "soil": "Sandy / Light Alluvial (રેતાળ-ગોરાડુ)",
        "soil_key": "sandy loam",
        "kharif": ["Bajra", "Castor", "Cotton", "Groundnut", "Tobacco"],
        "rabi":   ["Wheat", "Mustard", "Cumin", "Fennel", "Potato"],
        "perennial": ["Tobacco", "Vegetables"],
        "major_crops": ["Tobacco", "Bajra", "Fennel", "Castor"],
        "apmc_note": "Mehsana: Famous for Tobacco and North Gujarat spice belt (Cumin, Fennel). Fennel fetches high export value."
    },
    "patan": {
        "state": "Gujarat",
        "soil": "Sandy / Saline Alluvial (ખારી-રેતાળ)",
        "soil_key": "sandy loam",
        "kharif": ["Bajra", "Cotton", "Groundnut", "Castor"],
        "rabi":   ["Wheat", "Mustard", "Isabgol", "Cumin"],
        "perennial": ["Date Palm"],
        "major_crops": ["Bajra", "Isabgol", "Cumin"],
        "apmc_note": "Patan: Isabgol is export-quality spice crop. Bajra thrives in sandy soils. Date Palm in Radhanpur taluka."
    },
    "banaskantha": {
        "state": "Gujarat",
        "soil": "Sandy / Alluvial (રેતાળ-કાંપ)",
        "soil_key": "sandy loam",
        "kharif": ["Bajra", "Castor", "Groundnut", "Cotton", "Sesame"],
        "rabi":   ["Wheat", "Mustard", "Cumin", "Potato", "Garlic"],
        "perennial": ["Banana", "Vegetables"],
        "major_crops": ["Potato", "Bajra", "Cumin", "Castor"],
        "emerging_crops": ["Strawberry", "Broccoli", "Sweet Potato"],
        "apmc_note": "Banaskantha: India's leading Potato producing district (Deesa). Cumin and Castor also have strong APMC returns."
    },
    "sabarkantha": {
        "state": "Gujarat",
        "soil": "Shallow Black / Red Loamy (છીછરી કાળી-લાલ)",
        "soil_key": "red loamy",
        "kharif": ["Maize", "Cotton", "Soybean", "Bajra", "Groundnut"],
        "rabi":   ["Wheat", "Chickpea", "Mustard", "Vegetables"],
        "perennial": ["Mango", "Chiku", "Vegetables"],
        "major_crops": ["Maize", "Cotton", "Mango"],
        "apmc_note": "Sabarkantha hilly region: Maize and Cotton dominant. Tribal farmers grow millets on slopes."
    },
    "surat": {
        "state": "Gujarat",
        "soil": "Alluvial / Coastal Sandy (કાંપ-દરિયાઈ)",
        "soil_key": "alluvial",
        "kharif": ["Paddy", "Sugarcane", "Vegetables", "Banana"],
        "rabi":   ["Wheat", "Vegetables", "Chickpea"],
        "perennial": ["Sugarcane", "Banana", "Mango", "Chiku (Sapota)"],
        "major_crops": ["Paddy", "Sugarcane", "Banana"],
        "apmc_note": "Surat region: Sugarcane, Paddy and coastal vegetables. Alphonso/Kesar Mango in Valsad/Navsari proximity."
    },
    "navsari": {
        "state": "Gujarat",
        "soil": "Coastal Alluvial / Laterite (કાંપ-ખડ)",
        "soil_key": "alluvial",
        "kharif": ["Paddy", "Banana", "Sugarcane", "Groundnut"],
        "rabi":   ["Wheat", "Vegetables"],
        "perennial": ["Chiku (Sapota)", "Mango (Alphonso/Kesar)", "Coconut", "Banana"],
        "major_crops": ["Chiku", "Mango", "Paddy", "Banana"],
        "emerging_crops": ["Dragon Fruit", "Avocado"],
        "apmc_note": "Navsari: Chiku (Sapota) capital of Gujarat. Alphonso and Kesar Mango orchards. Strong horticulture belt."
    },
    "vadodara": {
        "state": "Gujarat",
        "soil": "Alluvial / Medium Black (કાંપ-કાળી)",
        "soil_key": "black cotton",
        "kharif": ["Cotton", "Paddy", "Groundnut", "Soybean", "Maize"],
        "rabi":   ["Wheat", "Chickpea", "Mustard", "Vegetables"],
        "perennial": ["Mango", "Banana", "Sugarcane"],
        "major_crops": ["Cotton", "Wheat", "Paddy"],
        "apmc_note": "Vadodara: Cotton and Paddy dominant. Kesar Mango in adjacent areas. Strong APMC network."
    },
    "narmada": {
        "state": "Gujarat",
        "soil": "Medium Black / Red (મધ્યમ કાળી-લાલ)",
        "soil_key": "black cotton",
        "kharif": ["Maize", "Cotton", "Soybean", "Paddy", "Bajra"],
        "rabi":   ["Wheat", "Chickpea", "Mustard"],
        "perennial": ["Mango", "Banana"],
        "major_crops": ["Maize", "Cotton", "Soybean"],
        "apmc_note": "Narmada district: Tribal agri zone. Maize and Cotton are primary crops. Irrigation from Sardar Sarovar project."
    },

    # ══════════ MAHARASHTRA ══════════
    "pune": {
        "state": "Maharashtra", "soil": "Black Cotton / Red Laterite",
        "soil_key": "black cotton",
        "kharif": ["Soybean", "Bajra", "Maize", "Onion", "Cotton"],
        "rabi":   ["Wheat", "Chickpea", "Onion", "Potato"],
        "perennial": ["Grapes", "Pomegranate", "Sugarcane", "Tomato"],
        "major_crops": ["Grapes", "Soybean", "Onion", "Sugarcane"],
        "apmc_note": "Pune: Premium Grape wine region. Onion export hub. Soybean dominant Kharif oilseed."
    },
    "nashik": {
        "state": "Maharashtra", "soil": "Red Laterite / Black",
        "soil_key": "red loamy",
        "kharif": ["Onion", "Soybean", "Cotton", "Bajra"],
        "rabi":   ["Wheat", "Chickpea", "Onion", "Garlic"],
        "perennial": ["Grapes", "Pomegranate", "Tomato", "Strawberry"],
        "major_crops": ["Grapes", "Onion", "Tomato"],
        "apmc_note": "Nashik: India's wine and grape capital. Onion is #1 crop. Strong export demand."
    },
    "nagpur": {
        "state": "Maharashtra", "soil": "Black Cotton Soil (Vidarbha)",
        "soil_key": "black cotton",
        "kharif": ["Cotton", "Soybean", "Paddy", "Pigeonpea"],
        "rabi":   ["Wheat", "Chickpea", "Linseed"],
        "perennial": ["Nagpur Mandarin Orange", "Mango"],
        "major_crops": ["Cotton", "Soybean", "Nagpur Orange"],
        "apmc_note": "Nagpur: GI-tagged Nagpur Mandarin. Vidarbha Cotton belt."
    },

    # ══════════ PUNJAB ══════════
    "ludhiana": {
        "state": "Punjab", "soil": "Alluvial Sandy Loam",
        "soil_key": "alluvial",
        "kharif": ["Paddy", "Maize", "Cotton", "Bajra"],
        "rabi":   ["Wheat", "Mustard", "Potato", "Chickpea"],
        "perennial": ["Sugarcane", "Vegetables"],
        "major_crops": ["Paddy", "Wheat"],
        "apmc_note": "Ludhiana: Core Green Revolution wheat-paddy belt."
    },

    # ══════════ RAJASTHAN ══════════
    "jaipur": {
        "state": "Rajasthan", "soil": "Sandy Loam / Arid",
        "soil_key": "sandy loam",
        "kharif": ["Bajra", "Groundnut", "Maize", "Sorghum"],
        "rabi":   ["Wheat", "Mustard", "Chickpea", "Barley", "Cumin"],
        "perennial": ["Ber (Jujube)", "Pomegranate", "Guava"],
        "major_crops": ["Bajra", "Mustard", "Wheat", "Cumin"],
        "apmc_note": "Jaipur: Rajasthan Mustard belt. Bajra is drought-resilient Kharif."
    },
    "jodhpur": {
        "state": "Rajasthan", "soil": "Sandy / Desert Soil",
        "soil_key": "sandy arid",
        "kharif": ["Bajra", "Moth Bean", "Sesame", "Guar (Cluster Bean)"],
        "rabi":   ["Wheat", "Mustard", "Cumin", "Coriander", "Isabgol"],
        "perennial": ["Ber", "Pomegranate", "Date Palm"],
        "major_crops": ["Bajra", "Guar", "Cumin", "Isabgol"],
        "apmc_note": "Jodhpur: Desert agriculture. Guar (Cluster Bean) is major export crop for oil industry. Cumin is high-value spice."
    },

    # ══════════ UTTAR PRADESH ══════════
    "lucknow": {
        "state": "Uttar Pradesh", "soil": "Alluvial (Indo-Gangetic)",
        "soil_key": "alluvial",
        "kharif": ["Paddy", "Maize", "Sugarcane", "Arhar"],
        "rabi":   ["Wheat", "Mustard", "Potato", "Pea", "Lentil"],
        "perennial": ["Mango (Dasheri/Langra)", "Guava", "Banana"],
        "major_crops": ["Wheat", "Paddy", "Sugarcane", "Mango"],
        "apmc_note": "Lucknow: Dasheri Mango (GI). Wheat-Paddy rotation dominates."
    },

    # ══════════ MADHYA PRADESH ══════════
    "indore": {
        "state": "Madhya Pradesh", "soil": "Black Cotton Soil (Malwa)",
        "soil_key": "black cotton",
        "kharif": ["Soybean", "Maize", "Cotton", "Sorghum"],
        "rabi":   ["Wheat", "Chickpea", "Lentil", "Mustard"],
        "perennial": ["Orange", "Banana"],
        "major_crops": ["Soybean", "Wheat", "Maize"],
        "apmc_note": "Indore: Soybean capital of India. Malwa plateau is soybean heartland."
    },

    # ══════════ KARNATAKA ══════════
    "bangalore rural": {
        "state": "Karnataka", "soil": "Red Sandy Loam",
        "soil_key": "red loamy",
        "kharif": ["Ragi", "Maize", "Paddy", "Sunflower"],
        "rabi":   ["Wheat", "Chickpea", "Lentil"],
        "perennial": ["Grapes", "Mango", "Vegetables", "Flowers"],
        "major_crops": ["Ragi", "Grapes", "Flowers", "Vegetables"],
        "apmc_note": "Bangalore rural: Flower cultivation (Rose, Chrysanthemum) for export. Ragi is staple food crop."
    },
}

# State-level fallback when district not found
STATE_CROP_FALLBACK: Dict[str, Dict] = {
    "gujarat": {
        "soil": "Mixed — varies by district (Black Cotton in central, Sandy in Kutch/Saurashtra, Alluvial in central plains)",
        "soil_key": "black cotton",
        "kharif": ["Cotton", "Groundnut", "Bajra", "Castor", "Soybean", "Paddy"],
        "rabi": ["Wheat", "Chickpea", "Mustard", "Cumin", "Fennel", "Potato"],
        "perennial": ["Mango (Kesar/Alphonso)", "Banana", "Chiku", "Coconut"],
        "note": "Gujarat: Groundnut and Cotton dominate. Kutch = sandy arid; Saurashtra = sandy loam; Central = black cotton; South = alluvial."
    },
    "maharashtra": {
        "soil": "Black Cotton Soil (Vidarbha/Marathwada), Red Laterite (Western Maharashtra)",
        "soil_key": "black cotton",
        "kharif": ["Cotton", "Soybean", "Paddy", "Bajra", "Onion"],
        "rabi": ["Wheat", "Chickpea", "Onion", "Garlic"],
        "perennial": ["Sugarcane", "Grapes", "Pomegranate", "Orange"],
        "note": "Maharashtra: Vidarbha = Cotton; Western Mah = Grapes/Onion; Marathwada = Pulses."
    },
    "punjab": {
        "soil": "Alluvial Sandy Loam",
        "soil_key": "alluvial",
        "kharif": ["Paddy", "Maize", "Cotton"],
        "rabi": ["Wheat", "Mustard", "Potato"],
        "perennial": ["Sugarcane"],
        "note": "Punjab: Wheat-Paddy rotation is dominant. Green Revolution heartland."
    },
    "rajasthan": {
        "soil": "Sandy / Arid Desert Soil",
        "soil_key": "sandy arid",
        "kharif": ["Bajra", "Guar", "Moth Bean", "Sesame"],
        "rabi": ["Wheat", "Mustard", "Chickpea", "Barley", "Cumin", "Isabgol"],
        "perennial": ["Ber", "Pomegranate", "Date Palm"],
        "note": "Rajasthan: Arid agriculture. Guar, Cumin, Isabgol are export crops."
    },
    "madhya pradesh": {
        "soil": "Black Cotton Soil (Malwa Plateau)",
        "soil_key": "black cotton",
        "kharif": ["Soybean", "Cotton", "Maize", "Sorghum", "Paddy"],
        "rabi": ["Wheat", "Chickpea", "Lentil", "Mustard"],
        "perennial": ["Orange", "Banana"],
        "note": "MP: Soybean capital of India. Wheat-Chickpea rabi rotation dominant."
    },
    "karnataka": {
        "soil": "Red Loamy Soil",
        "soil_key": "red loamy",
        "kharif": ["Maize", "Paddy", "Cotton", "Ragi", "Bajra", "Sunflower"],
        "rabi": ["Wheat", "Chickpea", "Lentil"],
        "perennial": ["Coffee", "Arecanut", "Coconut", "Pomegranate"],
        "note": "Karnataka: Coffee, Ragi and Maize dominant."
    },
}


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


def lookup_district_crops(district: str, state: str) -> Optional[Dict]:
    """Look up crops + soil from district crop database with fuzzy matching."""
    d = district.lower().strip()
    s = state.lower().strip()

    # Exact or partial district match
    for key in DISTRICT_CROP_DB:
        db_entry = DISTRICT_CROP_DB[key]
        # Only match if state also aligns
        db_state = db_entry.get("state", "").lower()
        state_match = not db_state or s in db_state or db_state in s

        if state_match and (key in d or d in key or (len(d) > 3 and d[:4] in key)):
            return db_entry

    # State-level fallback
    for key in STATE_CROP_FALLBACK:
        if key in s or s in key:
            entry = STATE_CROP_FALLBACK[key].copy()
            entry["district"] = district
            return entry

    return None


def fetch_real_crops_for_location(
    lat: float,
    lon: float,
    location_name: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main function: fetches actual crops + CORRECT SOIL TYPE at GPS coordinates.
    Returns dict with kharif_crops, rabi_crops, perennial_crops, soil_type, district_info, source.
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
        "source": "none",
        "apmc_note": ""
    }

    # Step 1: Reverse geocode GPS → district
    geo = reverse_geocode_district(lat, lon)
    result["district"] = geo.get("district", "")
    result["state"] = geo.get("state", "")
    print(f"Geocoded: district='{result['district']}', state='{result['state']}', display='{geo.get('display_name','')[:60]}'")

    # Step 2: Database lookup for instant offline result
    db_data = lookup_district_crops(result["district"], result["state"])
    if db_data:
        result["kharif_crops"] = db_data.get("kharif", [])
        result["rabi_crops"] = db_data.get("rabi", [])
        result["perennial_crops"] = db_data.get("perennial", [])
        result["major_crops"] = db_data.get("major_crops", [])
        result["emerging_crops"] = db_data.get("emerging_crops", [])
        result["soil_type_regional"] = db_data.get("soil", "")
        result["soil_key"] = db_data.get("soil_key", "")
        result["apmc_note"] = db_data.get("apmc_note", "") or db_data.get("note", "")
        result["source"] = "district_database"
        print(f"DB Match: {result['district']}/{result['state']} → soil: {result['soil_type_regional']}")

    # Step 3: Gemini + Google Search for live, specific data (production statistics)
    if api_key and HAS_GEMINI:
        try:
            loc_query = location_name or f"{result['district']}, {result['state']}, India"
            search_prompt = f"""You are an Indian agricultural data expert with access to government agriculture statistics.

For the GPS location: {lat:.4f}°N, {lon:.4f}°E
Identified as: {loc_query}
District from geocoding: {result['district']}, {result['state']}

Using your knowledge of Indian district-level agriculture:

1. What is the ACTUAL DOMINANT SOIL TYPE in this specific district/taluka? (Be specific — e.g., "Sandy Arid Soil" for Kutch, "Red Laterite" for parts of Karnataka, NOT a generic answer)
2. What crops do farmers ACTUALLY GROW and SELL at the local APMC/mandi in this area?
3. What are the TOP PRODUCTION crops by area sown (hectares) in this district?
4. Any emerging/new crops being adopted in last 5 years?

Return ONLY a JSON object:
{{
    "district_name": "exact district name",
    "state_name": "state name",
    "actual_soil_type": "Specific soil type for this district (e.g. Sandy Arid Soil / Black Cotton Soil / Red Laterite / Alluvial Sandy Loam)",
    "soil_characteristics": "Brief description of soil texture and key properties",
    "kharif_crops": ["crop1 (Local name)", "crop2", "crop3", "crop4", "crop5"],
    "rabi_crops": ["crop1", "crop2", "crop3", "crop4"],
    "perennial_or_horticulture": ["fruit1", "vegetable1"],
    "major_cash_crops_by_production": ["highest production crop", "second", "third"],
    "emerging_crops_last_5_years": ["new1", "new2"],
    "local_apmc_insight": "Which crops get best APMC/mandi price in this district and why"
}}

Return ONLY JSON. No markdown. No explanation."""

            client = genai.Client(api_key=api_key)

            for model in ["gemini-2.0-flash", "gemini-1.5-flash"]:
                try:
                    try:
                        res = client.models.generate_content(
                            model=model, contents=search_prompt,
                            config=types.GenerateContentConfig(
                                tools=[{"google_search": {}}], temperature=0.1
                            )
                        )
                    except Exception:
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
                            # Override with Gemini data
                            if parsed.get("actual_soil_type"):
                                result["soil_type_regional"] = parsed["actual_soil_type"]
                                result["soil_characteristics"] = parsed.get("soil_characteristics", "")
                            if parsed.get("kharif_crops"):
                                result["kharif_crops"] = parsed["kharif_crops"]
                            if parsed.get("rabi_crops"):
                                result["rabi_crops"] = parsed["rabi_crops"]
                            if parsed.get("perennial_or_horticulture"):
                                result["perennial_crops"] = parsed["perennial_or_horticulture"]
                            if parsed.get("major_cash_crops_by_production"):
                                result["major_crops"] = parsed["major_cash_crops_by_production"]
                            if parsed.get("emerging_crops_last_5_years"):
                                result["emerging_crops"] = parsed["emerging_crops_last_5_years"]
                            if parsed.get("local_apmc_insight"):
                                result["apmc_note"] = parsed["local_apmc_insight"]
                            if parsed.get("district_name"):
                                result["district"] = parsed["district_name"]
                            if parsed.get("state_name"):
                                result["state"] = parsed["state_name"]
                            result["source"] = f"gemini_search ({model})"
                            print(f"Gemini found: soil={result['soil_type_regional']}, crops={result['kharif_crops'][:3]}")
                            break
                except Exception as e:
                    print(f"Gemini regional lookup failed ({model}): {e}")
                    continue
        except Exception as e:
            print(f"Gemini regional lookup global error: {e}")

    return result
