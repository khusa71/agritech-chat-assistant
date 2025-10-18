"""Simplified Streamlit application for AgriTech Chat Assistant."""

import streamlit as st
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.chat.query_parser import QueryParser
from src.chat.response_generator import ResponseGenerator
from src.chat.models import ChatQuery, Message, MessageRole, Conversation

# Configure Streamlit
st.set_page_config(
    page_title="AgriTech Chat Assistant",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def get_components():
    """Get cached components."""
    return QueryParser(), ResponseGenerator()

query_parser, response_generator = get_components()

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #4CAF50;
    }
    
    .user-message {
        background-color: #e8f5e8;
        border-left-color: #4CAF50;
    }
    
    .assistant-message {
        background-color: #f0f8ff;
        border-left-color: #2196F3;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 20px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    
    .stButton > button:hover {
        background-color: #45a049;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🌾 AgriTech Chat Assistant</h1>
    <p>Your AI agricultural advisor for crop recommendations, weather data, and farming insights</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("🔧 Settings")
    
    # Location Input
    st.subheader("📍 Location")
    col1, col2 = st.columns(2)
    with col1:
        latitude = st.number_input("Latitude", value=18.5204, format="%.4f", key="lat_input")
    with col2:
        longitude = st.number_input("Longitude", value=73.8567, format="%.4f", key="lon_input")
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    
    if st.button("🌾 Crop Recommendations", key="btn_crops"):
        st.session_state.pending_query = "What crops should I grow?"
    
    if st.button("🌤️ Weather Info", key="btn_weather"):
        st.session_state.pending_query = "What's the weather like?"
    
    if st.button("🌱 Soil Analysis", key="btn_soil"):
        st.session_state.pending_query = "Analyze soil conditions"
    
    if st.button("💰 Market Prices", key="btn_prices"):
        st.session_state.pending_query = "Check market prices"
    
    # Debug Options
    st.subheader("🐛 Debug")
    show_debug = st.checkbox("Show Debug Info", value=False, key="debug_checkbox")
    
    # Clear Chat
    if st.button("🗑️ Clear Chat", key="btn_clear"):
        st.session_state.messages = []
        st.session_state.conversation = Conversation(session_id="streamlit_session")
        st.rerun()

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation" not in st.session_state:
    st.session_state.conversation = Conversation(session_id="streamlit_session")

# Main chat interface
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Chat Interface")
    
    # Display chat messages
    for i, message in enumerate(st.session_state.messages):
        with st.container():
            if message["role"] == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong>👤 You:</strong><br>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message assistant-message">
                    <strong>🤖 Assistant:</strong><br>
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
                
                # Show suggestions if available (with unique keys)
                if "suggestions" in message and message["suggestions"]:
                    st.markdown("**💡 Suggestions:**")
                    cols = st.columns(len(message["suggestions"]))
                    for j, suggestion in enumerate(message["suggestions"]):
                        with cols[j]:
                            if st.button(suggestion, key=f"suggestion_{i}_{j}_{len(suggestion)}"):
                                st.session_state.pending_query = suggestion
    
    # Chat input
    user_input = st.text_input(
        "Ask me anything about farming...",
        key="main_input",
        placeholder="e.g., What crops should I grow? How to grow wheat?"
    )
    
    # Handle pending query from sidebar or suggestions
    if hasattr(st.session_state, 'pending_query'):
        user_input = st.session_state.pending_query
        delattr(st.session_state, 'pending_query')
    
    col_send, col_clear = st.columns([1, 1])
    with col_send:
        send_button = st.button("Send", type="primary", key="btn_send")
    with col_clear:
        clear_button = st.button("Clear Input", key="btn_clear_input")

with col2:
    st.subheader("📊 System Status")
    
    # Metrics
    col_metrics1, col_metrics2 = st.columns(2)
    with col_metrics1:
        st.metric("Messages", len(st.session_state.messages))
        st.metric("Session", "Active")
    
    with col_metrics2:
        st.metric("Location", f"{latitude:.4f}, {longitude:.4f}")
        st.metric("Status", "🟢 Ready")
    
    # Debug Information
    if show_debug and st.session_state.messages:
        st.subheader("🐛 Debug Info")
        last_message = st.session_state.messages[-1]
        if "debug_info" in last_message:
            st.json(last_message["debug_info"])

# Process user input
if send_button and user_input:
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })
    
    # Process query
    with st.spinner("🤖 Thinking..."):
        try:
            # Parse query
            query = query_parser.parse_query(
                user_input,
                st.session_state.conversation.get_recent_context()
            )
            
            # Add coordinates
            query.coordinates = {"latitude": latitude, "longitude": longitude}
            
            # Generate response (run async function)
            response = asyncio.run(response_generator.generate_response(query))
            
            # Add assistant message
            assistant_message = {
                "role": "assistant",
                "content": response.message,
                "timestamp": datetime.now().isoformat(),
                "suggestions": response.suggestions,
                "confidence": response.confidence,
                "sources": response.sources
            }
            
            # Add debug info if enabled
            if show_debug:
                assistant_message["debug_info"] = {
                    "intent": response.intent.value,
                    "confidence": response.confidence,
                    "sources": response.sources,
                    "query_parsed": {
                        "intent": query.intent.value,
                        "confidence": query.confidence,
                        "crop_name": query.crop_name,
                        "coordinates": query.coordinates
                    }
                }
            
            st.session_state.messages.append(assistant_message)
            
            # Update conversation context
            user_msg = Message(role=MessageRole.USER, content=user_input)
            assistant_msg = Message(role=MessageRole.ASSISTANT, content=response.message)
            st.session_state.conversation.add_message(user_msg)
            st.session_state.conversation.add_message(assistant_msg)
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"I encountered an error: {str(e)}. Please try again.",
                "timestamp": datetime.now().isoformat()
            })
    
    # Clear input by rerunning
    st.rerun()

# Clear input
if clear_button:
    st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🌾 AgriTech Chat Assistant - Development Version</p>
    <p>Built with Streamlit • Powered by AI • Real Agricultural Data</p>
</div>
""", unsafe_allow_html=True)
