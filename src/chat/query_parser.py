"""Natural language query parser and intent recognition."""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .models import QueryIntent, ChatQuery, Message

logger = logging.getLogger(__name__)


@dataclass
class EntityMatch:
    """Entity match result."""
    entity: str
    value: Any
    confidence: float
    start_pos: int
    end_pos: int


class QueryParser:
    """Natural language query parser with intent recognition."""
    
    def __init__(self):
        """Initialize query parser."""
        self.intent_patterns = self._build_intent_patterns()
        self.entity_patterns = self._build_entity_patterns()
        self.crop_names = self._load_crop_names()
        self.location_keywords = self._load_location_keywords()
    
    def parse_query(self, text: str, context: List[Message] = None) -> ChatQuery:
        """Parse user query and extract intent and entities."""
        logger.info(f"Parsing query: {text}")
        
        # Normalize text
        normalized_text = self._normalize_text(text)
        
        # Classify intent
        intent, confidence = self._classify_intent(normalized_text, context)
        
        # Extract entities
        entities = self._extract_entities(normalized_text)
        
        # Build query object
        query = ChatQuery(
            original_text=text,
            intent=intent,
            confidence=confidence,
            conversation_context=context or []
        )
        
        # Set extracted entities
        if entities.get('location'):
            query.location = entities['location']
        if entities.get('crop_name'):
            query.crop_name = entities['crop_name']
        if entities.get('coordinates'):
            query.coordinates = entities['coordinates']
        
        query.parameters = {k: v for k, v in entities.items() 
                           if k not in ['location', 'crop_name', 'coordinates']}
        
        logger.info(f"Parsed query - Intent: {intent}, Confidence: {confidence:.2f}")
        return query
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for processing."""
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Handle common abbreviations
        abbreviations = {
            'temp': 'temperature',
            'rain': 'rainfall',
            'soil ph': 'soil ph',
            'price': 'market price',
            'cost': 'market price',
            'profit': 'profitability',
            'yield': 'crop yield'
        }
        
        for abbr, full in abbreviations.items():
            text = text.replace(abbr, full)
        
        return text
    
    def _classify_intent(self, text: str, context: List[Message] = None) -> Tuple[QueryIntent, float]:
        """Classify query intent."""
        scores = {}
        
        # Check each intent pattern
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1.0
                    matches += 1
            
            if matches > 0:
                scores[intent] = score / len(patterns)
        
        # Context-based intent adjustment
        if context:
            scores = self._adjust_intent_with_context(scores, context)
        
        # Return best intent
        if scores:
            best_intent = max(scores.items(), key=lambda x: x[1])
            return QueryIntent(best_intent[0]), best_intent[1]
        
        # Default to general question
        return QueryIntent.GENERAL_QUESTION, 0.5
    
    def _adjust_intent_with_context(self, scores: Dict[str, float], context: List[Message]) -> Dict[str, float]:
        """Adjust intent scores based on conversation context."""
        # Boost intent if it's a follow-up to a related topic
        recent_messages = context[-3:] if len(context) > 3 else context
        
        for message in recent_messages:
            if message.role.value == "assistant":
                # If assistant mentioned crops, boost crop-related intents
                if any(word in message.content.lower() for word in ['crop', 'plant', 'grow']):
                    if QueryIntent.CROP_RECOMMENDATION.value in scores:
                        scores[QueryIntent.CROP_RECOMMENDATION.value] += 0.2
                    if QueryIntent.CROP_REQUIREMENTS.value in scores:
                        scores[QueryIntent.CROP_REQUIREMENTS.value] += 0.2
                
                # If assistant mentioned weather, boost weather intents
                if any(word in message.content.lower() for word in ['weather', 'temperature', 'rainfall']):
                    if QueryIntent.WEATHER_INFO.value in scores:
                        scores[QueryIntent.WEATHER_INFO.value] += 0.2
        
        return scores
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from text."""
        entities = {}
        
        # Extract crop names
        crop_match = self._extract_crop_name(text)
        if crop_match:
            entities['crop_name'] = crop_match
        
        # Extract coordinates
        coords = self._extract_coordinates(text)
        if coords:
            entities['coordinates'] = coords
        
        # Extract location information
        location = self._extract_location(text)
        if location:
            entities['location'] = location
        
        # Extract numerical values
        numbers = self._extract_numbers(text)
        if numbers:
            entities['numbers'] = numbers
        
        # Extract time references
        time_refs = self._extract_time_references(text)
        if time_refs:
            entities['time_references'] = time_refs
        
        return entities
    
    def _extract_crop_name(self, text: str) -> Optional[str]:
        """Extract crop name from text."""
        for crop in self.crop_names:
            if crop.lower() in text:
                return crop
        return None
    
    def _extract_coordinates(self, text: str) -> Optional[Dict[str, float]]:
        """Extract latitude and longitude from text."""
        # Pattern for coordinates like "18.5204, 73.8567" or "18.5204°N, 73.8567°E"
        coord_pattern = r'(\d+\.?\d*)\s*°?[NS]?\s*,\s*(\d+\.?\d*)\s*°?[EW]?'
        match = re.search(coord_pattern, text)
        
        if match:
            lat = float(match.group(1))
            lon = float(match.group(2))
            
            # Validate coordinate ranges
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return {'latitude': lat, 'longitude': lon}
        
        return None
    
    def _extract_location(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract location information from text."""
        location_info = {}
        
        # Check for city names
        for city in self.location_keywords['cities']:
            if city.lower() in text:
                location_info['city'] = city
                break
        
        # Check for state names
        for state in self.location_keywords['states']:
            if state.lower() in text:
                location_info['state'] = state
                break
        
        return location_info if location_info else None
    
    def _extract_numbers(self, text: str) -> List[float]:
        """Extract numerical values from text."""
        number_pattern = r'\d+\.?\d*'
        matches = re.findall(number_pattern, text)
        return [float(match) for match in matches]
    
    def _extract_time_references(self, text: str) -> List[str]:
        """Extract time references from text."""
        time_patterns = [
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b(?:spring|summer|autumn|winter|fall)\b',
            r'\b(?:kharif|rabi|zaid)\b',
            r'\b(?:monsoon|dry|wet)\s+season\b'
        ]
        
        time_refs = []
        for pattern in time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            time_refs.extend(matches)
        
        return time_refs
    
    def _build_intent_patterns(self) -> Dict[str, List[str]]:
        """Build intent classification patterns."""
        return {
            QueryIntent.CROP_RECOMMENDATION.value: [
                r'recommend.*crop',
                r'what.*crop.*grow',
                r'best.*crop.*for',
                r'suitable.*crop',
                r'which.*crop.*plant',
                r'crop.*suggestion',
                r'what.*plant.*here',
                r'grow.*crop',
                r'what.*should.*i.*grow',
                r'what.*crops.*should.*i.*grow',
                r'best.*crops.*for.*my.*location',
                r'what.*can.*i.*grow',
                r'suggest.*crops',
                r'crop.*recommendation',
                r'what.*to.*plant',
                r'which.*crops.*suitable'
            ],
            QueryIntent.WEATHER_INFO.value: [
                r'weather.*condition',
                r'temperature.*now',
                r'rainfall.*data',
                r'humidity.*level',
                r'weather.*forecast',
                r'climate.*condition',
                r'weather.*information'
            ],
            QueryIntent.SOIL_INFO.value: [
                r'soil.*type',
                r'soil.*ph',
                r'soil.*condition',
                r'soil.*quality',
                r'fertility.*level',
                r'soil.*analysis',
                r'land.*condition'
            ],
            QueryIntent.MARKET_PRICE.value: [
                r'market.*price',
                r'price.*crop',
                r'cost.*crop',
                r'profit.*crop',
                r'price.*trend',
                r'market.*rate',
                r'crop.*value'
            ],
            QueryIntent.CROP_REQUIREMENTS.value: [
                r'requirement.*crop',
                r'need.*grow',
                r'condition.*crop',
                r'care.*crop',
                r'cultivation.*method',
                r'growing.*condition',
                r'crop.*care',
                r'how.*to.*grow',
                r'how.*grow',
                r'growing.*requirements',
                r'cultivation.*requirements',
                r'what.*needed.*to.*grow',
                r'requirements.*for.*growing',
                r'how.*cultivate',
                r'growing.*guide'
            ],
            QueryIntent.LOCATION_ANALYSIS.value: [
                r'analyze.*location',
                r'location.*suitable',
                r'land.*analysis',
                r'area.*condition',
                r'location.*data',
                r'site.*analysis'
            ],
            QueryIntent.PROFITABILITY_ANALYSIS.value: [
                r'profit.*analysis',
                r'profitability.*crop',
                r'return.*investment',
                r'economic.*viability',
                r'cost.*benefit',
                r'profit.*potential'
            ],
            QueryIntent.SEASONAL_ADVICE.value: [
                r'season.*crop',
                r'planting.*time',
                r'growing.*season',
                r'seasonal.*advice',
                r'when.*plant',
                r'best.*time.*grow'
            ],
            QueryIntent.GREETING.value: [
                r'hello',
                r'hi',
                r'hey',
                r'good.*morning',
                r'good.*afternoon',
                r'good.*evening',
                r'greetings'
            ],
            QueryIntent.HELP.value: [
                r'help',
                r'what.*can.*do',
                r'how.*use',
                r'guide',
                r'assistance',
                r'support'
            ]
        }
    
    def _build_entity_patterns(self) -> Dict[str, str]:
        """Build entity extraction patterns."""
        return {
            'coordinates': r'(\d+\.?\d*)\s*°?[NS]?\s*,\s*(\d+\.?\d*)\s*°?[EW]?',
            'temperature': r'(\d+\.?\d*)\s*°?[CF]?',
            'ph': r'ph\s*(\d+\.?\d*)',
            'rainfall': r'(\d+\.?\d*)\s*mm',
            'area': r'(\d+\.?\d*)\s*acre'
        }
    
    def _load_crop_names(self) -> List[str]:
        """Load crop names from database."""
        # This would typically load from your crop database
        return [
            'wheat', 'rice', 'maize', 'soybean', 'cotton', 'sugarcane', 'potato',
            'onion', 'tomato', 'chilli', 'turmeric', 'ginger', 'garlic', 'mustard',
            'groundnut', 'sunflower', 'sorghum', 'millet', 'barley', 'oats',
            'pulses', 'lentil', 'chickpea', 'mungbean', 'pigeonpea'
        ]
    
    def _load_location_keywords(self) -> Dict[str, List[str]]:
        """Load location keywords."""
        return {
            'cities': [
                'mumbai', 'delhi', 'bangalore', 'hyderabad', 'ahmedabad', 'chennai',
                'kolkata', 'pune', 'jaipur', 'lucknow', 'kanpur', 'nagpur', 'indore',
                'thane', 'bhopal', 'visakhapatnam', 'pimpri', 'patna', 'vadodara'
            ],
            'states': [
                'maharashtra', 'karnataka', 'tamil nadu', 'west bengal', 'gujarat',
                'uttar pradesh', 'rajasthan', 'andhra pradesh', 'telangana', 'bihar',
                'madhya pradesh', 'punjab', 'haryana', 'kerala', 'odisha', 'assam',
                'jharkhand', 'chhattisgarh', 'himachal pradesh', 'uttarakhand'
            ]
        }
