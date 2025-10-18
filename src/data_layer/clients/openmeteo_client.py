"""Open-Meteo API client for fetching weather data (free, no API key required)."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .base_client import BaseAPIClient, APIError
from ...models.weather import WeatherData, WeatherCondition, WeatherForecast
from ...config.config import config

logger = logging.getLogger(__name__)


class OpenMeteoClient(BaseAPIClient):
    """Client for Open-Meteo weather API (free, no API key required)."""
    
    def __init__(self):
        """Initialize Open-Meteo client."""
        api_config = config.get_api_config('openmeteo')
        super().__init__(
            base_url=api_config.get('base_url', 'https://api.open-meteo.com/v1'),
            timeout=api_config.get('timeout', 10),
            retry_attempts=api_config.get('retry_attempts', 3)
        )
    
    async def fetch_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch current weather and forecast data for given coordinates."""
        logger.info(f"Fetching weather data for coordinates: {latitude}, {longitude}")
        
        try:
            # Fetch current weather and 7-day forecast
            current_data = await self._fetch_current_weather(latitude, longitude)
            forecast_data = await self._fetch_forecast(latitude, longitude)
            
            # Process the data
            weather_data = self._process_weather_data(current_data, forecast_data, latitude, longitude)
            
            logger.info(f"Successfully fetched weather data for {latitude}, {longitude}")
            return weather_data
            
        except Exception as e:
            logger.error(f"Error fetching weather data for {latitude}, {longitude}: {e}")
            raise APIError(f"Failed to fetch weather data: {e}") from e
    
    async def _fetch_current_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch current weather conditions."""
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'current': [
                'temperature_2m',
                'relative_humidity_2m',
                'precipitation',
                'weather_code',
                'wind_speed_10m',
                'wind_direction_10m',
                'surface_pressure'
            ],
            'timezone': 'auto'
        }
        
        response = await self.get('forecast', params=params)
        return response
    
    async def _fetch_forecast(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch 7-day weather forecast."""
        params = {
            'latitude': latitude,
            'longitude': longitude,
            'daily': [
                'temperature_2m_max',
                'temperature_2m_min',
                'precipitation_sum',
                'weather_code',
                'wind_speed_10m_max',
                'wind_direction_10m_dominant'
            ],
            'forecast_days': 7,
            'timezone': 'auto'
        }
        
        response = await self.get('forecast', params=params)
        return response
    
    def _process_weather_data(self, current_data: Dict[str, Any], forecast_data: Dict[str, Any], 
                            latitude: float, longitude: float) -> Dict[str, Any]:
        """Process weather data from Open-Meteo API."""
        try:
            # Process current weather
            current = current_data.get('current', {})
            current_weather = WeatherCondition(
                temperature_c=current.get('temperature_2m'),
                humidity_percent=current.get('relative_humidity_2m'),
                pressure_hpa=current.get('surface_pressure'),
                wind_speed_ms=current.get('wind_speed_10m'),  # Open-Meteo returns km/h, but model expects m/s
                wind_direction_deg=current.get('wind_direction_10m')
            )
            
            # Process forecast
            daily = forecast_data.get('daily', {})
            forecast_dates = daily.get('time', [])
            forecast_conditions = []
            
            for i in range(min(7, len(forecast_dates))):
                forecast_condition = WeatherForecast(
                    date=forecast_dates[i],
                    temperature_max_c=daily.get('temperature_2m_max', [None])[i],
                    temperature_min_c=daily.get('temperature_2m_min', [None])[i],
                    precipitation_mm=daily.get('precipitation_sum', [0])[i],
                    wind_speed_ms=daily.get('wind_speed_10m_max', [None])[i],  # Convert km/h to m/s
                    description=self._get_weather_description(daily.get('weather_code', [None])[i])
                )
                forecast_conditions.append(forecast_condition)
            
            # Create weather data object
            weather_data = WeatherData(
                current=current_weather,
                forecast=forecast_conditions,
                location={'latitude': latitude, 'longitude': longitude},
                data_source='openmeteo',
                timestamp=current_data.get('current', {}).get('time')
            )
            
            return {
                'weather_data': weather_data.dict(),
                'raw_data': {
                    'current': current_data,
                    'forecast': forecast_data
                },
                'coordinates': {'latitude': latitude, 'longitude': longitude},
                'data_source': 'openmeteo',
                'timestamp': current_data.get('current', {}).get('time')
            }
            
        except Exception as e:
            logger.error(f"Error processing weather data: {e}")
            raise APIError(f"Failed to process weather data: {e}") from e
    
    def _get_weather_description(self, weather_code: Optional[int]) -> str:
        """Convert weather code to description."""
        if weather_code is None:
            return "Unknown"
        
        weather_descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Light freezing drizzle",
            57: "Dense freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }
        
        return weather_descriptions.get(weather_code, f"Weather code {weather_code}")
    
    async def fetch_historical_weather(self, latitude: float, longitude: float, 
                                    start_date: str, end_date: str) -> Dict[str, Any]:
        """Fetch historical weather data."""
        logger.info(f"Fetching historical weather data for {latitude}, {longitude} from {start_date} to {end_date}")
        
        try:
            params = {
                'latitude': latitude,
                'longitude': longitude,
                'start_date': start_date,
                'end_date': end_date,
                'daily': [
                    'temperature_2m_max',
                    'temperature_2m_min',
                    'precipitation_sum',
                    'weather_code',
                    'wind_speed_10m_max',
                    'wind_direction_10m_dominant'
                ],
                'timezone': 'auto'
            }
            
            response = await self.get('forecast', params=params)
            
            # Process historical data
            historical_data = self._process_historical_data(response, latitude, longitude)
            
            logger.info(f"Successfully fetched historical weather data for {latitude}, {longitude}")
            return historical_data
            
        except Exception as e:
            logger.error(f"Error fetching historical weather data for {latitude}, {longitude}: {e}")
            raise APIError(f"Failed to fetch historical weather data: {e}") from e
    
    def _process_historical_data(self, response: Dict[str, Any], latitude: float, longitude: float) -> Dict[str, Any]:
        """Process historical weather data."""
        try:
            daily = response.get('daily', {})
            dates = daily.get('time', [])
            
            historical_conditions = []
            for i in range(len(dates)):
                condition = WeatherForecast(
                    date=dates[i],
                    temperature_max_c=daily.get('temperature_2m_max', [None])[i],
                    temperature_min_c=daily.get('temperature_2m_min', [None])[i],
                    precipitation_mm=daily.get('precipitation_sum', [0])[i],
                    wind_speed_ms=daily.get('wind_speed_10m_max', [None])[i],  # Convert km/h to m/s
                    description=self._get_weather_description(daily.get('weather_code', [None])[i])
                )
                historical_conditions.append(condition)
            
            return {
                'historical_weather': [condition.dict() for condition in historical_conditions],
                'raw_data': response,
                'coordinates': {'latitude': latitude, 'longitude': longitude},
                'data_source': 'openmeteo_historical',
                'timestamp': None
            }
            
        except Exception as e:
            logger.error(f"Error processing historical weather data: {e}")
            raise APIError(f"Failed to process historical weather data: {e}") from e
