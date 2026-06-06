import json
import logging
import os

from PIL import Image, ImageDraw

# Static folder inside app directory
STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static"
)
os.makedirs(STATIC_DIR, exist_ok=True)

# Mock coordinates dictionary for Accra locations
ACCRA_SITES = {
    "korle lagoon": {"lat": 5.5344, "lon": -0.2197},
    "odor river": {"lat": 5.5500, "lon": -0.2167},
    "sakumonor ramsar site": {"lat": 5.6294, "lon": -0.0431},
    "densu delta ramsar site": {"lat": 5.5167, "lon": -0.3333},
}

# Earth Engine Initialization State
_ee_initialized = False


def init_earth_engine() -> bool:
    """Initializes Google Earth Engine using Service Account credentials or ADC."""
    global _ee_initialized
    if _ee_initialized:
        return True
    try:
        import ee

        key_path = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_PATH")
        if key_path and os.path.exists(key_path):
            with open(key_path) as f:
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
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project:
            try:
                import google.auth

                _, project = google.auth.default()
                logging.info(f"Retrieved project from google.auth: {project}")
            except Exception as auth_err:
                logging.warning(
                    f"Could not retrieve project from google.auth: {auth_err}"
                )
        if project:
            logging.info(f"Initializing Earth Engine with project: {project}")
            ee.Initialize(project=project)
        else:
            logging.info("Initializing Earth Engine without explicit project...")
            ee.Initialize()
        _ee_initialized = True
        logging.info("Google Earth Engine initialized successfully.")
        return True
    except Exception as e:
        logging.warning(
            f"Google Earth Engine initialization failed: {e}. Using mock imagery fallback."
        )
        return False


def generate_mock_satellite_images(
    site_name: str, has_encroachment: bool = True
) -> dict:
    """Generates PNG images simulating Sentinel-2 satellite data and returns their static URLs.

    Generates:
      - Baseline RGB, Current RGB
      - Baseline NDVI, Current NDVI
      - Baseline MNDWI, Current MNDWI
    """
    site_key = site_name.lower().replace(" ", "_").replace("/", "_")

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
    img_base_rgb = Image.new("RGB", (w, h), (34, 139, 34))  # Forest green background
    draw_base = ImageDraw.Draw(img_base_rgb)
    # Winding river
    river_points = [(50, 0), (80, 80), (160, 160), (140, 240), (220, 320), (200, 400)]
    draw_base.line(
        river_points, fill=(30, 144, 255), width=24, joint="curve"
    )  # Dodger blue river
    # Lagoon body if Sakumo or Korle
    if "lagoon" in site_name.lower() or "ramsar" in site_name.lower():
        draw_base.ellipse([80, 100, 280, 300], fill=(30, 144, 255))
    img_base_rgb.save(os.path.join(STATIC_DIR, filenames["baseline_rgb"]))

    # 2. Current RGB: Encroached vegetation, structures built near/in river, brown pollution patches
    img_curr_rgb = img_base_rgb.copy()
    draw_curr = ImageDraw.Draw(img_curr_rgb)
    if has_encroachment:
        # Encroachment 1: Land clearing (grayish-brown patch)
        draw_curr.rectangle([40, 80, 120, 180], fill=(139, 115, 85))  # Sandy brown soil
        # Concrete structures (gray rectangles with red roofs)
        for x, y in [(50, 90), (85, 90), (50, 120), (85, 120), (50, 150), (85, 150)]:
            draw_curr.rectangle(
                [x, y, x + 25, y + 20], fill=(128, 128, 128)
            )  # Grey building walls
            draw_curr.polygon(
                [(x, y), (x + 12, y - 6), (x + 25, y)], fill=(205, 51, 51)
            )  # Red roof

        # Encroachment 2: Rubble/Waste dumping in the buffer zone
        draw_curr.ellipse([140, 220, 210, 270], fill=(139, 137, 137))  # Trash heap
        # Siltation in the water body (brownish green water)
        if "lagoon" in site_name.lower() or "ramsar" in site_name.lower():
            draw_curr.ellipse([120, 150, 220, 250], fill=(112, 128, 105))  # Muddy water
        else:
            draw_curr.line(river_points, fill=(112, 128, 105), width=20, joint="curve")
    img_curr_rgb.save(os.path.join(STATIC_DIR, filenames["current_rgb"]))

    # 3. Baseline NDVI: Vegetation health map (Green = High veg, Red/Orange = Built/Water)
    img_base_ndvi = Image.new("RGB", (w, h), (0, 180, 0))  # Healthy NDVI green
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
        draw_curr_ndvi.rectangle([40, 80, 120, 180], fill=(220, 220, 0))  # Yellow/bare
        for x, y in [(50, 90), (85, 90), (50, 120), (85, 120), (50, 150), (85, 150)]:
            draw_curr_ndvi.rectangle(
                [x, y, x + 25, y + 20], fill=(180, 50, 0)
            )  # Red (built-up)
        # Waste dump
        draw_curr_ndvi.ellipse([140, 220, 210, 270], fill=(200, 100, 0))  # Orange
    img_curr_ndvi.save(os.path.join(STATIC_DIR, filenames["current_ndvi"]))

    # 5. Baseline MNDWI: Water index map (Water = Bright blue/cyan, Land = Black/Dark green)
    img_base_mndwi = Image.new(
        "RGB", (w, h), (10, 10, 10)
    )  # Dark background (no water)
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
            draw_curr_mndwi.rectangle(
                [x, y, x + 25, y + 20], fill=(20, 20, 20)
            )  # Dark (filled land)
        # Siltation/waste reduces open water signature
        draw_curr_mndwi.ellipse([140, 220, 210, 270], fill=(20, 20, 20))
    img_curr_mndwi.save(os.path.join(STATIC_DIR, filenames["current_mndwi"]))

    # Return absolute web URLs (assuming backend serves '/static' route)
    urls = {k: f"/static/{v}" for k, v in filenames.items()}
    return urls
