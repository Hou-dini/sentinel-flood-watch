# DESIGN_SPEC.md — Sentinel Flood-Watch

## Overview
Sentinel Flood-Watch is an intelligent, agentic monitoring system designed to proactively detect and report human encroachment, unauthorized construction, and waste dumping within Accra's critical ecological and flood-prone zones (specifically Odaw River/Korle Lagoon, Sakumono Ramsar Site, and Densu Delta Ramsar Site).

The system integrates Google Earth Engine (Sentinel-2 imagery), Google ADK (for agent execution & tool calling), and the Gemini API (for advanced vision reasoning). When an anomaly (e.g., land clearing or new structures) is identified, the agent creates a persistent record in MongoDB and triggers notifications for environmental and disaster management authorities (NADMO, AMA). A responsive, glassmorphic web dashboard visualizes the alerts on an interactive map, shows before/after satellite bands (RGB, NDVI, MNDWI), and hosts a chat interface to interact with the agent.

## Example Use Cases

### 1. Automated Monitoring Cycle
* **Input:** Scheduled trigger for Sakumono Ramsar Site coordinates.
* **Agent Logic:** Calls Earth Engine to retrieve a cloud-free baseline image from 6 months ago and the most recent cloud-free image. Calculates NDVI and MNDWI. Compares the two images.
* **Expected Output:** JSON result indicating `anomaly_detected: true`, and `summary: "Detected a 15% decrease in vegetation index (NDVI) and 4 new reflective structures within 30 meters of the lagoon buffer."` Saves alert to MongoDB.

### 2. On-Demand Chat Inquiry
* **Input:** User types: *"Check Korle Lagoon for new structures near the water."*
* **Agent Logic:** Parses coordinates for Korle Lagoon, runs the GEE scan tool, and reviews the compared Sentinel-2 images.
* **Expected Output:** Agent replies: *"I have scanned the Korle Lagoon area (5.5344° N, 0.2197° W). The NDVI index shows significant vegetation clearing on the eastern bank. I have logged this encroachment as Alert #104."*

## Tools Required

### 1. `scan_zone_tool`
* **Purpose:** Fetch Sentinel-2 before/after images, compute indices, and determine severity.
* **Arguments:** `latitude: float`, `longitude: float`, `site_name: str`
* **Returns:** Dict containing URLs for Baseline RGB, Current RGB, Baseline NDVI, Current NDVI, Baseline MNDWI, and Current MNDWI, plus temporal metadata (`baseline_date`, `current_date`, `baseline_period`, `current_period`), anomaly detection flags, a pre-computed `evidence_summary`, and deterministic `suggested_severity` / `suggested_status` fields.
* **Severity Thresholds (Quantitative):**
  - **Low:** No significant change detected (both NDVI and MNDWI change ≤ 2%).
  - **Medium:** Moderate anomaly — max absolute change between 2% and 10%.
  - **High:** Severe anomaly — max absolute change ≥ 10% in either NDVI or MNDWI, or mock fallback (no GEE data).

### 2. `send_alert_tool`
* **Purpose:** Log a detected encroachment in the persistent database.
* **Arguments:** `latitude: float`, `longitude: float`, `site_name: str`, `agent_summary: str`, `severity: str` (Low/Medium/High)
* **Returns:** Dict indicating success and the database record ID.

### 3. `mongodb_mcp_tool`
* **Purpose:** Interfaces with `mongodb-mcp-server` to execute raw database queries on the alerts and scans collections.
* **Arguments:** Executes standard MCP database commands (e.g. `mongodb_find`, `mongodb_insert-many`).
* **Tool Filter:** Only `find` and `insert-many` are exposed to the agent via `tool_filter` to restrict the attack surface and prevent unintended database mutations (e.g., delete, update).
* **Returns:** Query outputs or insertion confirmations.

## Constraints & Safety Rules
- **No False Positives:** The agent must only flag anomalies when there is visible structural or land-clearing change.
- **Strict Buffer Zones:** Flag constructions within 100 meters of designated waterways.
- **GCP Location:** Ensure Vertex AI calls use the correct region.
- **Temporal Transparency:** Every scan result includes the exact acquisition dates of the baseline and current Sentinel-2 images used for comparison, displayed on the dashboard slider labels for user verification.
- **Deterministic Severity:** Severity classification (Low / Medium / High) is computed algorithmically from NDVI/MNDWI change magnitudes in `scan_zone_tool`, not by the LLM. The agent copies the `suggested_severity` verbatim.
- **Fallback Capability:** If Earth Engine credentials are unavailable, seamlessly generate realistic mock indices based on Accra's real coordinate patterns to prevent code crashes during hackathon presentations.
- **AI Application Guardrails (Model Armor):** The agent's prompts and outputs are wrapped with a Model Armor safety template to filter jailbreaks and prompt-injections. The guardrail is configured to fail-open during API timeouts and fail-closed when a safety match occurs. PII filtering is bypassed to optimize execution latency.

## Success Criteria
- **Detection Accuracy:** Over 90% accuracy in detecting simulated/real building encroachment.
- **Latency:** Interactive scan and chat responses under 15 seconds.
- **Observability:** 100% of LLM calls, tool runs, and errors are captured via Arize Phoenix OpenTelemetry spans.

## Edge Cases to Handle
- **Severe Cloud Cover:** Sentinel-2 images are frequently cloudy in coastal West Africa. The GEE pipeline must filter for lowest cloud percentage or use composite median imaging.
- **Database Connection Failure:** If MongoDB is down, log alerts locally to `alerts_db.json` and report warning to client without failing the entire transaction.
- **Out of Accra Coordinates:** If coordinates are provided outside the Greater Accra region, notify the user that monitoring is restricted to Accra's waterways.

## Scheduled Automated Monitoring

### 1. Hybrid Scheduling Architecture
To support both containerized cloud deployment (Google Cloud Run) and local development, the scheduling system uses a hybrid architecture:
- **Serverless Webhook Trigger (Production):** The backend exposes a secure HTTP endpoint `POST /api/v1/jobs/scan`. An external cron service (like Google Cloud Scheduler) calls this endpoint periodically.
- **Lifespan Task Loop (Local Development):** When `ENABLE_LOCAL_SCHEDULER=true` is set, a lightweight background `asyncio` loop is spawned in FastAPI's startup lifespan hook, executing scans at configured intervals (`LOCAL_SCHEDULER_INTERVAL_SECONDS`).

### 2. Authorization and Security
- All webhook requests must present an `X-Job-Key` header matching `JOB_API_KEY` from the environment.
- In production, if `JOB_API_KEY` is not set, requests fail with a `500 Internal Server Error` to prevent unauthenticated execution. Locally, the system defaults to `"sentinel_dev_job_key"` if unset.

### 3. Non-Blocking Execution
- When the webhook is triggered, scans are queued using FastAPI's `BackgroundTasks` and the server immediately returns a `202 Accepted` status to prevent HTTP client timeouts.

### 4. Naming Constraints
- Scan session IDs are formatted as `scheduled-run-YYYY-MM-DD-suffix` using only lowercase alphanumeric characters and dashes to comply with Vertex AI resource name constraints (`^[a-z0-9-]+$`).
