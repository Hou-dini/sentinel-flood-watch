# Project Write-Up: Sentinel Flood-Watch

## 1. System Description & Architecture
Sentinel Flood-Watch is an agentic AI system designed to monitor urban waterways, floodplains, and Ramsar sites in Accra, Ghana. The system detects illegal structures and waste dumping that block drainage channels and cause severe seasonal flooding.

The system uses a **FastAPI backend** that hosts a Google ADK AI Agent utilizing **Gemini 3 Flash**. The backend connects to **Google Earth Engine** to pull Sentinel-2 satellite imagery. It runs on a dual trigger:
- **On-Demand Scans:** Triggered via a web chat interface.
- **Scheduled Scans:** Executed automatically (every 5 days) to check risk zones.

A **Vanilla HTML/CSS/JS web dashboard** provides:
- Leaflet-based interactive map displaying risk zones and alert pins.
- Side-by-side split screen comparisons of baseline (historical) and current imagery.
- Visual heatmaps showing Normalized Difference Vegetation Index (NDVI) and Modified Normalized Difference Water Index (MNDWI) to highlight encroachment.
- AI Chatbot for querying and commanding the monitoring agent.
- **Live Analytics Bar:** Tracks and displays live statistics including the total number of active alerts, successful scans executed, and system processing success rate.

```
+------------------------------------------+
|          Web Dashboard (UI)              |
+---------------------+--------------------+
                      |
                      | HTTP REST
                      v
+------------------------------------------+
|          FastAPI Backend (API)           |
+---------------------+--------------------+
                      |
        +-------------+-------------+
        |                           |
        v                           v
+---------------+           +---------------+
|  Google ADK   |           | Earth Engine  |
|  AI Agent     |           | / Mock Images |
+-------+-------+           +---------------+
        |                           |
        v                           v
+---------------+           +---------------+
| Arize Phoenix |           |   MongoDB /   |
| (Tracing)     |           |   JSON DB     |
+---------------+           +---------------+
```

## 2. Tech Stack
- **AI Agent Framework:** Google ADK (Agent Development Kit)
- **AI Model:** Gemini 3 Flash (`gemini-3-flash-preview`)
- **Backend Server:** FastAPI / Uvicorn (Python 3.11)
- **Data Source:** Google Earth Engine (Sentinel-2 Harmonized Surface Reflectance: `COPERNICUS/S2_SR_HARMONIZED`)
- **Database:** MongoDB Atlas (fallback to local `alerts_db.json`)
- **Observability:** Arize Phoenix / OpenInference OTel Tracing
- **Frontend:** HTML5, CSS3 (Vanilla Dark Glassmorphism), JavaScript, Leaflet.js

## 3. Engineering Decisions & Trade-Offs
- **Mock Fallback Pipeline:** To ensure the system operates during evaluation without GEE credentials, the scanner falls back to Pillow-generated mock satellite bands.
- **Async Database Connection:** We use `motor` (async MongoDB client) to keep FastAPI non-blocking, falling back to synchronous local JSON read/writes only when database connection strings are absent.
- **Vanilla CSS over Tailwind:** Vanilla CSS provides maximum speed and visual customization, fitting the responsive glassmorphic aesthetic without introducing extra build pipelines.

## 4. Key Features
- **Visual Evidence Slider:** Compare NDVI/MNDWI indices dynamically.
- **Stateful Agent Chat:** Streaming agent thoughts and actions.
- **Accra Buffers:** Specific boundaries set for Odaw River, Korle Lagoon, Sakumonor, and Densu Delta.
- **Live Analytics Widgets:** Real-time database metrics displaying scans processed, alerts sent, and execution success rates.
- **Grounded Geocoding Search:** Real-time coordinate lookup for arbitrary Accra landmarks (such as Weija Dam) via OpenStreetMap Nominatim and DuckDuckGo API integration to prevent coordinate hallucinations.

## 5. Future Roadmap
- **Real-Time SMS Alerts:** Integration with Twilio to SMS NADMO coordinators.
- **Computer Vision Model Tuning:** Train a custom YOLO model to detect roofing sheets from high-resolution imagery.
