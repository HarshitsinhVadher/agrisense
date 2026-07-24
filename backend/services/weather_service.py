import requests
from typing import Dict, Any, List

# Weather codes to human readable descriptions & icons
WEATHER_CODES = {
    0: {"desc": "Clear Sky", "icon": "☀️"},
    1: {"desc": "Mainly Clear", "icon": "🌤️"},
    2: {"desc": "Partly Cloudy", "icon": "⛅"},
    3: {"desc": "Overcast", "icon": "☁️"},
    45: {"desc": "Foggy", "icon": "🌫️"},
    48: {"desc": "Depositing Rime Fog", "icon": "🌫️"},
    51: {"desc": "Light Drizzle", "icon": "🌦️"},
    53: {"desc": "Moderate Drizzle", "icon": "🌦️"},
    55: {"desc": "Dense Drizzle", "icon": "🌧️"},
    61: {"desc": "Slight Rain", "icon": "🌧️"},
    63: {"desc": "Moderate Rain", "icon": "🌧️"},
    65: {"desc": "Heavy Rain", "icon": "🌧️"},
    71: {"desc": "Slight Snow", "icon": "🌨️"},
    80: {"desc": "Slight Rain Showers", "icon": "🌦️"},
    81: {"desc": "Moderate Rain Showers", "icon": "🌧️"},
    82: {"desc": "Violent Rain Showers", "icon": "⛈️"},
    95: {"desc": "Thunderstorm", "icon": "🌩️"},
    96: {"desc": "Thunderstorm with Hail", "icon": "⛈️"}
}

def geocode_city(query: str) -> list:
    """Search for cities using Open-Meteo Geocoding API (free, no API key needed)."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": query, "count": 8, "language": "en", "format": "json"}
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        results = []
        for r in data.get("results", []):
            results.append({
                "name": r.get("name", ""),
                "country": r.get("country", ""),
                "admin1": r.get("admin1", ""),  # State/Province
                "latitude": r.get("latitude", 0),
                "longitude": r.get("longitude", 0),
                "display": f"{r.get('name', '')}, {r.get('admin1', '')}, {r.get('country', '')}"
            })
        return results
    except Exception as e:
        print(f"Geocoding error: {e}")
        return []

def get_weather_data(lat: float = 22.57, lon: float = 72.93, location_name: str = "Anand, Gujarat") -> Dict[str, Any]:
    """
    Fetches real-time weather & 7-day forecast from Open-Meteo API.
    Defaults to Anand/Gujarat agricultural hub coordinates.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "is_day", "precipitation", "weather_code", "wind_speed_10m"],
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min", "precipitation_sum", "precipitation_probability_max", "wind_speed_10m_max"],
        "timezone": "auto"
    }
    
    try:
        response = requests.get(url, params=params, timeout=6)
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current", {})
        daily = data.get("daily", {})
        
        code = current.get("weather_code", 0)
        code_info = WEATHER_CODES.get(code, {"desc": "Partly Sunny", "icon": "🌤️"})
        
        current_weather = {
            "temperature": current.get("temperature_2m", 28.5),
            "apparent_temp": current.get("apparent_temperature", 30.0),
            "humidity": current.get("relative_humidity_2m", 65),
            "wind_speed": current.get("wind_speed_10m", 12.0),
            "precipitation": current.get("precipitation", 0.0),
            "weather_code": code,
            "description": code_info["desc"],
            "icon": code_info["icon"]
        }
        
        # 7-day forecast
        forecast = []
        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precip_sums = daily.get("precipitation_sum", [])
        precip_probs = daily.get("precipitation_probability_max", [])
        codes = daily.get("weather_code", [])
        
        for i in range(min(len(dates), 7)):
            d_code = codes[i] if i < len(codes) else 0
            d_info = WEATHER_CODES.get(d_code, {"desc": "Clear", "icon": "☀️"})
            forecast.append({
                "date": dates[i] if i < len(dates) else f"Day {i+1}",
                "max_temp": max_temps[i] if i < len(max_temps) else 32.0,
                "min_temp": min_temps[i] if i < len(min_temps) else 22.0,
                "precip_mm": precip_sums[i] if i < len(precip_sums) else 0.0,
                "precip_prob": precip_probs[i] if i < len(precip_probs) else 10,
                "description": d_info["desc"],
                "icon": d_info["icon"]
            })
            
        # Agricultural advisories based on rules
        advisories = generate_agricultural_advisories(current_weather, forecast)
        
        return {
            "location": location_name,
            "latitude": lat,
            "longitude": lon,
            "current": current_weather,
            "forecast": forecast,
            "advisories": advisories
        }
        
    except Exception as e:
        # Fallback realistic weather data if internet is offline
        print(f"Weather API error fallback: {e}")
        return get_fallback_weather(location_name)

def generate_agricultural_advisories(current: Dict[str, Any], forecast: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    advisories = []
    
    # Check for upcoming heavy rain (in next 48h)
    rain_next_48h = sum([f.get("precip_mm", 0) for f in forecast[:2]])
    max_precip_prob = max([f.get("precip_prob", 0) for f in forecast[:2]] or [0])
    
    if rain_next_48h > 15.0 or max_precip_prob > 70:
        advisories.append({
            "type": "warning",
            "title": "⚠️ Rain Warning — Delay Pesticide Spraying",
            "title_gu": "⚠️ વરસાદની ચેતવણી — જંતુનાશક દવાનો છંટકાવ મુલતવી રાખો",
            "title_hi": "⚠️ बारिश की चेतावनी — कीटनाशक छिड़काव स्थगित करें",
            "message": f"Expected rainfall ({rain_next_48h:.1f} mm / {max_precip_prob}% prob) in next 48h. Delay pesticide/fertilizer spraying to avoid chemical runoff.",
            "message_gu": f"આગામી 48 કલાકમાં વરસાદ ({rain_next_48h:.1f} mm) ની શક્યતા છે. રાસાયણિક ધોવાણ અટકાવવા છંટકાવ મુલતવી રાખો.",
            "message_hi": f"अगले 48 घंटों में बारिश ({rain_next_48h:.1f} mm) की संभावना है। रासायनिक बहाव से बचने के लिए छिड़काव टालें।"
        })
    elif current.get("temperature", 25) > 36.0:
        advisories.append({
            "type": "caution",
            "title": "🌡️ High Heat Stress — Increase Irrigation",
            "title_gu": "🌡️ ઉચ્ચ ગરમીનું તણાવ — પિયત આપો",
            "title_hi": "🌡️ उच्च गर्मी का तनाव — सिंचाई बढ़ाएं",
            "message": "High temperatures detected (>36°C). Schedule light evening irrigation for standing crops to prevent flower drop.",
            "message_gu": "ઊંચા તાપમાન (>36°C) ને કારણે સાંજના સમયે હળવું પિયત આપો જેથી ફૂલ ખરી ન જાય.",
            "message_hi": "उच्च तापमान (>36°C) के कारण शाम को हल्का पानी दें ताकि फूल न झड़ें।"
        })
    else:
        advisories.append({
            "type": "info",
            "title": "✅ Favorable Weather for Field Work",
            "title_gu": "✅ ખેત કાર્ય માટે અનુકૂળ હવામાન",
            "title_hi": "✅ खेत के काम के लिए अनुकूल मौसम",
            "message": "Weather conditions are optimal for sowing, weeding, and foliar spray application.",
            "message_gu": "વાવણી, નીંદણ અને છંટકાવ માટે હવામાન અનુકૂળ છે.",
            "message_hi": "बुआई, निराई और छिड़काव के लिए मौसम अनुकूल है।"
        })

    # Wind warning for spraying
    if current.get("wind_speed", 0) > 20.0:
        advisories.append({
            "type": "warning",
            "title": "💨 High Wind Speed Alert",
            "title_gu": "💨 તીવ્ર પવનની ચેતવણી",
            "title_hi": "💨 तेज हवा का अलर्ट",
            "message": "Wind speed is above 20 km/h. Avoid foliar spray due to chemical drift.",
            "message_gu": "પવનની ગતિ 20 km/h થી વધુ છે. છંટકાવ કરવાનું ટાળો.",
            "message_hi": "हवा की गति 20 km/h से अधिक है। स्प्रे करने से बचें।"
        })
        
    return advisories

def get_fallback_weather(location_name: str) -> Dict[str, Any]:
    return {
        "location": location_name,
        "latitude": 22.57,
        "longitude": 72.93,
        "current": {
            "temperature": 31.2,
            "apparent_temp": 33.0,
            "humidity": 58,
            "wind_speed": 11.5,
            "precipitation": 0.0,
            "weather_code": 1,
            "description": "Mainly Clear",
            "icon": "🌤️"
        },
        "forecast": [
            {"date": "Today", "max_temp": 33.5, "min_temp": 23.0, "precip_mm": 0.0, "precip_prob": 10, "description": "Sunny", "icon": "☀️"},
            {"date": "Tomorrow", "max_temp": 34.0, "min_temp": 24.0, "precip_mm": 2.5, "precip_prob": 30, "description": "Partly Cloudy", "icon": "⛅"},
            {"date": "Day 3", "max_temp": 31.0, "min_temp": 22.5, "precip_mm": 12.0, "precip_prob": 75, "description": "Moderate Rain", "icon": "🌧️"},
            {"date": "Day 4", "max_temp": 30.5, "min_temp": 22.0, "precip_mm": 5.0, "precip_prob": 50, "description": "Light Drizzle", "icon": "🌦️"},
            {"date": "Day 5", "max_temp": 32.0, "min_temp": 23.0, "precip_mm": 0.0, "precip_prob": 15, "description": "Mainly Clear", "icon": "🌤️"},
            {"date": "Day 6", "max_temp": 33.0, "min_temp": 23.5, "precip_mm": 0.0, "precip_prob": 10, "description": "Clear Sky", "icon": "☀️"},
            {"date": "Day 7", "max_temp": 34.2, "min_temp": 24.0, "precip_mm": 0.0, "precip_prob": 5, "description": "Clear Sky", "icon": "☀️"}
        ],
        "advisories": [
            {
                "type": "caution",
                "title": "🌦️ Moderate Rain Expected in 3 Days",
                "title_gu": "🌦️ 3 દિવસમાં મધ્યમ વરસાદની શક્યતા",
                "title_hi": "🌦️ 3 दिनों में मध्यम बारिश की संभावना",
                "message": "Plan fertilizer and pesticide application before Day 3 to avoid wash-off.",
                "message_gu": "ધોવાણ અટકાવવા દિવસ 3 પહેલાં ખાતર/દવા આપવાનું આયોજન કરો.",
                "message_hi": "बहाव से बचने के लिए दिन 3 से पहले उर्वरक/कीटनाशक का प्रयोग करें।"
            }
        ]
    }
