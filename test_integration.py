#!/usr/bin/env python3
"""Test script to verify ChatGPT-style agricultural assistant functionality."""

import requests
import json
import time

def test_fastapi_chat():
    """Test the FastAPI chat endpoint."""
    print("🧪 Testing FastAPI Chat Endpoint...")
    
    test_queries = [
        {
            "message": "What crops should I grow?",
            "coordinates": {"latitude": 18.5204, "longitude": 73.8567}
        },
        {
            "message": "What's the weather like?",
            "coordinates": {"latitude": 12.9716, "longitude": 77.5946}
        },
        {
            "message": "How to grow wheat?",
            "coordinates": {"latitude": 28.7041, "longitude": 77.1025}
        },
        {
            "message": "Check market prices",
            "coordinates": {"latitude": 19.0760, "longitude": 72.8777}
        }
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {query['message']}")
        print(f"📍 Location: {query['coordinates']['latitude']}, {query['coordinates']['longitude']}")
        
        try:
            response = requests.post(
                "http://localhost:8000/chat",
                json=query,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success!")
                print(f"   Response: {data['message'][:100]}...")
                print(f"   Confidence: {data['confidence']:.2f}")
                print(f"   Suggestions: {len(data['suggestions'])} provided")
                print(f"   Sources: {', '.join(data['sources'])}")
            else:
                print(f"❌ Error: HTTP {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(1)  # Small delay between requests

def test_health_endpoints():
    """Test health endpoints."""
    print("\n🏥 Testing Health Endpoints...")
    
    endpoints = [
        ("FastAPI Health", "http://localhost:8000/health"),
        ("FastAPI Sessions", "http://localhost:8000/sessions"),
        ("Streamlit", "http://localhost:8501")
    ]
    
    for name, url in endpoints:
        try:
            if "streamlit" in url.lower():
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"✅ {name}: Running")
                else:
                    print(f"❌ {name}: HTTP {response.status_code}")
            else:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ {name}: {data.get('status', 'OK')}")
                else:
                    print(f"❌ {name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: {e}")

def test_api_endpoints():
    """Test additional API endpoints."""
    print("\n🔗 Testing Additional API Endpoints...")
    
    endpoints = [
        ("Crops List", "http://localhost:8000/crops"),
        ("Wheat Info", "http://localhost:8000/crops/wheat"),
        ("Rice Info", "http://localhost:8000/crops/rice")
    ]
    
    for name, url in endpoints:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {name}: Success")
                if 'crops' in data:
                    print(f"   Available crops: {len(data['crops'])}")
                elif 'crop' in data:
                    print(f"   Crop: {data['crop']['crop_name']}")
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: {e}")

def main():
    """Run all tests."""
    print("🚀 Starting AgriTech Chat Assistant Tests")
    print("=" * 50)
    
    # Test health endpoints first
    test_health_endpoints()
    
    # Test API endpoints
    test_api_endpoints()
    
    # Test chat functionality
    test_fastapi_chat()
    
    print("\n" + "=" * 50)
    print("🎉 Testing Complete!")
    print("\n📱 Access your applications:")
    print("   • Streamlit Development: http://localhost:8501")
    print("   • FastAPI Production: http://localhost:8000")
    print("   • API Documentation: http://localhost:8000/docs")
    print("   • Web Chat Interface: http://localhost:8000")
    
    print("\n🎯 Try these queries:")
    print("   • 'What crops should I grow?'")
    print("   • 'What's the weather like?'")
    print("   • 'How to grow wheat?'")
    print("   • 'Check market prices'")

if __name__ == "__main__":
    main()
