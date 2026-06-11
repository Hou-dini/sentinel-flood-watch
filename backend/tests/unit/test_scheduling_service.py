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
from fastapi.testclient import TestClient

from app.main import app
from app.services.scheduling_service import PREDEFINED_ZONES, SchedulingService


@pytest.fixture
def mock_runner():
    runner = MagicMock()
    runner.app_name = "sentinel"
    return runner


@pytest.fixture
def mock_agent_service():
    service = MagicMock()
    
    # Mock async generator method
    async def mock_task_stream(*args, **kwargs):
        yield {"is_final": True}
        
    service.run_agent_task_stream = mock_task_stream
    return service


@pytest.mark.asyncio
async def test_scheduling_service_run_loops(mock_runner, mock_agent_service) -> None:
    """Tests that SchedulingService iterates and runs scans for all predefined zones."""
    with patch("app.services.scheduling_service.uuid.uuid4") as mock_uuid:
        mock_uuid.return_value.hex = "test_uuid_hex"
        
        service = SchedulingService(mock_runner, mock_agent_service)
        
        # Patch the agent service call to spy on it
        spy_stream = AsyncMock()
        async def mock_generator(*args, **kwargs):
            yield {"is_final": True}
        spy_stream.side_effect = mock_generator
        
        mock_agent_service.run_agent_task_stream = spy_stream
        
        await service.run_scheduled_scan()
        
        # Verify it was called exactly for all predefined zones
        assert spy_stream.call_count == len(PREDEFINED_ZONES)
        
        # Check that coordinates and names match PREDEFINED_ZONES
        for idx, zone in enumerate(PREDEFINED_ZONES):
            called_kwargs = spy_stream.call_args_list[idx][1]
            assert "latitude" in called_kwargs["prompt"]
            assert zone["name"] in called_kwargs["prompt"]
            assert called_kwargs["user_id"] == "system_scheduler"
            assert called_kwargs["session_id"].startswith("scheduled_run_")


def test_job_scan_endpoint_auth() -> None:
    """Tests authorization and scheduling trigger on POST /api/v1/jobs/scan endpoint."""
    app.state.runner = MagicMock()
    
    # Mock scheduling service
    mock_sched_service = MagicMock()
    app.state.scheduling_service = mock_sched_service
    
    client = TestClient(app)
    
    # Case 1: Missing X-Job-Key header -> 401 Unauthorized
    with patch.dict(os.environ, {"JOB_API_KEY": "test_key"}, clear=False):
        response = client.post("/api/v1/jobs/scan")
        assert response.status_code == 401
        assert "X-Job-Key" in response.json()["detail"]
    
    # Case 2: Invalid X-Job-Key -> 401 Unauthorized
    with patch.dict(os.environ, {"JOB_API_KEY": "test_key"}, clear=False):
        response = client.post("/api/v1/jobs/scan", headers={"X-Job-Key": "wrong_key"})
        assert response.status_code == 401
    
    # Case 3: Valid X-Job-Key (local default fallback) -> 202 Accepted
    # Temporary clear JOB_API_KEY and GOOGLE_CLOUD_PROJECT to simulate local fallback
    with patch.dict(os.environ, {}, clear=True):
        response = client.post("/api/v1/jobs/scan", headers={"X-Job-Key": "sentinel_dev_job_key"})
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
        mock_sched_service.run_scheduled_scan.assert_called_once()
        
    # Case 4: Valid X-Job-Key (custom env) -> 202 Accepted
    mock_sched_service.reset_mock()
    with patch.dict(os.environ, {"JOB_API_KEY": "custom_prod_secret_key"}, clear=False):
        response = client.post("/api/v1/jobs/scan", headers={"X-Job-Key": "custom_prod_secret_key"})
        assert response.status_code == 200
        mock_sched_service.run_scheduled_scan.assert_called_once()
