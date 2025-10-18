"""Crop database and matching algorithms."""

import yaml
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from ..models.crop import CropRequirements, CropRecommendation, WaterRequirement, SoilType
from ..models.location import LocationData
from ..models.soil import SoilProfile, SoilTexture
from ..models.weather import WeatherData
from ..models.water import WaterAvailability, RainfallData
from ..models.market import MarketPrices
from ..config.config import config

logger = logging.getLogger(__name__)


class CropDatabase:
    """Crop requirements database manager."""
    
    def __init__(self, crop_data_file: str = "data/crop_requirements.yaml"):
        """Initialize crop database."""
        self.crop_data_file = crop_data_file
        self.crop_requirements: Dict[str, CropRequirements] = {}
        self._load_crop_data()
    
    def _load_crop_data(self):
        """Load crop requirements from YAML file."""
        try:
            data_path = Path(self.crop_data_file)
            if not data_path.exists():
                raise FileNotFoundError(f"Crop data file not found: {self.crop_data_file}")
            
            with open(data_path, 'r') as f:
                data = yaml.safe_load(f)
            
            crops_data = data.get('crops', {})
            
            for crop_name, crop_data in crops_data.items():
                try:
                    # Convert string enums to proper enum values
                    crop_data['water_requirement'] = WaterRequirement(crop_data['water_requirement'])
                    crop_data['soil_types'] = [SoilType(st) for st in crop_data.get('soil_types', [])]
                    
                    crop_req = CropRequirements(**crop_data)
                    self.crop_requirements[crop_name] = crop_req
                    
                except Exception as e:
                    logger.warning(f"Error loading crop data for {crop_name}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.crop_requirements)} crop requirements")
            
        except Exception as e:
            logger.error(f"Error loading crop data: {e}")
            raise
    
    def get_crop_requirements(self, crop_name: str) -> Optional[CropRequirements]:
        """Get crop requirements by name."""
        return self.crop_requirements.get(crop_name.lower())
    
    def get_all_crops(self) -> List[str]:
        """Get list of all available crops."""
        return list(self.crop_requirements.keys())
    
    def get_crops_by_season(self, month: int) -> List[str]:
        """Get crops suitable for given month."""
        suitable_crops = []
        
        for crop_name, requirements in self.crop_requirements.items():
            if month in requirements.growing_season_months:
                suitable_crops.append(crop_name)
        
        return suitable_crops


class CropMatcher:
    """Crop suitability matching algorithm."""
    
    def __init__(self, crop_database: CropDatabase):
        """Initialize crop matcher."""
        self.crop_database = crop_database
        self.scoring_weights = config.get_crop_recommendation_config().get('scoring_weights', {
            'soil_ph_match': 0.30,
            'temperature_suitability': 0.25,
            'rainfall_adequacy': 0.25,
            'soil_type_match': 0.10,
            'water_availability': 0.10
        })
    
    def calculate_suitability_score(
        self, 
        crop_requirements: CropRequirements, 
        location_data: LocationData
    ) -> Tuple[float, Dict[str, float]]:
        """Calculate overall suitability score for a crop."""
        try:
            scores = {}
            
            # Soil pH match score
            scores['soil_ph_score'] = self._calculate_ph_score(
                crop_requirements, 
                location_data.soil_profile
            )
            
            # Temperature suitability score
            scores['temperature_score'] = self._calculate_temperature_score(
                crop_requirements, 
                location_data.weather_data
            )
            
            # Rainfall adequacy score
            scores['rainfall_score'] = self._calculate_rainfall_score(
                crop_requirements, 
                location_data.rainfall_data
            )
            
            # Soil type match score
            scores['soil_type_score'] = self._calculate_soil_type_score(
                crop_requirements, 
                location_data.soil_profile
            )
            
            # Water availability score
            scores['water_availability_score'] = self._calculate_water_availability_score(
                crop_requirements, 
                location_data.rainfall_data
            )
            
            # Calculate weighted overall score
            overall_score = (
                scores['soil_ph_score'] * self.scoring_weights['soil_ph_match'] +
                scores['temperature_score'] * self.scoring_weights['temperature_suitability'] +
                scores['rainfall_score'] * self.scoring_weights['rainfall_adequacy'] +
                scores['soil_type_score'] * self.scoring_weights['soil_type_match'] +
                scores['water_availability_score'] * self.scoring_weights['water_availability']
            )
            
            return round(overall_score, 3), scores
            
        except Exception as e:
            logger.error(f"Error calculating suitability score: {e}")
            return 0.0, {}
    
    def _calculate_ph_score(
        self, 
        crop_requirements: CropRequirements, 
        soil_profile: Optional[SoilProfile]
    ) -> float:
        """Calculate soil pH match score."""
        if not soil_profile or soil_profile.properties.ph_h2o is None:
            return 0.5  # Neutral score if no data
        
        ph = soil_profile.properties.ph_h2o
        
        # Perfect match
        if crop_requirements.ph_min <= ph <= crop_requirements.ph_max:
            # Check if it's optimal
            if abs(ph - crop_requirements.ph_optimal) <= 0.5:
                return 1.0
            else:
                return 0.8
        
        # Partial match (within 0.5 pH units)
        elif (crop_requirements.ph_min - 0.5) <= ph <= (crop_requirements.ph_max + 0.5):
            return 0.6
        
        # Poor match
        else:
            return 0.2
    
    def _calculate_temperature_score(
        self, 
        crop_requirements: CropRequirements, 
        weather_data: Optional[WeatherData]
    ) -> float:
        """Calculate temperature suitability score."""
        if not weather_data:
            return 0.5  # Neutral score if no data
        
        # Get average temperature from forecast
        avg_temp = weather_data.get_average_temperature(7)  # 7-day average
        if avg_temp is None:
            avg_temp = weather_data.current.temperature_c
        
        # Perfect match
        if crop_requirements.temp_min_c <= avg_temp <= crop_requirements.temp_max_c:
            # Check if it's optimal
            if abs(avg_temp - crop_requirements.temp_optimal_c) <= 3:
                return 1.0
            else:
                return 0.8
        
        # Partial match (within 5°C)
        elif (crop_requirements.temp_min_c - 5) <= avg_temp <= (crop_requirements.temp_max_c + 5):
            return 0.6
        
        # Poor match
        else:
            return 0.2
    
    def _calculate_rainfall_score(
        self, 
        crop_requirements: CropRequirements, 
        rainfall_data: Optional[RainfallData]
    ) -> float:
        """Calculate rainfall adequacy score."""
        if not rainfall_data or not rainfall_data.records:
            return 0.5  # Neutral score if no data
        
        # Get 30-day rainfall
        recent_rainfall = rainfall_data.get_total_precipitation(30)
        
        # Perfect match
        if crop_requirements.rainfall_min_mm <= recent_rainfall <= (crop_requirements.rainfall_max_mm or float('inf')):
            return 1.0
        
        # Partial match (within 20% of requirements)
        elif recent_rainfall >= crop_requirements.rainfall_min_mm * 0.8:
            return 0.7
        
        # Low rainfall
        elif recent_rainfall >= crop_requirements.rainfall_min_mm * 0.5:
            return 0.4
        
        # Very low rainfall
        else:
            return 0.1
    
    def _calculate_soil_type_score(
        self, 
        crop_requirements: CropRequirements, 
        soil_profile: Optional[SoilProfile]
    ) -> float:
        """Calculate soil type match score."""
        if not soil_profile or not soil_profile.texture:
            return 0.5  # Neutral score if no data
        
        soil_texture = soil_profile.texture
        
        # Perfect match
        if soil_texture in crop_requirements.soil_types:
            return 1.0
        
        # Check for similar soil types
        similar_types = self._get_similar_soil_types(soil_texture)
        for similar_type in similar_types:
            if similar_type in crop_requirements.soil_types:
                return 0.7
        
        # Poor match
        return 0.3
    
    def _get_similar_soil_types(self, soil_texture: SoilTexture) -> List[SoilType]:
        """Get similar soil types for matching."""
        similar_map = {
            SoilTexture.LOAM: [SoilType.CLAY_LOAM, SoilType.SANDY_LOAM, SoilType.SILTY_LOAM],
            SoilTexture.CLAY_LOAM: [SoilType.LOAM, SoilType.CLAY, SoilType.SILTY_CLAY_LOAM],
            SoilTexture.SANDY_LOAM: [SoilType.LOAM, SoilType.SAND, SoilType.SANDY_CLAY_LOAM],
            SoilTexture.CLAY: [SoilType.CLAY_LOAM, SoilType.SILTY_CLAY],
            SoilTexture.SAND: [SoilType.SANDY_LOAM, SoilType.SANDY_CLAY_LOAM],
            SoilTexture.SILT: [SoilType.SILTY_LOAM, SoilType.SILTY_CLAY_LOAM]
        }
        
        return similar_map.get(soil_texture, [])
    
    def _calculate_water_availability_score(
        self, 
        crop_requirements: CropRequirements, 
        rainfall_data: Optional[RainfallData]
    ) -> float:
        """Calculate water availability score."""
        if not rainfall_data or not rainfall_data.records:
            return 0.5  # Neutral score if no data
        
        # Calculate water stress index based on recent rainfall
        recent_precipitation = rainfall_data.get_total_precipitation(30)
        
        # Thresholds for different stress levels (mm per 30 days)
        if recent_precipitation >= 150:  # Good rainfall
            water_stress = 0.0
        elif recent_precipitation >= 100:  # Moderate rainfall
            water_stress = 0.3
        elif recent_precipitation >= 50:   # Low rainfall
            water_stress = 0.6
        else:  # Very low rainfall
            water_stress = 0.9
        
        # Map water requirement to stress tolerance
        stress_tolerance = {
            WaterRequirement.LOW: 0.8,    # Can tolerate high stress
            WaterRequirement.MEDIUM: 0.5,  # Moderate stress tolerance
            WaterRequirement.HIGH: 0.2     # Low stress tolerance
        }
        
        tolerance = stress_tolerance.get(crop_requirements.water_requirement, 0.5)
        
        # Calculate score based on stress vs tolerance
        if water_stress <= tolerance:
            return 1.0
        elif water_stress <= tolerance + 0.2:
            return 0.7
        elif water_stress <= tolerance + 0.4:
            return 0.4
        else:
            return 0.1
    
    def get_crop_recommendations(
        self, 
        location_data: LocationData, 
        max_crops: int = 5,
        min_score: float = 0.3
    ) -> List[CropRecommendation]:
        """Get crop recommendations for a location."""
        try:
            recommendations = []
            
            # Get all available crops
            all_crops = self.crop_database.get_all_crops()
            
            # Calculate scores for all crops
            for crop_name in all_crops:
                crop_requirements = self.crop_database.get_crop_requirements(crop_name)
                if not crop_requirements:
                    continue
                
                suitability_score, score_breakdown = self.calculate_suitability_score(
                    crop_requirements, location_data
                )
                
                # Skip crops below minimum score
                if suitability_score < min_score:
                    continue
                
                # Calculate profitability score
                profitability_score = self._calculate_profitability_score(
                    crop_name, location_data, crop_requirements
                )
                
                # Calculate expected profit
                expected_profit = self._calculate_expected_profit(
                    crop_requirements, profitability_score
                )
                
                # Create recommendation
                recommendation = CropRecommendation(
                    crop_name=crop_name,
                    suitability_score=suitability_score,
                    expected_profit_per_acre=expected_profit,
                    profitability_score=profitability_score,
                    soil_ph_score=score_breakdown.get('soil_ph_score', 0.0),
                    temperature_score=score_breakdown.get('temperature_score', 0.0),
                    rainfall_score=score_breakdown.get('rainfall_score', 0.0),
                    soil_type_score=score_breakdown.get('soil_type_score', 0.0),
                    water_availability_score=score_breakdown.get('water_availability_score', 0.0),
                    key_factors=self._get_key_factors(score_breakdown, location_data),
                    summary=self._generate_summary(crop_name, suitability_score, score_breakdown),
                    risk_level=self._calculate_risk_level(suitability_score, profitability_score),
                    risk_factors=self._get_risk_factors(score_breakdown, location_data)
                )
                
                recommendations.append(recommendation)
            
            # Sort by combined score (suitability + profitability)
            recommendations.sort(
                key=lambda x: (x.suitability_score * 0.7 + x.profitability_score * 0.3), 
                reverse=True
            )
            
            return recommendations[:max_crops]
            
        except Exception as e:
            logger.error(f"Error getting crop recommendations: {e}")
            return []
    
    def _calculate_profitability_score(
        self, 
        crop_name: str, 
        location_data: LocationData, 
        crop_requirements: CropRequirements
    ) -> float:
        """Calculate profitability score for a crop."""
        if not location_data.market_prices:
            return 0.5  # Neutral score if no market data
        
        return location_data.market_prices.calculate_profitability_score(
            crop_name, crop_requirements.typical_yield_per_acre
        ) or 0.5
    
    def _calculate_expected_profit(
        self, 
        crop_requirements: CropRequirements, 
        profitability_score: float
    ) -> float:
        """Calculate expected profit per acre."""
        base_profit = crop_requirements.typical_yield_per_acre * crop_requirements.base_market_price_per_kg
        return base_profit * profitability_score
    
    def _get_key_factors(self, score_breakdown: Dict[str, float], location_data: LocationData) -> Dict[str, any]:
        """Get key factors influencing the recommendation."""
        factors = {}
        
        # Soil pH match
        if score_breakdown.get('soil_ph_score', 0) > 0.8:
            factors['soil_ph_match'] = True
        elif score_breakdown.get('soil_ph_score', 0) < 0.4:
            factors['soil_ph_match'] = False
        
        # Rainfall forecast
        if location_data.rainfall_data:
            factors['rainfall_forecast_mm'] = location_data.rainfall_data.get_total_precipitation(30)
        
        # Market price trend
        if location_data.market_prices:
            # This would be populated from market analysis
            factors['market_price_trend'] = "Stable"  # Placeholder
        
        return factors
    
    def _generate_summary(
        self, 
        crop_name: str, 
        suitability_score: float, 
        score_breakdown: Dict[str, float]
    ) -> str:
        """Generate summary for the recommendation."""
        if suitability_score >= 0.8:
            return f"{crop_name.title()} is highly suitable for this location with excellent environmental conditions."
        elif suitability_score >= 0.6:
            return f"{crop_name.title()} is suitable for this location with good growing conditions."
        elif suitability_score >= 0.4:
            return f"{crop_name.title()} is moderately suitable for this location with some limitations."
        else:
            return f"{crop_name.title()} has limited suitability for this location due to environmental constraints."
    
    def _calculate_risk_level(self, suitability_score: float, profitability_score: float) -> str:
        """Calculate risk level for the recommendation."""
        combined_score = (suitability_score * 0.7 + profitability_score * 0.3)
        
        if combined_score >= 0.8:
            return "low"
        elif combined_score >= 0.6:
            return "medium"
        else:
            return "high"
    
    def _get_risk_factors(self, score_breakdown: Dict[str, float], location_data: LocationData) -> List[str]:
        """Get risk factors for the recommendation."""
        risk_factors = []
        
        # Check for low scores
        if score_breakdown.get('soil_ph_score', 0) < 0.4:
            risk_factors.append("Poor soil pH match")
        
        if score_breakdown.get('temperature_score', 0) < 0.4:
            risk_factors.append("Temperature outside optimal range")
        
        if score_breakdown.get('rainfall_score', 0) < 0.4:
            risk_factors.append("Insufficient rainfall")
        
        if score_breakdown.get('water_availability_score', 0) < 0.4:
            risk_factors.append("High water stress")
        
        return risk_factors
