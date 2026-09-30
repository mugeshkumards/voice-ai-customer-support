"""
Tests for CRM REST API endpoints:
- /api/customers
- /api/tickets
- /api/call-summaries
"""


def test_list_customers(client):
    """Test retrieving list of customers."""
    response = client.get("/api/customers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(c["id"] == "CUST-TEST-001" for c in data)


def test_get_customer_by_id(client):
    """Test getting single customer with relations."""
    response = client.get("/api/customers/CUST-TEST-001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "CUST-TEST-001"
    assert data["name"] == "Test User"
    assert "tickets" in data
    assert len(data["tickets"]) >= 1


def test_get_customer_not_found(client):
    """Test 404 on non-existent customer."""
    response = client.get("/api/customers/CUST-999999")
    assert response.status_code == 404


def test_create_customer(client):
    """Test creating a new customer."""
    payload = {
        "name": "Sarah Connor",
        "phone": "+15554443322",
        "email": "sarah@skynet-defense.com",
        "plan": "Enterprise",
        "notes": "Urgent support tier"
    }
    response = client.post("/api/customers", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["phone"] == payload["phone"]
    assert data["id"].startswith("CUST-")


def test_update_customer(client):
    """Test updating existing customer."""
    payload = {"plan": "Diamond Tier", "notes": "Upgraded tier"}
    response = client.put("/api/customers/CUST-TEST-001", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["plan"] == "Diamond Tier"
    assert data["notes"] == "Upgraded tier"


def test_delete_customer(client):
    """Test deleting customer."""
    # Create a temporary customer
    c_res = client.post("/api/customers", json={"name": "Temp Customer", "phone": "+15550009999"})
    cid = c_res.json()["id"]

    del_res = client.delete(f"/api/customers/{cid}")
    assert del_res.status_code == 200

    # Verify 404 after deletion
    get_res = client.get(f"/api/customers/{cid}")
    assert get_res.status_code == 404


# =================================================================
# Ticket Tests
# =================================================================

def test_list_tickets(client):
    """Test listing support tickets."""
    response = client.get("/api/tickets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_create_ticket_success(client):
    """Test creating ticket for valid customer."""
    payload = {
        "customer_id": "CUST-TEST-001",
        "issue": "Slow connection on router Wi-Fi 5GHz band",
        "priority": "medium",
        "status": "open"
    }
    response = client.post("/api/tickets", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["customer_id"] == "CUST-TEST-001"
    assert data["issue"] == payload["issue"]


def test_create_ticket_invalid_customer(client):
    """Test 400 when creating ticket for non-existent customer."""
    payload = {
        "customer_id": "CUST-DOES-NOT-EXIST",
        "issue": "Cannot log in"
    }
    response = client.post("/api/tickets", json=payload)
    assert response.status_code == 400


def test_update_ticket(client):
    """Test updating ticket status and resolution."""
    payload = {
        "status": "resolved",
        "resolution_notes": "Replaced optical fiber cable"
    }
    response = client.put("/api/tickets/TICK-TEST-001", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["resolution_notes"] == "Replaced optical fiber cable"


# =================================================================
# Call Summary Tests
# =================================================================

def test_call_summary_crud(client):
    """Test creating, listing, and retrieving call summaries."""
    payload = {
        "call_sid": "CA_MOCK_123456",
        "customer_id": "CUST-TEST-001",
        "caller_phone": "+15550001111",
        "transcript": "Agent: How can I help?\nCustomer: Need billing help.",
        "summary": "Customer called regarding billing question.",
        "sentiment": "positive",
        "action_items": "Checked invoice",
        "duration_seconds": 45
    }
    create_res = client.post("/api/call-summaries", json=payload)
    assert create_res.status_code == 201
    summary_id = create_res.json()["id"]

    # Get by ID
    get_res = client.get(f"/api/call-summaries/{summary_id}")
    assert get_res.status_code == 200
    assert get_res.json()["call_sid"] == "CA_MOCK_123456"
    assert get_res.json()["sentiment"] == "positive"

    # List
    list_res = client.get("/api/call-summaries")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
