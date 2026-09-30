"""
Tests for Twilio Voice Webhooks and Call Processing:
- POST /voice
- POST /process-call
- POST /voice/simulate
"""


def test_incoming_voice_webhook_unknown_caller(client):
    """Test POST /voice with unknown caller phone returns valid TwiML Gather."""
    form_data = {
        "CallSid": "CA_TEST_VOICE_001",
        "From": "+19998887777",
        "To": "+18005550000",
        "CallStatus": "ringing",
    }
    response = client.post("/voice", data=form_data)
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    xml = response.text
    assert "<Response>" in xml
    assert "<Gather" in xml
    assert 'action="/process-call"' in xml
    assert "<Say" in xml
    assert "</Response>" in xml


def test_incoming_voice_webhook_known_caller(client):
    """Test POST /voice recognizes registered phone number in greeting."""
    form_data = {
        "CallSid": "CA_TEST_VOICE_002",
        "From": "+15550001111",  # Matches seeded test customer 'Test User'
        "To": "+18005550000",
        "CallStatus": "ringing",
    }
    response = client.post("/voice", data=form_data)
    assert response.status_code == 200
    xml = response.text
    assert "Test User" in xml or "Hello" in xml
    assert "<Gather" in xml


def test_process_call_empty_speech(client):
    """Test POST /process-call with no speech prompts caller again."""
    form_data = {
        "CallSid": "CA_TEST_VOICE_003",
        "From": "+15550001111",
        "SpeechResult": "",
    }
    response = client.post("/process-call", data=form_data)
    assert response.status_code == 200
    xml = response.text
    assert "<Gather" in xml
    assert "did not hear" in xml or "state your request" in xml


def test_process_call_with_ticket_request(client):
    """Test POST /process-call handles customer reporting an issue and creates ticket."""
    form_data = {
        "CallSid": "CA_TEST_VOICE_004",
        "From": "+15550001111",
        "SpeechResult": "I have an issue with my high speed internet connection being broken",
    }
    response = client.post("/process-call", data=form_data)
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    xml = response.text
    assert "<Response>" in xml
    assert "<Say" in xml

    # Verify call summary was stored in CRM
    summaries_res = client.get("/api/call-summaries")
    assert summaries_res.status_code == 200
    summaries = summaries_res.json()
    assert any(s["call_sid"] == "CA_TEST_VOICE_004" for s in summaries)


def test_process_call_goodbye_hangup(client):
    """Test POST /process-call ends call when caller says goodbye."""
    form_data = {
        "CallSid": "CA_TEST_VOICE_005",
        "From": "+15550001111",
        "SpeechResult": "Thank you, that is all. Goodbye!",
    }
    response = client.post("/process-call", data=form_data)
    assert response.status_code == 200
    xml = response.text
    assert "<Hangup/>" in xml or "<Hangup />" in xml
    assert "<Gather" not in xml


def test_voice_simulate_endpoint(client):
    """Test POST /voice/simulate developer endpoint for direct JSON interaction."""
    payload = {
        "speech": "Can you check my account details please?",
        "customer_id": "CUST-TEST-001",
        "call_sid": "CA_SIM_DEV_100",
        "caller_phone": "+15550001111"
    }
    response = client.post(
        "/voice/simulate",
        params=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert data["call_sid"] == "CA_SIM_DEV_100"
    assert "spoken_response" in data
    assert "call_summary" in data
    assert data["customer_id"] == "CUST-TEST-001"
