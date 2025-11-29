# API Reference - Customer Service Voice Agent

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer YOUR_API_SECRET_KEY
```

---

## Inbound Call Endpoints

### Get Active Inbound Calls
```http
GET /calls/inbound/active?page=1&page_size=50
```

**Response:**
```json
{
  "calls": [
    {
      "session_id": 123,
      "customer_id": 456,
      "room_name": "call-abc123",
      "start_time": "2025-01-15T10:30:00Z",
      "end_time": null,
      "duration_seconds": 0,
      "handled_by": "ai_agent",
      "sentiment": "positive",
      "transfer_count": 0
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 50
}
```

### Get Inbound Call Details
```http
GET /calls/inbound/{session_id}
```

**Response:**
```json
{
  "session_id": 123,
  "customer_id": 456,
  "room_name": "call-abc123",
  "start_time": "2025-01-15T10:30:00Z",
  "end_time": null,
  "duration_seconds": 120,
  "handled_by": "ai_agent",
  "sentiment": "positive",
  "transfer_count": 0
}
```

---

## Outbound Call Endpoints

### Create Outbound Call
```http
POST /calls/outbound/create
```

**Request Body:**
```json
{
  "to_number": "+1234567890",
  "from_number": "+15183171307",
  "customer_id": 123,
  "metadata": {
    "purpose": "follow_up",
    "campaign": "satisfaction_survey"
  },
  "play_ringtone": true
}
```

**Response:**
```json
{
  "success": true,
  "sip_call_id": "SC_abc123xyz",
  "participant_id": "PA_xyz789",
  "room_name": "outbound-1234567890-20250115103000",
  "to_number": "+1234567890",
  "from_number": "+15183171307",
  "status": "initiating",
  "message": "Outbound call initiated to +1234567890"
}
```

### Create Callback
```http
POST /calls/outbound/callback
```

**Request Body:**
```json
{
  "customer_phone": "+1234567890",
  "customer_id": 123,
  "reason": "scheduled_callback_from_support",
  "from_number": "+15183171307",
  "metadata": {
    "original_session_id": 456
  }
}
```

**Response:**
```json
{
  "success": true,
  "sip_call_id": "SC_callback123",
  "participant_id": "PA_callback789",
  "room_name": "callback-1234567890-1705315800",
  "to_number": "+1234567890",
  "from_number": "+15183171307",
  "status": "initiating",
  "message": "Callback initiated to +1234567890"
}
```

### Batch Create Calls
```http
POST /calls/outbound/batch
```

**Request Body:**
```json
{
  "calls": [
    {
      "to_number": "+1234567890",
      "metadata": {"name": "John Doe", "account": "ACC001"}
    },
    {
      "to_number": "+0987654321",
      "metadata": {"name": "Jane Smith", "account": "ACC002"}
    }
  ],
  "from_number": "+15183171307",
  "trunk_id": "ST_SXWwu7ArVEYE",
  "delay_seconds": 2
}
```

**Response:**
```json
{
  "total": 2,
  "successful": 2,
  "failed": 0,
  "results": [
    {
      "success": true,
      "call_info": {
        "sip_call_id": "SC_batch001",
        "to_number": "+1234567890"
      },
      "index": 1
    },
    {
      "success": true,
      "call_info": {
        "sip_call_id": "SC_batch002",
        "to_number": "+0987654321"
      },
      "index": 2
    }
  ]
}
```

### Get Active Outbound Calls
```http
GET /calls/outbound/active
```

**Response:**
```json
{
  "total": 3,
  "calls": [
    {
      "id": 1,
      "sip_call_id": "SC_abc123",
      "participant_id": "PA_xyz789",
      "room_name": "outbound-1234567890-20250115103000",
      "to_number": "+1234567890",
      "from_number": "+15183171307",
      "trunk_id": "ST_SXWwu7ArVEYE",
      "status": "answered",
      "metadata": {},
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

---

## Common Call Endpoints

### Get All Active Calls
```http
GET /calls/all/active
```

**Response:**
```json
{
  "total": 5,
  "inbound_count": 3,
  "outbound_count": 2,
  "inbound_calls": [...],
  "outbound_calls": [...]
}
```

### Get Call Transcript
```http
GET /calls/{session_id}/transcript
```

**Response:**
```json
[
  {
    "id": 1,
    "session_id": 123,
    "speaker": "customer",
    "text": "Hello, I need help with my account",
    "timestamp": "2025-01-15T10:30:05Z",
    "confidence": 0.95
  },
  {
    "id": 2,
    "session_id": 123,
    "speaker": "ai_agent",
    "text": "Hello! I'd be happy to help you with your account. What seems to be the issue?",
    "timestamp": "2025-01-15T10:30:08Z",
    "confidence": 1.0
  }
]
```

### Transfer Call
```http
POST /calls/{session_id}/transfer
```

**Request Body:**
```json
{
  "agent_id": 5,
  "transfer_type": "warm",
  "reason": "Customer requests billing specialist"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Call transferred to agent 5",
  "agent_id": 5,
  "transfer_type": "warm"
}
```

---

## SIP Management Endpoints

### List All Trunks
```http
GET /sip/trunks
```

**Response:**
```json
{
  "inbound": [
    {
      "trunk_id": "ST_UE2fnCs4yxSo",
      "trunk_type": "inbound",
      "name": "My inbound trunk AgnoX",
      "numbers": ["+15183171307"]
    }
  ],
  "outbound": [
    {
      "trunk_id": "ST_SXWwu7ArVEYE",
      "trunk_type": "outbound",
      "name": "My outbound trunk AgnoX",
      "address": "5njkgqf8llp.sip.livekit.cloud",
      "numbers": ["+15183171307"]
    }
  ],
  "total_inbound": 1,
  "total_outbound": 1
}
```

### List Dispatch Rules
```http
GET /sip/dispatch-rules
```

**Response:**
```json
[
  {
    "rule_id": "SDR_abc123",
    "name": "Default Customer Service Rule",
    "trunk_ids": ["ST_UE2fnCs4yxSo"],
    "room_pattern": "call-{call_id}",
    "hide_phone_number": false,
    "metadata": {
      "purpose": "customer_service",
      "routing_strategy": "ai_first"
    }
  }
]
```

### Create Dispatch Rule
```http
POST /sip/dispatch-rules
```

**Request Body:**
```json
{
  "name": "VIP Customer Service",
  "trunk_ids": ["ST_UE2fnCs4yxSo"],
  "room_name_pattern": "vip-call-{call_id}",
  "metadata": {
    "priority": "high",
    "department": "vip_support"
  },
  "hide_phone_number": false
}
```

**Response:**
```json
{
  "rule_id": "SDR_vip001",
  "name": "VIP Customer Service",
  "trunk_ids": ["ST_UE2fnCs4yxSo"],
  "room_pattern": "vip-call-{call_id}",
  "hide_phone_number": false,
  "has_pin": false,
  "metadata": {
    "priority": "high",
    "department": "vip_support"
  }
}
```

---

## Queue Management Endpoints

### Get Queue Status
```http
GET /queue/status
```

**Response:**
```json
{
  "waiting_count": 5,
  "assigned_count": 3,
  "avg_wait_time_seconds": 45.5,
  "active_agents": 2
}
```

### Get Queue Position
```http
GET /queue/{queue_id}/position
```

**Response:**
```json
{
  "queue_id": 123,
  "position": 3,
  "estimated_wait_minutes": 6
}
```

---

## Agent Management Endpoints

### List Agents
```http
GET /agents
```

**Response:**
```json
{
  "agents": [
    {
      "agent_id": 1,
      "name": "John Agent",
      "phone_number": "+15551234567",
      "status": "online",
      "current_call_count": 1,
      "max_concurrent_calls": 3,
      "skills": ["billing", "support"]
    }
  ],
  "total": 1
}
```

### Update Agent Status
```http
PUT /agents/{agent_id}/status
```

**Request Body:**
```json
{
  "status": "online"
}
```

**Response:**
```json
{
  "success": true,
  "agent_id": 1,
  "status": "online",
  "message": "Agent status updated successfully"
}
```

---

## Analytics Endpoints

### Get Real-time Metrics
```http
GET /analytics/realtime
```

**Response:**
```json
{
  "active_calls": 8,
  "inbound_active": 5,
  "outbound_active": 3,
  "queue_length": 2,
  "avg_wait_time_seconds": 30,
  "agents_online": 4,
  "agents_busy": 3,
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Get Call Metrics
```http
GET /analytics/calls?start_date=2025-01-01&end_date=2025-01-15
```

**Response:**
```json
{
  "total_calls": 150,
  "inbound_calls": 100,
  "outbound_calls": 50,
  "avg_duration_seconds": 240,
  "completion_rate": 0.95,
  "transfer_rate": 0.15,
  "sentiment_distribution": {
    "positive": 80,
    "neutral": 50,
    "negative": 20
  }
}
```

---

## Error Responses

All endpoints return standard error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid phone number format"
}
```

### 401 Unauthorized
```json
{
  "detail": "Invalid or missing authentication token"
}
```

### 404 Not Found
```json
{
  "detail": "Call session not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to create outbound call: Connection timeout"
}
```

---

## Rate Limiting

- Default: 100 requests per minute per API key
- Batch operations: 10 requests per minute
- Outbound calls: 30 calls per minute

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705315860
```

---

## WebSocket Endpoints

### Real-time Call Updates
```
ws://localhost:8000/ws/calls
```

**Message Format:**
```json
{
  "event": "call_started",
  "call_id": "SC_abc123",
  "room_name": "call-123",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### Real-time Transcript
```
ws://localhost:8000/ws/transcripts/{session_id}
```

**Message Format:**
```json
{
  "event": "transcript_update",
  "session_id": 123,
  "speaker": "customer",
  "text": "Hello, I need help",
  "timestamp": "2025-01-15T10:30:05Z"
}
```

---

## SDK Examples

### Python SDK
```python
from voice_agent_client import VoiceAgentClient

client = VoiceAgentClient(
    base_url="http://localhost:8000/api/v1",
    api_key="your-api-key"
)

# Create outbound call
call = client.calls.create_outbound(
    to_number="+1234567890",
    metadata={"purpose": "follow_up"}
)

# Get active calls
active = client.calls.get_all_active()
print(f"Active calls: {active['total']}")
```

### JavaScript SDK
```javascript
const VoiceAgentClient = require('voice-agent-client');

const client = new VoiceAgentClient({
    baseUrl: 'http://localhost:8000/api/v1',
    apiKey: 'your-api-key'
});

// Create outbound call
const call = await client.calls.createOutbound({
    toNumber: '+1234567890',
    metadata: { purpose: 'follow_up' }
});

// Get active calls
const active = await client.calls.getAllActive();
console.log(`Active calls: ${active.total}`);
```

---

## Postman Collection

Import this collection for easy testing:
```
https://api.postman.com/collections/your-collection-id
```

---

For support or questions, check the main documentation or logs at `logs/agent.log`.