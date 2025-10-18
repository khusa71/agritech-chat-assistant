"""FastAPI backend for ChatGPT-style agricultural assistant."""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging
import uuid
from datetime import datetime

from .models import ChatQuery, ChatResponse, Message, MessageRole, Conversation, ChatSession
from .query_parser import QueryParser
from .response_generator import ResponseGenerator, ConversationContextManager

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AgriTech Chat Assistant",
    description="ChatGPT-style conversational interface for agricultural recommendations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
query_parser = QueryParser()
response_generator = ResponseGenerator()
context_manager = ConversationContextManager()

# In-memory session storage (use Redis/database in production)
sessions: Dict[str, ChatSession] = {}


# Pydantic models for API
class ChatMessageRequest(BaseModel):
    """Request model for chat message."""
    message: str
    session_id: Optional[str] = None
    coordinates: Optional[Dict[str, float]] = None


class ChatMessageResponse(BaseModel):
    """Response model for chat message."""
    message: str
    session_id: str
    response_data: Optional[Dict[str, Any]] = None
    suggestions: List[str] = []
    confidence: float
    sources: List[str] = []


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    created_at: datetime
    message_count: int
    is_active: bool


# API Endpoints

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the chat interface."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AgriTech Chat Assistant</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
                color: white;
                padding: 20px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 24px;
            }
            .header p {
                margin: 5px 0 0 0;
                opacity: 0.9;
            }
            .chat-container {
                height: 400px;
                overflow-y: auto;
                padding: 20px;
                background: #f8f9fa;
            }
            .message {
                margin-bottom: 15px;
                padding: 12px 16px;
                border-radius: 18px;
                max-width: 80%;
                word-wrap: break-word;
            }
            .user-message {
                background: #007bff;
                color: white;
                margin-left: auto;
                text-align: right;
            }
            .assistant-message {
                background: white;
                border: 1px solid #e9ecef;
                margin-right: auto;
            }
            .input-container {
                padding: 20px;
                background: white;
                border-top: 1px solid #e9ecef;
            }
            .input-group {
                display: flex;
                gap: 10px;
            }
            .input-group input {
                flex: 1;
                padding: 12px 16px;
                border: 1px solid #ddd;
                border-radius: 25px;
                font-size: 16px;
                outline: none;
            }
            .input-group input:focus {
                border-color: #4CAF50;
            }
            .input-group button {
                padding: 12px 24px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 600;
            }
            .input-group button:hover {
                background: #45a049;
            }
            .suggestions {
                margin-top: 10px;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }
            .suggestion {
                background: #e9ecef;
                padding: 6px 12px;
                border-radius: 15px;
                font-size: 14px;
                cursor: pointer;
                transition: background 0.2s;
            }
            .suggestion:hover {
                background: #dee2e6;
            }
            .loading {
                display: none;
                text-align: center;
                padding: 20px;
                color: #666;
            }
            .coordinates-input {
                margin-bottom: 10px;
                display: flex;
                gap: 10px;
            }
            .coordinates-input input {
                flex: 1;
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 15px;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌾 AgriTech Chat Assistant</h1>
                <p>Your AI agricultural advisor for crop recommendations, weather data, and farming insights</p>
            </div>
            
            <div class="chat-container" id="chatContainer">
                <div class="message assistant-message">
                    <strong>Welcome!</strong> I'm your agricultural assistant. I can help you with:<br>
                    • Crop recommendations<br>
                    • Weather and soil analysis<br>
                    • Market prices and profitability<br>
                    • Growing requirements and seasonal advice<br><br>
                    <strong>Try asking:</strong> "What crops should I grow?" or "Check weather for 18.5204, 73.8567"
                </div>
            </div>
            
            <div class="loading" id="loading">
                🤖 Thinking...
            </div>
            
            <div class="input-container">
                <div class="coordinates-input">
                    <input type="number" id="latitude" placeholder="Latitude (e.g., 18.5204)" step="any">
                    <input type="number" id="longitude" placeholder="Longitude (e.g., 73.8567)" step="any">
                </div>
                
                <div class="input-group">
                    <input type="text" id="messageInput" placeholder="Ask me anything about farming..." autocomplete="off">
                    <button onclick="sendMessage()">Send</button>
                </div>
                
                <div class="suggestions" id="suggestions">
                    <div class="suggestion" onclick="setMessage('What crops should I grow?')">🌾 Crop Recommendations</div>
                    <div class="suggestion" onclick="setMessage('What is the weather like?')">🌤️ Weather Info</div>
                    <div class="suggestion" onclick="setMessage('Check soil conditions')">🌱 Soil Analysis</div>
                    <div class="suggestion" onclick="setMessage('What are current crop prices?')">💰 Market Prices</div>
                </div>
            </div>
        </div>

        <script>
            let sessionId = null;
            
            function setMessage(message) {
                document.getElementById('messageInput').value = message;
            }
            
            function addMessage(content, isUser = false) {
                const chatContainer = document.getElementById('chatContainer');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
                messageDiv.innerHTML = content.replace(/\\n/g, '<br>');
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            function showSuggestions(suggestions) {
                const suggestionsDiv = document.getElementById('suggestions');
                suggestionsDiv.innerHTML = '';
                suggestions.forEach(suggestion => {
                    const suggestionDiv = document.createElement('div');
                    suggestionDiv.className = 'suggestion';
                    suggestionDiv.textContent = suggestion;
                    suggestionDiv.onclick = () => setMessage(suggestion);
                    suggestionsDiv.appendChild(suggestionDiv);
                });
            }
            
            async function sendMessage() {
                const messageInput = document.getElementById('messageInput');
                const latitudeInput = document.getElementById('latitude');
                const longitudeInput = document.getElementById('longitude');
                const loading = document.getElementById('loading');
                
                const message = messageInput.value.trim();
                if (!message) return;
                
                // Add user message
                addMessage(message, true);
                messageInput.value = '';
                
                // Show loading
                loading.style.display = 'block';
                
                try {
                    const requestBody = {
                        message: message,
                        session_id: sessionId
                    };
                    
                    // Add coordinates if provided
                    if (latitudeInput.value && longitudeInput.value) {
                        requestBody.coordinates = {
                            latitude: parseFloat(latitudeInput.value),
                            longitude: parseFloat(longitudeInput.value)
                        };
                    }
                    
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(requestBody)
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        // Update session ID
                        sessionId = data.session_id;
                        
                        // Add assistant response
                        addMessage(data.message);
                        
                        // Show suggestions
                        if (data.suggestions && data.suggestions.length > 0) {
                            showSuggestions(data.suggestions);
                        }
                    } else {
                        addMessage(`Error: ${data.detail || 'Something went wrong'}`);
                    }
                } catch (error) {
                    addMessage(`Error: ${error.message}`);
                } finally {
                    loading.style.display = 'none';
                }
            }
            
            // Allow Enter key to send message
            document.getElementById('messageInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
        </script>
    </body>
    </html>
    """


@app.post("/chat", response_model=ChatMessageResponse)
async def chat(request: ChatMessageRequest):
    """Main chat endpoint."""
    try:
        logger.info(f"Received chat request: {request.message[:100]}...")
        
        # Get or create session
        session_id = request.session_id or str(uuid.uuid4())
        if session_id not in sessions:
            sessions[session_id] = ChatSession(
                session_id=session_id,
                conversation=Conversation(session_id=session_id)
            )
        
        session = sessions[session_id]
        
        # Add user message to conversation
        user_message = Message(
            role=MessageRole.USER,
            content=request.message
        )
        session.conversation.add_message(user_message)
        
        # Parse query
        query = query_parser.parse_query(
            request.message,
            session.conversation.get_recent_context()
        )
        
        # Add coordinates if provided
        if request.coordinates:
            query.coordinates = request.coordinates
        
        # Generate response
        response = await response_generator.generate_response(query)
        
        # Add assistant message to conversation
        assistant_message = Message(
            role=MessageRole.ASSISTANT,
            content=response.message
        )
        session.conversation.add_message(assistant_message)
        
        # Update context
        if response.context_updates:
            context_manager.update_context(session_id, response.context_updates)
        
        logger.info(f"Generated response for session {session_id}")
        
        return ChatMessageResponse(
            message=response.message,
            session_id=session_id,
            response_data=response.data,
            suggestions=response.suggestions,
            confidence=response.confidence,
            sources=response.sources
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session information."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return SessionInfo(
        session_id=session_id,
        created_at=session.conversation.created_at,
        message_count=len(session.conversation.messages),
        is_active=session.is_active
    )


@app.get("/sessions")
async def list_sessions():
    """List all active sessions."""
    return [
        SessionInfo(
            session_id=session_id,
            created_at=session.conversation.created_at,
            message_count=len(session.conversation.messages),
            is_active=session.is_active
        )
        for session_id, session in sessions.items()
    ]


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del sessions[session_id]
    context_manager.clear_context(session_id)
    
    return {"message": "Session deleted successfully"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "active_sessions": len(sessions)
    }


@app.get("/crops")
async def list_crops():
    """List available crops."""
    try:
        crops = response_generator.crop_database.get_all_crops()
        return {"crops": crops}
    except Exception as e:
        logger.error(f"Error listing crops: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/crops/{crop_name}")
async def get_crop_info(crop_name: str):
    """Get crop information."""
    try:
        requirements = response_generator.crop_database.get_crop_requirements(crop_name)
        if not requirements:
            raise HTTPException(status_code=404, detail="Crop not found")
        
        return {"crop": requirements.dict()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting crop info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
