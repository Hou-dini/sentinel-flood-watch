import os
import json
import logging
from typing import Optional
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
            with open(db_file, "r") as f:
                alerts = json.load(f)
        except Exception:
            alerts = []
    
    alert_id = str(uuid.uuid4())
    alert_doc["_id"] = alert_id
    alerts.append(alert_doc)
    
    with open(db_file, "w") as f:
        json.dump(alerts, f, indent=2, default=str)
        
    return alert_id

async def get_alerts(query_str: Optional[str] = None) -> list:
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
        with open(db_file, "r") as f:
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
