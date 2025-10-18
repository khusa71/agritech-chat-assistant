"""Location-based crop filtering and selection mechanism."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ClimateZone(Enum):
    """Climate zones for crop selection."""
    TROPICAL = "tropical"
    SUBTROPICAL = "subtropical"
    TEMPERATE = "temperate"
    ARID = "arid"
    SEMI_ARID = "semi_arid"

class SoilType(Enum):
    """Soil types for crop selection."""
    CLAY = "clay"
    SANDY = "sandy"
    LOAMY = "loamy"
    SILTY = "silty"
    RED_SOIL = "red_soil"
    BLACK_SOIL = "black_soil"

@dataclass
class LocationConditions:
    """Location conditions for crop selection."""
    latitude: float
    longitude: float
    climate_zone: ClimateZone
    soil_type: SoilType
    rainfall_mm: float
    temperature_c: float
    elevation_m: Optional[float] = None
    water_availability: str = "medium"  # low, medium, high

class CropSuitabilityFilter:
    """Filters crops based on location conditions."""
    
    def __init__(self):
        """Initialize crop suitability filter."""
        # Define crop requirements for different conditions
        self.crop_requirements = {
            'wheat': {
                'climate_zones': [ClimateZone.TEMPERATE, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.LOAMY, SoilType.CLAY],
                'rainfall_range': (300, 800),
                'temperature_range': (15, 25),
                'water_requirement': 'medium'
            },
            'rice': {
                'climate_zones': [ClimateZone.TROPICAL, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.CLAY, SoilType.LOAMY],
                'rainfall_range': (1000, 2000),
                'temperature_range': (20, 35),
                'water_requirement': 'high'
            },
            'maize': {
                'climate_zones': [ClimateZone.TROPICAL, ClimateZone.SUBTROPICAL, ClimateZone.TEMPERATE],
                'soil_types': [SoilType.LOAMY, SoilType.SANDY],
                'rainfall_range': (500, 1000),
                'temperature_range': (18, 30),
                'water_requirement': 'medium'
            },
            'soybean': {
                'climate_zones': [ClimateZone.TEMPERATE, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.LOAMY, SoilType.CLAY],
                'rainfall_range': (600, 1200),
                'temperature_range': (20, 30),
                'water_requirement': 'medium'
            },
            'cotton': {
                'climate_zones': [ClimateZone.TROPICAL, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.BLACK_SOIL, SoilType.LOAMY],
                'rainfall_range': (500, 1000),
                'temperature_range': (25, 35),
                'water_requirement': 'medium'
            },
            'sugarcane': {
                'climate_zones': [ClimateZone.TROPICAL, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.LOAMY, SoilType.CLAY],
                'rainfall_range': (1000, 2000),
                'temperature_range': (25, 35),
                'water_requirement': 'high'
            },
            'potato': {
                'climate_zones': [ClimateZone.TEMPERATE, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.LOAMY, SoilType.SANDY],
                'rainfall_range': (400, 800),
                'temperature_range': (15, 25),
                'water_requirement': 'medium'
            },
            'onion': {
                'climate_zones': [ClimateZone.TEMPERATE, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.LOAMY, SoilType.SANDY],
                'rainfall_range': (300, 600),
                'temperature_range': (15, 30),
                'water_requirement': 'low'
            },
            'tomato': {
                'climate_zones': [ClimateZone.TROPICAL, ClimateZone.SUBTROPICAL, ClimateZone.TEMPERATE],
                'soil_types': [SoilType.LOAMY, SoilType.SANDY],
                'rainfall_range': (400, 800),
                'temperature_range': (20, 30),
                'water_requirement': 'medium'
            },
            'chilli': {
                'climate_zones': [ClimateZone.TROPICAL, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.LOAMY, SoilType.SANDY],
                'rainfall_range': (500, 1000),
                'temperature_range': (20, 35),
                'water_requirement': 'medium'
            },
            'turmeric': {
                'climate_zones': [ClimateZone.TROPICAL, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.LOAMY, SoilType.CLAY],
                'rainfall_range': (1000, 2000),
                'temperature_range': (20, 35),
                'water_requirement': 'high'
            },
            'ginger': {
                'climate_zones': [ClimateZone.TROPICAL, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.LOAMY, SoilType.CLAY],
                'rainfall_range': (1000, 2000),
                'temperature_range': (20, 35),
                'water_requirement': 'high'
            },
            'garlic': {
                'climate_zones': [ClimateZone.TEMPERATE, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.LOAMY, SoilType.SANDY],
                'rainfall_range': (300, 600),
                'temperature_range': (15, 30),
                'water_requirement': 'low'
            },
            'mustard': {
                'climate_zones': [ClimateZone.TEMPERATE, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.LOAMY, SoilType.CLAY],
                'rainfall_range': (400, 800),
                'temperature_range': (15, 25),
                'water_requirement': 'medium'
            },
            'groundnut': {
                'climate_zones': [ClimateZone.TROPICAL, ClimateZone.SUBTROPICAL],
                'soil_types': [SoilType.SANDY, SoilType.LOAMY],
                'rainfall_range': (500, 1000),
                'temperature_range': (20, 35),
                'water_requirement': 'medium'
            }
        }
    
    def determine_climate_zone(self, latitude: float, longitude: float) -> ClimateZone:
        """Determine climate zone based on coordinates."""
        if latitude < 10:
            return ClimateZone.TROPICAL
        elif latitude < 25:
            return ClimateZone.SUBTROPICAL
        elif latitude < 35:
            return ClimateZone.TEMPERATE
        else:
            return ClimateZone.TEMPERATE
    
    def determine_soil_type(self, soil_data: Dict[str, Any]) -> SoilType:
        """Determine soil type based on soil data."""
        # This is simplified - in production, you'd use more sophisticated soil analysis
        clay_content = soil_data.get('clay_content', 0)
        sand_content = soil_data.get('sand_content', 0)
        
        if clay_content > 40:
            return SoilType.CLAY
        elif sand_content > 60:
            return SoilType.SANDY
        elif 20 <= clay_content <= 40 and 20 <= sand_content <= 60:
            return SoilType.LOAMY
        else:
            return SoilType.LOAMY  # Default
    
    def filter_suitable_crops(self, location_conditions: LocationConditions) -> List[str]:
        """Filter crops that are suitable for the given location conditions."""
        suitable_crops = []
        
        for crop_name, requirements in self.crop_requirements.items():
            if self._is_crop_suitable(crop_name, requirements, location_conditions):
                suitable_crops.append(crop_name)
        
        logger.info(f"Found {len(suitable_crops)} suitable crops for location: {suitable_crops}")
        return suitable_crops
    
    def _is_crop_suitable(self, crop_name: str, requirements: Dict[str, Any], 
                         conditions: LocationConditions) -> bool:
        """Check if a crop is suitable for the given conditions."""
        try:
            # Check climate zone
            if conditions.climate_zone not in requirements['climate_zones']:
                return False
            
            # Check soil type
            if conditions.soil_type not in requirements['soil_types']:
                return False
            
            # Check rainfall
            rainfall_min, rainfall_max = requirements['rainfall_range']
            if not (rainfall_min <= conditions.rainfall_mm <= rainfall_max):
                return False
            
            # Check temperature
            temp_min, temp_max = requirements['temperature_range']
            if not (temp_min <= conditions.temperature_c <= temp_max):
                return False
            
            # Check water requirement
            water_req = requirements['water_requirement']
            if water_req == 'high' and conditions.water_availability == 'low':
                return False
            elif water_req == 'low' and conditions.water_availability == 'high':
                return False  # Can still grow, but not optimal
            
            return True
            
        except Exception as e:
            logger.warning(f"Error checking suitability for {crop_name}: {e}")
            return False
    
    def get_crop_suitability_scores(self, location_conditions: LocationConditions) -> Dict[str, float]:
        """Get suitability scores for all crops (0.0 to 1.0)."""
        scores = {}
        
        for crop_name, requirements in self.crop_requirements.items():
            score = self._calculate_suitability_score(crop_name, requirements, location_conditions)
            scores[crop_name] = score
        
        return scores
    
    def _calculate_suitability_score(self, crop_name: str, requirements: Dict[str, Any], 
                                   conditions: LocationConditions) -> float:
        """Calculate suitability score for a crop (0.0 to 1.0)."""
        try:
            score = 0.0
            max_score = 4.0  # 4 criteria
            
            # Climate zone match (1.0 if perfect, 0.5 if close, 0.0 if no match)
            if conditions.climate_zone in requirements['climate_zones']:
                score += 1.0
            else:
                score += 0.0
            
            # Soil type match
            if conditions.soil_type in requirements['soil_types']:
                score += 1.0
            else:
                score += 0.0
            
            # Rainfall match (graduated score)
            rainfall_min, rainfall_max = requirements['rainfall_range']
            if rainfall_min <= conditions.rainfall_mm <= rainfall_max:
                score += 1.0
            else:
                # Calculate how far off we are
                if conditions.rainfall_mm < rainfall_min:
                    diff = rainfall_min - conditions.rainfall_mm
                    max_diff = rainfall_min
                else:
                    diff = conditions.rainfall_mm - rainfall_max
                    max_diff = rainfall_max
                
                if max_diff > 0:
                    score += max(0.0, 1.0 - (diff / max_diff))
            
            # Temperature match
            temp_min, temp_max = requirements['temperature_range']
            if temp_min <= conditions.temperature_c <= temp_max:
                score += 1.0
            else:
                # Calculate how far off we are
                if conditions.temperature_c < temp_min:
                    diff = temp_min - conditions.temperature_c
                    max_diff = temp_min
                else:
                    diff = conditions.temperature_c - temp_max
                    max_diff = temp_max
                
                if max_diff > 0:
                    score += max(0.0, 1.0 - (diff / max_diff))
            
            return score / max_score
            
        except Exception as e:
            logger.warning(f"Error calculating suitability score for {crop_name}: {e}")
            return 0.0
