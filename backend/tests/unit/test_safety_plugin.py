import pytest
from unittest.mock import MagicMock, patch
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.cloud import modelarmor_v1
from google.genai import types

from app.app_utils.safety_plugin import ModelArmorSafetyPlugin

@pytest.fixture
def mock_ma_client():
    with patch("app.app_utils.safety_plugin.modelarmor_v1.ModelArmorClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client

@pytest.mark.asyncio
async def test_before_model_callback_safe_prompt(mock_ma_client):
    """Test that a safe prompt passes through seamlessly."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.sanitization_result.filter_match_state = modelarmor_v1.FilterMatchState.NO_MATCH_FOUND
    mock_ma_client.sanitize_user_prompt.return_value = mock_response

    # Initialize plugin
    plugin = ModelArmorSafetyPlugin(template_name="projects/test/locations/global/templates/test")

    # Construct request
    llm_req = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text="What is Korle Lagoon?")]
            )
        ]
    )

    # Invoke callback
    res = await plugin.before_model_callback(callback_context=MagicMock(), llm_request=llm_req)

    # Assertions
    assert res is None
    mock_ma_client.sanitize_user_prompt.assert_called_once()

@pytest.mark.asyncio
async def test_before_model_callback_unsafe_prompt_blocks(mock_ma_client):
    """Test that an unsafe prompt is blocked (fail-closed)."""
    # Setup mock response indicating match found
    mock_response = MagicMock()
    mock_response.sanitization_result.filter_match_state = modelarmor_v1.FilterMatchState.MATCH_FOUND
    mock_ma_client.sanitize_user_prompt.return_value = mock_response

    # Initialize plugin
    plugin = ModelArmorSafetyPlugin(template_name="projects/test/locations/global/templates/test")

    # Construct request
    llm_req = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text="Jailbreak instructions...")]
            )
        ]
    )

    # Invoke callback
    res = await plugin.before_model_callback(callback_context=MagicMock(), llm_request=llm_req)

    # Assertions
    assert isinstance(res, LlmResponse)
    assert "blocked by the application security policy" in res.content.parts[0].text
    mock_ma_client.sanitize_user_prompt.assert_called_once()

@pytest.mark.asyncio
async def test_before_model_callback_exception_fail_open(mock_ma_client):
    """Test that API failures allow the call to proceed (fail-open)."""
    # Setup mock to raise exception
    mock_ma_client.sanitize_user_prompt.side_effect = Exception("Connection Timeout")

    # Initialize plugin
    plugin = ModelArmorSafetyPlugin(template_name="projects/test/locations/global/templates/test")

    # Construct request
    llm_req = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text="Please scan Korle Lagoon")]
            )
        ]
    )

    # Invoke callback
    res = await plugin.before_model_callback(callback_context=MagicMock(), llm_request=llm_req)

    # Assertions
    assert res is None  # Connection failed, but we fall back to open (None)
    mock_ma_client.sanitize_user_prompt.assert_called_once()

@pytest.mark.asyncio
async def test_after_model_callback_safe_response(mock_ma_client):
    """Test that a safe model response passes through unmodified."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.sanitization_result.filter_match_state = modelarmor_v1.FilterMatchState.NO_MATCH_FOUND
    mock_ma_client.sanitize_model_response.return_value = mock_response

    # Initialize plugin
    plugin = ModelArmorSafetyPlugin(template_name="projects/test/locations/global/templates/test")

    # Construct response
    llm_res = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="Scan results: safe.")]
        )
    )

    # Invoke callback
    res = await plugin.after_model_callback(callback_context=MagicMock(), llm_response=llm_res)

    # Assertions
    assert res is None
    mock_ma_client.sanitize_model_response.assert_called_once()

@pytest.mark.asyncio
async def test_after_model_callback_unsafe_response_blocks(mock_ma_client):
    """Test that an unsafe model response gets redacted (fail-closed)."""
    # Setup mock response indicating match found
    mock_response = MagicMock()
    mock_response.sanitization_result.filter_match_state = modelarmor_v1.FilterMatchState.MATCH_FOUND
    mock_ma_client.sanitize_model_response.return_value = mock_response

    # Initialize plugin
    plugin = ModelArmorSafetyPlugin(template_name="projects/test/locations/global/templates/test")

    # Construct response
    llm_res = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="Some unsafe or PII leaking text...")]
        )
    )

    # Invoke callback
    res = await plugin.after_model_callback(callback_context=MagicMock(), llm_response=llm_res)

    # Assertions
    assert isinstance(res, LlmResponse)
    assert "redacted due to security and privacy guidelines" in res.content.parts[0].text
    mock_ma_client.sanitize_model_response.assert_called_once()

@pytest.mark.asyncio
async def test_after_model_callback_exception_fail_open(mock_ma_client):
    """Test that API response failures let the model output pass (fail-open)."""
    # Setup mock to raise exception
    mock_ma_client.sanitize_model_response.side_effect = Exception("API Unavailable")

    # Initialize plugin
    plugin = ModelArmorSafetyPlugin(template_name="projects/test/locations/global/templates/test")

    # Construct response
    llm_res = LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text="Standard response.")]
        )
    )

    # Invoke callback
    res = await plugin.after_model_callback(callback_context=MagicMock(), llm_response=llm_res)

    # Assertions
    assert res is None  # Pass-through
    mock_ma_client.sanitize_model_response.assert_called_once()
