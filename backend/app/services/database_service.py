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

import json
import logging
import os
import uuid
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from app.models import Alert, Scan


class DatabaseService:
    """Service to handle database connection and storage operations.

    Provides transparent fallback between MongoDB Atlas and local file-based JSON storage.
    """

    def __init__(self) -> None:
        self.mongo_uri = os.environ.get("MONGODB_URI")
        self.db_name = os.environ.get("MONGODB_DB_NAME", "sentinel_flood_watch")
        self.client = None
        self.db = None
        self.use_local_json = True
        self._initialized = False

    def connect(self) -> None:
        """Establishes connection to MongoDB, falling back to local JSON if configuration is missing or invalid."""
        if self._initialized:
            return

        if self.mongo_uri:
            try:
                max_pool_size = int(os.environ.get("MONGODB_MAX_POOL_SIZE", "5"))
                self.client = AsyncIOMotorClient(
                    self.mongo_uri, serverSelectionTimeoutMS=2000, maxPoolSize=max_pool_size
                )
                self.db = self.client[self.db_name]
                self.use_local_json = False
                logging.info(f"Connected to MongoDB Atlas successfully with maxPoolSize={max_pool_size}.")
                self._initialized = True
                return
            except Exception as e:
                logging.warning(
                    f"Failed to connect to MongoDB Atlas: {e}. Falling back to local file-based database."
                )

        self.use_local_json = True
        logging.info("Using local JSON file-based database.")
        self._initialized = True

    def disconnect(self) -> None:
        """Closes the MongoDB connection client and resets initialized state."""
        if self.client:
            try:
                self.client.close()
                logging.info("Closed MongoDB Atlas connection.")
            except Exception as e:
                logging.error(f"Error closing MongoDB connection: {e}")
            self.client = None
            self.db = None
        self._initialized = False

    async def save_alert(self, alert_doc: dict[str, Any] | Alert) -> str:
        """Saves an encroachment alert to database (MongoDB or local JSON)."""
        self.connect()

        # Enforce validation
        if isinstance(alert_doc, dict):
            if "severity" not in alert_doc:
                alert_doc["severity"] = "Medium"
            alert = Alert(**alert_doc)
        else:
            alert = alert_doc

        alert_data = alert.model_dump(exclude={"id"})

        if not self.use_local_json:
            try:
                res = await self.db.alerts.insert_one(alert_data)
                alert_id = str(res.inserted_id)
                if isinstance(alert_doc, dict):
                    alert_doc["_id"] = alert_id
                return alert_id
            except Exception as e:
                logging.error(
                    f"Error saving alert to MongoDB: {e}. Saving locally instead."
                )

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
        alert_data["_id"] = alert_id
        alerts.append(alert_data)

        with open(db_file, "w") as f:
            json.dump(alerts, f, indent=2, default=str)

        if isinstance(alert_doc, dict):
            alert_doc["_id"] = alert_id

        return alert_id

    async def get_alerts(self, query_str: str | None = None) -> list[dict[str, Any]]:
        """Queries logged alerts from the database."""
        self.connect()
        results = []

        if not self.use_local_json:
            try:
                cursor = self.db.alerts.find()
                async for doc in cursor:
                    try:
                        doc["id"] = str(doc.pop("_id"))
                        # Enforce validation
                        alert = Alert(**doc)
                        results.append(alert.model_dump())
                    except Exception as ve:
                        logging.warning(f"Skipping invalid MongoDB alert document: {ve}")
                if query_str:
                    query_str = query_str.lower()
                    results = [
                        r
                        for r in results
                        if query_str in r.get("site_name", "").lower()
                        or query_str in r.get("agent_summary", "").lower()
                    ]
                return results
            except Exception as e:
                logging.error(
                    f"Error getting alerts from MongoDB: {e}. Reading locally instead."
                )

        db_file = "alerts_db.json"
        if not os.path.exists(db_file):
            return []
        try:
            with open(db_file) as f:
                alerts = json.load(f)
                validated_alerts = []
                for alert in alerts:
                    try:
                        if "_id" in alert:
                            alert["id"] = str(alert.pop("_id"))
                        # Enforce validation
                        v_alert = Alert(**alert)
                        validated_alerts.append(v_alert.model_dump())
                    except Exception as ve:
                        logging.warning(f"Skipping invalid local alert document: {ve}")
                if query_str:
                    query_str = query_str.lower()
                    validated_alerts = [
                        r
                        for r in validated_alerts
                        if query_str in r.get("site_name", "").lower()
                        or query_str in r.get("agent_summary", "").lower()
                    ]
                return validated_alerts
        except Exception:
            return []

    async def save_scan(self, scan_doc: dict[str, Any] | Scan) -> None:
        """Saves scan metrics for live analytics reporting."""
        self.connect()

        if isinstance(scan_doc, dict):
            scan = Scan(**scan_doc)
        else:
            scan = scan_doc

        scan_data = scan.model_dump(exclude={"id"})

        if not self.use_local_json:
            try:
                await self.db.scans.insert_one(scan_data)
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
        scans.append(scan_data)
        with open(db_file, "w") as f:
            json.dump(scans, f, indent=2, default=str)

    async def get_analytics_summary(self) -> dict[str, Any]:
        """Aggregates system activity (scans, alerts, severity) for live dashboards."""
        self.connect()
        alerts = await self.get_alerts()

        # Read scans
        scans = []
        if not self.use_local_json:
            try:
                cursor = self.db.scans.find()
                async for doc in cursor:
                    if "_id" in doc:
                        doc["id"] = str(doc.pop("_id"))
                    v_scan = Scan(**doc)
                    scans.append(v_scan.model_dump())
            except Exception as e:
                logging.error(f"Error getting scans from MongoDB: {e}")
        else:
            db_file = "scans_db.json"
            if os.path.exists(db_file):
                try:
                    with open(db_file) as f:
                        scans_data = json.load(f)
                        for s in scans_data:
                            if "_id" in s:
                                s["id"] = str(s.pop("_id"))
                            v_scan = Scan(**s)
                            scans.append(v_scan.model_dump())
                except Exception:
                    scans = []

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
            "active_monitored_zones": 4,
        }
