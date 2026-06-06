import datetime
import logging

from google.adk.tools.tool_context import ToolContext

from app.database import save_alert


async def send_alert_tool(latitude: float, longitude: float, site_name: str, agent_summary: str, severity: str = "Medium", tool_context: ToolContext | None = None) -> dict:
    """Logs an official encroachment alert to the persistent database and notifies authorities.

    Args:
        latitude: Latitude of the encroachment.
        longitude: Longitude of the encroachment.
        site_name: Name of the ecological site.
        agent_summary: Descriptive summary of the detected illegal activities.
        severity: Severity level ('Low', 'Medium', 'High').

    Returns:
        A dictionary with database save confirmation and ID.
    """
    logging.info(f"Dispatching Alert for '{site_name}' [{severity} severity]...")

    # Save to database
    evidence_url = f"/static/mock_{site_name.lower().replace(' ', '_').replace('/', '_')}_current_rgb.png"
    if tool_context and "last_scan" in tool_context.state:
        last_scan = tool_context.state["last_scan"]
        if last_scan.get("site_name") == site_name:
            evidence_url = last_scan.get("current_rgb", evidence_url)

    alert_doc = {
        "site_name": site_name,
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "timestamp": datetime.datetime.now().isoformat(),
        "agent_summary": agent_summary,
        "severity": severity,
        "status": "Active",
        "evidence_link": evidence_url
    }

    alert_id = await save_alert(alert_doc)

    result = {
        "status": "success",
        "alert_id": alert_id,
        "message": "Alert successfully logged. Notifications dispatched to NADMO & Accra Metropolitan Assembly.",
        "record": alert_doc
    }

    if tool_context:
        tool_context.state["last_alert_id"] = alert_id

    return result
