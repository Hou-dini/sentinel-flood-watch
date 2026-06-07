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

from google.adk.tools.tool_context import ToolContext

from app.database import get_alerts


async def send_alert_tool(
    alert_id: str,
    recipient: str = "+233555000111",
    tool_context: ToolContext | None = None,
) -> dict:
    """Simulates sending an SMS alert via Twilio for a pre-saved encroachment alert.

    Args:
        alert_id: The database ID of the pre-saved alert.
        recipient: The target phone number (e.g. disaster management authorities).

    Returns:
        dict: Success status and simulated SMS dispatch details.
    """
    logging.info(f"Retrieving alert '{alert_id}' for simulated SMS dispatch...")

    # Fetch alert from database
    try:
        alerts = await get_alerts()
        alert = next((a for a in alerts if a.get("id") == alert_id), None)
    except Exception as e:
        logging.error(f"Error fetching alert from database: {e}")
        alert = None

    if not alert:
        return {
            "status": "error",
            "message": f"Alert with ID {alert_id} not found in database. Cannot dispatch SMS.",
        }

    # Format the SMS alert message
    coordinates = alert.get("coordinates", {})
    lat = coordinates.get("latitude", "Unknown")
    lon = coordinates.get("longitude", "Unknown")

    message_body = (
        f"🚨 sentinel-flood-watch ALERT 🚨\n"
        f"Site: {alert.get('site_name')}\n"
        f"Severity: {alert.get('severity')}\n"
        f"Location: [{lat}, {lon}]\n"
        f"Details: {alert.get('agent_summary')[:100]}...\n"
        f"Evidence: {alert.get('evidence_link')}"
    )

    logging.info(
        f"Simulating Twilio SMS dispatch to {recipient}...\nBody:\n{message_body}"
    )

    result = {
        "status": "success",
        "message": f"SMS alert successfully dispatched to NADMO & Accra Metropolitan Assembly via simulated Twilio to {recipient}.",
        "sms_body": message_body,
        "alert_id": alert_id,
    }

    if tool_context:
        tool_context.state["last_sent_alert_id"] = alert_id

    return result
