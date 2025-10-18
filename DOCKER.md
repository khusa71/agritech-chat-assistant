# AgriTech Chat Assistant - Docker Setup

## Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (FastAPI server)
CMD ["python", "start_chat_server.py"]
```

## Docker Compose

```yaml
version: '3.8'

services:
  agritech-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  agritech-streamlit:
    build: .
    ports:
      - "8501:8501"
    command: ["streamlit", "run", "streamlit_app_fixed.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
    depends_on:
      - agritech-api
    environment:
      - API_URL=http://agritech-api:8000

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

## Build and Run

```bash
# Build the image
docker build -t agritech-chat-assistant .

# Run with Docker Compose
docker-compose up -d

# Or run individual containers
docker run -p 8000:8000 agritech-chat-assistant
docker run -p 8501:8501 agritech-chat-assistant streamlit run streamlit_app_fixed.py --server.port 8501 --server.address 0.0.0.0
```

## Production Deployment

For production deployment, consider:

1. **Load Balancer**: Use nginx or similar
2. **Database**: Use PostgreSQL with persistent volumes
3. **Caching**: Use Redis for session management
4. **Monitoring**: Add Prometheus/Grafana
5. **Logging**: Use structured logging with ELK stack
6. **Security**: Add authentication and rate limiting
