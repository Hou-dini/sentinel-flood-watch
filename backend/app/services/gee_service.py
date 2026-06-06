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
import logging
from typing import Any

from app.tools.common import init_earth_engine


class EarthEngineService:
    """Service class encapsulating interactions with Google Earth Engine.

    Handles connection initialization, Sentinel-2 collections filtering,
    remote sensing indices computation, and thumbnail generation.
    """

    def __init__(self) -> None:
        self._ee = None
        self._initialized = False

    def initialize(self) -> bool:
        """Initializes Earth Engine, importing the package and authenticating.

        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        self._initialized = init_earth_engine()
        if self._initialized:
            try:
                import ee

                self._ee = ee
            except ImportError as e:
                logging.error(f"Failed to import ee library: {e}")
                self._initialized = False
        return self._initialized

    def get_dynamic_dates(self) -> dict[str, str]:
        """Calculates dynamic date windows for baseline and current imagery.

        Returns:
            dict: Start and end dates for both baseline and current queries.
        """
        today = datetime.date.today()

        # Current: last 540 days ending today
        current_end = today.strftime("%Y-%m-%d")
        current_start = (today - datetime.timedelta(days=540)).strftime("%Y-%m-%d")

        # Baseline: same duration offset by exactly 5 years (1826 days)
        baseline_end = (today - datetime.timedelta(days=1826)).strftime("%Y-%m-%d")
        baseline_start = (today - datetime.timedelta(days=1826 + 540)).strftime(
            "%Y-%m-%d"
        )

        return {
            "current_start": current_start,
            "current_end": current_end,
            "baseline_start": baseline_start,
            "baseline_end": baseline_end,
        }

    def fetch_scan_metrics(
        self, latitude: float, longitude: float
    ) -> dict[str, Any] | None:
        """Queries Earth Engine for S2 imagery, computes indices and extracts mean metrics.

        Args:
            latitude: Target latitude coordinate.
            longitude: Target longitude coordinate.

        Returns:
            dict containing imagery URLs and extracted stats, or None if pipeline failed.
        """
        if not self._initialized and not self.initialize():
            logging.info("Earth Engine pipeline is inactive.")
            return None

        ee = self._ee
        try:
            point = ee.Geometry.Point([longitude, latitude])
            region = point.buffer(1200).bounds()
            s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")

            dates = self.get_dynamic_dates()

            # Baseline Collection
            baseline_col = (
                s2.filterBounds(point)
                .filterDate(dates["baseline_start"], dates["baseline_end"])
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
                .sort("CLOUDY_PIXEL_PERCENTAGE")
            )

            # Current Collection
            current_col = (
                s2.filterBounds(point)
                .filterDate(dates["current_start"], dates["current_end"])
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
                .sort("CLOUDY_PIXEL_PERCENTAGE")
            )

            if baseline_col.size().getInfo() <= 0 or current_col.size().getInfo() <= 0:
                logging.warning(
                    "Not enough clear Sentinel-2 imagery found in selected date bounds."
                )
                return None

            base_img = ee.Image(baseline_col.first())
            curr_img = ee.Image(current_col.first())

            # Visual parameters for RGB
            rgb_params = {
                "bands": ["B4", "B3", "B2"],
                "min": 0,
                "max": 3000,
                "region": region,
                "dimensions": 400,
                "format": "png",
            }

            # Compute NDVI
            base_ndvi = base_img.normalizedDifference(["B8", "B4"]).rename("NDVI")
            curr_ndvi = curr_img.normalizedDifference(["B8", "B4"]).rename("NDVI")
            ndvi_params = {
                "min": -0.1,
                "max": 0.8,
                "palette": ["red", "yellow", "green"],
                "region": region,
                "dimensions": 400,
                "format": "png",
            }

            # Compute MNDWI
            base_mndwi = base_img.normalizedDifference(["B3", "B11"]).rename("MNDWI")
            curr_mndwi = curr_img.normalizedDifference(["B3", "B11"]).rename("MNDWI")
            mndwi_params = {
                "min": -0.2,
                "max": 0.6,
                "palette": ["black", "blue", "cyan"],
                "region": region,
                "dimensions": 400,
                "format": "png",
            }

            # Retrieve URL links
            urls = {
                "baseline_rgb": base_img.getThumbURL(rgb_params),
                "current_rgb": curr_img.getThumbURL(rgb_params),
                "baseline_ndvi": base_ndvi.getThumbURL(ndvi_params),
                "current_ndvi": curr_ndvi.getThumbURL(ndvi_params),
                "baseline_mndwi": base_mndwi.getThumbURL(mndwi_params),
                "current_mndwi": curr_mndwi.getThumbURL(mndwi_params),
            }

            # Calculate stats
            base_mean_ndvi = (
                base_ndvi.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=region, scale=30
                )
                .get("NDVI")
                .getInfo()
            )
            curr_mean_ndvi = (
                curr_ndvi.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=region, scale=30
                )
                .get("NDVI")
                .getInfo()
            )
            base_mean_mndwi = (
                base_mndwi.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=region, scale=30
                )
                .get("MNDWI")
                .getInfo()
            )
            curr_mean_mndwi = (
                curr_mndwi.reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=region, scale=30
                )
                .get("MNDWI")
                .getInfo()
            )

            return {
                "urls": urls,
                "stats": {
                    "base_mean_ndvi": base_mean_ndvi,
                    "curr_mean_ndvi": curr_mean_ndvi,
                    "base_mean_mndwi": base_mean_mndwi,
                    "curr_mean_mndwi": curr_mean_mndwi,
                },
            }

        except Exception as e:
            logging.error(f"Error in Earth Engine image compilation: {e}")
            return None
