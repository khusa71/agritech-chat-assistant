#!/usr/bin/env python3
"""Startup script for AgriTech Chat Assistant."""

import uvicorn
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

if __name__ == "__main__":
    print("🌾 Starting AgriTech Chat Assistant...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("💬 Chat Interface: http://localhost:8000")
    print("\nPress Ctrl+C to stop the server")
    
    uvicorn.run(
        "src.chat.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
