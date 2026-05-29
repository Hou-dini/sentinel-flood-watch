# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os


def setup_telemetry() -> str | None:
    """Configure OpenTelemetry, GenAI telemetry, and Arize Phoenix tracing."""
    os.environ.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")

    # 1. Google Cloud Agent Engine Prompt-Response Telemetry
    bucket = os.environ.get("LOGS_BUCKET_NAME")
    capture_content = os.environ.get(
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
    )
    if bucket and capture_content != "false":
        logging.info(
            "Prompt-response logging enabled - mode: NO_CONTENT (metadata only, no prompts/responses)"
        )
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "NO_CONTENT"
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_FORMAT", "jsonl")
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_COMPLETION_HOOK", "upload")
        os.environ.setdefault(
            "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
        )
        commit_sha = os.environ.get("COMMIT_SHA", "dev")
        os.environ.setdefault(
            "OTEL_RESOURCE_ATTRIBUTES",
            f"service.namespace=backend,service.version={commit_sha}",
        )
        path = os.environ.get("GENAI_TELEMETRY_PATH", "completions")
        os.environ.setdefault(
            "OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH",
            f"gs://{bucket}/{path}",
        )
    else:
        logging.info(
            "Prompt-response logging disabled (set LOGS_BUCKET_NAME=gs://your-bucket and OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT to enable)"
        )

    # 2. Arize Phoenix OpenTelemetry Tracing
    try:
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor
        from phoenix.otel import register

        # Phoenix project configuration
        project = os.environ.get("PHOENIX_PROJECT_NAME", "sentinel-flood-watch")

        # Avoid OTLP 401 Unauthorized errors by validating the cloud collector credentials at startup
        endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "").rstrip("/")
        api_key = os.environ.get("PHOENIX_API_KEY", "").strip()

        if endpoint.startswith("https://app.phoenix.arize.com") or "phoenix.arize.com" in endpoint:
            if not api_key or "your_" in api_key:
                logging.info("Arize Phoenix API key is missing or placeholder. Falling back to local collector to avoid 401 unauthorized errors.")
                os.environ.pop("PHOENIX_COLLECTOR_ENDPOINT", None)
                os.environ.pop("PHOENIX_API_KEY", None)
            else:
                # Fast connection check to verify if the API key is active and valid
                try:
                    import urllib.error
                    import urllib.request

                    test_url = f"{endpoint}/v1/traces" if not endpoint.endswith("/v1/traces") else endpoint
                    req = urllib.request.Request(
                        test_url,
                        method="GET",
                        headers={"Authorization": f"Bearer {api_key}"}
                    )
                    try:
                        with urllib.request.urlopen(req, timeout=2.0):
                            pass
                    except urllib.error.HTTPError as e:
                        if e.code == 401:
                            logging.warning("Arize Phoenix API key is invalid or expired (HTTP 401). Falling back to local collector to avoid trace export errors.")
                            os.environ.pop("PHOENIX_COLLECTOR_ENDPOINT", None)
                            os.environ.pop("PHOENIX_API_KEY", None)
                        else:
                            logging.info(f"Arize Phoenix API key validation response code: {e.code}")
                except Exception as e:
                    logging.info(f"Arize Phoenix startup validation skipped: {e}")

        # Initialize tracer provider
        tracer_provider = register(
            project_name=project,
            auto_instrument=True
        )

        # Instrument ADK
        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
        logging.info("Arize Phoenix OpenTelemetry tracing initialized successfully.")
    except Exception as ex:
        logging.warning(f"Could not initialize Arize Phoenix tracing: {ex}")

    return bucket
