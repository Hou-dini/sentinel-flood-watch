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

from collections.abc import AsyncGenerator

from google.adk.runners import Runner
from google.genai import types


class AgentService:
    """Service to orchestrate execution of agent tasks, handling streaming,

    session management, and prompt security constraints.
    """

    def __init__(self, runner: Runner) -> None:
        """Inject the Runner into the service constructor."""
        self.runner = runner

    async def run_agent_task_stream(
        self, prompt: str, user_id: str, session_id: str
    ) -> AsyncGenerator[dict, None]:
        """Orchestrates the execution of agent tasks, handling streaming,

        session management, and boundary markers.
        """
        # Session management
        session = await self.runner.session_service.get_session(
            app_name=self.runner.app_name, user_id=user_id, session_id=session_id
        )
        if session is None:
            await self.runner.session_service.create_session(
                app_name=self.runner.app_name, user_id=user_id, session_id=session_id
            )

        # Secure the user input with strict boundary markers to mitigate prompt injection and inject current time
        import datetime

        current_time = datetime.datetime.utcnow().isoformat() + "Z"
        secure_prompt = (
            f"Current UTC Time Context: {current_time}\n\n"
            f"The following is raw input from the user:\n<user_input>\n{prompt}\n</user_input>"
        )

        async for chunk in self._get_agent_response_stream(
            secure_prompt, user_id, session_id
        ):
            yield chunk

    async def _get_agent_response_stream(
        self, secure_prompt: str, user_id: str, session_id: str
    ) -> AsyncGenerator[dict, None]:
        """Helper method to run the secured prompt on the ADK runner and yield formatted chunks."""
        new_msg = types.Content(
            role="user", parts=[types.Part.from_text(text=secure_prompt)]
        )

        async for event in self.runner.run_async(
            user_id=user_id, session_id=session_id, new_message=new_msg
        ):
            author = event.author
            text = ""
            if event.content and event.content.parts:
                text = "".join([p.text for p in event.content.parts if p.text])

            # Check for tool/function calls
            func_calls = []
            for fc in event.get_function_calls():
                func_calls.append(
                    {"name": fc.name, "args": dict(fc.args) if fc.args else {}}
                )

            # Check for tool/function responses
            func_responses = []
            for fr in event.get_function_responses():
                func_responses.append({"name": fr.name, "response": fr.response})

            chunk = {
                "id": event.id,
                "author": author,
                "text": text,
                "function_calls": func_calls,
                "function_responses": func_responses,
                "is_final": event.is_final_response(),
            }
            yield chunk
