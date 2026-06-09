# Session Summary - Sentinel Flood-Watch

## Session Date: May 23, 2026

### Activities Completed
1. **Design & Planning:**
   - Established the product scope for "Sentinel Flood-Watch".
   - Wrote and approved the `DESIGN_SPEC.md` specifying coordinates, example use cases, and tool specifications.
   - Initialized Git/Workspace layout planning.
2. **Project Scaffolding:**
   - Successfully scaffolded the backend codebase inside `backend/` using the Google ADK `agent-starter-pack` CLI.
   - Configured `PYTHONIOENCODING=utf-8` and skipped environment checks (`--skip-checks`) to resolve Windows-specific CLI charmap codec errors.
3. **Dependency Setup:**
   - Initiated backend package installs including `fastapi`, `uvicorn`, `earthengine-api`, `arize-phoenix-otel`, `openinference-instrumentation-google-adk`, `motor`, and `pymongo`.
4. **Documentation Artifacts Created:**
   - `project_write.md` (System overview, architecture, tech stack)
   - `lessons_learned.md` (Key engineering challenges and fixes)
   - `project_instruction.md` (Codified SOLID, CI/CD, Git philosophies)
   - `session_summary.md` (This file)

### Next Steps
- Implement Twilio alerts (SMS/Email triggers).
- Deploy to Vertex AI Agent Engine.

---

## Session Date: May 24, 2026

### Activities Completed
1. **Explain Remote Sensing Indices:**
   - Described NDVI (Normalized Difference Vegetation Index) and MNDWI (Modified Normalized Difference Water Index) calculations, formulas, and their application to Accra urban monitoring.
2. **Version Control & Repository Setup:**
   - Initialized a local Git repository in the project root.
   - Made the initial commit of all dashboard code, backend ADK modules, and mock database files.
   - Created a private remote repository `sentinel-flood-watch` on GitHub under the user's profile (`Hou-dini`) using the `gh` CLI.
   - Pushed the repository main branch to GitHub (`https://github.com/Hou-dini/sentinel-flood-watch`).

---

## Session Date: May 26, 2026

### Activities Completed
1. **Environment & Credentials Setup:**
   - Populated root-level and backend-level `.env` files with `GOOGLE_APPLICATION_CREDENTIALS` and `GEE_SERVICE_ACCOUNT_KEY_PATH` pointing to `credentials/gee-key.json` to configure secure, git-ignored service account credentials.
2. **FastAPI Serve Integration:**
   - Mounted the `frontend/` directory in FastAPI (`main.py`) to serve the dashboard interface natively at `http://localhost:8000/dashboard/`.
3. **Session & Telemetry Bug Fixes:**
   - Fixed a session runner crash in `main.py` by properly handling `get_session()` returning `None` instead of raising an exception.
   - Silenced recurring `OTLP trace exporter 401 Unauthorized` errors in `telemetry.py` by dynamically falling back to a local tracer when `PHOENIX_API_KEY` is missing.
4. **Transition to Live GEE Sentinel-2 Imagery:**
   - Replaced mock satellite imagery with the real **Harmonized Sentinel-2 Level-2A (`COPERNICUS/S2_SR_HARMONIZED`)** collection.
   - Built a dynamic pipeline in `tools.py` that computes RGB visual bands, NDVI (vegetation index), and MNDWI (water index) directly in GEE.
   - Implemented real-time GEE spatial reduction (`ee.Reducer.mean()`) to compute index shifts and detect real ecological changes (> 2% threshold).
5. **Grounded Geocoding & Hallucination Prevention:**
   - Integrated `lookup_coordinates_tool` (OpenStreetMap Nominatim geocoding) and `web_search_tool` (DuckDuckGo Instant Answers) to resolve coordinates of unlisted locations (e.g., Weija Dam) in real-time.
   - Hardened the agent system prompt instructions in `agent.py` to prevent coordinate hallucinations.
6. **Frontend Slider Updates:**
   - Modified `index.js` to dynamically support absolute GEE thumbnail URLs and parse completed SSE `scan_zone_tool` responses to immediately update the comparison slider and pan the Leaflet map.
7. **Percentage and Raw Index Citation:**
   - Formatted the agent instructions in `agent.py` to always convert index alterations to percentages and cite both percentage changes and raw index values (e.g., `"Water Channels (MNDWI): There was a -13.4% change (from -0.462 to -0.328)"`).

### Next Steps
- Implement a real/simulated Twilio SMS alert dispatcher.
- Deploy the ADK agent engine to Google Cloud Vertex AI.

---

## Session Date: May 28, 2026

### Activities Completed
1. **Explain Remote Sensing Interpretations:**
   - Documented index color mappings: explained how MNDWI maps low values to black (land/buildings) and high values to blue/cyan (water), and how NDVI maps low values to red (water/barren land) and higher values to yellow/green (vegetation).
   - Clarified the threshold rationale of `0.02` for index difference comparison as a 2% average regional shift to filter seasonal, atmospheric, and calibration noise.
2. **Dynamic Earth Engine Date Filtering:**
   - Refactored [tools.py](file:///c:/Users/Elikplim/VS%20Code%20Projects/sentinel_flood_watch/backend/app/tools.py#L183-L208) to remove hardcoded dates for Earth Engine Sentinel-2 collection queries.
   - Implemented a dynamic rolling 1.5-year (540 days) window ending on the current date for the current imagery.
   - Implemented a dynamic historical baseline window of identical length (1.5 years) offset by exactly 5 years (to align seasonal patterns and prevent false positives from wet/dry season differences).

### Next Steps
- Verify Docker execution under live environment conditions once the Docker Desktop daemon is started.
- Deploy the system using cloud platforms (e.g. Cloud Run, GCP).

---

## Session Date: May 29, 2026

### Activities Completed
1. **Decision and Approval Verification:**
   - Verified alignment with the recommendations in `implementation_plan.md`. Approved HTML-based overlay legends (rather than pixel editing) for accessibility, and a containerized local MongoDB service with Atlas fallback.
2. **Modular Backend Refactoring:**
   - Decomposed the monolithic `tools.py` into a structured, single-responsibility `tools/` package.
   - Created `common.py` (GEE init & mock generator), `scan_zone_tool.py`, `send_alert_tool.py`, `search_alerts_tool.py`, `lookup_coordinates_tool.py`, and `web_search_tool.py`.
   - Updated imports and verified that all endpoints (`main.py`) and ADK agents (`agent.py`) import correctly.
3. **CI/CD Integration:**
   - Added a GitHub Actions workflow in `.github/workflows/ci.yml` that triggers on main pushes and pull requests.
   - Set up Python, cached dependencies with `uv`, ran `ruff` linter checks, and executed unit tests under mock conditions to avoid cloud credential failures on public runners.
4. **Docker Containerization:**
   - Created a multi-stage production `Dockerfile` utilizing `uv` for dependency caching, ensuring a slim runtime image.
   - Created a `docker-compose.yml` file coordinating `sentinel_backend` and a persistent local `mongo:6.0` database service (`sentinel_mongodb`), supporting runtime secrets via a git-ignored `./credentials` volume mount.
5. **Frontend Accessibility Legends:**
   - Designed and styled a dark glassmorphic `legend-overlay-card` in `index.html` and `index.css`.
   - Programmed `index.js` to dynamically reload specific index descriptions and color-coded dot scales (RGB vegetation/water/concrete, NDVI ranges, MNDWI ranges) when the user toggles visual bands.
6. **Linter & Test Verification:**
   - Configured `pyproject.toml` to ignore module-level imports (`E402`) to accommodate `load_dotenv()` requirements, and exception chaining (`B904`).
   - Ran `ruff check .` with clean results (all checks passed).
   - Verified that the backend test suites run successfully.

### Next Steps
- Verify container startup once the Docker service is running on the host system.
- Deploy the system to Cloud Run and verify GEE/Vertex AI integrations.

---

## Session Date: June 6, 2026

### Activities Completed
1. **Dynamic GEE Project Resolution for Cloud Run:**
   - Updated the Earth Engine initialization in `app/tools/common.py` to dynamically resolve the active GCP Project ID using `google.auth.default()` when `GOOGLE_CLOUD_PROJECT` is absent. This passes the required project context to `ee.Initialize(project=project)` to ensure Application Default Credentials (ADC) work on Cloud Run.
2. **MongoDB Database ObjectId Casting:**
   - Resolved a JSON serialization crash on alert saving by converting MongoDB `ObjectId` fields to string parameters inside `app/database.py` during database insertion.
3. **Vertex AI Model Migration:**
   - Migrated the agent's LLM model from the retired/inaccessible `gemini-3-flash-preview` to **`gemini-3.5-flash`** in `app/agent.py` and evaluation configurations (`tests/eval/eval_config.json`), resolving prediction 403 API errors on Vertex AI.
   - Aligned all documentation, HTML flowchart diagrams, and specifications with the new model name.
4. **Workload Identity Federation (WIF) setup:**
   - Configured WIF resources (Workload Identity Pool `github-pool` and OIDC Provider `github-provider`) on Google Cloud, binding the GitHub repository `Hou-dini/sentinel-flood-watch` to the deployment service account.
   - Enforced OIDC attribute condition checking (`assertion.repository == 'Hou-dini/sentinel-flood-watch'`) to comply with GCP Organization Policy constraints.
   - Registered `GCP_WIF_PROVIDER` and `GCP_WIF_SERVICE_ACCOUNT` secrets directly to the GitHub repository using the GitHub CLI (`gh`).
5. **WIF Developer Skill Contribution:**
    - Created a custom reusable agent skill named `gcp-wif-github-setup` with permissive open-source metadata (`license: "Apache-2.0"` and `author: "Elikplim Kudowor (Hou-dini)"`), and copied it to the workspace's `skills/` folder to be tracked in version control.
6. **Dynamic Earth Engine Date Filtering Refactoring:**
    - Restored dynamic date calculations in `app/tools/scan_zone_tool.py` based on `datetime.date.today()` to replace the outdated, hardcoded dates (e.g. May 26th).
    - Configured the rolling window for the current collection to be the last 540 days, and the baseline collection to be a 540-day window offset by exactly 5 years (1826 days) to maintain seasonal consistency and avoid false positives.
    - Wrote unit tests in `tests/unit/test_scan_zone_tool.py` using `unittest.mock` to verify the calculated dates and mock Google Earth Engine collection filtering.
    - Ran unit tests and Ruff linter/formatter on the backend to ensure code quality and compliance.
    - Staged, committed, and pushed the changes to the remote repository.
    - Monitored the GitHub Actions CI/CD pipeline which successfully built and deployed the updated app to Cloud Run.
7. **Arize Phoenix Telemetry Connection and CLI setup:**
    - Resolved the Arize trace export issue on Cloud Run by removing a fragile urllib startup GET request validation check in `app/app_utils/telemetry.py` that incorrectly caused the system to fall back to the local collector.
    - Installed the `arize-ax-cli` tool globally on the local system and configured the active CLI profile using the `PHOENIX_API_KEY` from the environment.
    - Verified the CLI's connectivity to the Arize cloud by querying the space list successfully.
    - Staged, committed, and pushed the telemetry configuration fix to trigger the CI/CD pipeline deployment.
8. **MongoDB MCPToolset Integration:**
    - Transitioned the agent's database integration to the official MongoDB MCP server (`@mongodb-js/mongodb-mcp-server`) via Google ADK's `McpToolset` class.
    - Updated `app/agent.py` to configure the MCP `StdioConnectionParams` using `npx` and forward the `MONGODB_URI` environment variable.
    - Updated system instructions directing the agent to use its native MongoDB MCP tools to inspect and query collections directly.
    - Removed the obsolete `search_alerts_tool.py` and cleaned up package exports in `app/tools/__init__.py`.
    - Updated the `Dockerfile` to install Node.js/npm in the runtime image so that `npx` can successfully launch the MCP server on Cloud Run.
    - Verified all changes against the unit test suite and pushed them to GitHub, triggering a successful CI/CD deployment.
9. **GEE Refactoring and EarthEngineService Abstraction:**
    - Abstracted all Google Earth Engine calculations and imagery retrieval out of the 200+ line `scan_zone_tool.py` into a reusable `EarthEngineService` class in `app/services/gee_service.py`.
    - Simplified `scan_zone_tool.py` to act as a clean ADK tool wrapper, delegating all geometry building, collection queries, index calculations, and statistics reduction to the service object.
    - Updated unit tests in `tests/unit/test_scan_zone_tool.py` to cover both `EarthEngineService` (asserting date calculations and collection bounds filtering) and `scan_zone_tool` fallback behaviors.
    - Staged, committed, and pushed the refactoring to remote, leading to a successful CI/CD build and Cloud Run deployment.
10. **Database Refactoring and DatabaseService Abstraction:**
    - Abstracted all MongoDB Atlas and local file-based JSON storage operations out of `app/database.py` into a reusable `DatabaseService` class under `app/services/database_service.py`, eliminating global mutable connection state.
    - Updated `app/database.py` to act as a backward-compatible wrapper that delegates calls to a singleton `db_service = DatabaseService()` instance.
    - Created a new test suite in `tests/unit/test_database_service.py` to cover both the local JSON fallback flow and the mocked MongoDB database connection/operations flow.
    - Ran local pytest validation successfully and verified the automated CI/CD pipeline built and deployed the changes to Cloud Run.
11. **MCP Tool Refactoring and Separation:**
    - Migrated the `mongodb_mcp_tool` configuration code out of `app/agent.py` into a dedicated package `app/tools/mcp`.
    - Created `app/tools/mcp/mongodb_mcp_tool.py` and exported it via `app/tools/mcp/__init__.py`.
    - Updated the main `app/tools/__init__.py` module to import and expose `mongodb_mcp_tool` uniformly alongside other system tools.
    - Simplified `app/agent.py` to import `mongodb_mcp_tool` cleanly from `app.tools`, preserving all functionality while reducing code clutter in the agent definition.
12. **Pydantic Model Schema Enforcement:**
    - Enforced structured schemas for core domain entities by creating a new `app/models/` package.
    - Defined `Coordinates`, `Alert`, and `Scan` Pydantic models in `app/models/coordinates.py`, `app/models/alert.py`, and `app/models/scan.py` respectively.
    - Integrated model validation directly into `DatabaseService` reads and writes (`save_alert`, `get_alerts`, `save_scan`, and `get_analytics_summary`), raising validation errors if data does not match the schemas.
    - Updated the test suite in `tests/unit/test_database_service.py` to pass valid mock data matching the new schemas, ensuring all 9 unit tests pass.
13. **Separate Alert Saving from SMS Dispatching & Root Agent Schema Enforcement:**
    - Refactored `send_alert_tool` to no longer save alerts directly. It now takes an `alert_id` (retrieved from the database) and simulates sending a Twilio SMS dispatch.
    - Configured the root agent (`sentinel_flood_watch_agent`) with `output_schema=Alert` to enforce schema-adherent responses using ADK's native model-level schema reinforcement.
    - Updated agent instructions (`INSTRUCTIONS`) in `app/agent.py` to outline the structured output requirement and expected schema format.
    - Directed the root agent to structure encroachment findings into a JSON object matching the `Alert` schema, write it directly to MongoDB using the native `mongodb_insert_one` MCP tool, and then pass the resulting `inserted_id` to `send_alert_tool`.
    - Avoided any sub-agent overhead or complexity, keeping the entire workflow managed by the single root agent.
    - Created the `sentinel-alert-builder` prompt template in the Arize Prompt Hub under `elikplim Space` using the Arize CLI, and verified its template message configuration.
14. **AgentService Orchestrator, Prompt Security boundaries, and Lifespan Configuration:**
    - Created [agent_service.py](file:///C:/Users/Elikplim/VS%20Code%20Projects/sentinel_flood_watch/backend/app/services/agent_service.py) under the `services` package to encapsulate agent task execution, session setup, and output stream formatting.
    - Fortified the agent against prompt injection attacks by wrapping user input inside strict XML boundary markers (`<user_input>... </user_input>`) before building the `types.Content` request.
    - Implemented a FastAPI `lifespan(app: FastAPI)` handler in [main.py](file:///C:/Users/Elikplim/VS%20Code%20Projects/sentinel_flood_watch/backend/app/main.py) to manage telemetry setup and asynchronously initialize the ADK `Runner` and `InMemorySessionService`.
    - Attached the `Runner` instance to the FastAPI `app.state` to enable dynamic dependency injection into services like `AgentService` in API routes.
    - Created [test_agent_service.py](file:///C:/Users/Elikplim/VS%20Code%20Projects/sentinel_flood_watch/backend/tests/unit/test_agent_service.py) to verify session orchestration, security formatting, and message stream decoding.

### Next Steps
- Verify end-to-end functionality of the deployed live endpoint.

---

## Session Date: June 9, 2026

### Activities Completed
1. **Vertex AI Agent Engine Deployment:**
   - Successfully deployed the Sentinel Flood-Watch agent to **Vertex AI Agent Engine** in `europe-west1` using the project's `deploy.py` CLI script.
   - Resolved three deployment blockers encountered along the way:
     - **Wrong Python environment:** The system `PATH` resolved `python` to the Hermes agent's venv (`hermes-agent/venv`) instead of the project's `.venv`. Fixed by invoking the project venv's Python explicitly.
     - **Windows `cp1252` Unicode encoding error:** The deploy banner's box-drawing characters and emoji crashed on Windows. Fixed by setting `PYTHONIOENCODING=utf-8`.
     - **Missing `.requirements.txt`:** The deploy script (`deploy.py`) defaulted to `app/app_utils/.requirements.txt` for Agent Engine container dependencies, but the file did not exist. Created [.requirements.txt](file:///c:/Users/Elikplim/VS%20Code%20Projects/sentinel_flood_watch/backend/app/app_utils/.requirements.txt) with all production dependencies pinned to current versions.
   - The deployed Agent Engine resource ID is `2697823302562349056` in project `gen-lang-client-0892878190`.
2. **Agent Engine ID Configuration for Session & Memory Services:**
   - Investigated the `VertexAiSessionService` and `VertexAiMemoryBankService` constructor signatures. Confirmed that `VertexAiMemoryBankService` **requires** `agent_engine_id` (raises `ValueError` if missing), while `VertexAiSessionService` accepts it optionally for proper session persistence.
   - Updated [main.py](file:///c:/Users/Elikplim/VS%20Code%20Projects/sentinel_flood_watch/backend/app/main.py) to read `AGENT_ENGINE_ID` from the environment and pass it to both services, with a warning log if the variable is unset.
   - Added `AGENT_ENGINE_ID=2697823302562349056` to the backend `.env` file for local development.
3. **Deploy Script Customization:**
   - Updated default region in `deploy.py` from `us-east1` to `europe-west1` and description from `"Simple ReAct agent"` to `"Sentinel floodwatch agent"`.
4. **Deployment Metadata Update:**
   - The deployment script automatically wrote the engine resource name and timestamp to [deployment_metadata.json](file:///c:/Users/Elikplim/VS%20Code%20Projects/sentinel_flood_watch/backend/deployment_metadata.json).

### Next Steps
- Set `AGENT_ENGINE_ID` environment variable in Cloud Run.
- Verify end-to-end production functionality with persistent sessions and memory.
