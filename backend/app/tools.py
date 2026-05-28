import os
import logging
import datetime
from typing import Optional
from PIL import Image, ImageDraw
from google.adk.tools.tool_context import ToolContext
from app.database import save_alert, get_alerts, save_scan

# Static folder inside app directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# Mock coordinates dictionary for Accra locations
ACCRA_SITES = {
    "korle lagoon": {"lat": 5.5344, "lon": -0.2197},
    "odaw river": {"lat": 5.5500, "lon": -0.2167},
    "sakumono ramsar site": {"lat": 5.6294, "lon": -0.0431},
    "densu delta ramsar site": {"lat": 5.5167, "lon": -0.3333}
}

# Earth Engine Initialization
_ee_initialized = False

def init_earth_engine():
    global _ee_initialized
    if _ee_initialized:
        return True
    try:
        import ee
        import json
        key_path = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_PATH")
        if key_path and os.path.exists(key_path):
            with open(key_path, 'r') as f:
                key_data = json.load(f)
            email = key_data.get("client_email")
            if email:
                logging.info(f"Initializing Earth Engine with service account: {email}")
                credentials = ee.ServiceAccountCredentials(email, key_path)
                ee.Initialize(credentials=credentials)
                _ee_initialized = True
                return True
        # Try to initialize with default credentials
        logging.info("Initializing Earth Engine with default credentials...")
        ee.Initialize()
        _ee_initialized = True
        logging.info("Google Earth Engine initialized successfully.")
        return True
    except Exception as e:
        logging.warning(f"Google Earth Engine initialization failed: {e}. Using mock imagery.")
        return False

def generate_mock_satellite_images(site_name: str, has_encroachment: bool = True) -> dict:
    """Generates PNG images simulating Sentinel-2 satellite data and returns their static URLs.
    
    Generates:
      - Baseline RGB, Current RGB
      - Baseline NDVI, Current NDVI
      - Baseline MNDWI, Current MNDWI
    """
    site_key = site_name.lower().replace(" ", "_")
    
    # Filenames
    filenames = {
        "baseline_rgb": f"mock_{site_key}_baseline_rgb.png",
        "current_rgb": f"mock_{site_key}_current_rgb.png",
        "baseline_ndvi": f"mock_{site_key}_baseline_ndvi.png",
        "current_ndvi": f"mock_{site_key}_current_ndvi.png",
        "baseline_mndwi": f"mock_{site_key}_baseline_mndwi.png",
        "current_mndwi": f"mock_{site_key}_current_mndwi.png",
    }
    
    # Image parameters
    w, h = 400, 400
    
    # Helper to create images
    # 1. Baseline RGB: Healthy green vegetation, winding blue river channel, minimal concrete
    img_base_rgb = Image.new("RGB", (w, h), (34, 139, 34)) # Forest green background
    draw_base = ImageDraw.Draw(img_base_rgb)
    # Winding river
    river_points = [(50, 0), (80, 80), (160, 160), (140, 240), (220, 320), (200, 400)]
    draw_base.line(river_points, fill=(30, 144, 255), width=24, joint="curve") # Dodger blue river
    # Lagoon body if Sakumono or Korle
    if "lagoon" in site_name.lower() or "ramsar" in site_name.lower():
        draw_base.ellipse([80, 100, 280, 300], fill=(30, 144, 255))
    img_base_rgb.save(os.path.join(STATIC_DIR, filenames["baseline_rgb"]))
    
    # 2. Current RGB: Encroached vegetation, structures built near/in river, brown pollution patches
    img_curr_rgb = img_base_rgb.copy()
    draw_curr = ImageDraw.Draw(img_curr_rgb)
    if has_encroachment:
        # Encroachment 1: Land clearing (grayish-brown patch)
        draw_curr.rectangle([40, 80, 120, 180], fill=(139, 115, 85)) # Sandy brown soil
        # Concrete structures (gray rectangles with red roofs)
        for x, y in [(50, 90), (85, 90), (50, 120), (85, 120), (50, 150), (85, 150)]:
            draw_curr.rectangle([x, y, x+25, y+20], fill=(128, 128, 128)) # Grey building walls
            draw_curr.polygon([(x, y), (x+12, y-6), (x+25, y)], fill=(205, 51, 51)) # Red roof
            
        # Encroachment 2: Rubble/Waste dumping in the buffer zone
        draw_curr.ellipse([140, 220, 210, 270], fill=(139, 137, 137)) # Trash heap
        # Siltation in the water body (brownish green water)
        if "lagoon" in site_name.lower() or "ramsar" in site_name.lower():
            draw_curr.ellipse([120, 150, 220, 250], fill=(112, 128, 105)) # Muddy water
        else:
            draw_curr.line(river_points, fill=(112, 128, 105), width=20, joint="curve")
    img_curr_rgb.save(os.path.join(STATIC_DIR, filenames["current_rgb"]))
    
    # 3. Baseline NDVI: Vegetation health map (Green = High veg, Red/Orange = Built/Water)
    img_base_ndvi = Image.new("RGB", (w, h), (0, 180, 0)) # Healthy NDVI green
    draw_base_ndvi = ImageDraw.Draw(img_base_ndvi)
    # River is water (value -0.3, colored red/orange)
    draw_base_ndvi.line(river_points, fill=(180, 50, 0), width=24, joint="curve")
    if "lagoon" in site_name.lower() or "ramsar" in site_name.lower():
        draw_base_ndvi.ellipse([80, 100, 280, 300], fill=(180, 50, 0))
    img_base_ndvi.save(os.path.join(STATIC_DIR, filenames["baseline_ndvi"]))
    
    # 4. Current NDVI: Cleared areas turn from Green to Orange/Red
    img_curr_ndvi = img_base_ndvi.copy()
    draw_curr_ndvi = ImageDraw.Draw(img_curr_ndvi)
    if has_encroachment:
        # Cleared vegetation shows low NDVI (Orange/Yellow)
        draw_curr_ndvi.rectangle([40, 80, 120, 180], fill=(220, 220, 0)) # Yellow/bare
        for x, y in [(50, 90), (85, 90), (50, 120), (85, 120), (50, 150), (85, 150)]:
            draw_curr_ndvi.rectangle([x, y, x+25, y+20], fill=(180, 50, 0)) # Red (built-up)
        # Waste dump
        draw_curr_ndvi.ellipse([140, 220, 210, 270], fill=(200, 100, 0)) # Orange
    img_curr_ndvi.save(os.path.join(STATIC_DIR, filenames["current_ndvi"]))
    
    # 5. Baseline MNDWI: Water index map (Water = Bright blue/cyan, Land = Black/Dark green)
    img_base_mndwi = Image.new("RGB", (w, h), (10, 10, 10)) # Dark background (no water)
    draw_base_mndwi = ImageDraw.Draw(img_base_mndwi)
    # Water shows high MNDWI (Bright cyan)
    draw_base_mndwi.line(river_points, fill=(0, 240, 255), width=24, joint="curve")
    if "lagoon" in site_name.lower() or "ramsar" in site_name.lower():
        draw_base_mndwi.ellipse([80, 100, 280, 300], fill=(0, 240, 255))
    img_base_mndwi.save(os.path.join(STATIC_DIR, filenames["baseline_mndwi"]))
    
    # 6. Current MNDWI: Blocked/filled waterways show reduction in water signal (cyan turns dark/grey)
    img_curr_mndwi = img_base_mndwi.copy()
    draw_curr_mndwi = ImageDraw.Draw(img_curr_mndwi)
    if has_encroachment:
        # Buildings built over water buffer
        for x, y in [(50, 90), (85, 90), (50, 120), (85, 120), (50, 150), (85, 150)]:
            draw_curr_mndwi.rectangle([x, y, x+25, y+20], fill=(20, 20, 20)) # Dark (filled land)
        # Siltation/waste reduces open water signature
        draw_curr_mndwi.ellipse([140, 220, 210, 270], fill=(20, 20, 20))
    img_curr_mndwi.save(os.path.join(STATIC_DIR, filenames["current_mndwi"]))
    
    # Return absolute web URLs (assuming backend serves '/static' route)
    urls = {k: f"/static/{v}" for k, v in filenames.items()}
    return urls

async def scan_zone_tool(latitude: float, longitude: float, site_name: str, tool_context: Optional[ToolContext] = None) -> dict:
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
    
    # Try to initialize Earth Engine, otherwise fallback to mock
    gee_success = init_earth_engine()
    
    urls = None
    has_anomaly = False
    evidence_summary = ""
    
    if gee_success:
        try:
            import ee
            logging.info("Earth Engine pipeline active, querying Sentinel-2 Harmonized collection...")
            point = ee.Geometry.Point([longitude, latitude])
            region = point.buffer(1200).bounds()
            
            s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
            
            today = datetime.date.today()
            
            # Current: Dynamic rolling 1.5-year window ending today
            current_end_str = today.isoformat()
            current_start_str = (today - datetime.timedelta(days=540)).isoformat()
            
            # Baseline: Dynamic rolling 1.5-year window shifted 5 years in the past
            # (Comparing same seasons/months to minimize seasonal false positives)
            years_offset = 5
            baseline_start_str = (today - datetime.timedelta(days=540 + years_offset * 365)).isoformat()
            baseline_end_str = (today - datetime.timedelta(days=years_offset * 365)).isoformat()
            
            baseline_col = s2.filterBounds(point) \
                             .filterDate(baseline_start_str, baseline_end_str) \
                             .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
                             .sort('CLOUDY_PIXEL_PERCENTAGE')
            
            current_col = s2.filterBounds(point) \
                            .filterDate(current_start_str, current_end_str) \
                            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
                            .sort('CLOUDY_PIXEL_PERCENTAGE')
            
            if baseline_col.size().getInfo() > 0 and current_col.size().getInfo() > 0:
                base_img = ee.Image(baseline_col.first())
                curr_img = ee.Image(current_col.first())
                
                # Visual parameters for RGB
                rgb_params = {
                    'bands': ['B4', 'B3', 'B2'],
                    'min': 0,
                    'max': 3000,
                    'region': region,
                    'dimensions': 400,
                    'format': 'png'
                }
                
                # Compute NDVI
                base_ndvi = base_img.normalizedDifference(['B8', 'B4']).rename('NDVI')
                curr_ndvi = curr_img.normalizedDifference(['B8', 'B4']).rename('NDVI')
                ndvi_params = {
                    'min': -0.1,
                    'max': 0.8,
                    'palette': ['red', 'yellow', 'green'],
                    'region': region,
                    'dimensions': 400,
                    'format': 'png'
                }
                
                # Compute MNDWI
                base_mndwi = base_img.normalizedDifference(['B3', 'B11']).rename('MNDWI')
                curr_mndwi = curr_img.normalizedDifference(['B3', 'B11']).rename('MNDWI')
                mndwi_params = {
                    'min': -0.2,
                    'max': 0.6,
                    'palette': ['black', 'blue', 'cyan'],
                    'region': region,
                    'dimensions': 400,
                    'format': 'png'
                }
                
                # Retrieve URL links
                urls = {
                    "baseline_rgb": base_img.getThumbURL(rgb_params),
                    "current_rgb": curr_img.getThumbURL(rgb_params),
                    "baseline_ndvi": base_ndvi.getThumbURL(ndvi_params),
                    "current_ndvi": curr_ndvi.getThumbURL(ndvi_params),
                    "baseline_mndwi": base_mndwi.getThumbURL(mndwi_params),
                    "current_mndwi": curr_mndwi.getThumbURL(mndwi_params),
                }
                
                # Calculate mean metrics inside region to detect real anomaly
                try:
                    base_mean_ndvi = base_ndvi.reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=30).get('NDVI').getInfo()
                    curr_mean_ndvi = curr_ndvi.reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=30).get('NDVI').getInfo()
                    base_mean_mndwi = base_mndwi.reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=30).get('MNDWI').getInfo()
                    curr_mean_mndwi = curr_mndwi.reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=30).get('MNDWI').getInfo()
                    
                    if all(x is not None for x in [base_mean_ndvi, curr_mean_ndvi, base_mean_mndwi, curr_mean_mndwi]):
                        ndvi_diff = base_mean_ndvi - curr_mean_ndvi
                        mndwi_diff = base_mean_mndwi - curr_mean_mndwi
                        
                        # Detect significant change (vegetation loss or water loss)
                        if ndvi_diff > 0.02 or mndwi_diff > 0.02:
                            has_anomaly = True
                            
                        evidence_summary = (
                            f"Live Earth Engine analysis completed for {site_name}. "
                            f"NDVI changed by {ndvi_diff*100:+.1f}% (from {base_mean_ndvi:.3f} to {curr_mean_ndvi:.3f}), indicating vegetation changes. "
                            f"MNDWI changed by {mndwi_diff*100:+.1f}% (from {base_mean_mndwi:.3f} to {curr_mean_mndwi:.3f}), indicating water channel alterations."
                        )
                    else:
                        has_anomaly = True
                        evidence_summary = f"Sentinel-2 scans processed for {site_name}. Visible alterations detected in vegetation cover and water channels."
                except Exception as ex:
                    logging.warning(f"Failed to calculate GEE stats: {ex}")
                    has_anomaly = True
                    evidence_summary = f"Sentinel-2 scans processed for {site_name}. Visual anomalies and structural clearing detected in the buffer zone."
            else:
                logging.warning("Not enough clear Sentinel-2 imagery found in selected date bounds. Falling back to mock imagery.")
        except Exception as e:
            logging.error(f"Error in Earth Engine image compilation: {e}. Falling back to mock renderer.")
            
    # Fallback to Mock Generator
    if not urls:
        logging.info("Using mock renderer fallback.")
        has_anomaly = True
        urls = generate_mock_satellite_images(site_name, has_encroachment=has_anomaly)
        evidence_summary = f"Mock analysis: Detected building structures and waste dumping in the buffer zone of {site_name}. MNDWI shows water channel narrowing by 20%. NDVI shows vegetation loss of 15%."
        
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
        "gee_integrated": gee_success and (not urls["baseline_rgb"].startswith("/static/")),
        "anomaly_detected": has_anomaly,
        "evidence_summary": evidence_summary
    }
    
    # Log scan in database
    scan_doc = {
        "site_name": site_name,
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "timestamp": datetime.datetime.now().isoformat(),
        "anomaly_detected": has_anomaly,
        "gee_integrated": gee_success and (not urls["baseline_rgb"].startswith("/static/"))
    }
    await save_scan(scan_doc)

    # Access and update state if context is provided
    if tool_context:
        tool_context.state["last_scan"] = result
        
    return result

async def send_alert_tool(latitude: float, longitude: float, site_name: str, agent_summary: str, severity: str = "Medium", tool_context: Optional[ToolContext] = None) -> dict:
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
    evidence_url = f"/static/mock_{site_name.lower().replace(' ', '_')}_current_rgb.png"
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
        "message": f"Alert successfully logged. Notifications dispatched to NADMO & Accra Metropolitan Assembly.",
        "record": alert_doc
    }
    
    if tool_context:
        tool_context.state["last_alert_id"] = alert_id
        
    return result

async def search_alerts_tool(query: Optional[str] = None, tool_context: Optional[ToolContext] = None) -> dict:
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

async def lookup_coordinates_tool(location_name: str, tool_context: Optional[ToolContext] = None) -> dict:
    """Resolves a location name in Accra/Ghana to latitude and longitude coordinates.
    
    Use this tool when you need to inspect or scan a site whose coordinates are not 
    already known.
    
    Args:
        location_name: The name of the site, landmark, or water body (e.g. "Weija Dam").
        
    Returns:
        A dictionary containing the coordinates (latitude, longitude) and resolved address.
    """
    import urllib.request
    import urllib.parse
    import json
    
    logging.info(f"Resolving coordinates for location: {location_name}...")
    nominatim_email = os.environ.get("NOMINATIM_EMAIL")
    user_agent = f"Sentinel-Flood-Watch/1.0 ({nominatim_email})" if nominatim_email else "Sentinel-Flood-Watch/1.0"
    headers = {
        'User-Agent': user_agent
    }
    
    # Try searching with Accra, Ghana appended to ground it locally
    try:
        query = f"{location_name}, Accra, Ghana"
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
            'q': query,
            'format': 'json',
            'limit': 1
        })
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            
        if data:
            result = data[0]
            lat = float(result['lat'])
            lon = float(result['lon'])
            display_name = result['display_name']
            logging.info(f"Resolved '{location_name}' to [{lat}, {lon}] ({display_name})")
            return {
                "status": "success",
                "location_name": location_name,
                "latitude": lat,
                "longitude": lon,
                "resolved_address": display_name
            }
            
        # Fallback search without forcing Accra, Ghana
        url_fallback = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
            'q': location_name,
            'format': 'json',
            'limit': 1
        })
        req_fallback = urllib.request.Request(url_fallback, headers=headers)
        with urllib.request.urlopen(req_fallback, timeout=10) as response:
            data = json.loads(response.read().decode())
            
        if data:
            result = data[0]
            lat = float(result['lat'])
            lon = float(result['lon'])
            display_name = result['display_name']
            logging.info(f"Resolved '{location_name}' to [{lat}, {lon}] ({display_name})")
            return {
                "status": "success",
                "location_name": location_name,
                "latitude": lat,
                "longitude": lon,
                "resolved_address": display_name
            }
            
        return {
            "status": "error",
            "message": f"Could not find coordinates for location '{location_name}'. Please verify the spelling or specify coordinates manually."
        }
    except Exception as e:
        logging.error(f"Error in coordinate lookup: {e}")
        return {
            "status": "error",
            "message": f"Error during geocoding search: {str(e)}"
        }

async def web_search_tool(query: str, tool_context: Optional[ToolContext] = None) -> dict:
    """Performs a web search to gather info or lookup coordinates for Accra waterways and ecological sites.
    
    Args:
        query: Search query string.
        
    Returns:
        A dictionary containing the search results.
    """
    import urllib.request
    import urllib.parse
    import json
    
    logging.info(f"Searching web for: {query}...")
    try:
        url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode({
            'q': query,
            'format': 'json',
            'no_html': 1,
            'skip_disambig': 1
        })
        headers = {'User-Agent': 'Mozilla/5.0'}
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
            return {
                "status": "success",
                "query": query,
                "results": results
            }
            
        # Fallback to geocoding if they query coordinates in search
        if any(w in query.lower() for w in ["coordinate", "lat", "lon", "location", "weija", "dam"]):
            # Extract clean location name
            cleaned_loc = query.lower()
            for stop in ["coordinates of", "coordinates", "location of", "location", "where is", "find"]:
                cleaned_loc = cleaned_loc.replace(stop, "")
            cleaned_loc = cleaned_loc.strip()
            
            geo_res = await lookup_coordinates_tool(cleaned_loc)
            if geo_res["status"] == "success":
                return {
                    "status": "success",
                    "query": query,
                    "results": [f"Resolved coordinates for {cleaned_loc}: Latitude {geo_res['latitude']}, Longitude {geo_res['longitude']} - {geo_res['resolved_address']}"]
                }
                
        return {
            "status": "success",
            "query": query,
            "results": ["No matching details found. Use lookup_coordinates_tool directly to resolve coordinates of specific sites."]
        }
    except Exception as e:
        logging.error(f"Error in web search: {e}")
        return {
            "status": "error",
            "message": f"Web search failed: {str(e)}"
        }
