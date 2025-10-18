"""Market price client with Agmarknet integration for real Indian agricultural prices."""

import asyncio
import logging
import random
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .base_client import BaseAPIClient, APIError
from .agmarknet_client import AgmarknetClient
from ...models.market import MarketPrices, CropPrice, PriceAnalysis, PriceTrend
from ...config.config import config

logger = logging.getLogger(__name__)


class MarketPriceClient(BaseAPIClient):
    """Client for market price data with Agmarknet integration."""
    
    def __init__(self):
        """Initialize market price client."""
        api_config = config.get_api_config('market_prices')
        super().__init__(
            base_url='https://api.example.com',  # Placeholder
            timeout=api_config.get('timeout', 10),
            retry_attempts=api_config.get('retry_attempts', 3)
        )
        
        # Initialize Agmarknet client for real prices
        self.agmarknet_client = AgmarknetClient()
        
        # Indian crop base prices (per kg in INR) - fallback data
        self.base_prices = {
            'wheat': 25.0,
            'rice': 35.0,
            'maize': 20.0,
            'soybean': 45.0,
            'cotton': 60.0,
            'sugarcane': 3.0,
            'groundnut': 80.0,
            'mustard': 55.0,
            'potato': 15.0,
            'onion': 20.0,
            'tomato': 30.0,
            'brinjal': 25.0,
            'chilli': 120.0,
            'turmeric': 150.0,
            'ginger': 200.0,
            'garlic': 80.0,
            'coriander': 100.0,
            'cumin': 300.0,
            'fenugreek': 80.0,
            'cardamom': 2000.0,
            'pepper': 500.0,
            'cinnamon': 800.0,
            'cloves': 1200.0,
            'nutmeg': 600.0,
            'mace': 1500.0
        }
    
    async def fetch_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch market price data with Agmarknet integration."""
        logger.info(f"Fetching market price data for coordinates: {latitude}, {longitude}")
        
        try:
            # Try to get real data from Agmarknet first
            try:
                agmarknet_data = await self.agmarknet_client.fetch_data(latitude, longitude)
                if agmarknet_data and agmarknet_data.get('market_prices'):
                    # Validate that we have non-zero prices
                    market_prices = agmarknet_data['market_prices']
                    if market_prices.get('prices') and any(p.get('price_per_kg', 0) > 0 for p in market_prices['prices']):
                        logger.info("Successfully fetched real market prices from Agmarknet")
                        return agmarknet_data
                    else:
                        logger.warning("Agmarknet data has no valid prices, using fallback")
            except Exception as e:
                logger.warning(f"Agmarknet data unavailable: {e}")
            
            # Fallback to simulated data with realistic prices
            logger.info("Using simulated market price data as fallback")
            return self._generate_simulated_prices(latitude, longitude)
            
        except Exception as e:
            logger.error(f"Error fetching market price data for {latitude}, {longitude}: {e}")
            raise APIError(f"Failed to fetch market price data: {e}") from e
    
    def _generate_simulated_prices(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Generate simulated market price data."""
        try:
            # Determine market location based on coordinates
            market_location = self._determine_market_location(latitude, longitude)
            
            # Generate price records for last 12 months
            prices = []
            analyses = []
            
            for crop_name, base_price in self.base_prices.items():
                # Generate historical prices with trend and volatility
                price_records = self._generate_price_history(crop_name, base_price)
                prices.extend(price_records)
                
                # Generate price analysis
                analysis = self._generate_price_analysis(crop_name, price_records)
                analyses.append(analysis)
            
            # Create market prices object
            market_prices = MarketPrices(
                prices=prices,
                analyses=analyses,
                market_location=market_location,
                last_updated=datetime.now().isoformat()
            )
            
            return {
                'market_prices': market_prices.dict(),
                'raw_data': {'simulated': True, 'crop_count': len(self.base_prices)},
                'coordinates': {'latitude': latitude, 'longitude': longitude},
                'data_source': 'simulated',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating simulated price data: {e}")
            raise APIError(f"Failed to generate price data: {e}") from e
    
    def _determine_market_location(self, latitude: float, longitude: float) -> str:
        """Determine market location based on coordinates."""
        # Simple mapping based on Indian states
        if 18.0 <= latitude <= 19.0 and 73.0 <= longitude <= 74.0:
            return "Pune, Maharashtra"
        elif 28.0 <= latitude <= 29.0 and 76.0 <= longitude <= 77.0:
            return "Delhi"
        elif 19.0 <= latitude <= 20.0 and 72.0 <= longitude <= 73.0:
            return "Mumbai, Maharashtra"
        elif 12.0 <= latitude <= 13.0 and 77.0 <= longitude <= 78.0:
            return "Bangalore, Karnataka"
        elif 22.0 <= latitude <= 23.0 and 88.0 <= longitude <= 89.0:
            return "Kolkata, West Bengal"
        elif 13.0 <= latitude <= 14.0 and 80.0 <= longitude <= 81.0:
            return "Chennai, Tamil Nadu"
        else:
            return "Regional Market"
    
    def _generate_price_history(self, crop_name: str, base_price: float) -> List[CropPrice]:
        """Generate price history for a crop."""
        prices = []
        current_date = datetime.now()
        
        # Generate prices for last 12 months
        for i in range(365):
            date = current_date - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            # Add seasonal variation and random fluctuation
            seasonal_factor = self._get_seasonal_factor(crop_name, date.month)
            random_factor = random.uniform(0.8, 1.2)
            
            price = base_price * seasonal_factor * random_factor
            
            price_record = CropPrice(
                crop_name=crop_name,
                price_per_kg=round(price, 2),
                currency="INR",
                date=date_str,
                market_location=self._determine_market_location(18.5, 73.8),  # Default to Pune
                data_source="simulated"
            )
            
            prices.append(price_record)
        
        return prices
    
    def _get_seasonal_factor(self, crop_name: str, month: int) -> float:
        """Get seasonal price factor for a crop."""
        # Define seasonal patterns for different crops
        seasonal_patterns = {
            'wheat': {1: 1.1, 2: 1.0, 3: 0.9, 4: 0.8, 5: 0.9, 6: 1.0, 7: 1.1, 8: 1.2, 9: 1.1, 10: 1.0, 11: 0.9, 12: 1.0},
            'rice': {1: 1.0, 2: 0.9, 3: 0.8, 4: 0.9, 5: 1.0, 6: 1.1, 7: 1.2, 8: 1.1, 9: 1.0, 10: 0.9, 11: 1.0, 12: 1.1},
            'maize': {1: 1.0, 2: 0.9, 3: 0.8, 4: 0.9, 5: 1.0, 6: 1.1, 7: 1.2, 8: 1.1, 9: 1.0, 10: 0.9, 11: 1.0, 12: 1.1},
            'soybean': {1: 1.0, 2: 0.9, 3: 0.8, 4: 0.9, 5: 1.0, 6: 1.1, 7: 1.2, 8: 1.1, 9: 1.0, 10: 0.9, 11: 1.0, 12: 1.1},
            'cotton': {1: 1.0, 2: 0.9, 3: 0.8, 4: 0.9, 5: 1.0, 6: 1.1, 7: 1.2, 8: 1.1, 9: 1.0, 10: 0.9, 11: 1.0, 12: 1.1},
            'sugarcane': {1: 1.0, 2: 0.9, 3: 0.8, 4: 0.9, 5: 1.0, 6: 1.1, 7: 1.2, 8: 1.1, 9: 1.0, 10: 0.9, 11: 1.0, 12: 1.1}
        }
        
        pattern = seasonal_patterns.get(crop_name, {})
        return pattern.get(month, 1.0)
    
    def _generate_price_analysis(self, crop_name: str, price_records: List[CropPrice]) -> PriceAnalysis:
        """Generate price analysis for a crop."""
        if not price_records:
            # Use base price as fallback instead of 0.0
            base_price = self.base_prices.get(crop_name, 25.0)  # Default to wheat price
            return PriceAnalysis(
                crop_name=crop_name,
                current_price=base_price,
                average_price_3_months=base_price,
                average_price_12_months=base_price,
                price_trend=PriceTrend.STABLE,
                volatility_index=0.1,  # Low volatility for fallback
                price_change_percent=0.0
            )
        
        # Sort by date (most recent first)
        sorted_prices = sorted(price_records, key=lambda x: x.date, reverse=True)
        
        current_price = sorted_prices[0].price_per_kg
        
        # Calculate 3-month average
        three_month_prices = [p.price_per_kg for p in sorted_prices[:90]]
        avg_3_months = sum(three_month_prices) / len(three_month_prices)
        
        # Calculate 12-month average
        twelve_month_prices = [p.price_per_kg for p in sorted_prices[:365]]
        avg_12_months = sum(twelve_month_prices) / len(twelve_month_prices)
        
        # Calculate price change percentage
        price_change_percent = ((current_price - avg_3_months) / avg_3_months) * 100
        
        # Determine trend
        if price_change_percent > 5:
            trend = PriceTrend.RISING
        elif price_change_percent < -5:
            trend = PriceTrend.FALLING
        else:
            trend = PriceTrend.STABLE
        
        # Calculate volatility (standard deviation)
        prices_list = [p.price_per_kg for p in sorted_prices[:90]]
        if len(prices_list) > 1:
            mean_price = sum(prices_list) / len(prices_list)
            variance = sum((p - mean_price) ** 2 for p in prices_list) / len(prices_list)
            volatility = (variance ** 0.5) / mean_price
            volatility_index = min(volatility, 1.0)
        else:
            volatility_index = 0.0
        
        return PriceAnalysis(
            crop_name=crop_name,
            current_price=current_price,
            average_price_3_months=avg_3_months,
            average_price_12_months=avg_12_months,
            price_trend=trend,
            volatility_index=volatility_index,
            price_change_percent=price_change_percent
        )
