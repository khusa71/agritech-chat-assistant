"""Location and coordinate models."""

from typing import Optional
from pydantic import BaseModel, Field, validator


class Coordinates(BaseModel):
    """Geographic coordinates."""
    
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    
    @validator('latitude', 'longitude')
    def validate_coordinates(cls, v):
        """Validate coordinate precision."""
        if abs(v) > 0 and abs(v) < 0.0001:
            raise ValueError("Coordinates must have at least 4 decimal places for accuracy")
        return round(v, 6)  # Round to 6 decimal places


class Location(BaseModel):
    """Location information with coordinates and metadata."""
    
    coordinates: Coordinates
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State or region name")
    region: Optional[str] = Field(None, description="Region or state name")
    country: Optional[str] = Field(None, description="Country name")
    elevation_m: Optional[float] = Field(None, ge=0, description="Elevation in meters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "coordinates": {"latitude": 18.5204, "longitude": 73.8567},
                "region": "Maharashtra",
                "country": "India",
                "elevation_m": 560.0
            }
        }


class LocationData(BaseModel):
    """Complete location data including all environmental factors."""
    
    location: Location
    soil_profile: Optional['SoilProfile'] = None
    weather_data: Optional['WeatherData'] = None
    rainfall_data: Optional['RainfallData'] = None
    market_prices: Optional['MarketPrices'] = None
    timestamp: Optional[str] = Field(None, description="ISO timestamp when data was collected")
    
    class Config:
        json_schema_extra = {
            "example": {
                "location": {
                    "coordinates": {"latitude": 18.5204, "longitude": 73.8567},
                    "region": "Maharashtra",
                    "country": "India"
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
