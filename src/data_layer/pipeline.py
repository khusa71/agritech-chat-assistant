"""Main data pipeline for orchestrating data collection and processing."""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from .clients.soilgrids_client import SoilGridsClient
from .clients.openmeteo_client import OpenMeteoClient
from .clients.rainfall_client import RainfallClient
from .clients.market_price_client import MarketPriceClient
from .crop_database import CropDatabase, CropMatcher
from ..models.location import LocationData, Location, Coordinates
from ..models.soil import SoilProfile
from ..models.weather import WeatherData
from ..models.water import WaterAvailability, RainfallData
from ..models.market import MarketPrices
from ..models.crop import CropRecommendation
from ..config.config import config

logger = logging.getLogger(__name__)

# Rebuild models to ensure all references are resolved
LocationData.model_rebuild()


class DataPipeline:
    """Main data pipeline for orchestrating data collection and processing."""
    
    def __init__(self):
        """Initialize data pipeline."""
        self.soil_client = SoilGridsClient()
        self.weather_client = OpenMeteoClient()
        self.rainfall_client = RainfallClient()
        self.market_client = MarketPriceClient()
        
        self.crop_database = CropDatabase()
        self.crop_matcher = CropMatcher(self.crop_database)
        
        # Cache for location data
        self.location_cache: Dict[str, LocationData] = {}
        self.cache_ttl_days = config.get_cache_ttl_days()
    
    async def fetch_location_data(self, latitude: float, longitude: float) -> LocationData:
        """Fetch complete location data from all sources with robust error handling."""
        logger.info(f"Fetching location data for {latitude}, {longitude}")
        
        # Validate coordinates
        if not self._validate_coordinates(latitude, longitude):
            raise ValueError(f"Invalid coordinates: {latitude}, {longitude}")
        
        try:
            # Check cache first
            cached_data = self._get_cached_data(latitude, longitude)
            if cached_data:
                logger.info(f"Using cached data for {latitude}, {longitude}")
                return cached_data
            
            # Create location object with city/state info
            location = Location(
                coordinates=Coordinates(latitude=latitude, longitude=longitude),
                city=self._get_city_name(latitude, longitude),
                state=self._get_state_name(latitude, longitude)
            )
            
            # Fetch data from all sources in parallel with timeout
            tasks = [
                self._fetch_with_timeout(self._fetch_soil_data(latitude, longitude), "soil"),
                self._fetch_with_timeout(self._fetch_weather_data(latitude, longitude), "weather"),
                self._fetch_with_timeout(self._fetch_rainfall_data(latitude, longitude), "rainfall"),
                self._fetch_with_timeout(self._fetch_market_data(latitude, longitude), "market")
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results with detailed logging
            soil_profile = None
            weather_data = None
            rainfall_data = None
            market_prices = None
            
            source_names = ["soil", "weather", "rainfall", "market"]
            for i, result in enumerate(results):
                source_name = source_names[i]
                if isinstance(result, Exception):
                    logger.warning(f"Failed to fetch {source_name} data: {result}")
                    continue
                
                if result:
                    try:
                        if i == 0:  # Soil data
                            soil_profile = self._process_soil_data(result)
                            logger.info(f"✅ Soil data processed successfully")
                        elif i == 1:  # Weather data
                            weather_data = self._process_weather_data(result)
                            logger.info(f"✅ Weather data processed successfully")
                        elif i == 2:  # Rainfall data
                            rainfall_data = self._process_rainfall_data(result)
                            logger.info(f"✅ Rainfall data processed successfully")
                        elif i == 3:  # Market data
                            market_prices = self._process_market_data(result)
                            logger.info(f"✅ Market data processed successfully")
                    except Exception as e:
                        logger.error(f"Error processing {source_name} data: {e}")
                        continue
                else:
                    logger.warning(f"No {source_name} data returned")
            
            # Create location data object with proper handling of None values
            location_data = LocationData(
                location=location,
                soil_profile=soil_profile,
                weather_data=weather_data,
                rainfall_data=rainfall_data,
                market_prices=market_prices,
                timestamp=datetime.now().isoformat()
            )
            
            # Cache the result
            self._cache_data(latitude, longitude, location_data)
            
            logger.info(f"Successfully fetched location data for {latitude}, {longitude}")
            return location_data
            
        except Exception as e:
            logger.error(f"Error fetching location data for {latitude}, {longitude}: {e}")
            raise
    
    async def _fetch_soil_data(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Fetch soil data."""
        try:
            async with self.soil_client as client:
                return await client.fetch_data(latitude, longitude)
        except Exception as e:
            logger.warning(f"Error fetching soil data: {e}")
            return None
    
    async def _fetch_weather_data(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Fetch weather data."""
        try:
            async with self.weather_client as client:
                return await client.fetch_data(latitude, longitude)
        except Exception as e:
            logger.warning(f"Error fetching weather data: {e}")
            return None
    
    async def _fetch_rainfall_data(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Fetch rainfall data."""
        try:
            async with self.rainfall_client as client:
                return await client.fetch_data(latitude, longitude)
        except Exception as e:
            logger.warning(f"Error fetching rainfall data: {e}")
            return None
    
    async def _fetch_market_data(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Fetch market data."""
        try:
            async with self.market_client as client:
                return await client.fetch_data(latitude, longitude)
        except Exception as e:
            logger.warning(f"Error fetching market data: {e}")
            return None
    
    def _process_soil_data(self, data: Dict[str, Any]) -> Optional[SoilProfile]:
        """Process soil data from API response."""
        try:
            soil_profile_data = data.get('soil_profile')
            if soil_profile_data:
                return SoilProfile(**soil_profile_data)
            return None
        except Exception as e:
            logger.warning(f"Error processing soil data: {e}")
            return None
    
    def _process_weather_data(self, data: Dict[str, Any]) -> Optional[WeatherData]:
        """Process weather data from API response."""
        try:
            weather_data = data.get('weather_data')
            if weather_data:
                return WeatherData(**weather_data)
            return None
        except Exception as e:
            logger.warning(f"Error processing weather data: {e}")
            return None
    
    def _process_rainfall_data(self, data: Dict[str, Any]) -> Optional[RainfallData]:
        """Process rainfall data from API response."""
        try:
            rainfall_data_dict = data.get('rainfall_data')
            if rainfall_data_dict:
                return RainfallData(**rainfall_data_dict)
            return None
        except Exception as e:
            logger.warning(f"Error processing rainfall data: {e}")
            return None
    
    def _process_market_data(self, data: Dict[str, Any]) -> Optional[MarketPrices]:
        """Process market data from API response."""
        try:
            market_prices_data = data.get('market_prices')
            if market_prices_data:
                return MarketPrices(**market_prices_data)
            return None
        except Exception as e:
            logger.warning(f"Error processing market data: {e}")
            return None
    
    def _get_cached_data(self, latitude: float, longitude: float) -> Optional[LocationData]:
        """Get cached location data if still valid."""
        cache_key = f"{latitude}_{longitude}"
        
        if cache_key in self.location_cache:
            cached_data = self.location_cache[cache_key]
            
            # Check if cache is still valid
            if cached_data.timestamp:
                cached_time = datetime.fromisoformat(cached_data.timestamp)
                expiry_time = cached_time + timedelta(days=self.cache_ttl_days)
                
                if datetime.now() < expiry_time:
                    return cached_data
                else:
                    # Remove expired cache entry
                    del self.location_cache[cache_key]
        
        return None
    
    def _cache_data(self, latitude: float, longitude: float, location_data: LocationData):
        """Cache location data."""
        cache_key = f"{latitude}_{longitude}"
        self.location_cache[cache_key] = location_data
        
        # Limit cache size (keep only last 100 entries)
        if len(self.location_cache) > 100:
            # Remove oldest entries
            oldest_keys = list(self.location_cache.keys())[:len(self.location_cache) - 100]
            for key in oldest_keys:
                del self.location_cache[key]
    
    def get_crop_recommendations(
        self, 
        location_data: LocationData, 
        max_crops: int = 5,
        min_score: float = 0.3
    ) -> List[CropRecommendation]:
        """Get crop recommendations for a location."""
        try:
            recommendations = self.crop_matcher.get_crop_recommendations(
                location_data, max_crops, min_score
            )
            
            logger.info(f"Generated {len(recommendations)} crop recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting crop recommendations: {e}")
            return []
    
    def _validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """Validate coordinate ranges."""
        return -90 <= latitude <= 90 and -180 <= longitude <= 180
    
    async def _fetch_with_timeout(self, coro, source_name: str, timeout: int = 30):
        """Fetch data with timeout and error handling."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {source_name} data after {timeout}s")
            return None
        except Exception as e:
            logger.warning(f"Error fetching {source_name} data: {e}")
            return None
    
    def get_cached_data(self, latitude: float, longitude: float, max_age_days: int = 7) -> Optional[LocationData]:
        """Get cached data if within specified age limit."""
        cache_key = f"{latitude}_{longitude}"
        
        if cache_key in self.location_cache:
            cached_data = self.location_cache[cache_key]
            
            if cached_data.timestamp:
                cached_time = datetime.fromisoformat(cached_data.timestamp)
                expiry_time = cached_time + timedelta(days=max_age_days)
                
                if datetime.now() < expiry_time:
                    return cached_data
        
        return None
    
    def clear_cache(self):
        """Clear all cached data."""
        self.location_cache.clear()
        logger.info("Location cache cleared")
    
    def _get_city_name(self, latitude: float, longitude: float) -> Optional[str]:
        """Get city name from coordinates (simplified mapping)."""
        # Simplified city mapping for major Indian cities
        city_mapping = {
            (18.5204, 73.8567): "Pune",
            (19.0760, 72.8777): "Mumbai", 
            (12.9716, 77.5946): "Bangalore",
            (17.3850, 78.4867): "Hyderabad",
            (28.7041, 77.1025): "Delhi",
            (22.5726, 88.3639): "Kolkata",
            (26.2389, 73.0243): "Jodhpur",
            (25.2048, 55.2708): "Dubai",  # For testing
        }
        
        # Find closest city (within 0.5 degrees)
        for (lat, lon), city in city_mapping.items():
            if abs(latitude - lat) < 0.5 and abs(longitude - lon) < 0.5:
                return city
        
        return None
    
    def _get_state_name(self, latitude: float, longitude: float) -> Optional[str]:
        """Get state name from coordinates (simplified mapping)."""
        # Simplified state mapping for Indian states
        state_mapping = {
            (18.5204, 73.8567): "Maharashtra",
            (19.0760, 72.8777): "Maharashtra",
            (12.9716, 77.5946): "Karnataka", 
            (17.3850, 78.4867): "Telangana",
            (28.7041, 77.1025): "Delhi",
            (22.5726, 88.3639): "West Bengal",
            (26.2389, 73.0243): "Rajasthan",
        }
        
        # Find closest state (within 1 degree)
        for (lat, lon), state in state_mapping.items():
            if abs(latitude - lat) < 1.0 and abs(longitude - lon) < 1.0:
                return state
        
        return None
    
    def get_crop_requirements(self, crop_name: str) -> Optional[Dict[str, Any]]:
        """Get crop requirements by name."""
        requirements = self.crop_database.get_crop_requirements(crop_name)
        if requirements:
            return requirements.dict()
        return None
    
    def get_available_crops(self) -> List[str]:
        """Get list of all available crops."""
        return self.crop_database.get_all_crops()
    
    def get_crops_by_season(self, month: int) -> List[str]:
        """Get crops suitable for given month."""
        return self.crop_database.get_crops_by_season(month)
    
    async def process_and_store(self, location_data: LocationData) -> str:
        """Process and store location data (placeholder for database integration)."""
        try:
            # This would integrate with database storage
            # For now, just return a success message
            logger.info(f"Processing location data for {location_data.location.coordinates.latitude}, {location_data.location.coordinates.longitude}")
            
            # In a real implementation, this would:
            # 1. Validate the data
            # 2. Store in database
            # 3. Update indexes
            # 4. Return storage ID
            
            return "data_processed_successfully"
            
        except Exception as e:
            logger.error(f"Error processing and storing location data: {e}")
            raise
