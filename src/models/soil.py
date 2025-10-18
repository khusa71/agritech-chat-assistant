"""Soil data models."""

from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class SoilTexture(str, Enum):
    """Soil texture classifications."""
    CLAY = "clay"
    CLAY_LOAM = "clay_loam"
    LOAM = "loam"
    LOAMY_SAND = "loamy_sand"
    SAND = "sand"
    SANDY_CLAY = "sandy_clay"
    SANDY_CLAY_LOAM = "sandy_clay_loam"
    SANDY_LOAM = "sandy_loam"
    SILT = "silt"
    SILTY_CLAY = "silty_clay"
    SILTY_CLAY_LOAM = "silty_clay_loam"
    SILTY_LOAM = "silty_loam"


class SoilProperties(BaseModel):
    """Individual soil property measurements."""
    
    ph_h2o: Optional[float] = Field(None, ge=3.0, le=10.0, description="Soil pH in water")
    organic_carbon: Optional[float] = Field(None, ge=0.0, description="Organic carbon content (%)")
    bulk_density: Optional[float] = Field(None, ge=0.5, le=2.5, description="Bulk density (g/cm³)")
    clay_content: Optional[float] = Field(None, ge=0.0, le=100.0, description="Clay content (%)")
    sand_content: Optional[float] = Field(None, ge=0.0, le=100.0, description="Sand content (%)")
    silt_content: Optional[float] = Field(None, ge=0.0, le=100.0, description="Silt content (%)")
    
    @validator('clay_content', 'sand_content', 'silt_content')
    def validate_texture_percentages(cls, v):
        """Validate that texture percentages are reasonable."""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Texture percentages must be between 0 and 100")
        return v
    
    @validator('clay_content', 'sand_content', 'silt_content', always=True)
    def validate_texture_sum(cls, v, values):
        """Validate that clay + sand + silt ≈ 100%."""
        if all(val is not None for val in [v, values.get('clay_content'), values.get('sand_content'), values.get('silt_content')]):
            total = sum([v, values.get('clay_content', 0), values.get('sand_content', 0), values.get('silt_content', 0)])
            if abs(total - 100) > 5:  # Allow 5% tolerance
                raise ValueError("Clay + sand + silt content should sum to approximately 100%")
        return v


class SoilProfile(BaseModel):
    """Complete soil profile for a location."""
    
    properties: SoilProperties
    texture: Optional[SoilTexture] = Field(None, description="Dominant soil texture")
    depth_cm: Optional[int] = Field(None, ge=0, le=200, description="Profile depth in cm")
    fertility_index: Optional[float] = Field(None, ge=0.0, le=1.0, description="Calculated fertility index")
    
    @validator('texture', always=True)
    def determine_texture(cls, v, values):
        """Auto-determine soil texture if not provided."""
        if v is not None:
            return v
        
        props = values.get('properties')
        if props and all(val is not None for val in [props.clay_content, props.sand_content, props.silt_content]):
            # Simplified texture determination based on USDA triangle
            clay = props.clay_content
            sand = props.sand_content
            silt = props.silt_content
            
            if clay >= 40:
                return SoilTexture.CLAY
            elif sand >= 70:
                return SoilTexture.SAND
            elif silt >= 80:
                return SoilTexture.SILT
            elif 20 <= clay <= 40 and sand <= 50:
                return SoilTexture.CLAY_LOAM
            elif 20 <= clay <= 40 and sand > 50:
                return SoilTexture.SANDY_CLAY_LOAM
            elif clay < 20 and sand <= 50:
                return SoilTexture.LOAM
            else:
                return SoilTexture.SANDY_LOAM
        
        return None
    
    class Config:
        json_schema_extra = {
            "example": {
                "properties": {
                    "ph_h2o": 6.5,
                    "organic_carbon": 2.1,
                    "bulk_density": 1.3,
                    "clay_content": 25.0,
                    "sand_content": 45.0,
                    "silt_content": 30.0
                },
                "texture": "loam",
                "depth_cm": 100,
                "fertility_index": 0.75
            }
        }
