# DESIGN_SPEC.md — Sentinel Flood-Watch

## Overview
Sentinel Flood-Watch is an intelligent, agentic monitoring system designed to proactively detect and report human encroachment, unauthorized construction, and waste dumping within Accra's critical ecological and flood-prone zones (specifically Odor River/Korle Lagoon, Sakumonor Ramsar Site, and Densu Delta Ramsar Site).

The system integrates Google Earth Engine (Sentinel-2 imagery), Google ADK (for agent execution & tool calling), and the Gemini API (for advanced vision reasoning). When an anomaly (e.g., land clearing or new structures) is identified, the agent creates a persistent record in MongoDB and triggers notifications for environmental and disaster management authorities (NADMO, AMA). A responsive, glassmorphic web dashboard visualizes the alerts on an interactive map, shows before/after satellite bands (RGB, NDVI, MNDWI), and hosts a chat interface to interact with the agent.

## Example Use Cases

### 1. Automated Monitoring Cycle
* **Input:** Scheduled trigger for Sakumo Ramsar Site coordinates.
* **Agent Logic:** Calls Earth Engine to retrieve a cloud-free baseline image from 6 months ago and the most recent cloud-free image. Calculates NDVI and MNDWI. Compares the two images.
* **Expected Output:** JSON result indicating `anomaly_detected: true`, and `summary: "Detected a 15% decrease in vegetation index (NDVI) and 4 new reflective structures within 30 meters of the lagoon buffer."` Saves alert to MongoDB.

### 2. On-Demand Chat Inquiry
* **Input:** User types: *"Check Korle Lagoon for new structures near the water."*
* **Agent Logic:** Parses coordinates for Korle Lagoon, runs the GEE scan tool, and reviews the compared Sentinel-2 images.
* **Expected Output:** Agent replies: *"I have scanned the Korle Lagoon area (5.5344° N, 0.2197° W). The NDVI index shows significant vegetation clearing on the eastern bank. I have logged this encroachment as Alert #104."*

## Tools Required

### 1. `scan_zone_tool`
* **Purpose:** Fetch Sentinel-2 before/after images and compute indices.
* **Arguments:** `latitude: float`, `longitude: float`, `site_name: str`
* **Returns:** Dict containing URLs for Baseline RGB, Current RGB, Baseline NDVI, Current NDVI, Baseline MNDWI, and Current MNDWI.

### 2. `send_alert_tool`
* **Purpose:** Log a detected encroachment in the persistent database.
* **Arguments:** `latitude: float`, `longitude: float`, `site_name: str`, `agent_summary: str`, `severity: str` (Low/Medium/High)
* **Returns:** Dict indicating success and the database record ID.

### 3. `search_alerts_tool`
* **Purpose:** Query database of existing alerts.
* **Arguments:** `query: str`
* **Returns:** List of matching alert records.

## Constraints & Safety Rules
- **No False Positives:** The agent must only flag anomalies when there is visible structural or land-clearing change.
- **Strict Buffer Zones:** Flag constructions within 100 meters of designated waterways.
- **GCP Location:** Ensure Vertex AI calls use the correct region.
- **Fallback Capability:** If Earth Engine credentials are unavailable, seamlessly generate realistic mock indices based on Accra's real coordinate patterns to prevent code crashes during hackathon presentations.

## Success Criteria
- **Detection Accuracy:** Over 90% accuracy in detecting simulated/real building encroachment.
- **Latency:** Interactive scan and chat responses under 15 seconds.
- **Observability:** 100% of LLM calls, tool runs, and errors are captured via Arize Phoenix OpenTelemetry spans.

## Edge Cases to Handle
- **Severe Cloud Cover:** Sentinel-2 images are frequently cloudy in coastal West Africa. The GEE pipeline must filter for lowest cloud percentage or use composite median imaging.
- **Database Connection Failure:** If MongoDB is down, log alerts locally to `alerts_db.json` and report warning to client without failing the entire transaction.
- **Out of Accra Coordinates:** If coordinates are provided outside the Greater Accra region, notify the user that monitoring is restricted to Accra's waterways.
