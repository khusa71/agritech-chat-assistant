"""Chat models for conversational interface."""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class QueryIntent(str, Enum):
    """Query intent classification."""
    CROP_RECOMMENDATION = "crop_recommendation"
    WEATHER_INFO = "weather_info"
    SOIL_INFO = "soil_info"
    MARKET_PRICE = "market_price"
    CROP_REQUIREMENTS = "crop_requirements"
    LOCATION_ANALYSIS = "location_analysis"
    PROFITABILITY_ANALYSIS = "profitability_analysis"
    SEASONAL_ADVICE = "seasonal_advice"
    GENERAL_QUESTION = "general_question"
    GREETING = "greeting"
    HELP = "help"


class Message(BaseModel):
    """Individual message in conversation."""
    
    role: MessageRole = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now, description="Message timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional message metadata")


class ChatQuery(BaseModel):
    """User query with extracted information."""
    
    original_text: str = Field(..., description="Original user query text")
    intent: QueryIntent = Field(..., description="Classified intent of the query")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for intent classification")
    
    # Extracted entities
    location: Optional[Dict[str, Any]] = Field(None, description="Extracted location information")
    crop_name: Optional[str] = Field(None, description="Extracted crop name")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Extracted coordinates")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional extracted parameters")
    
    # Context
    conversation_context: List[Message] = Field(default_factory=list, description="Previous conversation context")


class ChatResponse(BaseModel):
    """Response to user query."""
    
    message: str = Field(..., description="Response message")
    intent: QueryIntent = Field(..., description="Responded intent")
    
    # Response data
    data: Optional[Dict[str, Any]] = Field(None, description="Structured response data")
    recommendations: Optional[List[Dict[str, Any]]] = Field(None, description="Crop recommendations if applicable")
    
    # Response metadata
    confidence: float = Field(..., ge=0.0, le=1.0, description="Response confidence")
    sources: List[str] = Field(default_factory=list, description="Data sources used")
    suggestions: List[str] = Field(default_factory=list, description="Follow-up suggestions")
    
    # Context for next interaction
    context_updates: Dict[str, Any] = Field(default_factory=dict, description="Context updates for next query")


class Conversation(BaseModel):
    """Complete conversation session."""
    
    session_id: str = Field(..., description="Unique session identifier")
    messages: List[Message] = Field(default_factory=list, description="All messages in conversation")
    context: Dict[str, Any] = Field(default_factory=dict, description="Conversation context")
    created_at: datetime = Field(default_factory=datetime.now, description="Conversation start time")
    last_updated: datetime = Field(default_factory=datetime.now, description="Last message timestamp")
    
    # User context
    user_location: Optional[Dict[str, Any]] = Field(None, description="User's location context")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    
    def add_message(self, message: Message):
        """Add message to conversation."""
        self.messages.append(message)
        self.last_updated = datetime.now()
    
    def get_recent_context(self, limit: int = 10) -> List[Message]:
        """Get recent messages for context."""
        return self.messages[-limit:] if self.messages else []
    
    def update_context(self, updates: Dict[str, Any]):
        """Update conversation context."""
        self.context.update(updates)


class ChatSession(BaseModel):
    """Chat session management."""
    
    session_id: str = Field(..., description="Session identifier")
    conversation: Conversation = Field(..., description="Conversation data")
    is_active: bool = Field(default=True, description="Whether session is active")
    
    def end_session(self):
        """End the chat session."""
        self.is_active = False
