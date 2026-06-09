import logging
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.cloud import modelarmor_v1
from google.genai import types

class ModelArmorSafetyPlugin(BasePlugin):
    """ADK App Plugin that filters prompts and responses using Google Cloud Model Armor."""

    def __init__(self, template_name: str):
        """
        Args:
            template_name: The full resource path of the Model Armor template.
                           e.g., 'projects/PROJECT_ID/locations/LOCATION/templates/TEMPLATE_ID'
        """
        super().__init__(name="model_armor_safety")
        self.template_name = template_name
        
        # Parse location from template name (e.g., projects/PROJECT/locations/LOCATION/templates/TEMPLATE)
        location = "europe-west1" # Fallback
        parts = template_name.split("/")
        if len(parts) >= 4 and parts[2] == "locations":
            location = parts[3]
        
        api_endpoint = f"modelarmor.{location}.rep.googleapis.com"
        self.client = modelarmor_v1.ModelArmorClient(
            client_options={"api_endpoint": api_endpoint}
        )
        logging.info(f"ModelArmorSafetyPlugin initialized with template: {self.template_name} on endpoint: {api_endpoint}")

    async def before_model_callback(self, *, callback_context, llm_request: LlmRequest) -> LlmResponse | None:
        """Sanitizes the prompt prior to LLM submission."""
        user_prompt = ""
        if llm_request.contents:
            parts = []
            for content in llm_request.contents:
                if content.parts:
                    parts.extend([p.text for p in content.parts if p.text])
            user_prompt = "\n".join(parts)

        if not user_prompt:
            return None

        try:
            req = modelarmor_v1.SanitizeUserPromptRequest(
                name=self.template_name,
                user_prompt_data=modelarmor_v1.DataItem(text=user_prompt)
            )
            response = self.client.sanitize_user_prompt(request=req)
            
            # If the filter matched a safety policy violation, enforce fail-closed
            if response.sanitization_result.filter_match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND:
                logging.warning(f"Model Armor blocked prompt safety violation: {user_prompt}")
                safety_msg = "Your request was blocked by the application security policy."
                return LlmResponse(
                    content=types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=safety_msg)]
                    )
                )
        except Exception as e:
            # Enforce fail-open policy on timeout/connection exceptions
            logging.error(f"Error calling Model Armor (fail-open): {e}")

        return None

    async def after_model_callback(self, *, callback_context, llm_response: LlmResponse) -> LlmResponse | None:
        """Inspects and sanitizes the LLM response to prevent safety violations."""
        response_text = ""
        if llm_response.content and llm_response.content.parts:
            response_text = "".join([p.text for p in llm_response.content.parts if p.text])

        if not response_text:
            return None

        try:
            req = modelarmor_v1.SanitizeModelResponseRequest(
                name=self.template_name,
                model_response_data=modelarmor_v1.DataItem(text=response_text)
            )
            response = self.client.sanitize_model_response(request=req)
            
            # If the filter matched a safety policy violation, enforce fail-closed
            if response.sanitization_result.filter_match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND:
                logging.warning("Model Armor blocked model response safety violation.")
                block_msg = "The response was redacted due to security and privacy guidelines."
                llm_response.content = types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=block_msg)]
                )
                return llm_response
        except Exception as e:
            # Enforce fail-open policy on timeout/connection exceptions
            logging.error(f"Error calling Model Armor (fail-open): {e}")

        return None
