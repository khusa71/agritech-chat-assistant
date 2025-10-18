"""Data validation utilities."""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from ..models.location import LocationData, Coordinates
from ..models.soil import SoilProfile, SoilProperties
from ..models.weather import WeatherData, WeatherCondition
from ..models.water import WaterAvailability, RainfallData
from ..models.market import MarketPrices

logger = logging.getLogger(__name__)


class DataValidator:
    """Data validation utilities."""
    
    @staticmethod
    def validate_coordinates(latitude: float, longitude: float) -> Tuple[bool, Optional[str]]:
        """Validate coordinate values."""
        if not (-90 <= latitude <= 90):
            return False, f"Latitude must be between -90 and 90, got {latitude}"
        
        if not (-180 <= longitude <= 180):
            return False, f"Longitude must be between -180 and 180, got {longitude}"
        
        return True, None
    
    @staticmethod
    def validate_soil_data(soil_profile: SoilProfile) -> Tuple[bool, List[str]]:
        """Validate soil profile data."""
        errors = []
        
        if not soil_profile.properties:
            errors.append("Soil properties are required")
            return False, errors
        
        props = soil_profile.properties
        
        # Validate pH
        if props.ph_h2o is not None:
            if not (3.0 <= props.ph_h2o <= 10.0):
                errors.append(f"pH must be between 3.0 and 10.0, got {props.ph_h2o}")
        
        # Validate organic carbon
        if props.organic_carbon is not None:
            if props.organic_carbon < 0 or props.organic_carbon > 20:
                errors.append(f"Organic carbon must be between 0 and 20%, got {props.organic_carbon}")
        
        # Validate bulk density
        if props.bulk_density is not None:
            if not (0.5 <= props.bulk_density <= 2.5):
                errors.append(f"Bulk density must be between 0.5 and 2.5 g/cm³, got {props.bulk_density}")
        
        # Validate texture percentages
        texture_values = [props.clay_content, props.sand_content, props.silt_content]
        if all(v is not None for v in texture_values):
            total = sum(texture_values)
            if abs(total - 100) > 5:  # Allow 5% tolerance
                errors.append(f"Texture percentages should sum to ~100%, got {total}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_weather_data(weather_data: WeatherData) -> Tuple[bool, List[str]]:
        """Validate weather data."""
        errors = []
        
        if not weather_data.current:
            errors.append("Current weather data is required")
            return False, errors
        
        current = weather_data.current
        
        # Validate temperature
        if not (-50 <= current.temperature_c <= 60):
            errors.append(f"Temperature must be between -50 and 60°C, got {current.temperature_c}")
        
        # Validate humidity
        if not (0 <= current.humidity_percent <= 100):
            errors.append(f"Humidity must be between 0 and 100%, got {current.humidity_percent}")
        
        # Validate pressure
        if current.pressure_hpa is not None:
            if not (800 <= current.pressure_hpa <= 1100):
                errors.append(f"Pressure must be between 800 and 1100 hPa, got {current.pressure_hpa}")
        
        # Validate wind speed
        if current.wind_speed_ms is not None:
            if current.wind_speed_ms < 0:
                errors.append(f"Wind speed must be non-negative, got {current.wind_speed_ms}")
        
        # Validate wind direction
        if current.wind_direction_deg is not None:
            if not (0 <= current.wind_direction_deg <= 360):
                errors.append(f"Wind direction must be between 0 and 360 degrees, got {current.wind_direction_deg}")
        
        # Validate forecast data
        for forecast in weather_data.forecast:
            if forecast.temperature_min_c > forecast.temperature_max_c:
                errors.append(f"Min temperature cannot be greater than max temperature for {forecast.date}")
            
            if forecast.precipitation_mm is not None and forecast.precipitation_mm < 0:
                errors.append(f"Precipitation cannot be negative for {forecast.date}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_rainfall_data(rainfall_data: WaterAvailability) -> Tuple[bool, List[str]]:
        """Validate rainfall data."""
        errors = []
        
        if not rainfall_data.rainfall_data:
            errors.append("Rainfall data is required")
            return False, errors
        
        rainfall = rainfall_data.rainfall_data
        
        # Validate records
        for record in rainfall.records:
            if record.precipitation_mm < 0:
                errors.append(f"Precipitation cannot be negative for {record.date}")
            
            if record.precipitation_mm > 500:  # Unrealistic daily rainfall
                errors.append(f"Precipitation seems unrealistic for {record.date}: {record.precipitation_mm}mm")
        
        # Validate water stress index
        if rainfall_data.water_stress_index is not None:
            if not (0.0 <= rainfall_data.water_stress_index <= 1.0):
                errors.append(f"Water stress index must be between 0.0 and 1.0, got {rainfall_data.water_stress_index}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_market_data(market_prices: MarketPrices) -> Tuple[bool, List[str]]:
        """Validate market price data."""
        errors = []
        
        # Validate price records
        for price in market_prices.prices:
            if price.price_per_kg < 0:
                errors.append(f"Price cannot be negative for {price.crop_name}")
            
            if price.price_per_kg > 10000:  # Unrealistic price
                errors.append(f"Price seems unrealistic for {price.crop_name}: {price.price_per_kg}")
        
        # Validate price analyses
        for analysis in market_prices.analyses:
            if analysis.current_price < 0:
                errors.append(f"Current price cannot be negative for {analysis.crop_name}")
            
            if abs(analysis.price_change_percent) > 1000:
                errors.append(f"Price change percentage seems unrealistic for {analysis.crop_name}")
            
            if not (0.0 <= analysis.volatility_index <= 1.0):
                errors.append(f"Volatility index must be between 0.0 and 1.0 for {analysis.crop_name}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_location_data(location_data: LocationData) -> Tuple[bool, List[str]]:
        """Validate complete location data."""
        errors = []
        
        # Validate coordinates
        if location_data.location and location_data.location.coordinates:
            coords = location_data.location.coordinates
            is_valid, error = DataValidator.validate_coordinates(coords.latitude, coords.longitude)
            if not is_valid:
                errors.append(error)
        
        # Validate soil data
        if location_data.soil_profile:
            is_valid, soil_errors = DataValidator.validate_soil_data(location_data.soil_profile)
            if not is_valid:
                errors.extend(soil_errors)
        
        # Validate weather data
        if location_data.weather_data:
            is_valid, weather_errors = DataValidator.validate_weather_data(location_data.weather_data)
            if not is_valid:
                errors.extend(weather_errors)
        
        # Validate rainfall data
        if location_data.rainfall_data:
            is_valid, rainfall_errors = DataValidator.validate_rainfall_data(location_data.rainfall_data)
            if not is_valid:
                errors.extend(rainfall_errors)
        
        # Validate market data
        if location_data.market_prices:
            is_valid, market_errors = DataValidator.validate_market_data(location_data.market_prices)
            if not is_valid:
                errors.extend(market_errors)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_crop_requirements(crop_name: str, requirements: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate crop requirements data."""
        errors = []
        
        # Validate pH range
        ph_min = requirements.get('ph_min')
        ph_max = requirements.get('ph_max')
        ph_optimal = requirements.get('ph_optimal')
        
        if ph_min and ph_max and ph_optimal:
            if not (ph_min <= ph_optimal <= ph_max):
                errors.append(f"pH values must be in order: min <= optimal <= max")
            
            if not (3.0 <= ph_min <= 10.0):
                errors.append(f"pH min must be between 3.0 and 10.0, got {ph_min}")
            
            if not (3.0 <= ph_max <= 10.0):
                errors.append(f"pH max must be between 3.0 and 10.0, got {ph_max}")
        
        # Validate temperature range
        temp_min = requirements.get('temp_min_c')
        temp_max = requirements.get('temp_max_c')
        temp_optimal = requirements.get('temp_optimal_c')
        
        if temp_min and temp_max and temp_optimal:
            if not (temp_min <= temp_optimal <= temp_max):
                errors.append(f"Temperature values must be in order: min <= optimal <= max")
            
            if not (-10 <= temp_min <= 50):
                errors.append(f"Temperature min must be between -10 and 50°C, got {temp_min}")
            
            if not (-10 <= temp_max <= 50):
                errors.append(f"Temperature max must be between -10 and 50°C, got {temp_max}")
        
        # Validate rainfall
        rainfall_min = requirements.get('rainfall_min_mm')
        rainfall_max = requirements.get('rainfall_max_mm')
        
        if rainfall_min and rainfall_max:
            if rainfall_min > rainfall_max:
                errors.append(f"Rainfall min cannot be greater than max")
        
        if rainfall_min and rainfall_min < 0:
            errors.append(f"Rainfall min cannot be negative, got {rainfall_min}")
        
        # Validate growing season months
        growing_months = requirements.get('growing_season_months', [])
        if not growing_months:
            errors.append("Growing season months are required")
        else:
            for month in growing_months:
                if not (1 <= month <= 12):
                    errors.append(f"Growing month must be between 1 and 12, got {month}")
        
        # Validate growth duration
        duration = requirements.get('growth_duration_days')
        if duration and not (30 <= duration <= 365):
            errors.append(f"Growth duration must be between 30 and 365 days, got {duration}")
        
        # Validate yield and price
        yield_per_acre = requirements.get('typical_yield_per_acre')
        if yield_per_acre and yield_per_acre < 0:
            errors.append(f"Yield per acre cannot be negative, got {yield_per_acre}")
        
        base_price = requirements.get('base_market_price_per_kg')
        if base_price and base_price < 0:
            errors.append(f"Base market price cannot be negative, got {base_price}")
        
        return len(errors) == 0, errors
