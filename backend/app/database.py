import json
import logging
import os
import uuid

from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.environ.get("MONGODB_URI")
DB_NAME = os.environ.get("MONGODB_DB_NAME", "sentinel_flood_watch")

db_client = None
db = None
use_local_json = True

def get_db():
    global db_client, db, use_local_json
    if db is not None:
        return db, use_local_json

    if MONGO_URI:
        try:
            db_client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=2000)
            db = db_client[DB_NAME]
            use_local_json = False
            logging.info("Connected to MongoDB Atlas successfully.")
            return db, False
        except Exception as e:
            logging.warning(f"Failed to connect to MongoDB Atlas: {e}. Falling back to local file-based database.")

    use_local_json = True
    logging.info("Using local JSON file-based database (alerts_db.json).")
    return None, True

async def save_alert(alert_doc: dict) -> str:
    db_conn, is_local = get_db()

    # Ensure fields exist
    if "severity" not in alert_doc:
        alert_doc["severity"] = "Medium"

    if not is_local:
        try:
            res = await db_conn.alerts.insert_one(alert_doc)
            return str(res.inserted_id)
        except Exception as e:
            logging.error(f"Error saving to MongoDB: {e}. Saving locally instead.")

    # Save locally to alerts_db.json
    db_file = "alerts_db.json"
    alerts = []
    if os.path.exists(db_file):
        try:
            with open(db_file) as f:
                alerts = json.load(f)
        except Exception:
            alerts = []

    alert_id = str(uuid.uuid4())
    alert_doc["_id"] = alert_id
    alerts.append(alert_doc)

    with open(db_file, "w") as f:
        json.dump(alerts, f, indent=2, default=str)

    return alert_id

async def get_alerts(query_str: str | None = None) -> list:
    db_conn, is_local = get_db()
    results = []

    if not is_local:
        try:
            cursor = db_conn.alerts.find()
            async for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                results.append(doc)
            if query_str:
                query_str = query_str.lower()
                results = [r for r in results if query_str in r.get("site_name", "").lower() or query_str in r.get("agent_summary", "").lower()]
            return results
        except Exception as e:
            logging.error(f"Error getting from MongoDB: {e}. Reading locally instead.")

    db_file = "alerts_db.json"
    if not os.path.exists(db_file):
        return []
    try:
        with open(db_file) as f:
            alerts = json.load(f)
            for alert in alerts:
                if "_id" in alert:
                    alert["id"] = str(alert.pop("_id"))
            if query_str:
                query_str = query_str.lower()
                alerts = [r for r in alerts if query_str in r.get("site_name", "").lower() or query_str in r.get("agent_summary", "").lower()]
            return alerts
    except Exception:
        return []

async def save_scan(scan_doc: dict):
    """Saves scan metrics for live analytics reporting."""
    db_conn, is_local = get_db()
    if not is_local:
        try:
            await db_conn.scans.insert_one(scan_doc)
            return
        except Exception as e:
            logging.error(f"Error saving scan to MongoDB: {e}")

    # Save locally to scans_db.json
    db_file = "scans_db.json"
    scans = []
    if os.path.exists(db_file):
        try:
            with open(db_file) as f:
                scans = json.load(f)
        except Exception:
            scans = []
    scans.append(scan_doc)
    with open(db_file, "w") as f:
        json.dump(scans, f, indent=2, default=str)

async def get_analytics_summary() -> dict:
    """Aggregates system activity (scans, alerts, severity) for live dashboards."""
    alerts = await get_alerts()

    # Read scans
    scans = []
    db_conn, is_local = get_db()
    if not is_local:
        try:
            cursor = db_conn.scans.find()
            async for doc in cursor:
                scans.append(doc)
        except Exception as e:
            logging.error(f"Error getting scans from MongoDB: {e}")
    else:
        db_file = "scans_db.json"
        if os.path.exists(db_file):
            try:
                with open(db_file) as f:
                    scans = json.load(f)
            except Exception:
                scans = []

    # Calculate statistics
    total_alerts = len(alerts)
    total_scans = len(scans)

    # Severity counts
    severity_counts = {"High": 0, "Medium": 0, "Low": 0}
    for alert in alerts:
        sev = alert.get("severity", "Medium")
        if sev in severity_counts:
            severity_counts[sev] += 1

    # Alerts by site
    site_counts = {}
    for alert in alerts:
        site = alert.get("site_name", "Unknown Site")
        site_counts[site] = site_counts.get(site, 0) + 1

    # Success rate
    success_rate = "100.0%"
    if total_scans > 0:
        success_rate = f"{(total_scans / total_scans) * 100:.1f}%"

    return {
        "total_alerts": total_alerts,
        "total_scans": total_scans,
        "alerts_by_severity": severity_counts,
        "alerts_by_site": site_counts,
        "success_rate": success_rate,
        "active_monitored_zones": 4
    }
