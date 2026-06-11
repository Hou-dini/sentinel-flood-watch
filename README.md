# Sentinel Flood-Watch

[![CI/CD Pipeline](https://github.com/Hou-dini/sentinel-flood-watch/actions/workflows/ci.yml/badge.svg)](https://github.com/Hou-dini/sentinel-flood-watch/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Built with Google ADK](https://img.shields.io/badge/Built%20with-Google%20ADK-green)](https://github.com/GoogleCloudPlatform/agent-starter-pack)
[![Model](https://img.shields.io/badge/Reasoning%20Model-Gemini%203.5%20Flash-orange)](https://deepmind.google/technologies/gemini/)

Sentinel Flood-Watch is an intelligent, agentic remote sensing and monitoring system designed to proactively detect and report human encroachment, illegal construction, and waste dumping within Accra's critical ecological and flood-prone zones (specifically Odaw River, Korle Lagoon, Sakumono Ramsar Site, and Densu Delta Ramsar Site).

The system integrates **Google Earth Engine** (using Sentinel-2 imagery), **Google ADK** (for ReAct agent orchestration), and the **Gemini API** (for advanced reasoning and decision making). When an anomaly (e.g. vegetation clearing or new structures) is identified, the agent creates a persistent record in MongoDB and triggers notifications for environmental and disaster management authorities.

---

## 1. System Architecture

Sentinel Flood-Watch uses a decoupled, hybrid architecture to serve on-demand scans via a web dashboard and scheduled monitoring tasks via external cron triggers.

```mermaid
graph TD
    User([User]) -->|Web Dashboard| Frontend[HTML/JS/Leaflet UI]
    Frontend -->|SSE HTTP Chat Stream| Backend[FastAPI Backend]
    Scheduler[Google Cloud Scheduler] -->|POST /api/v1/jobs/scan| Backend
    
    subgraph FastAPI Backend App
        Backend -->|Orchestrates| AgentService[Agent Service]
        AgentService -->|Invokes| ADK[Google ADK Runner]
        ADK -->|Gemini 3.5 Flash| LLM[Vertex AI Model API]
        
        ADK -->|Tools| scan_zone_tool[scan_zone_tool]
        scan_zone_tool -->|Queries| GEE[Earth Engine Service]
        GEE -->|Fetches Sentinel-2| Sentinel[Sentinel-2 L2A Harmonized]
        
        ADK -->|Tools| mongodb_mcp[MongoDB MCP Server]
        mongodb_mcp -->|find / insert-many| MongoDB[(MongoDB Atlas)]
        
        ADK -->|Tools| send_alert_tool[send_alert_tool]
        send_alert_tool -->|SMS alerts| SMS[Twilio Alert Dispatcher]
    end
    
    Backend -->|OTel Tracing| Phoenix[Arize Phoenix Cloud]
```

---

## 2. Core Features

- **Side-by-Side Visual Comparison:** Compare historical baseline and current satellite bands (RGB, NDVI, MNDWI) using a sliding visual comparisons tool.
- **Date-Annotated Imagery Labels:** Displays the exact Sentinel-2 image acquisition dates extracted from the raster metadata on comparison slides.
- **Dynamic remote sensing indices:** Calculates vegetation (NDVI) and water indices (MNDWI) over rolling GEE collections to isolate environmental shifts.
- **Stateful Agent Chat:** Conversation stream interface visualizing the ReAct agent's thoughts, tools triggered, and analytical findings.
- **Grounded Geocoding Search:** Automatically resolves Accra landmark text queries to precise coordinates using OpenStreetMap Nominatim and DuckDuckGo API integration, preventing coordinate hallucination.
- **Interactive Legend Overlay:** Floating glassmorphic panel explaining GEE band index ranges (NDVI health metrics and MNDWI water profiles) in non-technical terms.
- **Automated Scheduled Monitoring:** Hybrid scheduler supporting secure token-authorized cloud webhooks (`POST /api/v1/jobs/scan`) for production cron jobs and local lifespan background loops (`ENABLE_LOCAL_SCHEDULER`) for developer verification. Scans run asynchronously in FastAPI's `BackgroundTasks` queue to prevent connection timeouts.
- **IP-Based Hashing & Session Storage:** Salted SHA-256 IP hashing dynamically generates a unique `user_id` to persist user state securely, combined with client-side `sessionStorage` UUIDs to avoid session collisions across browser tabs.
- **Model Armor Safety Plugin:** Protects the agent against jailbreaks and prompt-injections via a Google Cloud Model Armor integration, with a custom callback fallback ensuring 100% compliance during security incidents.

---

## 3. Directory Structure

```
sentinel_flood_watch/
├── backend/
│   ├── app/
│   │   ├── agent/             # Root ADK agent configurations and safety callbacks
│   │   ├── app_utils/         # Telemetry setups, Model Armor plugins
│   │   ├── models/            # Pydantic schemas (Alert, Scan, Coordinates)
│   │   ├── services/          # Services (EarthEngineService, DatabaseService, SchedulingService)
│   │   ├── tools/             # Modular ADK tool definitions (scan_zone, send_alert, geocoding)
│   │   └── main.py            # FastAPI Application & webhook entrypoint
│   ├── tests/
│   │   ├── unit/              # Isolated pytest unit checks (database, GEE, scheduling)
│   │   └── integration/       # ADK stream tests and session app checks
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── index.html             # Glassmorphic dark dashboard UI
│   ├── index.css              # Custom styled responsive layouts
│   └── index.js               # Leaflet maps, split slider, and chat handlers
├── credentials/               # Local GEE service account credentials (git-ignored)
├── docker-compose.yml         # Local MongoDB + FastAPI server orchestration
└── session_summary.md         # Chronological development log
```

---

## 4. Getting Started

### 4.1 Prerequisites
- **Python 3.11** (recommended: [uv](https://docs.astral.sh/uv/) for package management)
- **Node.js / npm** (required to launch the database MCP server subprocess)
- **Google Cloud SDK** (configured with Vertex AI access)
- **Docker & Docker Compose** (for running locally in containerized environments)

### 4.2 Configuration Setup
Create a `.env` file in both the project root and the `backend/` directory based on `.env.example` templates:

```ini
# GCP Platform & Vertex AI Config
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_CLOUD_MODEL=gemini-3.5-flash
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_APPLICATION_CREDENTIALS=C:/path/to/credentials/gee-key.json
MODEL_ARMOR_TEMPLATE=projects/your-gcp-project-id/locations/your-location/templates/your-template-id

# Earth Engine Service Account Key
GEE_SERVICE_ACCOUNT_KEY_PATH=C:/path/to/credentials/gee-key.json

# MongoDB Database Configuration
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?appName=Sentinel-Cluster&maxPoolSize=5
MONGODB_DB_NAME=sentinel_flood_watch
MONGODB_MAX_POOL_SIZE=5

# Arize Telemetry & Observability
PHOENIX_PROJECT_NAME=sentinel-flood-watch
ARIZE_SPACE_ID=your-arize-space-id
ARIZE_API_KEY=your-arize-api-key

# Nominatim User-Agent Email
NOMINATIM_EMAIL=your-email@example.com

# IP Hashing Salt
IP_SALT=your-random-secure-salt-string

# Automated Scheduled Monitoring Webhook Configuration
JOB_API_KEY=your-secure-webhook-api-key
ENABLE_LOCAL_SCHEDULER=true
LOCAL_SCHEDULER_INTERVAL_SECONDS=300
```

### 4.3 Running Locally via Docker Compose
To spin up both the FastAPI application and a local persistent MongoDB instance:

```bash
docker-compose up --build
```
The web dashboard will be available at `http://localhost:8000/dashboard/`.

### 4.4 Running Manually
1. **Initialize the Backend Virtual Environment:**
   ```bash
   cd backend
   uv sync
   ```
2. **Install MongoDB MCP globally:**
   ```bash
   npm install -g mongodb-mcp-server
   ```
3. **Launch the FastAPI Server:**
   ```bash
   .venv\Scripts\uvicorn app.main:app --port 8000
   ```
4. **Access the Dashboard:** Open your browser and navigate to `http://localhost:8000/dashboard/`.

---

## 5. Testing & Verification

Sentinel Flood-Watch features a comprehensive testing suite verifying model trajectories, geocoding logic, database serialization fallbacks, and scheduling triggers.

To run the tests:
```bash
cd backend
.venv\Scripts\pytest
```

---

## 6. Scheduled Scan Webhook Triggers

The system exposes a secure API endpoint to trigger automated monitoring manually or via a cloud scheduler:
- **Route:** `POST /api/v1/jobs/scan`
- **Header:** `X-Job-Key: <JOB_API_KEY>`

**Example HTTP trigger command (curl):**
```bash
curl -X POST http://localhost:8000/api/v1/jobs/scan \
  -H "X-Job-Key: sentinel_dev_job_key"
```
Scans will execute asynchronously in the background, logging metrics directly to MongoDB and forwarding alert traces to Arize Phoenix.

---

## 7. License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details.
