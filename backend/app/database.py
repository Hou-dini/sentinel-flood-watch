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

from typing import Any

from app.services import DatabaseService

# Global service instance to maintain connection pool reuse
db_service = DatabaseService()


async def save_alert(alert_doc: dict[str, Any]) -> str:
    """Delegates alert saving to DatabaseService."""
    return await db_service.save_alert(alert_doc)


async def get_alerts(query_str: str | None = None) -> list[dict[str, Any]]:
    """Delegates alert querying to DatabaseService."""
    return await db_service.get_alerts(query_str)


async def save_scan(scan_doc: dict[str, Any]) -> None:
    """Delegates scan metrics saving to DatabaseService."""
    await db_service.save_scan(scan_doc)


async def get_analytics_summary() -> dict[str, Any]:
    """Delegates analytics querying to DatabaseService."""
    return await db_service.get_analytics_summary()
