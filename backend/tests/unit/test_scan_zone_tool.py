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

import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.gee_service import EarthEngineService
from app.tools.scan_zone_tool import scan_zone_tool


@pytest.mark.asyncio
async def test_gee_service_date_calculation() -> None:
    """Test that EarthEngineService dynamically calculates the correct dates

    for current and baseline imagery collections.
    """
    service = EarthEngineService()
    fixed_date = datetime.date(2026, 6, 6)

    # Expected dates
    expected_current_end = "2026-06-06"
    expected_current_start = (fixed_date - datetime.timedelta(days=540)).strftime(
        "%Y-%m-%d"
    )
    expected_baseline_end = (fixed_date - datetime.timedelta(days=1826)).strftime(
        "%Y-%m-%d"
    )
    expected_baseline_start = (
        fixed_date - datetime.timedelta(days=1826 + 540)
    ).strftime("%Y-%m-%d")

    with patch("datetime.date") as mock_date:
        mock_date.today.return_value = fixed_date
        mock_date.side_effect = lambda *args, **kwargs: datetime.date(*args, **kwargs)

        dates = service.get_dynamic_dates()
        assert dates["current_start"] == expected_current_start
        assert dates["current_end"] == expected_current_end
        assert dates["baseline_start"] == expected_baseline_start
        assert dates["baseline_end"] == expected_baseline_end


@pytest.mark.asyncio
async def test_gee_service_fetch_scan_metrics() -> None:
    """Test that EarthEngineService correctly filters collections and calls GEE."""
    service = EarthEngineService()

    mock_ee = MagicMock()
    mock_point = MagicMock()
    mock_region = MagicMock()
    mock_collection = MagicMock()

    mock_ee.Geometry.Point.return_value = mock_point
    mock_point.buffer.return_value.bounds.return_value = mock_region
    mock_ee.ImageCollection.return_value = mock_collection

    mock_collection.filterBounds.return_value = mock_collection
    mock_collection.filterDate.return_value = mock_collection
    mock_collection.filter.return_value = mock_collection
    mock_collection.sort.return_value = mock_collection
    mock_collection.size.return_value.getInfo.return_value = 0

    with (
        patch("app.services.gee_service.init_earth_engine", return_value=True),
        patch("sys.modules", {"ee": mock_ee}),
    ):
        service.initialize()
        result = service.fetch_scan_metrics(latitude=5.55, longitude=-0.2167)
        assert result is None  # Since collection size is 0, it returns None

        # Verify correct filterDate calls
        filter_date_calls = mock_collection.filterDate.call_args_list
        assert len(filter_date_calls) == 2


@pytest.mark.asyncio
async def test_scan_zone_tool_fallback() -> None:
    """Test that scan_zone_tool falls back to mock imagery if GEE fails."""
    with (
        patch("app.tools.scan_zone_tool.save_scan", return_value=None),
        patch("app.tools.scan_zone_tool.generate_mock_satellite_images") as mock_gen,
        patch("app.services.gee_service.init_earth_engine", return_value=False),
    ):
        mock_gen.return_value = {
            "baseline_rgb": "/static/mock_base_rgb.png",
            "current_rgb": "/static/mock_curr_rgb.png",
            "baseline_ndvi": "/static/mock_base_ndvi.png",
            "current_ndvi": "/static/mock_curr_ndvi.png",
            "baseline_mndwi": "/static/mock_base_mndwi.png",
            "current_mndwi": "/static/mock_curr_mndwi.png",
        }

        result = await scan_zone_tool(
            latitude=5.55, longitude=-0.2167, site_name="Odaw River Basin"
        )

        assert result["status"] == "success"
        assert result["anomaly_detected"] is True
        assert "baseline_rgb" in result
        mock_gen.assert_called_once_with("Odaw River Basin", has_encroachment=True)
