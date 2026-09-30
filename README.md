# AI Voice Customer Support Agent (Production-Style MVP)

An intelligent, production-style MVP for automated voice customer support powered by **FastAPI**, **Twilio Voice API**, **DeepSeek LLM** (with native Tool/Function Calling), and an integrated **SQLite CRM**.

---

## 📋 Features

- 📞 **Twilio Voice Integration**: Handles live inbound phone calls with Twilio Voice Webhooks and dynamic TwiML XML responses.
- 🤖 **DeepSeek AI Agent**: Conversational voice agent powered by DeepSeek (`deepseek-chat`) with prompt engineering optimized for natural spoken dialogue (TTS).
- 🛠️ **AI Agent Function Calling / Tools**:
  - `get_customer(customer_id)`: Fetches customer details, subscription tier, notes, and active support tickets.
  - `update_customer(customer_id, data)`: Modifies customer profile, subscription plans, contact info, and notes.
  - `create_support_ticket(customer_id, issue, priority)`: Logs customer support tickets with severity levels.
- 🗄️ **Built-in CRM & SQLite Database**: Complete REST API for managing Customers, Support Tickets, and Post-Call Summaries.
- 📝 **Automatic Post-Call Summarization**: Summarizes conversation turns, customer sentiment (`positive`, `neutral`, `frustrated`), and action items.
- 🧪 **Comprehensive Automated Test Suite**: 28 unit and integration tests covering CRM endpoints, agent tools, LLM tool execution loops, and Twilio webhooks.
- 💻 **Offline / Developer Simulation Mode**: Allows full local testing via REST API without requiring live phone credits or Twilio accounts.

---

## 📁 Complete File Structure

```
voice-ai-customer-support/
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore configuration
├── requirements.txt          # Python dependencies
├── pytest.ini                # Pytest configuration
├── README.md                 # Complete documentation & API guides
├── app/
│   ├── __init__.py           # Application package
│   ├── main.py               # FastAPI entrypoint, middleware, lifecycle & routing
│   ├── config.py             # Pydantic Settings & environment loader
│   ├── database.py           # SQLAlchemy engine, session maker & Base
│   ├── models.py             # SQLAlchemy models (Customer, Ticket, CallSummary)
│   ├── schemas.py            # Pydantic validation schemas & request/response models
│   ├── crud.py               # Database CRUD operations & demo data seeder
│   ├── agent/
│   │   ├── __init__.py       # Agent package exports
│   │   ├── tools.py          # AI tools (get_customer, update_customer, create_support_ticket)
│   │   └── deepseek_agent.py # DeepSeek client, tool-calling loop & call summarizer
│   ├── routers/
│   │   ├── __init__.py       # Router exports
│   │   ├── voice.py          # Twilio webhooks (/voice, /process-call, /voice/simulate)
│   │   └── crm.py            # CRM REST API (/api/customers, /api/tickets, /api/call-summaries)
│   └── utils/
│       ├── __init__.py       # Utility exports
│       ├── logger.py         # Structured logging configuration
│       └── twiml_builder.py  # Twilio TwiML Voice XML generator
└── tests/
    ├── __init__.py           # Test package
    ├── conftest.py           # Pytest in-memory database & TestClient fixtures
    ├── test_crm.py           # CRM REST API tests
    ├── test_agent_tools.py   # Agent tool unit tests
    ├── test_deepseek_agent.py# DeepSeek tool calling & summarizer tests
    └── test_voice.py         # Twilio webhook & simulation tests
```

---

## 🛠️ Tech Stack

| Technology | Purpose |
| :--- | :--- |
| **Python 3.11+** | Application runtime |
| **FastAPI** | High-performance asynchronous REST API framework |
| **Twilio Voice API** | Telephony, Speech-to-Text (STT), Text-to-Speech (TTS), and TwiML Webhooks |
| **DeepSeek API** | LLM model (`deepseek-chat`) with tool / function calling capabilities |
| **SQLAlchemy 2.0** | Object-Relational Mapping (ORM) and database management |
| **SQLite** | Embedded SQL database for persistence |
| **Pydantic v2** | Data validation and serialization |
| **Pytest** | Automated test framework |

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.11 or higher
- (Optional for live telephony) A [Twilio Account](https://www.twilio.com) and an [ngrok](https://ngrok.com) tunnel.
- (Optional for real LLM reasoning) A [DeepSeek API Key](https://platform.deepseek.com).

### 2. Installation

Clone or navigate to the project directory:

```bash
cd "voice ai"
```

Create and activate a virtual environment:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```ini
# DeepSeek API Configuration
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Twilio Voice Configuration (Required for live inbound phone calls)
TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Database & Server
DATABASE_URL=sqlite:///./voice_support.db
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
APP_ENV=development
```

> **Note:** If `DEEPSEEK_API_KEY` is not provided, the application automatically runs in an **Intelligent Mock Fallback Mode**, allowing full offline development and testing.

### 4. Running the Application

Start the FastAPI server with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The interactive Swagger API documentation will be available at:
👉 **`http://localhost:8000/docs`**

---

## 📞 Twilio Voice Setup (Live Telephony)

> ⚠️ **REQUIRES A REAL TWILIO ACCOUNT & PHONE NUMBER**

To connect a real telephone number to this AI Agent:

### Step 1: Expose your local server via ngrok

Run ngrok to create a public HTTPS tunnel to port 8000:

```bash
ngrok http 8000
```

Copy your public HTTPS forwarding URL (e.g. `https://abc1234.ngrok-free.app`).

### Step 2: Configure Twilio Phone Number Webhook

1. Log in to the [Twilio Console](https://console.twilio.com/).
2. Navigate to **Phone Numbers** > **Manage** > **Active numbers**.
3. Click on your Twilio phone number.
4. Scroll down to the **Voice Configuration** section.
5. Set **"A CALL COMES IN"** to:
   - **Webhook**
   - URL: `https://<YOUR-NGROK-SUBDOMAIN>.ngrok-free.app/voice`
   - HTTP Method: `HTTP POST`
6. Click **Save Configuration**.

### Step 3: Call Your Twilio Number

Call your Twilio phone number from any mobile or landline phone!
1. The AI Agent will greet you with Amazon Polly voice.
2. Say something like:
   - *"Hi, my name is Alice Johnson. Can you check my account details?"*
   - *"I want to report an issue with my internet connection being slow."*
   - *"Can you change my plan to Premium?"*
3. The AI Agent will dynamically invoke the CRM tools and speak the result.
4. When you say *"Goodbye"*, the agent will politely conclude and hang up.

---

## 🧪 Testing Locally (Without Twilio or Phone)

You can fully test the voice dialogue and tool calling logic without Twilio using our simulated endpoints or `curl`.

### Option A: Direct Voice Simulation (JSON)

Use the developer simulation endpoint `POST /voice/simulate`:

```bash
curl -X POST "http://localhost:8000/voice/simulate?speech=I%20have%20an%20issue%20with%20my%20router%20wifi&customer_id=CUST-1001"
```

**Sample Response:**
```json
{
  "call_sid": "DEV_SIMULATION_001",
  "spoken_response": "I have logged support ticket TICK-8B12 for your issue. Our technical team is reviewing it. Is there anything else I can help with?",
  "tools_called": [
    {
      "tool_name": "create_support_ticket",
      "tool_args": {
        "customer_id": "CUST-1001",
        "issue": "I have an issue with my router wifi"
      },
      "result": {
        "success": true,
        "message": "Support ticket created successfully with ID TICK-8B12.",
        "ticket": {
          "id": "TICK-8B12",
          "customer_id": "CUST-1001",
          "issue": "I have an issue with my router wifi",
          "priority": "medium",
          "status": "open"
        }
      }
    }
  ],
  "should_hangup": false,
  "customer_id": "CUST-1001",
  "call_summary": {
    "summary": "Customer reported router wifi issue. Support ticket TICK-8B12 created.",
    "sentiment": "neutral",
    "action_items": "create_support_ticket -> ticket logged"
  }
}
```

### Option B: Simulating Twilio Webhooks (TwiML XML)

#### 1. Simulate Incoming Call (`POST /voice`)
```bash
curl -X POST "http://localhost:8000/voice" \
  -d "CallSid=CA123456789" \
  -d "From=+15551234567" \
  -d "To=+18005550000"
```

**TwiML Response:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Gather action="/process-call" input="speech" language="en-US" method="POST" speechTimeout="auto">
    <Say language="en-US" voice="Polly.Amy">Hello Alice Johnson! Thank you for calling Customer Support. How can I help you today?</Say>
  </Gather>
  <Say language="en-US" voice="Polly.Amy">We did not receive any input. Please call back if you need assistance. Goodbye.</Say>
  <Hangup/>
</Response>
```

#### 2. Simulate Caller Speaking (`POST /process-call`)
```bash
curl -X POST "http://localhost:8000/process-call" \
  -d "CallSid=CA123456789" \
  -d "From=+15551234567" \
  -d "SpeechResult=What is my current subscription plan?"
```

---

## 🏢 CRM REST API Reference

The CRM API provides full CRUD access to customers, support tickets, and post-call analytics.

### 1. Customers API (`/api/customers`)

#### List Customers
```bash
curl -X GET "http://localhost:8000/api/customers?limit=10"
```

#### Get Customer Details (with Tickets & Call History)
```bash
curl -X GET "http://localhost:8000/api/customers/CUST-1001"
```

#### Create New Customer
```bash
curl -X POST "http://localhost:8000/api/customers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "David Miller",
    "phone": "+15557778888",
    "email": "david.miller@example.com",
    "plan": "Enterprise",
    "notes": "Prefers evening contact"
  }'
```

#### Update Customer
```bash
curl -X PUT "http://localhost:8000/api/customers/CUST-1001" \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "Premium Plus",
    "email": "alice.updated@example.com"
  }'
```

#### Delete Customer
```bash
curl -X DELETE "http://localhost:8000/api/customers/CUST-1001"
```

---

### 2. Support Tickets API (`/api/tickets`)

#### List Tickets
```bash
curl -X GET "http://localhost:8000/api/tickets?status=open"
```

#### Create Support Ticket
```bash
curl -X POST "http://localhost:8000/api/tickets" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "CUST-1001",
    "issue": "Fiber broadband connection dropping every 20 minutes",
    "priority": "high",
    "status": "open"
  }'
```

#### Update Support Ticket
```bash
curl -X PUT "http://localhost:8000/api/tickets/TICK-1001" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "resolution_notes": "Replaced modem firmware and reset port"
  }'
```

---

### 3. Call Summaries API (`/api/call-summaries`)

#### List Historical Call Summaries
```bash
curl -X GET "http://localhost:8000/api/call-summaries"
```

#### Get Single Call Summary
```bash
curl -X GET "http://localhost:8000/api/call-summaries/CALL-1001"
```

---

## 🤖 AI Agent Tools Reference

The voice agent is equipped with 3 native tools defined in `app/agent/tools.py`:

```python
# 1. Fetch Customer Account & Open Tickets
get_customer(customer_id: str) -> dict

# 2. Update Customer Contact / Plan / Notes
update_customer(customer_id: str, data: dict) -> dict

# 3. Create Support Ticket
create_support_ticket(customer_id: str, issue: str, priority: str = "medium") -> dict
```

When a user speaks over the telephone, DeepSeek LLM analyzes the caller's intent, chooses the right tool, executes the database change in SQLite, and synthesizes a spoken confirmation response.

---

## 🧪 Running Automated Tests

Run the complete test suite using `pytest`:

```bash
python -m pytest -v
```

All 28 tests will run across:
- `test_agent_tools.py` — Unit tests for the 3 AI agent tools & tool schema.
- `test_crm.py` — Full CRUD integration tests for Customers, Tickets, and Summaries.
- `test_deepseek_agent.py` — DeepSeek LLM tool execution loop & AI summarization.
- `test_voice.py` — Twilio webhook simulation, TwiML XML assertions & hangup flow.

---

## 🔒 Production Readiness Considerations

For scaling this MVP to high-volume production:
1. **Database**: Switch `DATABASE_URL` in `.env` to PostgreSQL or AWS RDS (`postgresql://user:password@host:5432/dbname`).
2. **Webhook Security**: Add Twilio Request Signature validation (`X-Twilio-Signature`) via `twilio.request_validator.RequestValidator` to ensure only Twilio can call the `/voice` and `/process-call` endpoints.
3. **Session State**: For distributed scaling across multiple container instances, use Redis for caching in-flight phone call session state (`CALL_SESSIONS`).
4. **Speech Latency**: DeepSeek response streaming or Twilio Media Streams (WebSockets) can be utilized for ultra-low-latency real-time voice streaming.

---

## 📄 License

MIT License. Free for development and commercial use.
