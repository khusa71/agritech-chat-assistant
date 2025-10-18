"""OpenWeatherMap API client for fetching weather data."""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .base_client import BaseAPIClient, APIError
from ...models.weather import WeatherData, WeatherCondition, WeatherForecast
from ...config.config import config

logger = logging.getLogger(__name__)


class OpenWeatherClient(BaseAPIClient):
    """Client for OpenWeatherMap API."""
    
    def __init__(self):
        """Initialize OpenWeather client."""
        api_config = config.get_api_config('openweather')
        super().__init__(
            base_url=api_config.get('base_url', 'https://api.openweathermap.org/data/2.5'),
            timeout=api_config.get('timeout', 10),
            retry_attempts=api_config.get('retry_attempts', 3)
        )
        self.api_key = config.get_openweather_api_key()
    
    async def fetch_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch weather data for given coordinates."""
        logger.info(f"Fetching weather data for coordinates: {latitude}, {longitude}")
        
        try:
            # Fetch current weather and forecast in parallel
            current_task = self._fetch_current_weather(latitude, longitude)
            forecast_task = self._fetch_forecast(latitude, longitude)
            
            current_data, forecast_data = await asyncio.gather(
                current_task, forecast_task, return_exceptions=True
            )
            
            # Handle exceptions
            if isinstance(current_data, Exception):
                logger.error(f"Error fetching current weather: {current_data}")
                current_data = None
            
            if isinstance(forecast_data, Exception):
                logger.error(f"Error fetching forecast: {forecast_data}")
                forecast_data = None
            
            # Process data
            weather_data = self._process_weather_data(current_data, forecast_data, latitude, longitude)
            
            logger.info(f"Successfully fetched weather data for {latitude}, {longitude}")
            return weather_data
            
        except Exception as e:
            logger.error(f"Error fetching weather data for {latitude}, {longitude}: {e}")
            raise APIError(f"Failed to fetch weather data: {e}") from e
    
    async def _fetch_current_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch current weather conditions."""
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        return await self.get('weather', params=params, cache_ttl_days=1)  # Cache for 1 day
    
    async def _fetch_forecast(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch 5-day weather forecast."""
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        return await self.get('forecast', params=params, cache_ttl_days=1)  # Cache for 1 day
    
    def _process_weather_data(
        self, 
        current_data: Optional[Dict[str, Any]], 
        forecast_data: Optional[Dict[str, Any]], 
        latitude: float, 
        longitude: float
    ) -> Dict[str, Any]:
        """Process weather data from API responses."""
        try:
            # Process current weather
            current_weather = None
            if current_data:
                current_weather = self._process_current_weather(current_data)
            
            # Process forecast
            forecast = []
            if forecast_data:
                forecast = self._process_forecast(forecast_data)
            
            # Create weather data object
            weather_data = WeatherData(
                current=current_weather or self._get_default_current_weather(),
                forecast=forecast,
                location_name=current_data.get('name') if current_data else None,
                last_updated=datetime.now().isoformat()
            )
            
            return {
                'weather_data': weather_data.dict(),
                'raw_data': {
                    'current': current_data,
                    'forecast': forecast_data
                },
                'coordinates': {'latitude': latitude, 'longitude': longitude},
                'data_source': 'openweather',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing weather data: {e}")
            raise APIError(f"Failed to process weather data: {e}") from e
    
    def _process_current_weather(self, data: Dict[str, Any]) -> WeatherCondition:
        """Process current weather data."""
        main = data.get('main', {})
        wind = data.get('wind', {})
        weather = data.get('weather', [{}])[0]
        
        return WeatherCondition(
            temperature_c=main.get('temp', 0),
            humidity_percent=main.get('humidity', 0),
            pressure_hpa=main.get('pressure'),
            wind_speed_ms=wind.get('speed'),
            wind_direction_deg=wind.get('deg'),
            visibility_km=data.get('visibility', 0) / 1000 if data.get('visibility') else None,
            uv_index=None  # Not available in current weather API
        )
    
    def _process_forecast(self, data: Dict[str, Any]) -> List[WeatherForecast]:
        """Process forecast data."""
        forecast_list = []
        forecast_items = data.get('list', [])
        
        # Group forecast items by date
        daily_forecasts = {}
        
        for item in forecast_items:
            dt_txt = item.get('dt_txt', '')
            if not dt_txt:
                continue
            
            date_str = dt_txt.split(' ')[0]  # Extract date part
            
            if date_str not in daily_forecasts:
                daily_forecasts[date_str] = []
            
            daily_forecasts[date_str].append(item)
        
        # Process each day
        for date_str, items in daily_forecasts.items():
            if not items:
                continue
            
            # Calculate daily min/max temperatures
            temps = [item.get('main', {}).get('temp', 0) for item in items]
            humidities = [item.get('main', {}).get('humidity', 0) for item in items]
            precipitations = [item.get('rain', {}).get('3h', 0) for item in items]
            wind_speeds = [item.get('wind', {}).get('speed', 0) for item in items]
            
            # Get weather description from first item of the day
            weather_desc = items[0].get('weather', [{}])[0].get('description', '')
            
            forecast = WeatherForecast(
                date=date_str,
                temperature_min_c=min(temps),
                temperature_max_c=max(temps),
                humidity_percent=sum(humidities) / len(humidities),
                precipitation_mm=sum(precipitations),
                wind_speed_ms=sum(wind_speeds) / len(wind_speeds),
                description=weather_desc
            )
            
            forecast_list.append(forecast)
        
        return forecast_list[:7]  # Limit to 7 days
    
    def _get_default_current_weather(self) -> WeatherCondition:
        """Get default current weather when API fails."""
        return WeatherCondition(
            temperature_c=25.0,
            humidity_percent=60.0,
            pressure_hpa=1013.25,
            wind_speed_ms=2.0,
            wind_direction_deg=180.0,
            visibility_km=10.0,
            uv_index=5.0
        )
