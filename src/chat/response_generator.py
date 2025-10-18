"""Intelligent response generation for chat interface."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import asyncio

from .models import ChatQuery, ChatResponse, QueryIntent, Message, MessageRole
from ..data_layer.pipeline import DataPipeline
from ..data_layer.crop_database import CropDatabase
from ..models.location import LocationData

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generates intelligent responses to user queries."""
    
    def __init__(self):
        """Initialize response generator."""
        self.pipeline = DataPipeline()
        self.crop_database = CropDatabase()
        self.response_templates = self._build_response_templates()
        self.context_manager = ConversationContextManager()
    
    async def generate_response(self, query: ChatQuery) -> ChatResponse:
        """Generate response to user query."""
        logger.info(f"Generating response for intent: {query.intent}")
        
        try:
            # Route to appropriate handler based on intent
            if query.intent == QueryIntent.CROP_RECOMMENDATION:
                return await self._handle_crop_recommendation(query)
            elif query.intent == QueryIntent.WEATHER_INFO:
                return await self._handle_weather_info(query)
            elif query.intent == QueryIntent.SOIL_INFO:
                return await self._handle_soil_info(query)
            elif query.intent == QueryIntent.MARKET_PRICE:
                return await self._handle_market_price(query)
            elif query.intent == QueryIntent.CROP_REQUIREMENTS:
                return await self._handle_crop_requirements(query)
            elif query.intent == QueryIntent.LOCATION_ANALYSIS:
                return await self._handle_location_analysis(query)
            elif query.intent == QueryIntent.PROFITABILITY_ANALYSIS:
                return await self._handle_profitability_analysis(query)
            elif query.intent == QueryIntent.SEASONAL_ADVICE:
                return await self._handle_seasonal_advice(query)
            elif query.intent == QueryIntent.GREETING:
                return await self._handle_greeting(query)
            elif query.intent == QueryIntent.HELP:
                return await self._handle_help(query)
            else:
                return await self._handle_general_question(query)
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._generate_error_response(str(e))
    
    async def _handle_crop_recommendation(self, query: ChatQuery) -> ChatResponse:
        """Handle crop recommendation queries."""
        # Get location data
        location_data = await self._get_location_data(query)
        if not location_data:
            return self._generate_location_required_response()
        
        # Get crop recommendations
        recommendations = self.pipeline.get_crop_recommendations(location_data)
        
        if not recommendations:
            return ChatResponse(
                message="I couldn't find suitable crops for your location. Please check if the coordinates are correct or try a different location.",
                intent=query.intent,
                confidence=0.8,
                suggestions=["Try providing coordinates", "Ask about soil conditions", "Check weather data"]
            )
        
        # Format recommendations
        message = self._format_crop_recommendations(recommendations, location_data)
        
        return ChatResponse(
            message=message,
            intent=query.intent,
            data={
                "recommendations": [rec.dict() for rec in recommendations],
                "location": location_data.location.dict()
            },
            recommendations=[rec.dict() for rec in recommendations],
            confidence=0.9,
            sources=["SoilGrids", "Open-Meteo", "Agmarknet"],
            suggestions=[
                "Ask about specific crop requirements",
                "Get weather forecast",
                "Check market prices",
                "Analyze profitability"
            ]
        )
    
    async def _handle_weather_info(self, query: ChatQuery) -> ChatResponse:
        """Handle weather information queries."""
        location_data = await self._get_location_data(query)
        if not location_data:
            return self._generate_location_required_response()
        
        weather = location_data.weather_data
        if not weather:
            return ChatResponse(
                message="I couldn't retrieve weather data for your location. Please try again later.",
                intent=query.intent,
                confidence=0.7
            )
        
        message = f"""🌤️ **Current Weather Conditions**

📍 **Location**: {location_data.location.city or 'Unknown'}, {location_data.location.state or 'Unknown'}
🌡️ **Temperature**: {weather.temperature_c:.1f}°C
💧 **Humidity**: {weather.humidity_percent:.1f}%
🌧️ **Rainfall**: {weather.rainfall_mm:.1f} mm
🌬️ **Wind Speed**: {weather.wind_speed_kmh:.1f} km/h
☁️ **Conditions**: {weather.conditions}

This weather data is perfect for agricultural planning!"""
        
        return ChatResponse(
            message=message,
            intent=query.intent,
            data={"weather": weather.dict()},
            confidence=0.9,
            sources=["Open-Meteo"],
            suggestions=[
                "Get crop recommendations",
                "Check soil conditions",
                "Analyze rainfall patterns"
            ]
        )
    
    async def _handle_soil_info(self, query: ChatQuery) -> ChatResponse:
        """Handle soil information queries."""
        location_data = await self._get_location_data(query)
        if not location_data:
            return self._generate_location_required_response()
        
        soil = location_data.soil_profile
        if not soil:
            return ChatResponse(
                message="I couldn't retrieve soil data for your location. Please try again later.",
                intent=query.intent,
                confidence=0.7
            )
        
        message = f"""🌱 **Soil Analysis Report**

📍 **Location**: {location_data.location.city or 'Unknown'}, {location_data.location.state or 'Unknown'}
🧪 **Soil pH**: {soil.ph:.2f}
🌿 **Fertility Level**: {soil.fertility_index:.2f}
🏗️ **Soil Type**: {soil.soil_type}
💧 **Water Holding Capacity**: {soil.water_holding_capacity:.2f}
🌾 **Organic Matter**: {soil.organic_matter_percent:.1f}%

**Soil Health**: {'Excellent' if soil.fertility_index > 0.8 else 'Good' if soil.fertility_index > 0.6 else 'Fair'}

This soil analysis helps determine the best crops for your land!"""
        
        return ChatResponse(
            message=message,
            intent=query.intent,
            data={"soil": soil.dict()},
            confidence=0.9,
            sources=["SoilGrids"],
            suggestions=[
                "Get crop recommendations",
                "Check soil pH requirements",
                "Analyze crop suitability"
            ]
        )
    
    async def _handle_market_price(self, query: ChatQuery) -> ChatResponse:
        """Handle market price queries."""
        location_data = await self._get_location_data(query)
        if not location_data:
            return self._generate_location_required_response()
        
        market_prices = location_data.market_prices
        if not market_prices or not market_prices.prices:
            return ChatResponse(
                message="I couldn't retrieve market price data for your location. Please try again later.",
                intent=query.intent,
                confidence=0.7
            )
        
        # Filter prices for specific crop if mentioned
        prices = market_prices.prices
        if query.crop_name:
            prices = [p for p in prices if query.crop_name.lower() in p.crop_name.lower()]
        
        if not prices:
            return ChatResponse(
                message=f"I couldn't find market prices for {query.crop_name or 'the requested crops'}. Please try a different crop or location.",
                intent=query.intent,
                confidence=0.7
            )
        
        message = f"""💰 **Market Price Information**

📍 **Location**: {location_data.location.city or 'Unknown'}, {location_data.location.state or 'Unknown'}
📅 **Last Updated**: {market_prices.last_updated}

**Current Market Prices:**
"""
        
        for price in prices[:5]:  # Show top 5 prices
            crop_name = price.crop_name
            price_value = price.price_per_kg
            market_name = price.market_location or 'Unknown'
            message += f"• **{crop_name.title()}**: ₹{price_value:.2f}/kg ({market_name})\n"
        
        message += f"\n💡 **Tip**: These prices help calculate profitability for crop selection!"
        
        return ChatResponse(
            message=message,
            intent=query.intent,
            data={"prices": prices},
            confidence=0.9,
            sources=["Agmarknet"],
            suggestions=[
                "Calculate profitability",
                "Get crop recommendations",
                "Check price trends"
            ]
        )
    
    async def _handle_crop_requirements(self, query: ChatQuery) -> ChatResponse:
        """Handle crop requirements queries."""
        if not query.crop_name:
            return ChatResponse(
                message="Please specify which crop you'd like to know about. For example: 'What are the requirements for growing wheat?'",
                intent=query.intent,
                confidence=0.8,
                suggestions=["Try: 'wheat requirements'", "Try: 'rice growing conditions'", "Try: 'maize cultivation'"]
            )
        
        requirements = self.crop_database.get_crop_requirements(query.crop_name)
        if not requirements:
            return ChatResponse(
                message=f"I don't have information about {query.crop_name}. Please try a different crop name.",
                intent=query.intent,
                confidence=0.7,
                suggestions=["Try: wheat, rice, maize, soybean", "Check available crops"]
            )
        
        message = f"""🌾 **{query.crop_name.title()} Growing Requirements**

🌡️ **Temperature**: {requirements.temp_min_c:.1f}°C - {requirements.temp_max_c:.1f}°C (Optimal: {requirements.temp_optimal_c:.1f}°C)
🧪 **Soil pH**: {requirements.ph_min:.1f} - {requirements.ph_max:.1f} (Optimal: {requirements.ph_optimal:.1f})
🌧️ **Rainfall**: {requirements.rainfall_min_mm:.0f} - {requirements.rainfall_max_mm or 'unlimited'} mm per season
💧 **Water Requirement**: {requirements.water_requirement.value.title()}
🌱 **Soil Types**: {', '.join([st.value for st in requirements.soil_types]) if requirements.soil_types else 'Any'}
📅 **Growing Season**: {', '.join([str(m) for m in requirements.growing_season_months])}
⏱️ **Growth Duration**: {requirements.growth_duration_days} days
🌾 **Typical Yield**: {requirements.typical_yield_per_acre:.0f} kg/acre
💰 **Base Price**: ₹{requirements.base_market_price_per_kg:.2f}/kg

**Growing Tips**: Plant during the recommended months for best results!"""
        
        return ChatResponse(
            message=message,
            intent=query.intent,
            data={"requirements": requirements.dict()},
            confidence=0.9,
            sources=["Crop Database"],
            suggestions=[
                "Check if suitable for your location",
                "Get planting schedule",
                "Calculate profitability"
            ]
        )
    
    async def _handle_location_analysis(self, query: ChatQuery) -> ChatResponse:
        """Handle location analysis queries."""
        location_data = await self._get_location_data(query)
        if not location_data:
            return self._generate_location_required_response()
        
        # Comprehensive location analysis
        analysis = {
            "coordinates": f"{location_data.location.coordinates.latitude:.4f}, {location_data.location.coordinates.longitude:.4f}",
            "city": location_data.location.city or "Unknown",
            "state": location_data.location.state or "Unknown",
            "soil": location_data.soil_profile.dict() if location_data.soil_profile else None,
            "weather": location_data.weather_data.dict() if location_data.weather_data else None,
            "rainfall": location_data.rainfall_data.dict() if location_data.rainfall_data else None,
            "market_prices": location_data.market_prices.dict() if location_data.market_prices else None
        }
        
        message = f"""📍 **Location Analysis Report**

**Location**: {analysis['city']}, {analysis['state']}
**Coordinates**: {analysis['coordinates']}

**Environmental Conditions:**
"""
        
        if analysis['soil']:
            message += f"• **Soil pH**: {analysis['soil']['ph']:.2f}\n"
            message += f"• **Fertility**: {analysis['soil']['fertility_index']:.2f}\n"
        
        if analysis['weather']:
            message += f"• **Temperature**: {analysis['weather']['temperature_c']:.1f}°C\n"
            message += f"• **Humidity**: {analysis['weather']['humidity_percent']:.1f}%\n"
        
        if analysis['rainfall']:
            message += f"• **Rainfall**: {analysis['rainfall']['total_rainfall_mm']:.1f} mm\n"
        
        message += "\n**Market Access**: Available" if analysis['market_prices'] else "\n**Market Access**: Limited data"
        
        message += "\n\nThis location analysis helps determine agricultural potential!"
        
        return ChatResponse(
            message=message,
            intent=query.intent,
            data=analysis,
            confidence=0.9,
            sources=["SoilGrids", "Open-Meteo", "Agmarknet"],
            suggestions=[
                "Get crop recommendations",
                "Check profitability",
                "Analyze seasonal patterns"
            ]
        )
    
    async def _handle_profitability_analysis(self, query: ChatQuery) -> ChatResponse:
        """Handle profitability analysis queries."""
        location_data = await self._get_location_data(query)
        if not location_data:
            return self._generate_location_required_response()
        
        recommendations = self.pipeline.get_crop_recommendations(location_data)
        if not recommendations:
            return ChatResponse(
                message="I couldn't generate profitability analysis. Please check your location coordinates.",
                intent=query.intent,
                confidence=0.7
            )
        
        # Sort by profitability
        sorted_recs = sorted(recommendations, key=lambda x: x.expected_profit_per_acre, reverse=True)
        
        message = f"""💰 **Profitability Analysis**

📍 **Location**: {location_data.location.city or 'Unknown'}, {location_data.location.state or 'Unknown'}

**Top Profitable Crops:**
"""
        
        for i, rec in enumerate(sorted_recs[:5], 1):
            message += f"{i}. **{rec.crop_name.title()}**: ₹{rec.expected_profit_per_acre:,.0f}/acre (Score: {rec.profitability_score:.2f})\n"
        
        message += f"\n💡 **Best Choice**: {sorted_recs[0].crop_name.title()} with ₹{sorted_recs[0].expected_profit_per_acre:,.0f} expected profit per acre!"
        
        return ChatResponse(
            message=message,
            intent=query.intent,
            data={"recommendations": [rec.dict() for rec in sorted_recs]},
            confidence=0.9,
            sources=["Market Prices", "Crop Database"],
            suggestions=[
                "Get detailed crop requirements",
                "Check market price trends",
                "Analyze risk factors"
            ]
        )
    
    async def _handle_seasonal_advice(self, query: ChatQuery) -> ChatResponse:
        """Handle seasonal advice queries."""
        current_month = datetime.now().month
        
        # Get crops suitable for current month
        suitable_crops = self.crop_database.get_crops_by_season(current_month)
        
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        
        message = f"""📅 **Seasonal Agricultural Advice**

🗓️ **Current Month**: {month_names[current_month - 1]}
🌱 **Suitable Crops for This Month**: {', '.join(suitable_crops[:5]) if suitable_crops else 'None'}

**This Month's Recommendations:**
"""
        
        if suitable_crops:
            message += f"• **Plant**: {', '.join(suitable_crops[:3])}\n"
            message += f"• **Harvest**: Check crops planted 3-6 months ago\n"
            message += f"• **Prepare**: Soil preparation for next season\n"
        else:
            message += "• **Focus**: Soil preparation and maintenance\n"
            message += "• **Plan**: Next season's crop selection\n"
        
        message += f"\n💡 **Tip**: Use location-specific recommendations for better results!"
        
        return ChatResponse(
            message=message,
            intent=query.intent,
            data={"suitable_crops": suitable_crops, "current_month": current_month},
            confidence=0.8,
            sources=["Crop Database"],
            suggestions=[
                "Get location-specific recommendations",
                "Check weather conditions",
                "Plan next season"
            ]
        )
    
    async def _handle_greeting(self, query: ChatQuery) -> ChatResponse:
        """Handle greeting queries."""
        greetings = [
            "Hello! I'm your AgriTech assistant. I can help you with crop recommendations, weather data, soil analysis, and market prices. What would you like to know?",
            "Hi there! I'm here to help you make better agricultural decisions. I can analyze your location and recommend suitable crops, check weather conditions, and provide market insights. How can I assist you today?",
            "Welcome! I'm your agricultural advisor. I can help you with crop selection, soil analysis, weather information, and profitability calculations. What's your farming question?"
        ]
        
        import random
        message = random.choice(greetings)
        
        return ChatResponse(
            message=message,
            intent=query.intent,
            confidence=1.0,
            suggestions=[
                "Get crop recommendations",
                "Check weather conditions",
                "Analyze soil data",
                "Check market prices"
            ]
        )
    
    async def _handle_help(self, query: ChatQuery) -> ChatResponse:
        """Handle help queries."""
        message = """🆘 **How I Can Help You**

I'm your AI agricultural assistant! Here's what I can do:

🌾 **Crop Recommendations**
• "What crops should I grow?"
• "Recommend crops for my location"
• "Best crops for 18.5204, 73.8567"

🌤️ **Weather Information**
• "What's the weather like?"
• "Temperature and rainfall data"
• "Weather conditions for farming"

🌱 **Soil Analysis**
• "What's my soil type?"
• "Soil pH and fertility"
• "Soil conditions analysis"

💰 **Market Prices**
• "What are current crop prices?"
• "Market rates for wheat"
• "Price trends and profitability"

📋 **Crop Requirements**
• "How to grow wheat?"
• "Rice cultivation requirements"
• "Maize growing conditions"

📍 **Location Analysis**
• "Analyze my location"
• "Agricultural potential"
• "Site suitability"

**Just ask me naturally - I understand context and can help with any farming question!**"""
        
        return ChatResponse(
            message=message,
            intent=query.intent,
            confidence=1.0,
            suggestions=[
                "Try asking about crops",
                "Check weather data",
                "Get location analysis"
            ]
        )
    
    async def _handle_general_question(self, query: ChatQuery) -> ChatResponse:
        """Handle general questions."""
        message = """I'm your agricultural assistant! I can help you with:

🌾 Crop recommendations and requirements
🌤️ Weather and climate data  
🌱 Soil analysis and conditions
💰 Market prices and profitability
📍 Location-based agricultural advice

Please ask me something specific about farming, crops, or agriculture. For example:
• "What crops should I grow?"
• "What's the weather like?"
• "How to grow wheat?"
• "Check market prices"

How can I help you today?"""
        
        return ChatResponse(
            message=message,
            intent=query.intent,
            confidence=0.7,
            suggestions=[
                "Ask about crop recommendations",
                "Check weather conditions",
                "Get soil analysis"
            ]
        )
    
    async def _get_location_data(self, query: ChatQuery) -> Optional[LocationData]:
        """Get location data for query."""
        # Try to get coordinates from query
        if query.coordinates:
            lat, lon = query.coordinates['latitude'], query.coordinates['longitude']
        else:
            # Use default coordinates (Pune) if none provided
            lat, lon = 18.5204, 73.8567
        
        try:
            return await self.pipeline.fetch_location_data(lat, lon)
        except Exception as e:
            logger.error(f"Error fetching location data: {e}")
            return None
    
    def _format_crop_recommendations(self, recommendations: List, location_data: LocationData) -> str:
        """Format crop recommendations into readable text."""
        message = f"""🌾 **Crop Recommendations**

📍 **Location**: {location_data.location.city or 'Unknown'}, {location_data.location.state or 'Unknown'}

**Top Recommendations:**
"""
        
        for i, rec in enumerate(recommendations[:5], 1):
            message += f"{i}. **{rec.crop_name.title()}**\n"
            message += f"   • Suitability: {rec.suitability_score:.1%}\n"
            message += f"   • Expected Profit: ₹{rec.expected_profit_per_acre:,.0f}/acre\n"
            message += f"   • Risk Level: {rec.risk_level.title()}\n"
            message += f"   • Summary: {rec.summary}\n\n"
        
        message += "💡 **Tip**: Consider soil conditions, weather patterns, and market prices for the best decision!"
        
        return message
    
    def _generate_location_required_response(self) -> ChatResponse:
        """Generate response when location is required."""
        return ChatResponse(
            message="I need your location to provide accurate recommendations. Please provide coordinates (e.g., '18.5204, 73.8567') or ask me to analyze a specific location.",
            intent=QueryIntent.LOCATION_ANALYSIS,
            confidence=0.8,
            suggestions=[
                "Provide coordinates",
                "Ask about a specific city",
                "Try: 'Analyze Pune location'"
            ]
        )
    
    def _generate_error_response(self, error: str) -> ChatResponse:
        """Generate error response."""
        return ChatResponse(
            message=f"I encountered an error: {error}. Please try again or rephrase your question.",
            intent=QueryIntent.GENERAL_QUESTION,
            confidence=0.5,
            suggestions=[
                "Try rephrasing your question",
                "Check your coordinates",
                "Ask for help"
            ]
        )
    
    def _build_response_templates(self) -> Dict[str, str]:
        """Build response templates for different scenarios."""
        return {
            "no_data": "I couldn't retrieve the requested data. Please try again later.",
            "location_required": "Please provide your location coordinates for accurate recommendations.",
            "crop_not_found": "I don't have information about that crop. Please try a different crop name.",
            "general_error": "I encountered an error. Please try again or rephrase your question."
        }


class ConversationContextManager:
    """Manages conversation context and memory."""
    
    def __init__(self):
        """Initialize context manager."""
        self.context_cache: Dict[str, Dict[str, Any]] = {}
    
    def get_context(self, session_id: str) -> Dict[str, Any]:
        """Get conversation context."""
        return self.context_cache.get(session_id, {})
    
    def update_context(self, session_id: str, updates: Dict[str, Any]):
        """Update conversation context."""
        if session_id not in self.context_cache:
            self.context_cache[session_id] = {}
        
        self.context_cache[session_id].update(updates)
    
    def clear_context(self, session_id: str):
        """Clear conversation context."""
        if session_id in self.context_cache:
            del self.context_cache[session_id]
