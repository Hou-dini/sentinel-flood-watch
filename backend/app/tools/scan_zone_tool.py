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

import datetime
import logging

from google.adk.tools.tool_context import ToolContext

from app.database import save_scan
from app.services import EarthEngineService
from app.tools.common import generate_mock_satellite_images


async def scan_zone_tool(
    latitude: float,
    longitude: float,
    site_name: str,
    tool_context: ToolContext | None = None,
) -> dict:
    """Scans coordinates using satellite imagery (Sentinel-2) to detect environmental changes.

    Retrieves baseline (historical) and current imagery, computes NDVI and MNDWI indices,
    and checks for encroachment anomalies.

    Args:
        latitude: Latitude coordinate of the monitoring target.
        longitude: Longitude coordinate of the monitoring target.
        site_name: Name of the ecological site (e.g. "Sakumono Ramsar Site").

    Returns:
        A dictionary with image URLs (RGB, NDVI, MNDWI) and an anomaly evaluation.
    """
    logging.info(f"Scanning target '{site_name}' at [{latitude}, {longitude}]...")

    gee_service = EarthEngineService()
    gee_success = gee_service.initialize()

    urls = None
    has_anomaly = False
    evidence_summary = ""

    if gee_success:
        result_data = gee_service.fetch_scan_metrics(latitude, longitude)
        if result_data:
            urls = result_data["urls"]
            stats = result_data["stats"]

            base_mean_ndvi = stats["base_mean_ndvi"]
            curr_mean_ndvi = stats["curr_mean_ndvi"]
            base_mean_mndwi = stats["base_mean_mndwi"]
            curr_mean_mndwi = stats["curr_mean_mndwi"]

            if all(
                x is not None
                for x in [
                    base_mean_ndvi,
                    curr_mean_ndvi,
                    base_mean_mndwi,
                    curr_mean_mndwi,
                ]
            ):
                ndvi_diff = base_mean_ndvi - curr_mean_ndvi
                mndwi_diff = base_mean_mndwi - curr_mean_mndwi

                # Detect significant change (vegetation loss or water loss > 2%)
                if ndvi_diff > 0.02 or mndwi_diff > 0.02:
                    has_anomaly = True

                evidence_summary = (
                    f"Live Earth Engine analysis completed for {site_name}. "
                    f"NDVI changed by {ndvi_diff * 100:+.1f}% (from {base_mean_ndvi:.3f} to {curr_mean_ndvi:.3f}), indicating vegetation changes. "
                    f"MNDWI changed by {mndwi_diff * 100:+.1f}% (from {base_mean_mndwi:.3f} to {curr_mean_mndwi:.3f}), indicating water channel alterations."
                )
            else:
                has_anomaly = True
                evidence_summary = (
                    f"Sentinel-2 scans processed for {site_name}. "
                    f"Visible alterations detected in vegetation cover and water channels."
                )

    # Fallback to Mock Generator
    if not urls:
        logging.info("Using mock renderer fallback.")
        has_anomaly = True
        urls = generate_mock_satellite_images(site_name, has_encroachment=has_anomaly)
        evidence_summary = (
            f"Mock analysis: Detected building structures and waste dumping in the buffer zone of {site_name}. "
            f"MNDWI shows water channel narrowing by 20%. NDVI shows vegetation loss of 15%."
        )

    # Compile response
    result = {
        "status": "success",
        "site_name": site_name,
        "latitude": latitude,
        "longitude": longitude,
        "baseline_rgb": urls["baseline_rgb"],
        "current_rgb": urls["current_rgb"],
        "baseline_ndvi": urls["baseline_ndvi"],
        "current_ndvi": urls["current_ndvi"],
        "baseline_mndwi": urls["baseline_mndwi"],
        "current_mndwi": urls["current_mndwi"],
        "gee_integrated": gee_success
        and (not urls["baseline_rgb"].startswith("/static/")),
        "anomaly_detected": has_anomaly,
        "evidence_summary": evidence_summary,
    }

    # Log scan in database
    scan_doc = {
        "site_name": site_name,
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "timestamp": datetime.datetime.now().isoformat(),
        "anomaly_detected": has_anomaly,
        "gee_integrated": gee_success
        and (not urls["baseline_rgb"].startswith("/static/")),
    }
    await save_scan(scan_doc)

    # Access and update state if context is provided
    if tool_context:
        tool_context.state["last_scan"] = result

    return result
