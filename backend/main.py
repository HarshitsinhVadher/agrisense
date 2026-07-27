import os
import sys
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Gemini API Key for AI Vision Label Scanner
os.environ["GEMINI_API_KEY"] = "AQ.Ab8RN6Js5DtkFTelDeudUBsR7OvYgi6u-45Ic7PMFR4d_h0RZA"

from models.crop_recommender import CropRecommender
from services.weather_service import get_weather_data, geocode_city
from services.ocr_service import process_soil_card_image, parse_soil_health_card_text
from services.label_service import scan_and_interpret_label, load_products_db
from services.ai_crop_advisor import generate_geographical_crop_advice, detect_default_soil_type
from services.auth_service import register_user, login_user, get_user_id_from_token
from services.db_service import (
    init_sql_db, get_farmer_profile, update_farmer_profile,
    record_soil_report_sql, record_label_scan_sql, record_crop_recommendation_sql,
    fetch_all_history_sql
)

app = FastAPI(
    title="AgriSense API v3.0 — Auth, GPS, AI Vision",
    version="3.0.0",
    description="Backend REST API: Authentication, GPS Weather, Gemini Vision Label Scanner, Crop ML, Soil OCR & SQL DB"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

recommender = CropRecommender()

# ─── Pydantic Models ───

class AuthRequest(BaseModel):
    username: str
    password: str

class CropRequest(BaseModel):
    farmer_id: int = 1
    N: float = 180.0
    P: float = 42.0
    K: float = 160.0
    temperature: float = 28.0
    humidity: float = 65.0
    ph: float = 7.2
    rainfall: float = 100.0
    soil_type: Optional[str] = "Auto-Detect"
    location_name: Optional[str] = "Anand, Gujarat"
    lang: str = "en"

class FarmerProfileUpdate(BaseModel):
    id: int = 1
    name: str = "Farmer"
    phone: str = ""
    location: str = ""
    latitude: float = 22.57
    longitude: float = 72.93
    soil_type: str = "Loamy Soil"
    N: float = 180.0
    P: float = 42.0
    K: float = 160.0
    pH: float = 7.2
    EC: float = 0.65
    OC: float = 0.52
    preferred_language: str = "en"

# ─── Helper: Extract user_id from Authorization header ───

def _get_user_id(request: Request) -> Optional[int]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return get_user_id_from_token(token)
    return None

# ─── Startup ───

@app.on_event("startup")
def startup_event():
    init_sql_db()

# ─── Health Check ───

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "app": "AgriSense Backend v3.0",
        "version": "3.0.0",
        "features": ["auth", "gps_weather", "gemini_vision", "crop_ml", "soil_ocr"],
        "gemini_api_key_set": bool(os.environ.get("GEMINI_API_KEY")),
        "model_loaded": recommender.model is not None
    }

# ─── Authentication Endpoints ───

@app.post("/api/auth/register")
def auth_register(data: AuthRequest):
    result = register_user(data.username, data.password)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@app.post("/api/auth/login")
def auth_login(data: AuthRequest):
    result = login_user(data.username, data.password)
    if result.get("error"):
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@app.get("/api/auth/me")
def auth_me(request: Request):
    user_id = _get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    profile = get_farmer_profile(user_id=user_id)
    return {"user_id": user_id, "profile": profile}

# ─── Geocoding Endpoint ───

@app.get("/api/geocode")
def geocode(query: str = Query(..., description="City name to search")):
    results = geocode_city(query)
    return {"results": results}

# ─── Weather ───

@app.get("/api/weather")
def fetch_weather(
    request: Request,
    lat: float = Query(22.57, description="Latitude"),
    lon: float = Query(72.93, description="Longitude"),
    location_name: str = Query("Anand, Gujarat", description="Location Display Name")
):
    return get_weather_data(lat=lat, lon=lon, location_name=location_name)

# ─── Crop Recommendation ───

@app.post("/api/recommend-crop")
def recommend_crop(data: CropRequest, request: Request):
    user_id = _get_user_id(request)

    # Fetch 3-month seasonal weather for location
    seasonal_weather = None
    try:
        weather_data = get_weather_data(location_name=data.location_name or "Anand, Gujarat")
        seasonal_weather = weather_data.get("seasonal_3month")
    except Exception as w_err:
        print(f"Weather fetch error in recommend_crop: {w_err}")
        seasonal_weather = None

    # AI Geographical Agronomic Reasoning
    ai_advice = generate_geographical_crop_advice(
        location_name=data.location_name or "Anand, Gujarat",
        soil_type=data.soil_type or "Auto-Detect",
        N=data.N, P=data.P, K=data.K, ph=data.ph,
        temperature=data.temperature, humidity=data.humidity, rainfall=data.rainfall,
        seasonal_weather=seasonal_weather,
        lang=data.lang
    )

    # Baseline ML predictions
    ml_predictions = recommender.predict(
        N=data.N, P=data.P, K=data.K,
        temperature=data.temperature, humidity=data.humidity,
        ph=data.ph, rainfall=data.rainfall,
        lang=data.lang
    )

    top_crop = "Crop Recommendation"
    if ai_advice.get("recommended_crops"):
        top_crop = ai_advice["recommended_crops"][0].get("crop_name", "Crop Recommendation")
    elif ml_predictions:
        top_crop = ml_predictions[0].get("name", "Unknown")

    record_crop_recommendation_sql(
        farmer_id=data.farmer_id, top_crop=top_crop, confidence=92.0,
        n=data.N, p=data.P, k=data.K, ph=data.ph,
        temp=data.temperature, humidity=data.humidity, rain=data.rainfall,
        user_id=user_id
    )

    return {
        "input_parameters": data.dict(),
        "ai_agronomic_plan": ai_advice,
        "recommendations": ml_predictions
    }

# ─── Soil Health Card Parser ───

@app.post("/api/parse-soil-card")
async def parse_soil_card(
    request: Request,
    farmer_id: int = Form(1),
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
    user_id = _get_user_id(request)

    if file:
        contents = await file.read()
        parsed = process_soil_card_image(contents)
    elif raw_text:
        parsed = parse_soil_health_card_text(raw_text)
    else:
        parsed = process_soil_card_image(b"")

    params = parsed.get("parameters", {})
    record_soil_report_sql(
        farmer_id=farmer_id,
        sample_id=f"SHC-{farmer_id}-2026",
        n=params.get("N", 180.0), p=params.get("P", 42.0),
        k=params.get("K", 160.0), ph=params.get("pH", 7.2),
        ec=params.get("EC", 0.65), oc=params.get("OC", 0.52),
        status=parsed.get("soil_status", {}),
        snippet=parsed.get("raw_text_snippet", ""),
        user_id=user_id
    )
    return parsed

# ─── Label Scanner (Gemini Vision + Fallback) ───

@app.post("/api/scan-label")
async def scan_product_label(
    request: Request,
    farmer_id: int = Form(1),
    file: Optional[UploadFile] = File(None),
    text_input: Optional[str] = Form(None),
    lang: str = Form("en")
):
    user_id = _get_user_id(request)
    image_bytes = None
    if file:
        image_bytes = await file.read()

    result = scan_and_interpret_label(image_bytes=image_bytes, text_input=text_input, lang=lang)
    matched_prod = result.get("matched_product", {}) or {}

    record_label_scan_sql(
        farmer_id=farmer_id,
        product_name=matched_prod.get("name", "Unknown"),
        confidence=result.get("match_confidence", 0.0),
        ocr_text=result.get("raw_ocr_text", ""),
        summary=result.get("ai_summary", ""),
        disclaimer=result.get("disclaimer", ""),
        user_id=user_id
    )
    return result

# ─── Products Database ───

@app.get("/api/products")
def get_products():
    return load_products_db()

# ─── Farmer Profile ───

@app.get("/api/profile")
def read_profile(request: Request, farmer_id: int = 1):
    user_id = _get_user_id(request)
    return get_farmer_profile(farmer_id=farmer_id, user_id=user_id)

@app.post("/api/profile")
def write_profile(profile: FarmerProfileUpdate, request: Request):
    user_id = _get_user_id(request)
    return update_farmer_profile(profile.dict(), farmer_id=profile.id, user_id=user_id)

# ─── History ───

@app.get("/api/history")
def read_history(request: Request, farmer_id: int = 1):
    user_id = _get_user_id(request)
    return fetch_all_history_sql(farmer_id=farmer_id, user_id=user_id)

# ─── Static Frontend Mount ───

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def read_root():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "AgriSense v3.0 API Server Active."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
