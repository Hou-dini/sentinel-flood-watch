import logging

from google.adk.tools.tool_context import ToolContext


async def lookup_coordinates_tool(
    location_name: str, tool_context: ToolContext | None = None
) -> dict:
    """Resolves a location name in Accra/Ghana to latitude and longitude coordinates.

    Use this tool when you need to inspect or scan a site whose coordinates are not
    already known.

    Args:
        location_name: The name of the site, landmark, or water body (e.g. "Weija Dam").

    Returns:
        A dictionary containing the coordinates (latitude, longitude) and resolved address.
    """
    import json
    import urllib.parse
    import urllib.request

    logging.info(f"Resolving coordinates for location: {location_name}...")
    headers = {"User-Agent": "Sentinel-Flood-Watch/1.0 (elikplim.kudowor@gmail.com)"}

    # Try searching with Accra, Ghana appended to ground it locally
    try:
        query = f"{location_name}, Accra, Ghana"
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
            {"q": query, "format": "json", "limit": 1}
        )

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        if data:
            result = data[0]
            lat = float(result["lat"])
            lon = float(result["lon"])
            display_name = result["display_name"]
            logging.info(
                f"Resolved '{location_name}' to [{lat}, {lon}] ({display_name})"
            )
            return {
                "status": "success",
                "location_name": location_name,
                "latitude": lat,
                "longitude": lon,
                "resolved_address": display_name,
            }

        # Fallback search without forcing Accra, Ghana
        url_fallback = (
            "https://nominatim.openstreetmap.org/search?"
            + urllib.parse.urlencode({"q": location_name, "format": "json", "limit": 1})
        )
        req_fallback = urllib.request.Request(url_fallback, headers=headers)
        with urllib.request.urlopen(req_fallback, timeout=10) as response:
            data = json.loads(response.read().decode())

        if data:
            result = data[0]
            lat = float(result["lat"])
            lon = float(result["lon"])
            display_name = result["display_name"]
            logging.info(
                f"Resolved '{location_name}' to [{lat}, {lon}] ({display_name})"
            )
            return {
                "status": "success",
                "location_name": location_name,
                "latitude": lat,
                "longitude": lon,
                "resolved_address": display_name,
            }

        return {
            "status": "error",
            "message": f"Could not find coordinates for location '{location_name}'. Please verify the spelling or specify coordinates manually.",
        }
    except Exception as e:
        logging.error(f"Error in coordinate lookup: {e}")
        return {"status": "error", "message": f"Error during geocoding search: {e!s}"}
