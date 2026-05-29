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

## 8. Modular Refactoring of Monolithic Tools
* **Problem:** Having all agent tools in a single large `tools.py` file made code reviews, unit testing, and maintenance difficult.
* **Solution:** Refactored the file into a Python package `tools/` with single-responsibility modules: `scan_zone_tool.py`, `send_alert_tool.py`, `search_alerts_tool.py`, `lookup_coordinates_tool.py`, and `web_search_tool.py`. Clean public exports are managed in `__init__.py`.

## 9. CI/CD Pipeline Mock Constraints
* **Problem:** In a standard GitHub Actions runner, cloud credentials for GCP/GEE are not available, leading to failures if integration tests run during CI.
* **Solution:** Structured tests to separate unit tests from integration tests. The CI workflow is configured to run only unit tests (`tests/unit/`) that mock live Earth Engine and GCP logging calls, keeping the build pipeline green and stable.

## 10. Multi-stage Docker Builds with `uv`
* **Problem:** Standard `pip install` in Docker builds is slow and produces bloated images containing compilers and build caches.
* **Solution:** Implemented a multi-stage Dockerfile using `uv`. The builder stage syncs dependencies in a virtual environment (`.venv`), which is then copied to a slim final runtime stage. This results in fast, cached builds and a minimal container footprint.

