# Customer Service Voice Agent - Complete System

## Production-Ready Inbound & Outbound Call Handling with LiveKit Cloud + Google Gemini AI

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![LiveKit](https://img.shields.io/badge/LiveKit-Cloud-green.svg)](https://livekit.io/)
[![Gemini](https://img.shields.io/badge/Google-Gemini%202.0-orange.svg)](https://ai.google.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12%2B-blue.svg)](https://www.postgresql.org/)

---

## Overview

This is a **production-ready** customer service voice agent system that handles both **inbound and outbound calls** using:

- **LiveKit Cloud** for real-time voice infrastructure and SIP integration
- **Google Gemini 2.0 Flash** for AI-powered conversations
- **PostgreSQL** for customer data and call records
- **FastAPI** for REST API management
- **Advanced Features**: Queue management, sentiment analysis, call transfers, transcripts

### Key Features

✅ **Inbound Calls** - Automatic AI agent answers incoming calls  
✅ **Outbound Calls** - Programmatic call initiation via API  
✅ **Smart Routing** - Queue management and priority handling  
✅ **Real-time Transcription** - Live speech-to-text for all calls  
✅ **Sentiment Analysis** - Detect customer frustration and escalate  
✅ **Call Transfers** - Seamless handoff to human agents  
✅ **Customer History** - Context-aware conversations with returning customers  
✅ **Production Ready** - No emojis, comprehensive error handling, logging  

---

## Quick Start

### 1. Prerequisites

```bash
# Required
- Python 3.9+
- PostgreSQL 12+
- LiveKit Cloud account with SIP enabled
- Google Gemini API key

# Your LiveKit Configuration (from screenshot)
Inbound Trunk ID: ST_UE2fnCs4yxSo
Outbound Trunk ID: ST_SXWwu7ArVEYE
Phone Number: +15183171307
```

### 2. Installation

```bash
# Clone repository
git clone <your-repo>
cd customer-service-voice-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required .env variables:**
```bash
# LiveKit Configuration
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxx

# SIP Trunks (from your LiveKit setup)
DEFAULT_INBOUND_TRUNK_ID=ST_UE2fnCs4yxSo
DEFAULT_OUTBOUND_TRUNK_ID=ST_SXWwu7ArVEYE
DEFAULT_CALLER_ID=+15183171307

# Google Gemini
GOOGLE_API_KEY=AIzaSyxxxxxxxxxx

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/customerservice

# API Security
API_SECRET_KEY=<generate-with-openssl-rand-hex-32>
```

### 4. Database Setup

```bash
# Run setup script
chmod +x setup.sh
./setup.sh

# Or manually
createdb customerservice
psql customerservice < database/schema.sql
```

### 5. Start Services

```bash
# Terminal 1: Start AI Agent
python app/agents/gemini_agent.py dev

# Terminal 2: Start API Server
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3: Start Queue Processor (optional)
python workers/queue_processor.py
```

### 6. Test It!

**Test Inbound Call:**
```bash
# Call your LiveKit number
Call: +15183171307
```

**Test Outbound Call:**
```bash
curl -X POST http://localhost:8000/api/v1/calls/outbound/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_SECRET_KEY" \
  -d '{
    "to_number": "+1234567890",
    "metadata": {"test": true}
  }'
```

---

## Documentation

📚 **[Complete Setup Guide](SETUP_GUIDE.md)** - Step-by-step installation and configuration  
📖 **[API Reference](API_REFERENCE.md)** - Complete API documentation with examples  
📋 **[Deployment Checklist](DEPLOYMENT_CHECKLIST.md)** - Pre-deployment verification  
📝 **[Update Summary](UPDATE_SUMMARY.md)** - What changed in this production version  

---

## System Architecture

```
┌─────────────────┐
│  Inbound Call   │  +15183171307
│  (Customer)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LiveKit SIP    │  ST_UE2fnCs4yxSo
│  Inbound Trunk  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Dispatch Rules  │  Routes to Room
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────┐
│  LiveKit Room   │◄─────►│  Gemini AI   │
│                 │       │  Agent       │
└────────┬────────┘       └──────────────┘
         │
         ▼
┌─────────────────┐
│   PostgreSQL    │  Customer Data
│   Database      │  Call Records
└─────────────────┘


┌─────────────────┐
│  API Request    │  Create Outbound Call
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI        │  /calls/outbound/create
│  Backend        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LiveKit SIP    │  ST_SXWwu7ArVEYE
│  Outbound Trunk │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Outbound Call  │  Customer receives call
│  (Customer)     │
└─────────────────┘
```

---

## API Endpoints

### Inbound Call Management
```
GET  /calls/inbound/active          - List active inbound calls
GET  /calls/inbound/{session_id}    - Get inbound call details
```

### Outbound Call Management
```
POST /calls/outbound/create         - Create outbound call
POST /calls/outbound/callback       - Schedule callback
POST /calls/outbound/batch          - Create multiple calls
GET  /calls/outbound/active         - List active outbound calls
```

### Common Operations
```
GET  /calls/all/active              - List all active calls
GET  /calls/{session_id}/transcript - Get call transcript
POST /calls/{session_id}/transfer   - Transfer to human agent
```

### Queue & Analytics
```
GET  /queue/status                  - Queue statistics
GET  /analytics/realtime            - Real-time metrics
GET  /analytics/calls               - Call analytics
```

See [API_REFERENCE.md](API_REFERENCE.md) for complete documentation.

---

## File Structure

```
customer-service-voice-agent/
├── app/
│   ├── agents/
│   │   └── gemini_agent.py              # Main AI agent (UPDATED)
│   ├── services/
│   │   ├── customer_service.py          # Customer management
│   │   ├── queue_manager.py             # Queue system (UPDATED)
│   │   ├── transcript_service.py        # Transcription
│   │   └── sentiment_analyzer.py        # Sentiment analysis
│   ├── sip/
│   │   ├── trunk_manager.py             # SIP trunk ops (UPDATED)
│   │   ├── dispatch_rules.py            # Call routing (UPDATED)
│   │   └── outbound_call_manager.py     # Outbound calls (NEW)
│   ├── api/
│   │   └── routes/
│   │       └── calls.py                 # API endpoints (UPDATED)
│   └── tools/
│       ├── account_tools.py             # Account functions
│       ├── scheduling_tools.py          # Scheduling
│       └── knowledge_base.py            # Knowledge search
├── config/
│   ├── settings.py                      # Configuration (UPDATED)
│   ├── database.py                      # DB connection
│   └── livekit_config.py                # LiveKit setup
├── database/
│   └── schema.sql                       # Database schema
├── workers/
│   └── queue_processor.py               # Background queue worker
├── logs/                                # Application logs
├── .env                                 # Environment config
├── requirements.txt                     # Python dependencies
├── setup.sh                             # Setup script
├── README.md                            # This file
├── SETUP_GUIDE.md                       # Complete setup guide
├── API_REFERENCE.md                     # API documentation
├── DEPLOYMENT_CHECKLIST.md              # Deployment checklist
└── UPDATE_SUMMARY.md                    # Update details
```

---

## Production Deployment

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f agent
docker-compose logs -f api
```

### Systemd Deployment

```bash
# Copy service files
sudo cp systemd/*.service /etc/systemd/system/

# Enable and start
sudo systemctl enable voice-agent
sudo systemctl enable voice-api
sudo systemctl start voice-agent
sudo systemctl start voice-api

# Check status
sudo systemctl status voice-agent
sudo systemctl status voice-api
```

---

## Monitoring & Logging

### View Logs
```bash
# Agent logs
tail -f logs/agent.log

# API logs
tail -f logs/api.log

# Filter errors
grep ERROR logs/agent.log

# Follow specific session
grep "session_id=123" logs/agent.log
```

### Metrics
```bash
# Get real-time metrics
curl http://localhost:8000/api/v1/analytics/realtime \
  -H "Authorization: Bearer YOUR_API_KEY"

# Queue status
curl http://localhost:8000/api/v1/queue/status \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Troubleshooting

### Common Issues

**Issue:** Inbound calls not connecting
```bash
# Check dispatch rules
curl http://localhost:8000/api/v1/sip/dispatch-rules \
  -H "Authorization: Bearer YOUR_API_KEY"

# Verify trunk ID matches
echo $DEFAULT_INBOUND_TRUNK_ID
```

**Issue:** Outbound calls fail
```bash
# Verify trunk configuration
curl http://localhost:8000/api/v1/sip/trunks \
  -H "Authorization: Bearer YOUR_API_KEY"

# Check caller ID is valid
echo $DEFAULT_CALLER_ID
```

**Issue:** Agent not responding
```bash
# Check agent logs
tail -f logs/agent.log

# Verify Gemini API
python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print('OK')"

# Test database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM customers;"
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for more troubleshooting tips.

---

## Features in Detail

### Inbound Call Flow
1. Customer calls your LiveKit number (+15183171307)
2. SIP trunk receives call
3. Dispatch rule routes to LiveKit room
4. AI agent automatically joins room
5. Agent greets customer (personalized for new/returning)
6. Conversation with Gemini AI
7. Transcript and sentiment saved in real-time
8. Transfer to human if needed
9. Call completion recorded

### Outbound Call Flow
1. API request to create outbound call
2. System validates phone number and trunk
3. LiveKit creates SIP participant
4. Call placed to customer
5. When answered, AI agent starts conversation
6. Same features as inbound (transcript, sentiment, transfer)
7. Call tracked in database

### Smart Features
- **Customer Recognition**: Returning customers get personalized greetings
- **Sentiment Tracking**: Real-time emotion analysis with escalation
- **Priority Queue**: VIP customers get faster service
- **Call Transfers**: Warm or cold transfer to human agents
- **Knowledge Base**: AI searches documentation for answers
- **Account Integration**: Check balance, transactions, update info

---

## What's New in This Version


 Full outbound call support added  
 Enhanced error handling with stack traces  
 Improved logging across all files  
 Comprehensive documentation  
 Database schema for outbound calls  
 Batch call operations  
 Setup automation script  

See [UPDATE_SUMMARY.md](UPDATE_SUMMARY.md) for complete details.

---

## Configuration Reference

### Your LiveKit Setup (from screenshot)

**Inbound Trunk:**
- ID: `ST_UE2fnCs4yxSo`
- Name: My inbound trunk AgnoX
- Number: +15183171307

**Outbound Trunk:**
- ID: `ST_SXWwu7ArVEYE`
- Name: My outbound trunk AgnoX
- Address: 5njkgqf8llp.sip.livekit.cloud
- Transport: AUTO
- Number: +15183171307

Make sure these values are in your `.env` file!

---

## Testing

### Run Tests
```bash
# All tests
pytest

# Specific test file
pytest tests/test_agents/test_gemini_agent.py

# With coverage
pytest --cov=app tests/
```

### Manual Testing
```bash
# Test inbound: Call +15183171307
# Test outbound: Use API endpoint
# Test transfer: Request human during call
# Test queue: Make multiple simultaneous calls
```

---

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## License

This project is licensed under the MIT License - see LICENSE file for details.

---

## Support

- 📧 Email: support@yourcompany.com
- 📖 Documentation: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- 🐛 Issues: GitHub Issues
- 💬 Chat: Slack #voice-agent

---

## Acknowledgments

- **LiveKit** for amazing real-time infrastructure
- **Google** for Gemini AI API
- **PostgreSQL** for reliable data storage
- **FastAPI** for excellent API framework

---

## Roadmap

- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Call recording with storage
- [ ] WhatsApp integration
- [ ] SMS notifications
- [ ] CRM integrations
- [ ] Machine learning for intent detection
- [ ] Voice cloning options

---

**Ready to deploy? Check the [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)!**