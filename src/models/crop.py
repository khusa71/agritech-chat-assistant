"""Crop-related data models."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class WaterRequirement(str, Enum):
    """Water requirement levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SoilType(str, Enum):
    """Preferred soil types."""
    CLAY = "clay"
    CLAY_LOAM = "clay_loam"
    LOAM = "loam"
    SANDY_LOAM = "sandy_loam"
    SANDY_CLAY_LOAM = "sandy_clay_loam"
    SANDY_CLAY = "sandy_clay"
    SILTY_CLAY = "silty_clay"
    SILTY_CLAY_LOAM = "silty_clay_loam"
    SILTY_LOAM = "silty_loam"
    SAND = "sand"
    SILT = "silt"
    ANY = "any"


class CropRequirements(BaseModel):
    """Crop growing requirements."""
    
    crop_name: str = Field(..., description="Name of the crop")
    ph_min: float = Field(..., ge=3.0, le=10.0, description="Minimum soil pH")
    ph_max: float = Field(..., ge=3.0, le=10.0, description="Maximum soil pH")
    ph_optimal: float = Field(..., ge=3.0, le=10.0, description="Optimal soil pH")
    temp_min_c: float = Field(..., ge=-10, le=50, description="Minimum temperature (C)")
    temp_max_c: float = Field(..., ge=-10, le=50, description="Maximum temperature (C)")
    temp_optimal_c: float = Field(..., ge=-10, le=50, description="Optimal temperature (C)")
    rainfall_min_mm: float = Field(..., ge=0, description="Minimum rainfall per season (mm)")
    rainfall_max_mm: Optional[float] = Field(None, ge=0, description="Maximum rainfall per season (mm)")
    growing_season_months: List[int] = Field(..., description="Preferred growing months (1-12)")
    soil_types: List[SoilType] = Field(default_factory=list, description="Preferred soil types")
    water_requirement: WaterRequirement = Field(..., description="Water requirement level")
    growth_duration_days: int = Field(..., ge=30, le=365, description="Growth duration in days")
    typical_yield_per_acre: float = Field(..., ge=0, description="Typical yield per acre (kg)")
    base_market_price_per_kg: float = Field(..., ge=0, description="Base market price per kg")
    
    @validator('ph_max')
    def validate_ph_range(cls, v, values):
        """Validate pH range."""
        ph_min = values.get('ph_min')
        ph_optimal = values.get('ph_optimal')
        if ph_min and ph_optimal and not (ph_min <= ph_optimal <= v):
            raise ValueError("pH values must be in ascending order: min <= optimal <= max")
        return v
    
    @validator('temp_max_c')
    def validate_temp_range(cls, v, values):
        """Validate temperature range."""
        temp_min = values.get('temp_min_c')
        temp_optimal = values.get('temp_optimal_c')
        if temp_min and temp_optimal and not (temp_min <= temp_optimal <= v):
            raise ValueError("Temperature values must be in ascending order: min <= optimal <= max")
        return v
    
    @validator('rainfall_max_mm')
    def validate_rainfall_range(cls, v, values):
        """Validate rainfall range."""
        rainfall_min = values.get('rainfall_min_mm')
        if rainfall_min and v and rainfall_min > v:
            raise ValueError("Minimum rainfall cannot be greater than maximum rainfall")
        return v
    
    @validator('growing_season_months')
    def validate_growing_months(cls, v):
        """Validate growing season months."""
        if not v:
            raise ValueError("At least one growing month must be specified")
        for month in v:
            if not 1 <= month <= 12:
                raise ValueError("Growing months must be between 1 and 12")
        return sorted(list(set(v)))  # Remove duplicates and sort


class CropRecommendation(BaseModel):
    """Crop recommendation with scoring."""
    
    crop_name: str = Field(..., description="Name of the recommended crop")
    suitability_score: float = Field(..., ge=0.0, le=1.0, description="Overall suitability score (0-1)")
    expected_profit_per_acre: float = Field(..., description="Expected profit per acre")
    profitability_score: float = Field(..., ge=0.0, le=1.0, description="Profitability score (0-1)")
    
    # Detailed scoring breakdown
    soil_ph_score: float = Field(..., ge=0.0, le=1.0, description="Soil pH match score")
    temperature_score: float = Field(..., ge=0.0, le=1.0, description="Temperature suitability score")
    rainfall_score: float = Field(..., ge=0.0, le=1.0, description="Rainfall adequacy score")
    soil_type_score: float = Field(..., ge=0.0, le=1.0, description="Soil type match score")
    water_availability_score: float = Field(..., ge=0.0, le=1.0, description="Water availability score")
    
    # Key factors influencing the recommendation
    key_factors: Dict[str, Any] = Field(default_factory=dict, description="Key factors affecting recommendation")
    summary: str = Field(..., description="Brief explanation of the recommendation")
    
    # Risk assessment
    risk_level: str = Field(..., description="Risk level: low, medium, high")
    risk_factors: List[str] = Field(default_factory=list, description="List of risk factors")
    
    @validator('risk_level')
    def validate_risk_level(cls, v):
        """Validate risk level."""
        if v not in ['low', 'medium', 'high']:
            raise ValueError("Risk level must be one of: low, medium, high")
        return v
    
    def calculate_risk_level(self) -> str:
        """Calculate risk level based on scores."""
        if self.suitability_score >= 0.8 and self.profitability_score >= 0.7:
            return "low"
        elif self.suitability_score >= 0.6 and self.profitability_score >= 0.5:
            return "medium"
        else:
            return "high"
    
    class Config:
        json_schema_extra = {
            "example": {
                "crop_name": "wheat",
                "suitability_score": 0.85,
                "expected_profit_per_acre": 45000.0,
                "profitability_score": 0.78,
                "soil_ph_score": 0.9,
                "temperature_score": 0.8,
                "rainfall_score": 0.7,
                "soil_type_score": 0.85,
                "water_availability_score": 0.75,
                "key_factors": {
                    "soil_ph_match": True,
                    "rainfall_forecast_mm": 780,
                    "market_price_trend": "+5% YoY"
                },
                "summary": "Wheat is highly suitable for this location with good soil pH match and adequate rainfall forecast.",
                "risk_level": "low",
                "risk_factors": []
            }
        }
