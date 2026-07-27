# AgriSense — AI-Powered Farming Assistant

Final Year B.E. ICT Project — Full Implementation & Mobile System.

---

## 🌾 Project Overview
**AgriSense** is a comprehensive, mobile-first AI-powered farming assistant built for smallholder and commercial farmers in India. It integrates four core agricultural decision-support modules with a shared farmer profile and multi-language support (English, Gujarati, Hindi).

### 🚀 Core Modules & Features

| # | Module | Core AI / Technology | Capabilities |
|---|--------|-----------------------|--------------|
| 1 | **Weather & Advisory** | Open-Meteo API + 3-Month Seasonal Climate Model | Live location-based weather, 7-day forecast, 90-day seasonal rainfall/temp forecast, and agricultural risk advisories. |
| 2 | **Crop AI Recommender** | Gemini AI Reasoning + Random Forest ML | 4-Layer context fusion (Location + Soil Type + NPK Deficits + 3-Month Weather). Recommends regional crop varieties, custom fertilizer NPK schedules, and intercropping advice. |
| 3 | **Soil Health Card Reader** | Document OCR + Gemini Vision | Parses Govt of India Soil Health Cards (N, P, K, pH, EC, OC), evaluates nutrient levels, and populates the farmer profile. |
| 4 | **Product Label Scanner** | Gemini Vision LLM + Chemical DB | Scans seed/fertilizer/pesticide label photos, extracts active ingredients, recommended dosage per acre, and safety precautions. |

---

## 🛠️ Technology Stack

- **Mobile App**: React Native + Expo (Expo SDK 54)
- **Backend**: Python + FastAPI + Uvicorn
- **AI / LLM**: Google Gemini 2.0 / Flash / Pro with Search Grounding (`google-genai`)
- **Machine Learning**: Scikit-Learn (Random Forest Classifier)
- **Database**: SQLite (`agrisense.db`) + Curated Indian Fertilizer/Pesticide DB (`products_db.json`)
- **Deployment**: Render / Railway / Heroku (Backend REST API) + EAS Build (Android Standalone APK)

---

## 📁 Repository Directory Structure

```
agrisense/
├── backend/
│   ├── data/
│   │   └── products_db.json        # Curated Indian agricultural input DB
│   ├── models/
│   │   ├── crop_recommender.py     # Crop ML model inference
│   │   └── crop_model.pkl          # Trained Random Forest artifact
│   ├── services/
│   │   ├── ai_crop_advisor.py      # Geographical AI Crop Advisor (Gemini + Search)
│   │   ├── weather_service.py      # Open-Meteo 7-day & 3-month forecast
│   │   ├── label_service.py        # Gemini Vision label interpreter
│   │   ├── ocr_service.py          # Soil Health Card OCR parser
│   │   ├── auth_service.py         # JWT Token & Password Hash Auth
│   │   └── db_service.py           # SQLite DB Manager
│   ├── main.py                     # FastAPI REST API Application
│   ├── Procfile                    # Cloud hosting startup entrypoint
│   └── requirements.txt            # Python dependencies
├── mobile/
│   ├── components/
│   │   └── CameraScanner.js        # Mobile camera & gallery scanner
│   ├── App.js                      # React Native app & multi-language UI (EN, GU, HI)
│   ├── app.json                    # Expo configuration & permissions
│   ├── eas.json                    # Standalone APK build profile
│   └── package.json                # React Native & Expo dependencies
├── Procfile                        # Root deployment entrypoint
└── README.md                       # Documentation
```

---

## ⚡ How to Run Backend Locally

```bash
cd backend
pip install -r requirements.txt
python main.py
```
Backend runs on `http://localhost:8000`.

Set environment variable `GEMINI_API_KEY` for live AI Vision & Search Grounding features.
