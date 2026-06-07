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

from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions import Session

from app.services.agent_service import AgentService


@pytest.mark.asyncio
async def test_agent_service_orchestration() -> None:
    """Test that AgentService secures the prompt, manages the session, and yields chunks."""
    # Mock Runner
    mock_runner = MagicMock(spec=Runner)
    mock_runner.app_name = "sentinel"

    # Mock SessionService
    mock_session_service = AsyncMock()
    mock_runner.session_service = mock_session_service

    # Simulate get_session returning None initially, then create_session called
    mock_session_service.get_session.return_value = None
    mock_session_service.create_session.return_value = MagicMock(spec=Session)

    # Mock Event
    mock_event = MagicMock(spec=Event)
    mock_event.id = "test-event-id"
    mock_event.author = "agent"
    mock_content = MagicMock()
    mock_part = MagicMock()
    mock_part.text = "Hello, world!"
    mock_content.parts = [mock_part]
    mock_event.content = mock_content
    mock_event.get_function_calls.return_value = []
    mock_event.get_function_responses.return_value = []
    mock_event.is_final_response.return_value = True

    # Async Generator for run_async
    async def mock_run_async(*args, **kwargs):
        yield mock_event

    mock_runner.run_async = mock_run_async

    # Initialize AgentService
    service = AgentService(mock_runner)

    # Execute run_agent_task_stream
    chunks = []
    async for chunk in service.run_agent_task_stream(
        prompt="Who are you?", user_id="user-1", session_id="session-1"
    ):
        chunks.append(chunk)

    # Assertions
    mock_session_service.get_session.assert_called_once_with(
        app_name="sentinel", user_id="user-1", session_id="session-1"
    )
    mock_session_service.create_session.assert_called_once_with(
        app_name="sentinel", user_id="user-1", session_id="session-1"
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk["id"] == "test-event-id"
    assert chunk["author"] == "agent"
    assert chunk["text"] == "Hello, world!"
    assert chunk["is_final"] is True
