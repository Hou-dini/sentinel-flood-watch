import logging

from google.adk.tools.tool_context import ToolContext

from app.tools.lookup_coordinates_tool import lookup_coordinates_tool


async def web_search_tool(query: str, tool_context: ToolContext | None = None) -> dict:
    """Performs a web search to gather info or lookup coordinates for Accra waterways and ecological sites.

    Args:
        query: Search query string.

    Returns:
        A dictionary containing the search results.
    """
    import json
    import urllib.parse
    import urllib.request

    logging.info(f"Searching web for: {query}...")
    try:
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
            {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
        )
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())

        abstract = data.get("AbstractText", "")
        related = data.get("RelatedTopics", [])

        results = []
        if abstract:
            results.append(f"Abstract: {abstract}")
        for topic in related[:3]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append(topic["Text"])

        if results:
            return {"status": "success", "query": query, "results": results}

        # Fallback to geocoding if they query coordinates in search
        if any(
            w in query.lower()
            for w in ["coordinate", "lat", "lon", "location", "weija", "dam"]
        ):
            # Extract clean location name
            cleaned_loc = query.lower()
            for stop in [
                "coordinates of",
                "coordinates",
                "location of",
                "location",
                "where is",
                "find",
            ]:
                cleaned_loc = cleaned_loc.replace(stop, "")
            cleaned_loc = cleaned_loc.strip()

            geo_res = await lookup_coordinates_tool(cleaned_loc)
            if geo_res["status"] == "success":
                return {
                    "status": "success",
                    "query": query,
                    "results": [
                        f"Resolved coordinates for {cleaned_loc}: Latitude {geo_res['latitude']}, Longitude {geo_res['longitude']} - {geo_res['resolved_address']}"
                    ],
                }

        return {
            "status": "success",
            "query": query,
            "results": [
                "No matching details found. Use lookup_coordinates_tool directly to resolve coordinates of specific sites."
            ],
        }
    except Exception as e:
        logging.error(f"Error in web search: {e}")
        return {"status": "error", "message": f"Web search failed: {e!s}"}
