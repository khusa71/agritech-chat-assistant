"""Water and rainfall data models."""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator
from datetime import datetime, date


class RainfallRecord(BaseModel):
    """Individual rainfall measurement."""
    
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    precipitation_mm: float = Field(..., ge=0, description="Precipitation in mm")
    data_source: Optional[str] = Field(None, description="Data source (e.g., 'open_meteo', 'nasa_gpm')")
    
    @validator('date')
    def validate_date_format(cls, v):
        """Validate date format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")


class RainfallData(BaseModel):
    """Rainfall data for a location."""
    
    records: List[RainfallRecord] = Field(default_factory=list, description="Historical rainfall records")
    location_name: Optional[str] = Field(None, description="Location name")
    data_period_days: Optional[int] = Field(None, ge=1, le=365, description="Number of days of data")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    
    def get_total_precipitation(self, days: int = 30) -> float:
        """Get total precipitation over specified days."""
        if not self.records or days <= 0:
            return 0.0
        
        recent_records = self.records[-days:] if len(self.records) >= days else self.records
        return sum(record.precipitation_mm for record in recent_records)
    
    def get_average_daily_precipitation(self, days: int = 30) -> float:
        """Get average daily precipitation over specified days."""
        total = self.get_total_precipitation(days)
        return total / days if days > 0 else 0.0
    
    def get_precipitation_trend(self, days: int = 30) -> Optional[str]:
        """Get precipitation trend (increasing/decreasing/stable)."""
        if len(self.records) < days:
            return None
        
        recent_records = self.records[-days:]
        if len(recent_records) < 7:  # Need at least a week for trend
            return None
        
        # Calculate trend using simple linear regression slope
        mid_point = len(recent_records) // 2
        first_half_avg = sum(r.precipitation_mm for r in recent_records[:mid_point]) / mid_point
        second_half_avg = sum(r.precipitation_mm for r in recent_records[mid_point:]) / (len(recent_records) - mid_point)
        
        if second_half_avg > first_half_avg * 1.1:
            return "increasing"
        elif second_half_avg < first_half_avg * 0.9:
            return "decreasing"
        else:
            return "stable"


class WaterAvailability(BaseModel):
    """Water availability assessment."""
    
    rainfall_data: RainfallData
    water_stress_index: Optional[float] = Field(None, ge=0.0, le=1.0, description="Water stress index (0=no stress, 1=severe stress)")
    irrigation_requirement: Optional[str] = Field(None, description="Irrigation requirement level")
    seasonal_pattern: Optional[str] = Field(None, description="Seasonal rainfall pattern")
    
    @validator('irrigation_requirement')
    def validate_irrigation_level(cls, v):
        """Validate irrigation requirement level."""
        if v is not None and v not in ['low', 'medium', 'high', 'critical']:
            raise ValueError("Irrigation requirement must be one of: low, medium, high, critical")
        return v
    
    def calculate_water_stress_index(self) -> float:
        """Calculate water stress index based on recent rainfall."""
        # Simple calculation based on 30-day precipitation
        recent_precipitation = self.rainfall_data.get_total_precipitation(30)
        
        # Thresholds for different stress levels (mm per 30 days)
        if recent_precipitation >= 150:  # Good rainfall
            return 0.0
        elif recent_precipitation >= 100:  # Moderate rainfall
            return 0.3
        elif recent_precipitation >= 50:   # Low rainfall
            return 0.6
        else:  # Very low rainfall
            return 0.9
    
    def determine_irrigation_requirement(self) -> str:
        """Determine irrigation requirement based on water stress."""
        stress_index = self.calculate_water_stress_index()
        
        if stress_index <= 0.2:
            return "low"
        elif stress_index <= 0.5:
            return "medium"
        elif stress_index <= 0.8:
            return "high"
        else:
            return "critical"
    
    class Config:
        json_schema_extra = {
            "example": {
                "rainfall_data": {
                    "records": [
                        {
                            "date": "2024-01-15",
                            "precipitation_mm": 5.2,
                            "data_source": "open_meteo"
                        }
                    ],
                    "location_name": "Pune",
                    "data_period_days": 30,
                    "last_updated": "2024-01-15T10:30:00Z"
                },
                "water_stress_index": 0.3,
                "irrigation_requirement": "medium",
                "seasonal_pattern": "monsoon"
            }
        }
