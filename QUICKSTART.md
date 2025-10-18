# AgriTech Chat Assistant

A production-ready ChatGPT-style conversational interface for agricultural recommendations.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the FastAPI server:
   ```bash
   python start_chat_server.py
   ```

3. Start the Streamlit interface (in another terminal):
   ```bash
   streamlit run streamlit_app_fixed.py --server.port 8501
   ```

4. Access the applications:
   - Streamlit: http://localhost:8501
   - FastAPI: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Features

- Natural language processing for agricultural queries
- Real-time weather, soil, and market data
- Intelligent crop recommendations
- Context-aware conversations
- Multiple interfaces (Streamlit + FastAPI)

## API Usage

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What crops should I grow?",
    "coordinates": {"latitude": 18.5204, "longitude": 73.8567}
  }'
```

## Testing

Run integration tests:
```bash
python test_integration.py
```

## License

MIT License - see LICENSE file for details.
