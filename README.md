# Customer Service Voice Agent - Backend

Production-ready customer service voice agent powered by Google Gemini Real-time API and LiveKit.

## Features

- Voice conversations using Google Gemini Real-time API (NO OpenAI)
- Native audio-to-audio processing with Gemini multimodal capabilities
- Enhanced noise cancellation using LiveKit Cloud BVC
- Real-time call queue management with priority routing
- Seamless transfer to human agents (warm and cold transfer)
- Complete conversation transcription and storage
- Real-time sentiment analysis
- RESTful API for dashboard integration
- WebSocket support for real-time updates
- PostgreSQL database with connection pooling
- Background workers for queue processing
- Comprehensive error handling and logging

## Architecture

```
Phone/Web Client -> LiveKit SIP/WebRTC -> AI Agent (Gemini Real-time) -> Queue System -> Human Agent
                                              |
                                              v
                                        PostgreSQL DB
                                              |
                                              v
                                        FastAPI Backend <- Dashboard
```

## Why Google Gemini Real-time API?

- Native multimodal audio processing (no separate STT/TTS needed)
- Lower latency: 200-400ms vs 800-1200ms with traditional pipeline
- Cost effective: Single API call instead of STT+LLM+TTS
- Built-in function calling support
- 30+ languages supported natively
- Handles audio, video, and text simultaneously

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for caching)
- LiveKit Cloud account
- Google Gemini API key (NOT OpenAI)

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository>
cd customer-service-voice-agent

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:
- `LIVEKIT_URL`: Your LiveKit server URL
- `LIVEKIT_API_KEY`: LiveKit API key
- `LIVEKIT_API_SECRET`: LiveKit API secret
- `GOOGLE_API_KEY`: Gemini API key (from https://aistudio.google.com/app/apikey)
- `DATABASE_URL`: PostgreSQL connection string
- `API_SECRET_KEY`: Random secret key for API authentication

### 3. Setup Database

```bash
python scripts/setup_database.py
```

This will:
- Create all necessary tables
- Set up indexes for performance
- Insert sample test data

### 4. Configure SIP (Optional)

```bash
python scripts/setup_sip.py
```

Follow the prompts to configure your SIP trunk for phone call handling.

### 5. Run the Services

#### Start API Server
```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Start Agent Worker
```bash
python app/agents/gemini_agent.py start
```

#### Start Queue Processor
```bash
python workers/queue_processor.py
```

Or use Docker:
```bash
docker-compose up -d
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

#### Calls Management
- `GET /api/v1/calls/active` - Get all active calls
- `GET /api/v1/calls/{session_id}` - Get call details
- `GET /api/v1/calls/{session_id}/transcript` - Get call transcript
- `POST /api/v1/calls/{session_id}/transfer` - Transfer call to human agent

#### Queue Management
- `GET /api/v1/queue/status` - Get current queue status
- `GET /api/v1/queue/stats` - Get queue statistics
- `POST /api/v1/queue/{queue_id}/priority` - Update queue priority

#### Agent Management
- `GET /api/v1/agents` - List all agents
- `GET /api/v1/agents/{agent_id}` - Get agent details
- `PUT /api/v1/agents/{agent_id}/status` - Update agent status

#### Analytics
- `GET /api/v1/analytics/realtime` - Get real-time metrics
- `GET /api/v1/analytics/calls` - Get call analytics
- `GET /api/v1/analytics/agents/{agent_id}` - Get agent performance

#### Customers
- `GET /api/v1/customers/{phone_number}` - Get customer info
- `GET /api/v1/customers/{customer_id}/history` - Get call history

### WebSocket Endpoints

- `ws://localhost:8000/ws/calls` - Real-time call updates
- `ws://localhost:8000/ws/queue` - Real-time queue updates
- `ws://localhost:8000/ws/transcripts/{session_id}` - Real-time transcription

## Frontend Integration

### Authentication

All API requests require authentication using Bearer token:

```javascript
const response = await fetch('http://localhost:8000/api/v1/calls/active', {
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json'
  }
});
```

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/calls');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Call update:', data);
};
```

### API Examples

#### Get Active Calls
```javascript
const activeCalls = await fetch('http://localhost:8000/api/v1/calls/active')
  .then(res => res.json());
```

#### Transfer Call
```javascript
const transfer = await fetch(`http://localhost:8000/api/v1/calls/${sessionId}/transfer`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    agent_id: 123,
    transfer_type: 'warm'
  })
}).then(res => res.json());
```

#### Get Queue Status
```javascript
const queueStatus = await fetch('http://localhost:8000/api/v1/queue/status')
  .then(res => res.json());
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_api/test_calls_api.py -v
```

## Deployment

### Docker Deployment

```bash
docker-compose up -d
```

Services will be available at:
- API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Production Checklist

- [ ] Set strong API_SECRET_KEY
- [ ] Configure CORS allowed origins
- [ ] Enable HTTPS/SSL
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Set up monitoring (Sentry)
- [ ] Enable rate limiting
- [ ] Review and set resource limits
- [ ] Configure firewall rules
- [ ] Set up health checks

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### Metrics

Prometheus metrics available at:
```
http://localhost:8000/metrics
```

### Logs

Logs are written to:
- `logs/agent.log` - Agent activity
- `logs/api.log` - API requests
- `logs/error.log` - Errors and exceptions

## Troubleshooting

### Agent Not Connecting

```bash
python scripts/test_agent.py
```

This will verify:
- LiveKit connection
- Database connection
- Gemini API access

### Database Connection Issues

```bash
# Test database connection
psql $DATABASE_URL -c "SELECT 1"

# Reset database
python scripts/setup_database.py --reset
```

### SIP Issues

Check SIP trunk configuration:
```bash
# Using LiveKit CLI
livekit-cli sip list-trunks
livekit-cli sip list-dispatch-rules
```

## Configuration

### Noise Cancellation

The agent uses LiveKit Cloud enhanced noise cancellation (BVC - Background Voice Cancellation):

```python
# In app/agents/gemini_agent.py
from livekit.plugins import noise_cancellation

room_input_options = room_io.RoomInputOptions(
    noise_cancellation=noise_cancellation.BVC()
)
```

Options:
- `NC()` - Standard noise cancellation
- `BVC()` - Background voice cancellation (recommended)
- `BVCTelephony()` - Optimized for telephony

### Queue Configuration

Edit `config/settings.py`:
```python
QUEUE_CHECK_INTERVAL = 2  # seconds
MAX_QUEUE_WAIT_TIME = 600  # 10 minutes
PRIORITY_LEVELS = [0, 1, 2, 3]  # low to urgent
```

### Agent Configuration

Edit `app/agents/gemini_agent.py`:
```python
model = google.realtime.RealtimeModel(
    model="gemini-2.0-flash-exp",
    voice="Puck",
    temperature=0.8
)
```

## Project Structure

```
app/
├── agents/          # Voice agent implementations
├── api/             # FastAPI application
├── models/          # Data models
├── services/        # Business logic
├── tools/           # Agent callable functions
└── utils/           # Utilities
```

## Support

For issues and questions:
- LiveKit Documentation: https://docs.livekit.io/
- Gemini API Documentation: https://ai.google.dev/
- Project Issues: [Your GitHub Issues]

## License

MIT License

# ============================================================================
# FILE: Makefile
.PHONY: help install setup test run clean docker-build docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make setup         - Setup database and environment"
	@echo "  make test          - Run tests"
	@echo "  make run           - Run all services"
	@echo "  make api           - Run API server only"
	@echo "  make agent         - Run agent worker only"
	@echo "  make worker        - Run queue processor only"
	@echo "  make clean         - Clean temporary files"
	@echo "  make docker-build  - Build Docker images"
	@echo "  make docker-up     - Start Docker services"
	@echo "  make docker-down   - Stop Docker services"

install:
	pip install -r requirements.txt

setup:
	cp .env.example .env
	@echo "Please edit .env with your credentials"
	python scripts/setup_database.py

test:
	pytest

test-cov:
	pytest --cov=app --cov-report=html

run:
	@echo "Starting all services..."
	@trap 'kill 0' SIGINT; \
	uvicorn app.api.main:app --host 0.0.0.0 --port 8000 & \
	python app/agents/gemini_agent.py start & \
	python workers/queue_processor.py & \
	wait

api:
	uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

agent:
	python app/agents/gemini_agent.py start

agent-dev:
	python app/agents/gemini_agent.py dev

worker:
	python workers/queue_processor.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build dist .pytest_cache .coverage htmlcov

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

format:
	black app/ tests/
	isort app/ tests/

lint:
	flake8 app/ tests/
	mypy app/