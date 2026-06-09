# Project Write-Up: Sentinel Flood-Watch

## 1. System Description & Architecture
Sentinel Flood-Watch is an agentic AI system designed to monitor urban waterways, floodplains, and Ramsar sites in Accra, Ghana. The system detects illegal structures and waste dumping that block drainage channels and cause severe seasonal flooding.

The system uses a **FastAPI backend** that hosts a Google ADK AI Agent utilizing **Gemini 2.5 Flash**. The backend connects to **Google Earth Engine** to pull Sentinel-2 satellite imagery. It runs on a dual trigger:
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
- **AI Model:** Gemini 2.5 Flash (`gemini-2.5-flash`)
- **Backend Server:** FastAPI / Uvicorn (Python 3.11)
- **Data Source:** Google Earth Engine (Sentinel-2 Harmonized Surface Reflectance: `COPERNICUS/S2_SR_HARMONIZED`)
- **Database:** MongoDB Atlas or local persistent `mongo:6.0` service (fallback to local `alerts_db.json`)
- **Production Session/Memory Persistence:** Google ADK `VertexAiSessionService` and `VertexAiMemoryBankService` (with local `InMemory` fallbacks)
- **AI Application Security:** Google Cloud Model Armor (`google-cloud-modelarmor`)
- **Observability:** Arize Phoenix / OpenInference OTel Tracing
- **Frontend:** HTML5, CSS3 (Vanilla Dark Glassmorphism), JavaScript, Leaflet.js
- **Containerization:** Docker & Docker Compose
- **CI/CD:** GitHub Actions (.github/workflows/ci.yml)
 
## 3. Engineering Decisions & Trade-Offs
- **Mock Fallback Pipeline:** To ensure the system operates during evaluation without GEE credentials, the scanner falls back to Pillow-generated mock satellite bands.
- **Async Database Connection:** We use `motor` (async MongoDB client) to keep FastAPI non-blocking, falling back to synchronous local JSON read/writes only when database connection strings are absent.
- **Vanilla CSS over Tailwind:** Vanilla CSS provides maximum speed and visual customization, fitting the responsive glassmorphic aesthetic without introducing extra build pipelines.
- **Modular Package Refactoring:** Refactored the monolithic `tools.py` into a modular `tools/` package structure to separate tool definitions (scanning, geocoding, searching, alerting) and improve maintainability.
- **CI/CD Environment Controls:** Configured GitHub Actions to only run unit tests that mock external GCP/GEE APIs, preventing build failures due to missing credentials on public runners.
- **Production Persistent State Migration:** Transitioned session and long-term memory management from transient local memory (`InMemorySessionService` and `InMemoryMemoryService`) to environment-aware persistence. In production, the system dynamically binds to Vertex AI Session Service and Memory Bank Service to support serverless container scaling, while preserving local in-memory fallbacks to keep offline developer tests fast and dependency-free.
- **Custom Security Guardrails with Model Armor:** Implemented a custom ADK safety plugin (`ModelArmorSafetyPlugin`) that intercepts LLM requests and responses. Designed a *fail-open* policy for API connection timeouts to guarantee satellite scanner availability, and a *fail-closed* policy for policy matches to protect the application from prompt-injection and jailbreak attacks. Prompt filtering is restricted to injection and jailbreaks (excluding PII scrubbing) to eliminate latency overhead for fields not present in current system inputs.

## 4. Key Features
- **Visual Evidence Slider:** Compare NDVI/MNDWI indices dynamically.
- **Stateful Agent Chat:** Streaming agent thoughts and actions.
- **Accra Buffers:** Specific boundaries set for Odaw River, Korle Lagoon, Sakumono, and Densu Delta.
- **Live Analytics Widgets:** Real-time database metrics displaying scans processed, alerts sent, and execution success rates.
- **Grounded Geocoding Search:** Real-time coordinate lookup for arbitrary Accra landmarks (such as Weija Dam) via OpenStreetMap Nominatim and DuckDuckGo API integration to prevent coordinate hallucinations.
- **Interactive Legend Overlay:** Floating glassmorphic legend next to the satellite image slider to explain NDVI, MNDWI, and RGB band outputs in non-technical terms with live updates.
- **Production Containerization:** Easy one-command local deploy utilizing Docker Compose linking FastAPI and MongoDB with volume mapping for persistence and GCP service account keys.

## 5. Future Roadmap
- **Real-Time SMS Alerts:** Integration with Twilio to SMS NADMO coordinators.
- **Computer Vision Model Tuning:** Train a custom YOLO model to detect roofing sheets from high-resolution imagery.
