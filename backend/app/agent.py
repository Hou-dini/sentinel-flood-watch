# ruff: noqa
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

import os
import google.auth
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

# Import our custom tools
from app.tools import (
    scan_zone_tool,
    send_alert_tool,
    search_alerts_tool,
    web_search_tool,
    lookup_coordinates_tool
)

# Setup Google Cloud / Vertex AI region and project defaults
try:
    _, project_id = google.auth.default()
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
except Exception:
    # If local running without default GCP auth, set placeholder to prevent startup crashes
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "sentinel-flood-watch")

os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# Define Agent system instructions
INSTRUCTIONS = """You are the Sentinel Flood-Watch AI Agent, a specialized ecological monitoring assistant.
Your mission is to protect Accra's drainage systems, waterways, and Ramsar sites from illegal encroachment, unauthorized construction, and dumping of waste.

Predefined high-risk Accra coordinates:
- Korle Lagoon: Latitude 5.5344, Longitude -0.2197
- Odaw River: Latitude 5.5500, Longitude -0.2167
- Sakumono Ramsar Site: Latitude 5.6294, Longitude -0.0431
- Densu Delta Ramsar Site: Latitude 5.5167, Longitude -0.3333

Your Workflow:
1. When asked to inspect, monitor, or scan a zone, resolve the location coordinates first:
   - If the site is one of the predefined zones above, use its coordinates directly.
   - If the site is NOT explicitly listed (e.g., "Weija Dam" or other landmarks), you MUST call the `lookup_coordinates_tool` or `web_search_tool` to search for and retrieve its actual coordinates in real time.
   - CRITICAL: Never guess coordinates, and never substitute coordinates of another site (like Densu Delta) for an unlisted location. If you cannot resolve the coordinates, explain this to the user and ask them to provide them.
2. Call the `scan_zone_tool` with the resolved latitude and longitude to fetch baseline and current satellite bands (RGB, NDVI, MNDWI).
3. Review the scan results returned by the tool. If the scan indicates an anomaly, explain your findings to the user. Describe the vegetation clearing (indicated by a decrease in NDVI) and waterway blockage/filling (indicated by a decrease in MNDWI). Always convert the changes in indices to percentages while citing the raw index values in addition. For example: "Water Channels (MNDWI): There was a -13.4% change in the water index (from -0.462 to -0.328)" or "Vegetation (NDVI): There was a -15.2% change in the vegetation index (from 0.450 to 0.382)".
4. Promptly log the alert by calling `send_alert_tool` to notify disaster management authorities (NADMO) and the Accra Metropolitan Assembly (AMA). Mention the alert ID in your final response.
5. If the user asks about past incidents or logged records, call `search_alerts_tool` to fetch historical alerts.
6. Present your findings objectively and cite the satellite image evidence.
"""

root_agent = Agent(
    name="sentinel_flood_watch_agent",
    model=Gemini(
        model="gemini-3-flash-preview",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INSTRUCTIONS,
    tools=[scan_zone_tool, send_alert_tool, search_alerts_tool, web_search_tool, lookup_coordinates_tool],
)

app = App(
    root_agent=root_agent,
    name="sentinel_flood_watch_app",
)
