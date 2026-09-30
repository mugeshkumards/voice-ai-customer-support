"""
Unit tests for AI Agent Tools:
1. get_customer(customer_id)
2. update_customer(customer_id, data)
3. create_support_ticket(customer_id, issue, priority)
"""

from app.agent.tools import (
    get_customer,
    update_customer,
    create_support_ticket,
    execute_tool_call,
    AGENT_TOOLS_SCHEMA,
)


def test_get_customer_success(db):
    """Test retrieving existing customer with active tickets."""
    result = get_customer(db, "CUST-TEST-001")
    assert result["success"] is True
    assert "customer" in result
    cust = result["customer"]
    assert cust["id"] == "CUST-TEST-001"
    assert cust["name"] == "Test User"
    assert cust["plan"] == "Premium"
    assert len(cust["tickets"]) == 1
    assert cust["tickets"][0]["id"] == "TICK-TEST-001"


def test_get_customer_not_found(db):
    """Test retrieving non-existent customer."""
    result = get_customer(db, "CUST-NONEXISTENT")
    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_update_customer_success(db):
    """Test updating customer contact details and plan."""
    update_data = {
        "email": "updated_test@example.com",
        "plan": "Enterprise",
        "notes": "Upgraded during support call"
    }
    result = update_customer(db, "CUST-TEST-001", update_data)
    assert result["success"] is True
    assert result["customer"]["email"] == "updated_test@example.com"
    assert result["customer"]["plan"] == "Enterprise"
    assert result["customer"]["notes"] == "Upgraded during support call"

    # Verify persistent state in db
    refreshed = get_customer(db, "CUST-TEST-001")
    assert refreshed["customer"]["email"] == "updated_test@example.com"


def test_update_customer_not_found(db):
    """Test updating a non-existent customer."""
    result = update_customer(db, "CUST-UNKNOWN", {"email": "test@mail.com"})
    assert result["success"] is False
    assert "does not exist" in result["error"].lower()


def test_create_support_ticket_success(db):
    """Test creating a new support ticket for a customer."""
    result = create_support_ticket(
        db=db,
        customer_id="CUST-TEST-001",
        issue="Payment gateway timeout on checkout",
        priority="urgent"
    )
    assert result["success"] is True
    assert "ticket" in result
    ticket = result["ticket"]
    assert ticket["customer_id"] == "CUST-TEST-001"
    assert ticket["issue"] == "Payment gateway timeout on checkout"
    assert ticket["priority"] == "urgent"
    assert ticket["status"] == "open"
    assert ticket["id"].startswith("TICK-")


def test_create_support_ticket_invalid_customer(db):
    """Test creating a support ticket for non-existent customer."""
    result = create_support_ticket(
        db=db,
        customer_id="CUST-INVALID",
        issue="Cannot access router"
    )
    assert result["success"] is False
    assert "does not exist" in result["error"].lower()


def test_execute_tool_call_dispatcher(db):
    """Test dynamic tool dispatcher for all tool functions."""
    # 1. get_customer dispatcher
    res1 = execute_tool_call(db, "get_customer", {"customer_id": "CUST-TEST-001"})
    assert res1["success"] is True

    # 2. update_customer dispatcher
    res2 = execute_tool_call(db, "update_customer", {"customer_id": "CUST-TEST-001", "data": {"plan": "Pro"}})
    assert res2["success"] is True
    assert res2["customer"]["plan"] == "Pro"

    # 3. create_support_ticket dispatcher
    res3 = execute_tool_call(db, "create_support_ticket", {"customer_id": "CUST-TEST-001", "issue": "Billing question", "priority": "low"})
    assert res3["success"] is True
    assert res3["ticket"]["priority"] == "low"

    # 4. unknown tool
    res4 = execute_tool_call(db, "unknown_tool", {})
    assert res4["success"] is False
    assert "not recognized" in res4["error"]


def test_tool_schemas_validity():
    """Verify tool schema format conforms to function calling standard."""
    assert len(AGENT_TOOLS_SCHEMA) == 3
    tool_names = [t["function"]["name"] for t in AGENT_TOOLS_SCHEMA]
    assert "get_customer" in tool_names
    assert "update_customer" in tool_names
    assert "create_support_ticket" in tool_names
