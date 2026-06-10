import hashlib
import os
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

def test_chat_stream_resolves_ip_and_hashes() -> None:
    # Set mock runner on app state to bypass lifespan startup
    app.state.runner = MagicMock()
    client = TestClient(app)
    
    # Mock AgentService.run_agent_task_stream to prevent calling Vertex AI model
    async def mock_generator(*args, **kwargs):
        yield {"id": "chunk-1", "author": "agent", "text": "Test response", "is_final": True}
        
    with patch("app.main.AgentService.run_agent_task_stream", side_effect=mock_generator) as mock_run:
        # Test request with X-Forwarded-For header
        response = client.post(
            "/api/v1/chat",
            json={"message": "hello", "session_id": "test_session_abc"},
            headers={"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}
        )
        assert response.status_code == 200
        mock_run.assert_called_once()
        called_args, called_kwargs = mock_run.call_args
        
        # Compute expected hash using current active IP_SALT in environment
        salt = os.environ.get("IP_SALT", "sentinel_secure_salt_2026")
        expected_hash = hashlib.sha256(f"192.168.1.100:{salt}".encode("utf-8")).hexdigest()[:16]
        
        assert called_kwargs["user_id"] == expected_hash
        assert called_kwargs["session_id"] == "test_session_abc"
