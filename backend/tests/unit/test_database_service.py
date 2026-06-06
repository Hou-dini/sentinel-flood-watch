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

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.database_service import DatabaseService


@pytest.mark.asyncio
async def test_database_service_initialization() -> None:
    """Test default initialization values of DatabaseService."""
    with patch.dict(os.environ, {}, clear=True):
        service = DatabaseService()
        assert service.mongo_uri is None
        assert service.db_name == "sentinel_flood_watch"
        assert service.client is None
        assert service.db is None
        assert service.use_local_json is True
        assert service._initialized is False


@pytest.mark.asyncio
async def test_database_service_connect_mongo_success() -> None:
    """Test successful connection to MongoDB Atlas."""
    mock_client_class = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_class.return_value = mock_client_instance

    with (
        patch.dict(
            os.environ,
            {
                "MONGODB_URI": "mongodb://localhost:27017",
                "MONGODB_DB_NAME": "test_db",
            },
        ),
        patch("app.services.database_service.AsyncIOMotorClient", mock_client_class),
    ):
        service = DatabaseService()
        service.connect()
        assert service.use_local_json is False
        assert service.client == mock_client_instance
        assert service.db == mock_client_instance["test_db"]
        assert service._initialized is True


@pytest.mark.asyncio
async def test_database_service_connect_mongo_failure() -> None:
    """Test MongoDB connection failure falls back to local JSON."""
    mock_client_class = MagicMock(side_effect=Exception("Connection timed out"))

    with (
        patch.dict(os.environ, {"MONGODB_URI": "mongodb://localhost:27017"}),
        patch("app.services.database_service.AsyncIOMotorClient", mock_client_class),
    ):
        service = DatabaseService()
        service.connect()
        assert service.use_local_json is True
        assert service.client is None
        assert service._initialized is True


@pytest.mark.asyncio
async def test_database_service_local_flow(tmp_path, monkeypatch) -> None:
    """Test save and retrieve flow using local JSON fallback."""
    # Change working directory to tmp_path to isolate file operations
    monkeypatch.chdir(tmp_path)

    service = DatabaseService()
    # Explicitly ensure use_local_json is True
    service.use_local_json = True
    service._initialized = True

    # Test save_alert
    alert_doc = {
        "site_name": "Korle Lagoon",
        "coordinates": {"latitude": 5.53, "longitude": -0.21},
        "agent_summary": "High MNDWI shift detected.",
        "severity": "Medium",
        "status": "Active",
        "evidence_link": "/static/mock_evidence.png",
        "timestamp": "2026-06-06T23:00:00",
    }
    alert_id = await service.save_alert(alert_doc)
    assert alert_id is not None
    assert alert_doc["_id"] == alert_id

    # Test get_alerts
    alerts = await service.get_alerts()
    assert len(alerts) == 1
    assert alerts[0]["id"] == alert_id
    assert alerts[0]["site_name"] == "Korle Lagoon"

    # Test get_alerts with query filtering
    filtered_alerts = await service.get_alerts(query_str="Korle")
    assert len(filtered_alerts) == 1

    empty_alerts = await service.get_alerts(query_str="Nonexistent")
    assert len(empty_alerts) == 0

    # Test save_scan
    scan_doc = {
        "site_name": "Korle Lagoon",
        "coordinates": {"latitude": 5.53, "longitude": -0.21},
        "timestamp": "2026-06-06T23:00:00",
        "anomaly_detected": True,
        "gee_integrated": False,
    }
    await service.save_scan(scan_doc)

    # Test get_analytics_summary
    summary = await service.get_analytics_summary()
    assert summary["total_alerts"] == 1
    assert summary["total_scans"] == 1
    assert summary["alerts_by_severity"]["Medium"] == 1
    assert summary["alerts_by_site"]["Korle Lagoon"] == 1
    assert summary["success_rate"] == "100.0%"


@pytest.mark.asyncio
async def test_database_service_mongodb_flow() -> None:
    """Test save and retrieve flow using MongoDB client mocks."""
    service = DatabaseService()
    service.use_local_json = False
    service._initialized = True

    # Mock DB collections
    mock_db = MagicMock()
    mock_alerts_coll = MagicMock()
    mock_alerts_coll.insert_one = AsyncMock()
    mock_scans_coll = MagicMock()
    mock_scans_coll.insert_one = AsyncMock()
    mock_db.alerts = mock_alerts_coll
    mock_db.scans = mock_scans_coll
    service.db = mock_db

    # Mock insert_one for alerts
    mock_insert_res = MagicMock()
    mock_insert_res.inserted_id = "mock_alert_id_123"
    mock_alerts_coll.insert_one.return_value = mock_insert_res

    # Test save_alert
    alert_doc = {
        "site_name": "Test Site",
        "coordinates": {"latitude": 5.53, "longitude": -0.21},
        "agent_summary": "Test Summary",
        "severity": "High",
        "status": "Active",
        "evidence_link": "/static/test_evidence.png",
        "timestamp": "2026-06-06T23:00:00",
    }
    expected_save_doc = alert_doc.copy()
    alert_id = await service.save_alert(alert_doc)
    assert alert_id == "mock_alert_id_123"
    mock_alerts_coll.insert_one.assert_called_once_with(expected_save_doc)

    # Simple AsyncIterator mock helper
    class MockAsyncCursor:
        def __init__(self, items):
            self.items = items
            self.index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self.index < len(self.items):
                item = self.items[self.index]
                self.index += 1
                return item
            raise StopAsyncIteration

    mock_doc = {
        "_id": "mock_alert_id_123",
        "site_name": "Test Site",
        "coordinates": {"latitude": 5.53, "longitude": -0.21},
        "agent_summary": "Test Summary",
        "severity": "High",
        "status": "Active",
        "evidence_link": "/static/test_evidence.png",
        "timestamp": "2026-06-06T23:00:00",
    }
    mock_alerts_coll.find.return_value = MockAsyncCursor([mock_doc])

    alerts = await service.get_alerts()
    assert len(alerts) == 1
    assert alerts[0]["id"] == "mock_alert_id_123"
    assert alerts[0]["site_name"] == "Test Site"

    # Test save_scan
    scan_doc = {
        "site_name": "Test Site",
        "coordinates": {"latitude": 5.53, "longitude": -0.21},
        "timestamp": "2026-06-06T23:00:00",
        "anomaly_detected": True,
        "gee_integrated": False,
    }
    await service.save_scan(scan_doc)
    mock_scans_coll.insert_one.assert_called_once_with(scan_doc)
