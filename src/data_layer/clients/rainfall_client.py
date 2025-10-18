"""Rainfall data client using Open-Meteo API."""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .base_client import BaseAPIClient, APIError
from ...models.water import RainfallData, RainfallRecord, WaterAvailability
from ...config.config import config

logger = logging.getLogger(__name__)


class RainfallClient(BaseAPIClient):
    """Client for Open-Meteo historical rainfall API."""
    
    def __init__(self):
        """Initialize rainfall client."""
        api_config = config.get_api_config('rainfall')
        super().__init__(
            base_url=api_config.get('base_url', 'https://archive-api.open-meteo.com/v1'),
            timeout=api_config.get('timeout', 10),
            retry_attempts=api_config.get('retry_attempts', 3)
        )
    
    async def fetch_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch rainfall data for given coordinates."""
        logger.info(f"Fetching rainfall data for coordinates: {latitude}, {longitude}")
        
        try:
            # Fetch historical rainfall data (last 90 days)
            rainfall_data = await self._fetch_historical_rainfall(latitude, longitude)
            
            # Process data
            processed_data = self._process_rainfall_data(rainfall_data, latitude, longitude)
            
            logger.info(f"Successfully fetched rainfall data for {latitude}, {longitude}")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error fetching rainfall data for {latitude}, {longitude}: {e}")
            raise APIError(f"Failed to fetch rainfall data: {e}") from e
    
    async def _fetch_historical_rainfall(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch historical rainfall data."""
        # Calculate date range (last 90 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'daily': 'precipitation_sum',
            'timezone': 'auto'
        }
        
        return await self.get('archive', params=params, cache_ttl_days=1)  # Cache for 1 day
    
    def _process_rainfall_data(self, data: Dict[str, Any], latitude: float, longitude: float) -> Dict[str, Any]:
        """Process rainfall data from API response."""
        try:
            daily_data = data.get('daily', {})
            dates = daily_data.get('time', [])
            precipitation = daily_data.get('precipitation_sum', [])
            
            # Create rainfall records
            records = []
            for i, date_str in enumerate(dates):
                if i < len(precipitation) and precipitation[i] is not None:
                    record = RainfallRecord(
                        date=date_str,
                        precipitation_mm=precipitation[i],
                        data_source='open_meteo'
                    )
                    records.append(record)
            
            # Create rainfall data object
            rainfall_data = RainfallData(
                records=records,
                data_period_days=len(records),
                last_updated=datetime.now().isoformat()
            )
            
            # Calculate water availability
            water_availability = WaterAvailability(
                rainfall_data=rainfall_data,
                water_stress_index=rainfall_data.get_water_stress_index() if hasattr(rainfall_data, 'get_water_stress_index') else 0.0,
                irrigation_requirement=rainfall_data.determine_irrigation_requirement() if hasattr(rainfall_data, 'determine_irrigation_requirement') else 'medium',
                seasonal_pattern=self._determine_seasonal_pattern(records)
            )
            
            return {
                'rainfall_data': rainfall_data.dict(),
                'water_availability': water_availability.dict(),
                'raw_data': data,
                'coordinates': {'latitude': latitude, 'longitude': longitude},
                'data_source': 'open_meteo',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing rainfall data: {e}")
            raise APIError(f"Failed to process rainfall data: {e}") from e
    
    def _determine_seasonal_pattern(self, records: List[RainfallRecord]) -> str:
        """Determine seasonal rainfall pattern."""
        if not records:
            return 'unknown'
        
        # Calculate monthly averages
        monthly_totals = {}
        for record in records:
            month = int(record.date.split('-')[1])
            if month not in monthly_totals:
                monthly_totals[month] = []
            monthly_totals[month].append(record.precipitation_mm)
        
        # Calculate average monthly precipitation
        monthly_averages = {}
        for month, totals in monthly_totals.items():
            monthly_averages[month] = sum(totals) / len(totals)
        
        if not monthly_averages:
            return 'unknown'
        
        # Determine pattern based on Indian monsoon seasons
        # June-September: Monsoon
        # October-November: Post-monsoon
        # December-February: Winter
        # March-May: Pre-monsoon
        
        monsoon_months = [6, 7, 8, 9]
        winter_months = [12, 1, 2]
        pre_monsoon_months = [3, 4, 5]
        
        monsoon_avg = sum(monthly_averages.get(m, 0) for m in monsoon_months) / len(monsoon_months)
        winter_avg = sum(monthly_averages.get(m, 0) for m in winter_months) / len(winter_months)
        pre_monsoon_avg = sum(monthly_averages.get(m, 0) for m in pre_monsoon_months) / len(pre_monsoon_months)
        
        if monsoon_avg > winter_avg * 2 and monsoon_avg > pre_monsoon_avg * 2:
            return 'monsoon'
        elif winter_avg > monsoon_avg * 1.5:
            return 'winter_rainfall'
        elif pre_monsoon_avg > monsoon_avg * 1.2:
            return 'pre_monsoon'
        else:
            return 'uniform'
    
    def _calculate_water_stress_index(self, records: List[RainfallRecord]) -> float:
        """Calculate water stress index based on recent rainfall."""
        if not records:
            return 0.9  # High stress if no data
        
        # Get last 30 days of data
        recent_records = records[-30:] if len(records) >= 30 else records
        total_precipitation = sum(record.precipitation_mm for record in recent_records)
        
        # Thresholds for different stress levels (mm per 30 days)
        if total_precipitation >= 150:  # Good rainfall
            return 0.0
        elif total_precipitation >= 100:  # Moderate rainfall
            return 0.3
        elif total_precipitation >= 50:   # Low rainfall
            return 0.6
        else:  # Very low rainfall
            return 0.9
    
    def _determine_irrigation_requirement(self, stress_index: float) -> str:
        """Determine irrigation requirement based on water stress."""
        if stress_index <= 0.2:
            return "low"
        elif stress_index <= 0.5:
            return "medium"
        elif stress_index <= 0.8:
            return "high"
        else:
            return "critical"
