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
