from google.adk.tools.tool_context import ToolContext

from app.database import get_alerts


async def search_alerts_tool(query: str | None = None, tool_context: ToolContext | None = None) -> dict:
    """Queries the database for historical encroachment alerts.

    Args:
        query: Optional search keyword to filter site name or agent summary.

    Returns:
        A dictionary containing the list of matching alerts.
    """
    alerts = await get_alerts(query)
    return {
        "status": "success",
        "count": len(alerts),
        "alerts": alerts
    }
