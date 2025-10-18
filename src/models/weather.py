"""Weather data models."""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator
from datetime import datetime


class WeatherCondition(BaseModel):
    """Current weather conditions."""
    
    temperature_c: float = Field(..., ge=-50, le=60, description="Temperature in Celsius")
    humidity_percent: float = Field(..., ge=0, le=100, description="Relative humidity (%)")
    pressure_hpa: Optional[float] = Field(None, ge=800, le=1100, description="Atmospheric pressure (hPa)")
    wind_speed_ms: Optional[float] = Field(None, ge=0, description="Wind speed (m/s)")
    wind_direction_deg: Optional[float] = Field(None, ge=0, le=360, description="Wind direction (degrees)")
    visibility_km: Optional[float] = Field(None, ge=0, description="Visibility (km)")
    uv_index: Optional[float] = Field(None, ge=0, le=15, description="UV index")
    
    @validator('wind_direction_deg')
    def validate_wind_direction(cls, v):
        """Validate wind direction is within valid range."""
        if v is not None and (v < 0 or v > 360):
            raise ValueError("Wind direction must be between 0 and 360 degrees")
        return v


class WeatherForecast(BaseModel):
    """Weather forecast for a specific day."""
    
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    temperature_min_c: float = Field(..., ge=-50, le=60, description="Minimum temperature (C)")
    temperature_max_c: float = Field(..., ge=-50, le=60, description="Maximum temperature (C)")
    humidity_percent: Optional[float] = Field(None, ge=0, le=100, description="Average humidity (%)")
    precipitation_mm: Optional[float] = Field(None, ge=0, description="Precipitation (mm)")
    wind_speed_ms: Optional[float] = Field(None, ge=0, description="Wind speed (m/s)")
    description: Optional[str] = Field(None, description="Weather description")
    
    @validator('temperature_min_c', 'temperature_max_c')
    def validate_temperature_range(cls, v, values):
        """Validate temperature range."""
        if 'temperature_min_c' in values and 'temperature_max_c' in values:
            min_temp = values.get('temperature_min_c')
            max_temp = values.get('temperature_max_c')
            if min_temp is not None and max_temp is not None and min_temp > max_temp:
                raise ValueError("Minimum temperature cannot be greater than maximum temperature")
        return v


class WeatherData(BaseModel):
    """Complete weather data including current conditions and forecast."""
    
    current: WeatherCondition
    forecast: List[WeatherForecast] = Field(default_factory=list, description="7-day weather forecast")
    location_name: Optional[str] = Field(None, description="Location name from weather API")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    
    @validator('forecast')
    def validate_forecast_length(cls, v):
        """Validate forecast length."""
        if len(v) > 14:  # Limit to 2 weeks
            raise ValueError("Forecast cannot exceed 14 days")
        return v
    
    def get_average_temperature(self, days: int = 7) -> Optional[float]:
        """Get average temperature over specified days."""
        if not self.forecast or days <= 0:
            return None
        
        forecast_days = self.forecast[:days]
        if not forecast_days:
            return None
        
        avg_temps = [(day.temperature_min_c + day.temperature_max_c) / 2 for day in forecast_days]
        return sum(avg_temps) / len(avg_temps)
    
    def get_total_precipitation(self, days: int = 7) -> float:
        """Get total precipitation over specified days."""
        if not self.forecast or days <= 0:
            return 0.0
        
        forecast_days = self.forecast[:days]
        return sum(day.precipitation_mm or 0.0 for day in forecast_days)
    
    class Config:
        json_schema_extra = {
            "example": {
                "current": {
                    "temperature_c": 28.5,
                    "humidity_percent": 65.0,
                    "pressure_hpa": 1013.25,
                    "wind_speed_ms": 3.2,
                    "wind_direction_deg": 180.0,
                    "visibility_km": 10.0,
                    "uv_index": 6.0
                },
                "forecast": [
                    {
                        "date": "2024-01-16",
                        "temperature_min_c": 22.0,
                        "temperature_max_c": 32.0,
                        "humidity_percent": 70.0,
                        "precipitation_mm": 5.0,
                        "wind_speed_ms": 4.0,
                        "description": "Partly cloudy"
                    }
                ],
                "location_name": "Pune",
                "last_updated": "2024-01-15T10:30:00Z"
            }
        }
