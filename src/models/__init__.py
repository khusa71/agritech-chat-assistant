"""Models package for AgriTech crop recommendation system."""

from .location import Coordinates, Location, LocationData
from .soil import SoilTexture, SoilProperties, SoilProfile
from .weather import WeatherCondition, WeatherForecast, WeatherData
from .water import RainfallRecord, RainfallData, WaterAvailability
from .market import PriceTrend, CropPrice, PriceAnalysis, MarketPrices
from .crop import WaterRequirement, SoilType, CropRequirements, CropRecommendation
from .db_schema import Base, Location as LocationDB, SoilData, WeatherData as WeatherDataDB, RainfallData as RainfallDataDB, MarketPrices as MarketPricesDB, CropRecommendation as CropRecommendationDB, CropRequirements as CropRequirementsDB

__all__ = [
    # Location models
    'Coordinates', 'Location', 'LocationData',
    
    # Soil models
    'SoilTexture', 'SoilProperties', 'SoilProfile',
    
    # Weather models
    'WeatherCondition', 'WeatherForecast', 'WeatherData',
    
    # Water models
    'RainfallRecord', 'RainfallData', 'WaterAvailability',
    
    # Market models
    'PriceTrend', 'CropPrice', 'PriceAnalysis', 'MarketPrices',
    
    # Crop models
    'WaterRequirement', 'SoilType', 'CropRequirements', 'CropRecommendation',
    
    # Database models
    'Base', 'LocationDB', 'SoilData', 'WeatherDataDB', 'RainfallDataDB', 
    'MarketPricesDB', 'CropRecommendationDB', 'CropRequirementsDB'
]
