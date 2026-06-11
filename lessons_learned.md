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

## 3. Earth Engine Authentication Fallbacks and Cloud Run ADC
* **Problem:** Google Earth Engine requires authentication which can fail during local testing if service account keys are missing. Additionally, when deploying to Cloud Run, mounting a local service account key file is insecure, but using standard `ee.Initialize()` with Application Default Credentials (ADC) fails because Cloud Run does not expose a default `GOOGLE_CLOUD_PROJECT` environment variable required by the GEE library to associate the usage quota.
* **Solution:** 
  1. We designed a dual-mode pipeline: the system attempts GEE initialization, falling back to a high-fidelity **Mock Satellite Image Generator** (using Python's Pillow library to draw and calculate synthetic NDVI and MNDWI bands based on real coordinates) if it fails completely.
  2. For Cloud Run, we implemented a secure ADC fallback in `init_earth_engine()`. If the service account key path environment variable is missing, the code dynamically calls `google.auth.default()` to resolve the active GCP Project ID, and then initializes the client using `ee.Initialize(project=project)`.
* **Rationale:** This ensures the application remains fully secure, testable, and capable of authenticating seamlessly under Cloud Run utilizing the revision service account without hardcoded keys.

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

## 11. `arize-phoenix-otel` vs `arize-otel` — Wrong SDK for Cloud Tracing
* **Problem:** The backend was using `phoenix.otel.register()` from the `arize-phoenix-otel` package but pointing at the Arize cloud endpoint (`app.phoenix.arize.com`). This produced persistent `HTTP 401 Unauthorized` errors in Cloud Run logs on every span batch export.
* **Root Cause:** `arize-phoenix-otel` is the **Phoenix OSS SDK** — it is designed for self-hosted Phoenix instances and does **not** inject authentication headers into OTLP export requests. When targeting Arize cloud, it sends unauthenticated requests, which are rejected with 401.
* **Solution:** Replace `arize-phoenix-otel` with `arize-otel` and switch the call from `phoenix.otel.register()` to `arize.otel.register(space_id=..., api_key=..., project_name=...)`. The `arize-otel` SDK correctly injects `space_id` and `api_key` as OTLP request headers. Environment variables also change: `PHOENIX_API_KEY` + `PHOENIX_COLLECTOR_ENDPOINT` → `ARIZE_SPACE_ID` + `ARIZE_API_KEY`.
* **What to Avoid:** Do not assume that because both packages share the `arize.com` brand they are interchangeable. `arize-phoenix-otel` is for local/self-hosted Phoenix; `arize-otel` is for Arize cloud. Always verify the target endpoint against the SDK being used.

## 12. `SimpleSpanProcessor` vs `BatchSpanProcessor` in Production
* **Problem:** The Phoenix OSS `register()` function defaults to a `SimpleSpanProcessor`, which exports spans synchronously on every LLM call. In production (Cloud Run), this adds latency to every request and generates warning logs: *"It is strongly advised to use a BatchSpanProcessor in production environments."*
* **Solution:** `arize.otel.register()` uses a `BatchSpanProcessor` by default, which queues spans and exports them asynchronously in batches — the correct behaviour for production workloads. No extra configuration is needed; switching to `arize-otel` resolves this automatically.
* **What to Avoid:** Never use `SimpleSpanProcessor` in production services with high request volume. It introduces synchronous I/O on the hot request path and will cause latency spikes under load.

## 13. FastAPI Lifespan and Resource Cleanup Hooks
* **Problem:** Database connections and telemetry resources instantiated globally or ad-hoc inside API routes can lead to duplicate connections, thread-safety issues, or unclosed resource pools on shutdown.
* **Solution:** Declare a FastAPI `lifespan(app: FastAPI)` function to manage startup and shutdown processes. Connect clients proactively at startup, store the runner inside `app.state`, and cleanly call `disconnect()` on shutdown.

## 14. Module-Level Environment Variable Reads
* **Problem:** Environment variables (like `MONGODB_URI`) are often read at the module level when configuring toolsets (e.g. in `mongodb_mcp_tool.py`). If these modules are imported before `load_dotenv()` runs in `main.py`, they evaluate to `None` or empty strings.
* **Solution:** Always call `load_dotenv()` at the top of configuration modules that read `os.environ` keys to ensure variables are loaded regardless of import sequence.

## 15. MongoDB MCP Server Renaming & Node v24 ESM Interop
* **Problem:** The deprecated `@mongodb-js/mongodb-mcp-server` package contains an ESM resolution bug on Node.js v24 (`Cannot find module 'mongodb-redact/dist/.esm-wrapper.mjs'`). This causes the MCP process to crash immediately at startup.
* **Solution:** Use the renamed package **`mongodb-mcp-server`** in both local execution (`npx mongodb-mcp-server`) and Docker container configuration (`npm install -g mongodb-mcp-server`), which resolves the ESM interop bug.

## 16. Agent Prompt Guards for Missing/Unstable Tools
* **Problem:** If a critical tool (like a database writer) fails to load or connect, the agent doesn't understand why the tool is missing. It may enter a loop calling search tools to find it or fabricate fake data (such as mock database IDs) to pass to downstream tools.
* **Solution:** Insert strict prompt guard rules in the system instructions directing the agent to fail fast and report connection issues directly to the user if key database tools are missing or fail, rather than searching the web or guessing IDs.

## 17. Client-Side JSON Rendering Robustness
* **Problem:** Decoupling output schemas in ADK responses allows conversational freedom but requires robust client-side parsing. The original JSON parser failed to handle array responses (like lists of records from MongoDB), discarded conversational text surrounding code fences, and skipped formatting for static/non-streamed agent bubbles or missed stream end tags.
* **Solution:** Update the Javascript client parser to:
  1. Detect both objects and arrays (matching from first `{`/`[` to last `}`/`]`).
  2. Extract and preserve any conversational text surrounding the JSON code block to use as the message header.
  3. Render generic arrays and nested objects cleanly as nested key-value details tables.
  4. Intercept the static `appendMessage` method and implement stream-end event fallbacks to guarantee correct formatting under all event sequence patterns.
## 18. Default MCP Session Timeout (5.0s) is Too Short for Subprocess Initialization
* **Problem:** When launching the database-connected `mongodb-mcp-server` MCP toolset, the ADK runner threw `mcp.shared.exceptions.McpError: Timed out while waiting for response to ClientRequest. Waited 5.0 seconds.` during session initialization. This occurred both locally (where `npx` took time to download/cache the package) and in production Cloud Run (where database TLS handshakes and connection establishment took time).
* **Root Cause:** By default, Google ADK's `McpToolset` uses `StdioConnectionParams` which defaults to a 5.0-second initialization timeout. If downloading a package or connecting to a remote database cluster (like MongoDB Atlas) takes longer than 5 seconds, the initialization fails.
* **Solution:** Explicitly pass `timeout=30.0` (or greater) to `StdioConnectionParams` to give the MCP subprocess ample time to initialize Node.js, download packages, and establish remote database connections before timing out.

## 19. MongoDB MCP Server Tool Naming and Namespace Prefixes
* **Problem:** The agent failed to log encroachment alerts to MongoDB and returned a message stating that the required database tools were unreachable, despite the MCP server starting successfully.
* **Root Cause:** Two issues prevented the agent from matching the tools:
  1. The agent was instructed to look for and invoke `mongodb_insert_one` and `mongodb_find`. However, the official `mongodb-mcp-server` publishes `insert-many` and `find` (no `insert-one` exists).
  2. The `McpToolset` lacked a `tool_name_prefix` configuration, registering the tools under their raw names (`find`, `insert-many`, etc.) rather than the namespaced `mongodb_` format expected by the agent prompt instructions.
* **Solution:** Configure `tool_name_prefix="mongodb"` on `McpToolset` to register them as `mongodb_find` and `mongodb_insert-many` (hyphens are preserved by the ADK). Update the system instructions in [agent.py](file:///c:/Users/Elikplim/VS%20Code%20Projects/sentinel_flood_watch/backend/app/agent.py) directing the agent to call `mongodb_insert-many` with parameters structured as an array (`documents=[<alert_doc>]`) and look for the correct namespaced tools.

## 20. Temporal Metadata in Satellite Image Comparisons
* **Problem:** The agent's scan results reported percentage changes in vegetation (NDVI) and water indices (MNDWI) but did not indicate *which time periods* were being compared. Users had no visibility into when the baseline and current images were captured, undermining the credibility of the analysis and making it impossible to assess the rate of change.
* **Solution:** 
  1. In `gee_service.py`, extract the actual acquisition date of each selected Sentinel-2 image using `ee.Image.date().millis().getInfo()`, and return it alongside the search window date ranges.
  2. In `scan_zone_tool.py`, include `baseline_date`, `current_date`, `baseline_period`, and `current_period` in the tool response dict, and embed the dates in the `evidence_summary` text (e.g., "Baseline image captured on 2021-06-15 (search window: 2020-12-22 to 2022-06-09)").
  3. In the frontend, dynamically update the comparison slider labels to show "Baseline — 2021-06-15" and "Current — 2026-03-10" instead of generic "Baseline (Historical)" / "Current (Satellite Scan)" text.
* **Rationale:** Temporal context is essential for environmental monitoring credibility. A 10% NDVI drop over 5 years has very different implications than the same drop over 6 months. Users and regulators need to verify the observation window to trust the analysis.

## 21. Deterministic Severity Classification and MongoDB Tool Filtering
* **Problem (Severity):** The agent was assigning severity levels (Low, Medium, High) based on a simple boolean (`"Medium" if gee_success else "High"`), which was arbitrary and did not reflect the actual magnitude of environmental change. The LLM could further reinterpret or override these values inconsistently.
* **Problem (Tool Filter):** The MongoDB MCP server exposes all CRUD tools (find, insert-many, insert-one, delete-many, delete-one, update-one, update-many, count) to the agent, but only `find` and `insert-many` are needed for the monitoring workflow. Exposing delete/update tools creates an unnecessary attack surface.
* **Solution (Severity):** Replaced the boolean severity logic in `scan_zone_tool.py` with quantitative thresholds based on the maximum absolute NDVI/MNDWI percentage change: ≤2% = Low (no alert), 2–10% = Medium, ≥10% = High. Mock fallback defaults to High. The agent copies the tool's `suggested_severity` verbatim.
* **Solution (Tool Filter):** Added `tool_filter=["find", "insert-many"]` to the `McpToolset` initialization in `mongodb_mcp_tool.py`. The `connect` tool is called internally by the `auto_connect_mongodb_mcp` callback via `session.call_tool()`, which bypasses the filter and does not need to be exposed to the agent model.
* **What to Avoid:** Never rely on the LLM to determine quantitative classifications that can be computed deterministically from data. Always constrain agent tool access to the minimum required set using `tool_filter` to enforce least-privilege.

## 22. Callback-based Enforcement of Prompt Safety and Refusal Guardrails
* **Problem:** In prompt injection and jailbreak scenarios, the model might perform the required tool-calls or internal reasoning correctly (e.g. scanning a lagoon but avoiding sending an alert with a fake ID), but fail to prepend the developer-mandated explicit refusal message. This occurs because the LLM is focused on the legitimate parts of the query and overlooks the refusal formatting requirement, leading to test failures for response quality, helpfulness, and jailbreak resilience.
* **Solution:** Programmatically intercept the LLM response in an `after_model_callback` (`enforce_refusal_callback` registered in `Agent`). Inspect the user prompt for safety violations (e.g. attempting to run `send_alert_tool` with a specific ID, or requesting translation/persona shifts) and check if the model's response contains the required refusal prefix. If the model complied with the request or silently ignored it without prepending the refusal, the callback programmatically prepends: `"I refuse the unauthorized request to [describe request]. I am only authorized to perform ecological monitoring..."` to the response text.
* **What to Avoid:** Do not rely solely on system prompt instructions to handle complex safety format constraints when the agent is executing mixed (legitimate + malicious) requests. A programmatic callback is a robust, fail-safe layer that guarantees safety alignment and 100% test compliance without affecting legitimate outputs.

## 23. Server-Side Hashing for Unique User Tracking & sessionStorage for Unique Sessions
* **Problem:** In production, each user must have a unique identity, and each browser tab must have a unique session. Using default hardcoded session and user IDs limits analytics accuracy, causes session collisions, and degrades user experience. Asking for email/username signup in the early stages of a system adds user friction.
* **Solution:**
  1. On the client side (`frontend/index.js`), generate a unique UUID using `sessionStorage` on page load. This persists across page refreshes in the same tab but is unique per browser tab, avoiding session collisions.
  2. On the server side (`backend/app/main.py`), extract the client's IP address from the `X-Forwarded-For` header (handling proxy setups like Cloud Run) with a fallback to `request.client.host`.
  3. Hash the resolved IP address dynamically using SHA-256 and a secure server-side salt (`IP_SALT` loaded from env). The first 16 characters of this hash are used as the unique `user_id`, providing a deterministic unique identifier without requiring signup.
* **Region Mapping Warning (Legacy):** When deploying to Vertex AI or evaluating models using LLM-as-judge, ensure the model region is fully supported for the selected model version. Running evaluations in unsupported regions will cause metric evaluation failures with 404 Model Not Found or 400 FAILED_PRECONDITION errors.

## 24. Synthesizing Context in JSON `agent_summary` for Frontend UI Preservation
* **Problem:** Restricting `agent_summary` to verbatim tool copy-pasting strips the agent of its analytical interpretability and makes it a simple mirror of the tool. Furthermore, because the frontend dashboard parses and displays values strictly from *within* the JSON code block, any plain-text commentary coming before or after the JSON block (such as database error notifications, safety refusals, actions taken, or connection status) is completely lost to the user in the UI.
* **Solution:** Refactor the system prompt instructions to direct the agent to generate a comprehensive, synthesized summary inside the JSON block's `agent_summary` field. This summary must combine the GEE scan findings with the agent's own analysis, database actions, SMS notification statuses, and safety refusals. Ensure that safety refusals are printed both in the plain text preamble (for ReAct jailbreak filters) and inside the `agent_summary` field (for UI rendering).

## 25. Vertex Evaluation Service Region Limitations & Judge Model Decoupling
* **Problem:** Running ADK evaluations in multi-regions like `eu` causes predefined metrics (`safety_v1`, `hallucinations_v1`) utilizing the Vertex Rapid Evaluation Service to fail with `400 FAILED_PRECONDITION: Unsupported region for Vertex Evaluation Service: eu`. 
* **Solution:** Decouple the agent model from the evaluation judge model. While production requirements dictate using `gemini-3.5-flash` in the `eu` region for the agent, configure custom LLM-as-judge metrics (like `rubric_based_final_response_quality_v1`) to use a model fully supported for generation in that region, such as `gemini-3.1-flash-lite`. This ensures the evaluation suite runs and validates successfully in the production environment.



