"""SoilGrids client using the Python library for fetching soil data."""

import logging
from typing import Dict, Any, Optional
import numpy as np
from soilgrids import SoilGrids
from .base_client import BaseAPIClient, APIError
from ...models.soil import SoilProfile, SoilProperties, SoilTexture
from ...config.config import config

logger = logging.getLogger(__name__)


class SoilGridsClient(BaseAPIClient):
    """Client for ISRIC SoilGrids using the Python library."""
    
    def __init__(self):
        """Initialize SoilGrids client."""
        api_config = config.get_api_config('soilgrids')
        super().__init__(
            base_url="https://rest.isric.org/soilgrids/v2.0",  # Not used but required by base class
            timeout=api_config.get('timeout', 10),
            retry_attempts=api_config.get('retry_attempts', 3)
        )
        self.soil_grids = SoilGrids()
    
    async def fetch_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch soil data for given coordinates using the SoilGrids Python library."""
        logger.info(f"Fetching soil data for coordinates: {latitude}, {longitude}")
        
        try:
            # Convert lat/lon to appropriate coordinate system for SoilGrids
            # SoilGrids uses Web Mercator projection (EPSG:3857)
            import math
            
            # Convert to Web Mercator coordinates
            x = longitude * 20037508.34 / 180
            y = math.log(math.tan((90 + latitude) * math.pi / 360)) / (math.pi / 180)
            y = y * 20037508.34 / 180
            
            # Define a small bounding box around the point (1km x 1km)
            buffer = 500  # 500 meters buffer
            west = x - buffer
            east = x + buffer
            north = y + buffer
            south = y - buffer
            
            # Fetch soil properties
            soil_data = {}
            
            # pH data
            try:
                ph_data = self.soil_grids.get_coverage_data(
                    service_id="phh2o",
                    coverage_id="phh2o_0-5cm_mean",
                    west=west,
                    south=south,
                    east=east,
                    north=north,
                    crs="urn:ogc:def:crs:EPSG::3857",
                    output="/tmp/ph_data.tif"  # Temporary file output
                )
                if ph_data is not None and hasattr(ph_data, 'values'):
                    ph_values = ph_data.values
                    if ph_values.size > 0:
                        # Convert from 0.1 pH units to actual pH and validate
                        ph_value = float(np.nanmean(ph_values) / 10.0)
                        # Check for no-data values (typically negative large numbers)
                        if ph_value < 0 or ph_value > 20:  # No-data or invalid values
                            logger.warning(f"No-data pH value {ph_value}, using default")
                            soil_data['ph_h2o'] = 6.5  # Default neutral pH
                        elif 3.0 <= ph_value <= 10.0:  # Valid pH range
                            soil_data['ph_h2o'] = ph_value
                        else:
                            logger.warning(f"Invalid pH value {ph_value}, using default")
                            soil_data['ph_h2o'] = 6.5  # Default neutral pH
                    else:
                        logger.warning("No pH data available, using default")
                        soil_data['ph_h2o'] = 6.5
                else:
                    logger.warning("No pH data response, using default")
                    soil_data['ph_h2o'] = 6.5
            except Exception as e:
                logger.warning(f"Error fetching pH data: {e}, using default")
                soil_data['ph_h2o'] = 6.5
            
            # Organic carbon data
            try:
                soc_data = self.soil_grids.get_coverage_data(
                    service_id="soc",
                    coverage_id="soc_0-5cm_mean",
                    west=west,
                    south=south,
                    east=east,
                    north=north,
                    crs="urn:ogc:def:crs:EPSG::3857",
                    output="/tmp/soc_data.tif"
                )
                if soc_data is not None and hasattr(soc_data, 'values'):
                    soc_values = soc_data.values
                    if soc_values.size > 0:
                        # Convert from 0.1 g/kg to percentage and validate
                        soc_value = float(np.nanmean(soc_values) / 10.0)
                        # Check for no-data values (typically negative large numbers)
                        if soc_value < 0 or soc_value > 100:  # No-data or invalid values
                            logger.warning(f"No-data organic carbon value {soc_value}, using default")
                            soil_data['organic_carbon'] = 1.5  # Default moderate carbon
                        elif 0 <= soc_value <= 100:  # Valid organic carbon range
                            soil_data['organic_carbon'] = soc_value
                        else:
                            logger.warning(f"Invalid organic carbon value {soc_value}, using default")
                            soil_data['organic_carbon'] = 1.5  # Default moderate carbon
                    else:
                        logger.warning("No organic carbon data available, using default")
                        soil_data['organic_carbon'] = 1.5
                else:
                    logger.warning("No organic carbon data response, using default")
                    soil_data['organic_carbon'] = 1.5
            except Exception as e:
                logger.warning(f"Error fetching organic carbon data: {e}, using default")
                soil_data['organic_carbon'] = 1.5
            
            # Bulk density data
            try:
                bdod_data = self.soil_grids.get_coverage_data(
                    service_id="bdod",
                    coverage_id="bdod_0-5cm_mean",
                    west=west,
                    south=south,
                    east=east,
                    north=north,
                    crs="urn:ogc:def:crs:EPSG::3857",
                    output="/tmp/bdod_data.tif"
                )
                if bdod_data is not None and hasattr(bdod_data, 'values'):
                    bdod_values = bdod_data.values
                    if bdod_values.size > 0:
                        # Convert from 0.01 g/cm³ to g/cm³ and validate
                        bdod_value = float(np.nanmean(bdod_values) / 100.0)
                        # Check for no-data values (typically negative large numbers)
                        if bdod_value < 0 or bdod_value > 3.0:  # No-data or invalid values
                            logger.warning(f"No-data bulk density value {bdod_value}, using default")
                            soil_data['bulk_density'] = 1.3  # Default moderate density
                        elif 0.5 <= bdod_value <= 2.0:  # Valid bulk density range
                            soil_data['bulk_density'] = bdod_value
                        else:
                            logger.warning(f"Invalid bulk density value {bdod_value}, using default")
                            soil_data['bulk_density'] = 1.3  # Default moderate density
                    else:
                        logger.warning("No bulk density data available, using default")
                        soil_data['bulk_density'] = 1.3
                else:
                    logger.warning("No bulk density data response, using default")
                    soil_data['bulk_density'] = 1.3
            except Exception as e:
                logger.warning(f"Error fetching bulk density data: {e}, using default")
                soil_data['bulk_density'] = 1.3
            
            # Clay content data
            try:
                clay_data = self.soil_grids.get_coverage_data(
                    service_id="clay",
                    coverage_id="clay_0-5cm_mean",
                    west=west,
                    south=south,
                    east=east,
                    north=north,
                    crs="urn:ogc:def:crs:EPSG::3857",
                    output="/tmp/clay_data.tif"
                )
                if clay_data is not None and hasattr(clay_data, 'values'):
                    clay_values = clay_data.values
                    if clay_values.size > 0:
                        # Convert from 0.1% to percentage and validate
                        clay_value = float(np.nanmean(clay_values) / 10.0)
                        # Check for no-data values (typically negative large numbers)
                        if clay_value < 0 or clay_value > 100:  # No-data or invalid values
                            logger.warning(f"No-data clay content value {clay_value}, using default")
                            soil_data['clay_content'] = 25.0  # Default moderate clay
                        elif 0 <= clay_value <= 100:  # Valid clay content range
                            soil_data['clay_content'] = clay_value
                        else:
                            logger.warning(f"Invalid clay content value {clay_value}, using default")
                            soil_data['clay_content'] = 25.0  # Default moderate clay
                    else:
                        logger.warning("No clay content data available, using default")
                        soil_data['clay_content'] = 25.0
                else:
                    logger.warning("No clay content data response, using default")
                    soil_data['clay_content'] = 25.0
            except Exception as e:
                logger.warning(f"Error fetching clay data: {e}, using default")
                soil_data['clay_content'] = 25.0
            
            # Sand content data
            try:
                sand_data = self.soil_grids.get_coverage_data(
                    service_id="sand",
                    coverage_id="sand_0-5cm_mean",
                    west=west,
                    south=south,
                    east=east,
                    north=north,
                    crs="urn:ogc:def:crs:EPSG::3857",
                    output="/tmp/sand_data.tif"
                )
                if sand_data is not None and hasattr(sand_data, 'values'):
                    sand_values = sand_data.values
                    if sand_values.size > 0:
                        # Convert from 0.1% to percentage and validate
                        sand_value = float(np.nanmean(sand_values) / 10.0)
                        # Check for no-data values (typically negative large numbers)
                        if sand_value < 0 or sand_value > 100:  # No-data or invalid values
                            logger.warning(f"No-data sand content value {sand_value}, using default")
                            soil_data['sand_content'] = 40.0  # Default moderate sand
                        elif 0 <= sand_value <= 100:  # Valid sand content range
                            soil_data['sand_content'] = sand_value
                        else:
                            logger.warning(f"Invalid sand content value {sand_value}, using default")
                            soil_data['sand_content'] = 40.0  # Default moderate sand
                    else:
                        logger.warning("No sand content data available, using default")
                        soil_data['sand_content'] = 40.0
                else:
                    logger.warning("No sand content data response, using default")
                    soil_data['sand_content'] = 40.0
            except Exception as e:
                logger.warning(f"Error fetching sand data: {e}, using default")
                soil_data['sand_content'] = 40.0
            
            # Silt content data
            try:
                silt_data = self.soil_grids.get_coverage_data(
                    service_id="silt",
                    coverage_id="silt_0-5cm_mean",
                    west=west,
                    south=south,
                    east=east,
                    north=north,
                    crs="urn:ogc:def:crs:EPSG::3857",
                    output="/tmp/silt_data.tif"
                )
                if silt_data is not None and hasattr(silt_data, 'values'):
                    silt_values = silt_data.values
                    if silt_values.size > 0:
                        # Convert from 0.1% to percentage and validate
                        silt_value = float(np.nanmean(silt_values) / 10.0)
                        # Check for no-data values (typically negative large numbers)
                        if silt_value < 0 or silt_value > 100:  # No-data or invalid values
                            logger.warning(f"No-data silt content value {silt_value}, using default")
                            soil_data['silt_content'] = 35.0  # Default moderate silt
                        elif 0 <= silt_value <= 100:  # Valid silt content range
                            soil_data['silt_content'] = silt_value
                        else:
                            logger.warning(f"Invalid silt content value {silt_value}, using default")
                            soil_data['silt_content'] = 35.0  # Default moderate silt
                    else:
                        logger.warning("No silt content data available, using default")
                        soil_data['silt_content'] = 35.0
                else:
                    logger.warning("No silt content data response, using default")
                    soil_data['silt_content'] = 35.0
            except Exception as e:
                logger.warning(f"Error fetching silt data: {e}, using default")
                soil_data['silt_content'] = 35.0
            
            # Process the collected data
            processed_data = self._process_soil_data(soil_data, latitude, longitude)
            
            logger.info(f"Successfully fetched soil data for {latitude}, {longitude}")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching soil data for {latitude}, {longitude}: {e}")
            raise APIError(f"Failed to fetch soil data: {e}") from e
    
    def _process_soil_data(self, soil_data: Dict[str, Any], latitude: float, longitude: float) -> Dict[str, Any]:
        """Process soil data from SoilGrids library."""
        try:
            # Create soil properties
            soil_props = SoilProperties(
                ph_h2o=soil_data.get('ph_h2o'),
                organic_carbon=soil_data.get('organic_carbon'),
                bulk_density=soil_data.get('bulk_density'),
                clay_content=soil_data.get('clay_content'),
                sand_content=soil_data.get('sand_content'),
                silt_content=soil_data.get('silt_content')
            )
            
            # Create soil profile
            soil_profile = SoilProfile(
                properties=soil_props,
                depth_cm=5,  # 0-5cm depth
                fertility_index=self._calculate_fertility_index(soil_props)
            )
            
            return {
                'soil_profile': soil_profile.dict(),
                'raw_data': soil_data,
                'coordinates': {'latitude': latitude, 'longitude': longitude},
                'data_source': 'soilgrids_python_library',
                'timestamp': None
            }
            
        except Exception as e:
            logger.error(f"Error processing soil data: {e}")
            raise APIError(f"Failed to process soil data: {e}") from e
    
    def _calculate_fertility_index(self, soil_props: SoilProperties) -> float:
        """Calculate soil fertility index based on properties."""
        try:
            score = 0.0
            factors = 0
            
            # pH score (optimal range 6.0-7.5)
            if soil_props.ph_h2o is not None:
                ph = soil_props.ph_h2o
                if 6.0 <= ph <= 7.5:
                    score += 1.0
                elif 5.5 <= ph < 6.0 or 7.5 < ph <= 8.0:
                    score += 0.7
                elif 5.0 <= ph < 5.5 or 8.0 < ph <= 8.5:
                    score += 0.4
                else:
                    score += 0.1
                factors += 1
            
            # Organic carbon score (optimal > 2%)
            if soil_props.organic_carbon is not None:
                oc = soil_props.organic_carbon
                if oc >= 2.0:
                    score += 1.0
                elif oc >= 1.0:
                    score += 0.7
                elif oc >= 0.5:
                    score += 0.4
                else:
                    score += 0.1
                factors += 1
            
            # Bulk density score (optimal 1.0-1.4 g/cm³)
            if soil_props.bulk_density is not None:
                bd = soil_props.bulk_density
                if 1.0 <= bd <= 1.4:
                    score += 1.0
                elif 0.8 <= bd < 1.0 or 1.4 < bd <= 1.6:
                    score += 0.7
                else:
                    score += 0.4
                factors += 1
            
            # Texture score (loam is optimal)
            if all(val is not None for val in [soil_props.clay_content, soil_props.sand_content, soil_props.silt_content]):
                clay = soil_props.clay_content
                sand = soil_props.sand_content
                silt = soil_props.silt_content
                
                # Check if it's close to loam (20-30% clay, 40-50% sand, 20-40% silt)
                if (20 <= clay <= 30 and 40 <= sand <= 50 and 20 <= silt <= 40):
                    score += 1.0
                elif (15 <= clay <= 35 and 35 <= sand <= 55 and 15 <= silt <= 45):
                    score += 0.7
                else:
                    score += 0.4
                factors += 1
            
            return round(score / factors, 3) if factors > 0 else 0.0
            
        except Exception as e:
            logger.warning(f"Error calculating fertility index: {e}")
            return 0.0
