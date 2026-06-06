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

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.coordinates import Coordinates


class Scan(BaseModel):
    """Pydantic model representing a satellite zone scan result log."""

    id: str | None = Field(
        None, description="Database unique identifier (maps from _id)"
    )
    site_name: str = Field(..., description="Name of the scanned ecological site")
    coordinates: Coordinates = Field(
        ..., description="Geographical coordinates of the scan"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO timestamp of the scan",
    )
    anomaly_detected: bool = Field(
        ..., description="Whether an encroachment anomaly was detected"
    )
    gee_integrated: bool = Field(
        ..., description="Whether Google Earth Engine was used for this scan"
    )
