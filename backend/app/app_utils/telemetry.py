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
        from arize.otel import register
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor

        # Arize cloud credentials — must be set as environment variables.
        # Retrieve your Space ID and API Key from:
        # https://app.arize.com/organizations/-/settings/space-api-keys
        space_id = os.environ.get("ARIZE_SPACE_ID", "").strip()
        api_key = os.environ.get("ARIZE_API_KEY", "").strip()
        project = os.environ.get("PHOENIX_PROJECT_NAME", "sentinel-flood-watch")

        if not space_id or not api_key:
            logging.warning(
                "Arize tracing disabled: ARIZE_SPACE_ID and/or ARIZE_API_KEY are not set. "
                "Set them to enable trace export to Arize cloud."
            )
        else:
            # arize.otel.register() correctly:
            #   - injects space_id + api_key as OTLP request headers (fixes 401)
            #   - uses a BatchSpanProcessor by default (fixes production warning)
            tracer_provider = register(
                space_id=space_id,
                api_key=api_key,
                project_name=project,
            )

            # Instrument Google ADK so all agent runs emit spans
            GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
            logging.info("Arize OpenTelemetry tracing initialized successfully.")
    except Exception as ex:
        logging.warning(f"Could not initialize Arize tracing: {ex}")

    return bucket
