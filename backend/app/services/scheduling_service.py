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

import asyncio
import datetime
import logging
import os
import uuid
from typing import Any

from google.adk.runners import Runner
from app.services.agent_service import AgentService

# Predefined high-risk zones in Accra
PREDEFINED_ZONES = [
    {"name": "Korle Lagoon", "latitude": 5.5344, "longitude": -0.2197},
    {"name": "Odaw River", "latitude": 5.5500, "longitude": -0.2167},
    {"name": "Sakumono Ramsar Site", "latitude": 5.6294, "longitude": -0.0431},
    {"name": "Densu Delta Ramsar Site", "latitude": 5.5167, "longitude": -0.3333},
]


class SchedulingService:
    """Service to handle scheduled automated monitoring of high-risk zones."""

    def __init__(self, runner: Runner, agent_service: AgentService) -> None:
        """Inject required dependencies."""
        self.runner = runner
        self.agent_service = agent_service
        self._scheduler_task: asyncio.Task | None = None

    async def run_scheduled_scan(self) -> None:
        """Runs scans sequentially for all high-risk zones and executes side effects."""
        logging.info("Starting scheduled automated scan for high-risk zones...")

        for zone in PREDEFINED_ZONES:
            logging.info(f"Running scheduled scan for zone: {zone['name']}")
            try:
                prompt = (
                    f"Scan coordinates latitude {zone['latitude']} "
                    f"longitude {zone['longitude']} for site name {zone['name']}"
                )
                
                # Generate unique session ID for this scheduled job run
                today_str = datetime.date.today().isoformat()
                unique_suffix = uuid.uuid4().hex[:6]
                session_id = f"scheduled_run_{today_str}_{unique_suffix}"
                
                # Consume stream to execute all side effects (GEE scan, DB inserts, SMS alerts)
                async for chunk in self.agent_service.run_agent_task_stream(
                    prompt=prompt,
                    user_id="system_scheduler",
                    session_id=session_id,
                ):
                    # We just consume the generator to trigger background execution
                    pass
                
                logging.info(f"Successfully completed scheduled scan for zone: {zone['name']}")
            except Exception as e:
                logging.error(
                    f"Error during scheduled scan for zone {zone['name']}: {e}",
                    exc_info=True,
                )

        logging.info("Scheduled automated scan completed.")

    def start_local_scheduler(self) -> None:
        """Starts the local background scheduler task loop if configured."""
        enable_local = os.environ.get("ENABLE_LOCAL_SCHEDULER", "false").lower() == "true"
        if not enable_local:
            logging.info("Local background scheduler is disabled.")
            return

        interval = int(os.environ.get("LOCAL_SCHEDULER_INTERVAL_SECONDS", "86400"))
        logging.info(f"Starting local background scheduler (interval: {interval} seconds)...")

        async def scheduler_loop():
            # Initial startup delay to let the app fully initialize
            await asyncio.sleep(10)
            while True:
                try:
                    await self.run_scheduled_scan()
                except Exception as e:
                    logging.error(f"Error in local scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(interval)

        self._scheduler_task = asyncio.create_task(scheduler_loop())

    def stop_local_scheduler(self) -> None:
        """Cleans up and cancels the running local background scheduler task."""
        if self._scheduler_task:
            logging.info("Stopping local background scheduler...")
            self._scheduler_task.cancel()
            self._scheduler_task = None
