"""Agmarknet API client for fetching real Indian agricultural commodity prices."""

import logging
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from .base_client import BaseAPIClient, APIError
from ...models.market import MarketPrices, CropPrice, PriceAnalysis, PriceTrend
from ...config.config import config

logger = logging.getLogger(__name__)


class AgmarknetClient(BaseAPIClient):
    """Client for Agmarknet API (web scraping based)."""
    
    def __init__(self):
        """Initialize Agmarknet client."""
        api_config = config.get_api_config('agmarknet')
        super().__init__(
            base_url=api_config.get('base_url', 'http://127.0.0.1:5000'),
            timeout=api_config.get('timeout', 30),
            retry_attempts=api_config.get('retry_attempts', 3)
        )
        
        # Mapping of crop names to Agmarknet commodity names (reduced to most important crops)
        self.crop_mapping = {
            'wheat': 'Wheat',
            'rice': 'Rice', 
            'maize': 'Maize',
            'soybean': 'Soybean',
            'cotton': 'Cotton',
            'sugarcane': 'Sugarcane',
            'potato': 'Potato',
            'onion': 'Onion',
            'tomato': 'Tomato',
            'chilli': 'Chilli',
            'turmeric': 'Turmeric',
            'ginger': 'Ginger',
            'garlic': 'Garlic',
            'mustard': 'Mustard',
            'groundnut': 'Groundnut'
        }
        
        # State mapping for Indian states
        self.state_mapping = {
            'maharashtra': 'Maharashtra',
            'karnataka': 'Karnataka',
            'tamil_nadu': 'Tamil Nadu',
            'kerala': 'Kerala',
            'andhra_pradesh': 'Andhra Pradesh',
            'telangana': 'Telangana',
            'gujarat': 'Gujarat',
            'rajasthan': 'Rajasthan',
            'punjab': 'Punjab',
            'haryana': 'Haryana',
            'uttar_pradesh': 'Uttar Pradesh',
            'bihar': 'Bihar',
            'west_bengal': 'West Bengal',
            'odisha': 'Odisha',
            'madhya_pradesh': 'Madhya Pradesh',
            'chhattisgarh': 'Chhattisgarh',
            'jharkhand': 'Jharkhand',
            'assam': 'Assam',
            'himachal_pradesh': 'Himachal Pradesh',
            'uttarakhand': 'Uttarakhand'
        }
    
    async def fetch_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch market price data for given coordinates."""
        logger.info(f"Fetching Agmarknet market data for coordinates: {latitude}, {longitude}")
        
        try:
            # Determine state and city from coordinates
            state, city = await self._get_location_info(latitude, longitude)
            
            # Fetch real prices for key crops
            key_crops = ['wheat', 'rice', 'maize', 'soybean', 'cotton']
            logger.info(f"Fetching real prices for key crops: {key_crops}")
            
            # Create tasks for parallel requests
            tasks = []
            for crop_name in key_crops:
                commodity_name = self.crop_mapping.get(crop_name.lower())
                if commodity_name:
                    task = self._fetch_crop_prices(commodity_name, state, city)
                    tasks.append((crop_name, task))
            
            if not tasks:
                logger.warning("No valid crops to fetch prices for")
                return self._get_empty_response(state, city, latitude, longitude)
            
            # Execute requests in parallel
            logger.info(f"Making {len(tasks)} parallel requests for real prices in {state}, {city}")
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # Process results
            crop_prices = []
            price_analyses = []
            
            for i, (crop_name, result) in enumerate(zip([name for name, _ in tasks], results)):
                try:
                    if isinstance(result, Exception):
                        logger.warning(f"Error fetching prices for {crop_name}: {result}")
                        continue
                        
                    if result:
                        crop_prices.extend(result)
                        
                        # Create price analysis
                        analysis = self._analyze_price_trend(result, crop_name)
                        if analysis:
                            price_analyses.append(analysis)
                            
                except Exception as e:
                    logger.warning(f"Error processing results for {crop_name}: {e}")
                    continue
            
            # Create market prices object
            market_prices = MarketPrices(
                prices=crop_prices,
                analyses=price_analyses,
                location={'state': state, 'city': city},
                data_source='agmarknet',
                last_updated=datetime.now().isoformat()
            )
            
            logger.info(f"Successfully fetched {len(crop_prices)} real price records for {state}, {city}")
            return {
                'market_prices': market_prices.dict(),
                'raw_data': crop_prices,
                'coordinates': {'latitude': latitude, 'longitude': longitude},
                'data_source': 'agmarknet',
                'timestamp': datetime.now().isoformat(),
                'location_info': {'state': state, 'city': city}
            }
            
        except Exception as e:
            logger.error(f"Error fetching Agmarknet data for {latitude}, {longitude}: {e}")
            raise APIError(f"Failed to fetch Agmarknet data: {e}") from e
    
    def _get_empty_response(self, state: str, city: str, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get empty response structure."""
        return {
            'market_prices': {
                'prices': [],
                'analyses': [],
                'location': {'state': state, 'city': city},
                'data_source': 'agmarknet',
                'last_updated': datetime.now().isoformat()
            },
            'raw_data': [],
            'coordinates': {'latitude': latitude, 'longitude': longitude},
            'data_source': 'agmarknet',
            'timestamp': datetime.now().isoformat(),
            'location_info': {'state': state, 'city': city}
        }
    
    async def fetch_prices_for_crops(self, crop_names: List[str], latitude: float, longitude: float) -> Dict[str, Any]:
        """Fetch prices only for specific crops that are suitable for the location."""
        logger.info(f"Fetching prices for {len(crop_names)} selected crops: {crop_names}")
        
        try:
            # Determine state and city from coordinates
            state, city = await self._get_location_info(latitude, longitude)
            
            # Create tasks for parallel requests only for selected crops
            tasks = []
            for crop_name in crop_names:
                commodity_name = self.crop_mapping.get(crop_name.lower())
                if commodity_name:
                    task = self._fetch_crop_prices(commodity_name, state, city)
                    tasks.append((crop_name, task))
                else:
                    logger.warning(f"No commodity mapping found for crop: {crop_name}")
            
            if not tasks:
                logger.warning("No valid crops to fetch prices for")
                return {'prices': [], 'analyses': []}
            
            # Execute requests in parallel
            logger.info(f"Making {len(tasks)} parallel requests for selected crops in {state}, {city}")
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # Process results
            crop_prices = []
            price_analyses = []
            
            for i, (crop_name, result) in enumerate(zip([name for name, _ in tasks], results)):
                try:
                    if isinstance(result, Exception):
                        logger.warning(f"Error fetching prices for {crop_name}: {result}")
                        continue
                        
                    if result:
                        crop_prices.extend(result)
                        
                        # Create price analysis
                        analysis = self._analyze_price_trend(result, crop_name)
                        if analysis:
                            price_analyses.append(analysis)
                            
                except Exception as e:
                    logger.warning(f"Error processing results for {crop_name}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(crop_prices)} price records for selected crops")
            return {
                'prices': crop_prices,
                'analyses': price_analyses,
                'location': {'state': state, 'city': city},
                'selected_crops': crop_names,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error fetching prices for selected crops: {e}")
            raise APIError(f"Failed to fetch prices for selected crops: {e}") from e
    
    async def _get_location_info(self, latitude: float, longitude: float) -> tuple[str, str]:
        """Get state and city from coordinates (simplified mapping)."""
        # This is a simplified mapping - in production, you'd use a geocoding service
        # For now, we'll use a basic coordinate-based mapping for Indian states
        
        if 18.0 <= latitude <= 20.0 and 72.0 <= longitude <= 75.0:
            return "Maharashtra", "Pune"
        elif 12.0 <= latitude <= 15.0 and 74.0 <= longitude <= 78.0:
            return "Karnataka", "Bangalore"
        elif 8.0 <= latitude <= 12.0 and 76.0 <= longitude <= 78.0:
            return "Kerala", "Kochi"
        elif 10.0 <= latitude <= 14.0 and 78.0 <= longitude <= 80.0:
            return "Tamil Nadu", "Chennai"
        elif 20.0 <= latitude <= 25.0 and 85.0 <= longitude <= 88.0:
            return "West Bengal", "Kolkata"
        elif 25.0 <= latitude <= 32.0 and 74.0 <= longitude <= 78.0:
            return "Punjab", "Chandigarh"
        elif 22.0 <= latitude <= 25.0 and 70.0 <= longitude <= 75.0:
            return "Gujarat", "Ahmedabad"
        else:
            # Default to Maharashtra, Pune
            return "Maharashtra", "Pune"
    
    async def _fetch_crop_prices(self, commodity: str, state: str, city: str) -> List[Dict[str, Any]]:
        """Fetch prices for a specific commodity from Agmarknet API."""
        try:
            # Use the Agmarknet API endpoint
            params = {
                'commodity': commodity,
                'state': state,
                'market': city
            }
            
            response = await self.get('request', params=params)
            
            if not response:
                return []
            
            # Handle different response formats
            if isinstance(response, str):
                logger.warning(f"Received string response for {commodity}: {response}")
                return []
            
            # Handle the actual API response structure
            if isinstance(response, dict):
                # Check if it's the expected API response format
                if 'success' in response and 'data' in response:
                    if response.get('success') and response.get('data'):
                        response = response['data']  # Extract the data array
                    else:
                        logger.warning(f"API returned unsuccessful response for {commodity}: {response}")
                        return []
                else:
                    # Handle single record response (legacy format)
                    response = [response]
            
            if not isinstance(response, list):
                logger.warning(f"Unexpected response format for {commodity}: {type(response)}")
                return []
            
            # Process the response
            prices = []
            for item in response:
                try:
                    # The API now provides prices per kg directly
                    min_price_per_kg = float(item.get('Min Prize Per Kg', 0))
                    max_price_per_kg = float(item.get('Max Prize Per Kg', 0))
                    modal_price_per_kg = float(item.get('Model Prize Per Kg', 0))
                    
                    # Fallback to quintal prices if per kg prices are not available
                    if min_price_per_kg == 0 and max_price_per_kg == 0 and modal_price_per_kg == 0:
                        min_price_per_quintal = float(item.get('Min Prize', 0))
                        max_price_per_quintal = float(item.get('Max Prize', 0))
                        modal_price_per_quintal = float(item.get('Model Prize', 0))
                        
                        # Convert quintal to per kg (1 quintal = 100 kg)
                        min_price_per_kg = min_price_per_quintal / 100.0
                        max_price_per_kg = max_price_per_quintal / 100.0
                        modal_price_per_kg = modal_price_per_quintal / 100.0
                    
                    # Skip if all prices are still 0 (invalid data)
                    if min_price_per_kg == 0 and max_price_per_kg == 0 and modal_price_per_kg == 0:
                        logger.warning(f"Skipping invalid price data for {item.get('Commodity', 'unknown')}: all prices are 0")
                        continue
                    
                    # Use modal price, but fallback to min/max if modal is 0
                    if modal_price_per_kg > 0:
                        final_price = modal_price_per_kg
                    elif max_price_per_kg > 0:
                        final_price = max_price_per_kg
                    elif min_price_per_kg > 0:
                        final_price = min_price_per_kg
                    else:
                        logger.warning(f"All prices are 0 for {item.get('Commodity', 'unknown')}, skipping")
                        continue
                    
                    # Convert date format from "18 Oct 2025" to "2025-10-18"
                    date_str = item.get('Date', '')
                    formatted_date = self._parse_agmarknet_date(date_str)
                    
                    price_record = CropPrice(
                        crop_name=item.get('Commodity', '').lower(),
                        price_per_kg=final_price,  # Use validated price
                        currency="INR",
                        date=formatted_date,
                        market_location=f"{item.get('City', '')}, {state}",
                        data_source="agmarknet"
                    )
                    prices.append(price_record.dict())
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing price record: {e}")
                    continue
            
            return prices
            
        except Exception as e:
            logger.error(f"Error fetching prices for {commodity}: {e}")
            return []
    
    def _analyze_price_trend(self, price_data: List[Dict[str, Any]], crop_name: str) -> Optional[Dict[str, Any]]:
        """Analyze price trend for a crop."""
        try:
            if not price_data:
                return None
            
            # Extract prices and dates
            prices = []
            dates = []
            
            for record in price_data:
                try:
                    modal_price = record.get('modal_price_per_quintal', 0)
                    if modal_price > 0:
                        prices.append(modal_price)
                        dates.append(record.get('date', ''))
                except (ValueError, TypeError):
                    continue
            
            if len(prices) < 2:
                return None
            
            # Calculate trend
            recent_prices = prices[:5]  # Last 5 records
            older_prices = prices[5:10] if len(prices) > 5 else prices[2:]
            
            if not older_prices:
                trend = PriceTrend.STABLE
            else:
                recent_avg = sum(recent_prices) / len(recent_prices)
                older_avg = sum(older_prices) / len(older_prices)
                
                change_percent = ((recent_avg - older_avg) / older_avg) * 100
                
                if change_percent > 5:
                    trend = PriceTrend.RISING
                elif change_percent < -5:
                    trend = PriceTrend.FALLING
                else:
                    trend = PriceTrend.STABLE
            
            # Calculate volatility (simplified)
            if len(prices) > 1:
                mean_price = sum(prices) / len(prices)
                variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
                volatility = (variance ** 0.5) / mean_price * 100
            else:
                volatility = 0
            
            # Calculate profitability score (simplified)
            current_price = prices[0] if prices else 0
            profitability_score = min(current_price / 1000, 1.0)  # Normalize to 0-1
            
            return PriceAnalysis(
                crop_name=crop_name,
                current_price=current_price,
                price_trend=trend,
                volatility=round(volatility, 2),
                profitability_score=round(profitability_score, 3),
                analysis_date=datetime.now().isoformat(),
                data_points=len(prices)
            ).dict()
            
        except Exception as e:
            logger.error(f"Error analyzing price trend for {crop_name}: {e}")
            return None
    
    async def start_agmarknet_server(self) -> bool:
        """Start the Agmarknet web scraping server (if not running)."""
        try:
            # Check if server is already running
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    logger.info("Agmarknet server is already running")
                    return True
        except:
            pass
        
        logger.info("Agmarknet server not running. Please start it manually:")
        logger.info("1. Clone the repository: git clone https://github.com/Prajwal-Shrimali/agmarknetAPI.git")
        logger.info("2. Install dependencies: pip install -r requirements.txt")
        logger.info("3. Run the server: python APIwebScraping.py")
        logger.info("4. Server will be available at http://127.0.0.1:5000")
        
        return False
    
    async def _check_server_status(self) -> bool:
        """Check if Agmarknet server is running."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/", timeout=2.0)
                return response.status_code == 200
        except:
            return False
    
    def _parse_agmarknet_date(self, date_str: str) -> str:
        """Parse Agmarknet date format to YYYY-MM-DD."""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Handle formats like "15 Oct 2025", "17 Oct 2025"
            parsed_date = datetime.strptime(date_str.strip(), '%d %b %Y')
            return parsed_date.strftime('%Y-%m-%d')
        except ValueError:
            try:
                # Try alternative format if first fails
                parsed_date = datetime.strptime(date_str.strip(), '%d-%m-%Y')
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                # If all parsing fails, return current date
                logger.warning(f"Could not parse date '{date_str}', using current date")
                return datetime.now().strftime('%Y-%m-%d')
