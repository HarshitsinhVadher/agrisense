import os
import sys
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.crop_recommender import CropRecommender
from services.weather_service import get_weather_data
from services.ocr_service import process_soil_card_image, parse_soil_health_card_text
from services.label_service import scan_and_interpret_label, load_products_db
from services.db_service import (
    init_sql_db, get_farmer_profile, update_farmer_profile,
    record_soil_report_sql, record_label_scan_sql, record_crop_recommendation_sql,
    fetch_all_history_sql
)

app = FastAPI(
    title="AgriSense API — Expo Mobile & FastAPI SQL Backend",
    version="2.0.0",
    description="Backend REST API for Expo Go Mobile App: Crop ML, Weather Advisories, Soil OCR, Label Scanner & Relational SQL DB"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

recommender = CropRecommender()

class CropRequest(BaseModel):
    farmer_id: int = 1
    N: float = 180.0
    P: float = 42.0
    K: float = 160.0
    temperature: float = 28.0
    humidity: float = 65.0
    ph: float = 7.2
    rainfall: float = 100.0

class FarmerProfileUpdate(BaseModel):
    id: int = 1
    name: str = "Ramesh Patel"
    phone: str = "+91 98765 43210"
    location: str = "Anand, Gujarat"
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

@app.on_event("startup")
def startup_event():
    init_sql_db()

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "app": "AgriSense Backend",
        "version": "2.0.0",
        "database": "SQLite Relational DB",
        "model_loaded": recommender.model is not None
    }

@app.get("/api/weather")
def fetch_weather(
    lat: float = Query(22.57, description="Latitude"),
    lon: float = Query(72.93, description="Longitude"),
    location_name: str = Query("Anand, Gujarat", description="Location Display Name")
):
    return get_weather_data(lat=lat, lon=lon, location_name=location_name)

@app.post("/api/recommend-crop")
def recommend_crop(data: CropRequest):
    predictions = recommender.predict(
        N=data.N,
        P=data.P,
        K=data.K,
        temperature=data.temperature,
        humidity=data.humidity,
        ph=data.ph,
        rainfall=data.rainfall
    )
    
    top_crop = predictions[0]['name'] if predictions else "Unknown"
    confidence = predictions[0]['confidence'] if predictions else 0.0
    
    record_crop_recommendation_sql(
        farmer_id=data.farmer_id,
        top_crop=top_crop,
        confidence=confidence,
        n=data.N, p=data.P, k=data.K, ph=data.ph,
        temp=data.temperature, humidity=data.humidity, rain=data.rainfall
    )
    
    return {
        "input_parameters": data.dict(),
        "recommendations": predictions
    }

@app.post("/api/parse-soil-card")
async def parse_soil_card(
    farmer_id: int = Form(1),
    file: Optional[UploadFile] = File(None),
    raw_text: Optional[str] = Form(None)
):
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
        n=params.get("N", 180.0),
        p=params.get("P", 42.0),
        k=params.get("K", 160.0),
        ph=params.get("pH", 7.2),
        ec=params.get("EC", 0.65),
        oc=params.get("OC", 0.52),
        status=parsed.get("soil_status", {}),
        snippet=parsed.get("raw_text_snippet", "")
    )
    return parsed

@app.post("/api/scan-label")
async def scan_product_label(
    farmer_id: int = Form(1),
    file: Optional[UploadFile] = File(None),
    text_input: Optional[str] = Form(None),
    lang: str = Form("en")
):
    image_bytes = None
    if file:
        image_bytes = await file.read()

    result = scan_and_interpret_label(image_bytes=image_bytes, text_input=text_input, lang=lang)
    matched_prod = result.get("matched_product", {})
    
    record_label_scan_sql(
        farmer_id=farmer_id,
        product_name=matched_prod.get("name", "Unknown"),
        confidence=result.get("match_confidence", 0.0),
        ocr_text=result.get("raw_ocr_text", ""),
        summary=result.get("ai_summary", ""),
        disclaimer=result.get("disclaimer", "")
    )
    return result

@app.get("/api/products")
def get_products():
    return load_products_db()

@app.get("/api/profile")
def read_profile(farmer_id: int = 1):
    return get_farmer_profile(farmer_id)

@app.post("/api/profile")
def write_profile(profile: FarmerProfileUpdate):
    return update_farmer_profile(profile.dict(), profile.id)

@app.get("/api/history")
def read_history(farmer_id: int = 1):
    return fetch_all_history_sql(farmer_id)

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def read_root():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "AgriSense Expo & FastAPI API Server Active."}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
