# Lessons Learned - Sentinel Flood-Watch

This document captures engineering lessons, technical challenges, options considered, and design decisions made while developing the Sentinel Flood-Watch agent.

## 1. Windows Unicode Encoding Challenges in CLI
* **Problem:** Running `uvx agent-starter-pack create` failed with `Error: 'charmap' codec can't encode characters in position 2-3: character maps to <undefined>`.
* **Rationale:** On Windows, python shells often default to local code pages (like CP1252) which fail when CLI commands attempt to output UTF-8 styled unicode icons and checkmarks.
* **Solution:** Set environment variable `PYTHONIOENCODING=utf-8` before invoking the CLI to force Python to output UTF-8, and use the `--skip-checks` flag to bypass GCP credential verification checks during local scaffolding.
* **What to Avoid:** Do not attempt to rerun commands repeatedly without modifying environment settings or skipping platform checks, as this triggers loop lock failures.

## 2. API Tracing and Observability with Arize Phoenix
* **Problem:** Integrating third-party observability with Arize Phoenix alongside GCP Agent Engine.
* **Solution:** Implement the OpenTelemetry `openinference-instrumentation-google-adk` package. Configure environment variables like `PHOENIX_API_KEY` and `PHOENIX_COLLECTOR_ENDPOINT` to direct traces to the Phoenix collector.
* **Trade-Off:** Local vs. Cloud Phoenix. For development, we set up local tracing, but the code is architected to seamlessly point to Phoenix Cloud using standard environment variables.

## 3. Earth Engine Authentication Fallbacks
* **Problem:** Google Earth Engine requires authentication which can fail during local testing if service account keys are missing.
* **Solution:** Create a robust dual-mode pipeline. The system attempts to initialize GEE. On failure, it falls back to a high-fidelity **Mock Satellite Image Generator** (using Python's Pillow library to draw and calculate synthetic NDVI and MNDWI bands based on real coordinates).
* **Rationale:** This ensures the application remains fully testable, interactive, and demonstrable even in environments lacking live cloud authorization.

## 4. API Session Interface Behaviors in ADK
* **Problem:** In Google ADK's session management, `InMemorySessionService.get_session()` returns `None` rather than raising a lookup exception for non-existent session IDs.
* **Solution:** Instead of nesting the logic in `try...except Exception`, explicitly test `session is None` and then invoke `create_session()`.

## 5. OTLP Trace Exporter API Key Handshakes
* **Problem:** When integrating Arize Phoenix observability without a `PHOENIX_API_KEY`, pointing `PHOENIX_COLLECTOR_ENDPOINT` to the cloud results in spammy HTTP 401 Unauthorized errors in the console on every OTel span batch.
* **Solution:** Programmatically check if the API key is set. If missing, drop `PHOENIX_COLLECTOR_ENDPOINT` from environment variables, which forces the OpenTelemetry provider to route traces to a local collector silently.

## 6. Live Earth Engine Raster Calculations & Frontend Image Handling
* **Problem:** True Earth Engine thumbnail URLs generated via `.getThumbURL()` are absolute HTTP paths, while local mock images are relative paths (e.g. `/static/mock_...`). Prepending base URLs uniformly to all images broke absolute GEE images.
* **Solution:** Enhance the Javascript source to perform string boundary checking: only prepend the backend server origin if the URL does not begin with `http://` or `https://`. In addition, capture the SSE stream tool-response events to update the slider dynamically upon GEE computation completion.

## 7. Preventing Coordinate Hallucination with Nominatim Geocoding
* **Problem:** When asked to inspect a site outside the pre-configured high-risk zones, the LLM tended to hallucinate coordinates or default to another site because it lacked geographical grounding.
* **Solution:** Implement a keyless lookup tool utilizing the OpenStreetMap Nominatim geocoding API to resolve site coordinates in real time. Refine the system prompt to mandate geocoding lookup instead of guessing.

