"""Market price data models."""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from enum import Enum


class PriceTrend(str, Enum):
    """Price trend directions."""
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    VOLATILE = "volatile"


class CropPrice(BaseModel):
    """Individual crop price record."""
    
    crop_name: str = Field(..., description="Name of the crop")
    price_per_kg: float = Field(..., ge=0, description="Price per kg in local currency")
    currency: str = Field(default="INR", description="Currency code")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    market_location: Optional[str] = Field(None, description="Market location")
    data_source: Optional[str] = Field(None, description="Data source")
    
    @validator('date')
    def validate_date_format(cls, v):
        """Validate date format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")


class PriceAnalysis(BaseModel):
    """Price analysis for a crop."""
    
    crop_name: str = Field(..., description="Name of the crop")
    current_price: float = Field(..., ge=0, description="Current price per kg")
    average_price_3_months: float = Field(..., ge=0, description="Average price over 3 months")
    average_price_12_months: float = Field(..., ge=0, description="Average price over 12 months")
    price_trend: PriceTrend = Field(..., description="Price trend direction")
    volatility_index: float = Field(..., ge=0, le=1, description="Price volatility index (0=stable, 1=highly volatile)")
    price_change_percent: float = Field(..., description="Price change percentage from 3 months ago")
    
    @validator('price_change_percent')
    def validate_price_change(cls, v):
        """Validate price change percentage."""
        if abs(v) > 1000:  # More than 1000% change seems unrealistic
            raise ValueError("Price change percentage seems unrealistic")
        return v


class MarketPrices(BaseModel):
    """Market prices data for multiple crops."""
    
    prices: List[CropPrice] = Field(default_factory=list, description="Historical price records")
    analyses: List[PriceAnalysis] = Field(default_factory=list, description="Price analyses by crop")
    last_updated: Optional[str] = Field(None, description="Last update timestamp")
    market_location: Optional[str] = Field(None, description="Primary market location")
    
    def get_crop_price(self, crop_name: str) -> Optional[float]:
        """Get current price for a specific crop."""
        crop_prices = [p for p in self.prices if p.crop_name.lower() == crop_name.lower()]
        if not crop_prices:
            return None
        
        # Return the most recent price
        latest_price = max(crop_prices, key=lambda p: p.date)
        return latest_price.price_per_kg
    
    def get_crop_analysis(self, crop_name: str) -> Optional[PriceAnalysis]:
        """Get price analysis for a specific crop."""
        for analysis in self.analyses:
            if analysis.crop_name.lower() == crop_name.lower():
                return analysis
        return None
    
    def calculate_profitability_score(self, crop_name: str, yield_per_acre: float) -> Optional[float]:
        """Calculate profitability score for a crop."""
        analysis = self.get_crop_analysis(crop_name)
        if not analysis:
            return None
        
        # Base profitability from current price and yield
        base_profit = analysis.current_price * yield_per_acre
        
        # Adjust for price trend
        trend_multiplier = 1.0
        if analysis.price_trend == PriceTrend.RISING:
            trend_multiplier = 1.2
        elif analysis.price_trend == PriceTrend.FALLING:
            trend_multiplier = 0.8
        elif analysis.price_trend == PriceTrend.VOLATILE:
            trend_multiplier = 0.9
        
        # Adjust for volatility (higher volatility = lower score)
        volatility_adjustment = 1.0 - (analysis.volatility_index * 0.3)
        
        # Normalize to 0-1 scale (assuming max profit of 100,000 per acre)
        normalized_profit = min(base_profit * trend_multiplier * volatility_adjustment / 100000, 1.0)
        
        return max(0.0, normalized_profit)
    
    class Config:
        json_schema_extra = {
            "example": {
                "prices": [
                    {
                        "crop_name": "wheat",
                        "price_per_kg": 25.50,
                        "currency": "INR",
                        "date": "2024-01-15",
                        "market_location": "Pune",
                        "data_source": "agmarknet"
                    }
                ],
                "analyses": [
                    {
                        "crop_name": "wheat",
                        "current_price": 25.50,
                        "average_price_3_months": 24.80,
                        "average_price_12_months": 23.20,
                        "price_trend": "rising",
                        "volatility_index": 0.3,
                        "price_change_percent": 2.8
                    }
                ],
                "last_updated": "2024-01-15T10:30:00Z",
                "market_location": "Pune"
            }
        }
