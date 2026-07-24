# AgriSense — AI-Powered Farming Assistant

Final Year B.E. ICT Project — Full Implementation Document & System Documentation.

---

## 🌾 Project Overview
**AgriSense** is a comprehensive, mobile-first AI-powered farming assistant built for smallholder and commercial farmers in India. It integrates four core agricultural decision-support modules with a shared farmer profile and multi-language support (English, Gujarati, Hindi).

### 🚀 Core Modules & Features

| # | Module | Core AI / Technology | Capabilities |
|---|--------|-----------------------|--------------|
| 1 | **Weather & Advisory** | Open-Meteo API + Agronomic Rule Engine | Live location-based weather, 7-day forecast, and agricultural risk warnings (rain delays for spraying, heat stress, frost alerts). |
| 2 | **Crop Recommender** | Scikit-Learn Random Forest Classifier | Trained on 2,200 soil-climate profiles (N, P, K, pH, temp, humidity, rain). Outputs top 3 suitable crops with confidence % and agronomic tips. |
| 3 | **Soil Health Card Reader** | Document OCR + RegEx Parser | Parses Govt of India Soil Health Cards (N, P, K, pH, EC, OC, Zn, Fe, Cu, Mn, B), evaluates nutrient levels, and populates the farmer profile. |
| 4 | **Product Label Scanner** | OCR + RapidFuzz + Gemini 2.5 Flash LLM | Scans seed/fertilizer/pesticide label photos, matches against a 20+ item curated database, generates plain-language AI summaries, and displays dosage safety warnings. |

---

## 🛠️ Technology Stack

- **Frontend**: Mobile-first Responsive Web App (PWA format with manifest and offline service worker)
  - HTML5, Modern CSS3 (Glassmorphism, mobile bottom navigation, earth color palette)
  - Vanilla JS ES Modules & multi-language translation dictionary (EN / GU / HI)
- **Backend**: Python 3.14 + FastAPI
- **Machine Learning**: Scikit-Learn (Random Forest Classifier trained on 22 crop classes)
- **Database**: SQLite (`agrisense.db`) + Curated Indian Fertilizer/Pesticide JSON DB (`products_db.json`)
- **APIs**: Open-Meteo (Free weather forecast) + Google Gemini API (`google-genai` for label summaries)

---

## 📁 Repository Directory Structure

```
agrisense/
├── backend/
│   ├── data/
│   │   └── products_db.json        # 20+ Curated Indian agricultural input DB
│   ├── models/
│   │   ├── train_crop_model.py     # Script to generate dataset & train RF model
│   │   ├── crop_recommender.py     # Inference engine loading model .pkl
│   │   └── crop_model.pkl          # Trained Random Forest artifact
│   ├── services/
│   │   ├── weather_service.py      # Open-Meteo API & rule engine
│   │   ├── ocr_service.py          # Soil Health Card OCR parser
│   │   ├── label_service.py        # Label matcher & Gemini LLM grounding
│   │   └── db_service.py           # SQLite manager for profile & history
│   ├── main.py                     # FastAPI application & PWA static file server
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── css/
│   │   └── styles.css              # Mobile app styling & glassmorphism system
│   ├── js/
│   │   ├── translations.js         # Multi-language dictionary (EN, GU, HI)
│   │   ├── weather_ui.js           # Weather UI renderer
│   │   ├── recommendation_ui.js    # ML recommendation UI & sliders
│   │   ├── soil_card_ui.js         # Soil Health Card OCR UI
│   │   ├── label_scanner_ui.js     # Product label scanner UI
│   │   ├── profile_ui.js           # Farmer profile & history UI
│   │   └── app.js                  # Main SPA router & state manager
│   ├── index.html                  # Mobile App frame structure
│   ├── manifest.json               # PWA manifest
│   └── sw.js                       # PWA service worker
└── README.md                       # Project documentation
```

---

## ⚡ How to Run Locally

### 1. Train the ML Crop Model
From the root directory:
```bash
python backend/models/train_crop_model.py
```
This generates `crop_dataset.csv` (2,200 rows) and trains the Random Forest model (`crop_model.pkl`), achieving ~98%+ classification accuracy.

### 2. Start the AgriSense Application Server
```bash
python backend/main.py
```
Or with Uvicorn directly:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Open in Browser / Mobile Phone
Navigate to **`http://localhost:8000`** in any web browser.
- Open Chrome DevTools -> Toggle Device Toolbar (Ctrl+Shift+M) -> Select iPhone or Pixel for full mobile experience.
- Optional: Set environment variable `GEMINI_API_KEY` for live Gemini 2.5 Flash summaries in the Label Scanner module.

---

## 🎓 Project Viva Explanation Points

1. **Why OCR + Database Grounding instead of pure CNN image classification for pesticides?**
   > *Answer*: Training a CNN for thousands of pesticide brands requires unfeasible amounts of labeled data. OCR extracting text matched against a verified chemical database combined with an LLM gives 100% accurate dosage information and eliminates dangerous AI hallucinations.
2. **Why Random Forest for Crop Recommendation?**
   > *Answer*: Random Forest is an ensemble of decision trees ideal for tabular soil-climate datasets. It provides non-linear boundary separation across NPK, pH, temperature, humidity, and rainfall, yielding high precision without overfitting.
3. **Multi-Language Social Impact**:
   > *Answer*: Grounding AI advisories in Gujarati and Hindi ensures real-world usability for Indian farmers who may not be proficient in English.
