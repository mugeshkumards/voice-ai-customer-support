"""
AI Agent Tools for Customer Support.
Provides the 3 required tools:
1. get_customer(customer_id)
2. update_customer(customer_id, data)
3. create_support_ticket(customer_id, issue)
"""

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app import crud
from app.schemas import CustomerUpdate, TicketCreate
from app.utils.logger import logger


def get_customer(db: Session, customer_id: str) -> Dict[str, Any]:
    """
    Retrieve customer details and active support tickets by customer_id.

    Args:
        db: Database session.
        customer_id: Unique customer ID (e.g., 'CUST-1001').

    Returns:
        Dict with customer details or error message.
    """
    logger.info(f"[Tool: get_customer] Querying customer_id: {customer_id}")
    customer = crud.get_customer(db, customer_id)
    if not customer:
        logger.warning(f"[Tool: get_customer] Customer {customer_id} not found.")
        return {
            "success": False,
            "error": f"Customer with ID '{customer_id}' was not found in the database."
        }

    tickets = crud.get_tickets(db, customer_id=customer.id)
    return {
        "success": True,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "email": customer.email,
            "plan": customer.plan,
            "status": customer.status,
            "notes": customer.notes,
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
            "tickets": [
                {
                    "id": t.id,
                    "issue": t.issue,
                    "priority": t.priority,
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                }
                for t in tickets
            ]
        }
    }


def update_customer(db: Session, customer_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing customer's contact details, plan, notes, or status.

    Args:
        db: Database session.
        customer_id: Unique customer ID (e.g., 'CUST-1001').
        data: Key-value dictionary containing fields to update (e.g. email, phone, plan, notes, status).

    Returns:
        Dict with updated customer details or error message.
    """
    logger.info(f"[Tool: update_customer] Updating customer_id: {customer_id} with data: {data}")
    customer = crud.get_customer(db, customer_id)
    if not customer:
        logger.warning(f"[Tool: update_customer] Customer {customer_id} not found.")
        return {
            "success": False,
            "error": f"Cannot update. Customer with ID '{customer_id}' does not exist."
        }

    try:
        updated = crud.update_customer(db, customer_id, data)
        return {
            "success": True,
            "message": f"Customer '{customer_id}' updated successfully.",
            "customer": {
                "id": updated.id,
                "name": updated.name,
                "phone": updated.phone,
                "email": updated.email,
                "plan": updated.plan,
                "status": updated.status,
                "notes": updated.notes
            }
        }
    except Exception as e:
        logger.error(f"[Tool: update_customer] Error updating {customer_id}: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to update customer: {str(e)}"
        }


def create_support_ticket(
    db: Session,
    customer_id: str,
    issue: str,
    priority: str = "medium"
) -> Dict[str, Any]:
    """
    Create a new support ticket for a customer.

    Args:
        db: Database session.
        customer_id: Unique customer ID (e.g., 'CUST-1001').
        issue: Detailed description of the customer issue or request.
        priority: Ticket priority level ('low', 'medium', 'high', 'urgent'). Defaults to 'medium'.

    Returns:
        Dict with created ticket details or error message.
    """
    logger.info(f"[Tool: create_support_ticket] Creating ticket for {customer_id}, issue: '{issue}', priority: {priority}")
    customer = crud.get_customer(db, customer_id)
    if not customer:
        logger.warning(f"[Tool: create_support_ticket] Customer {customer_id} not found.")
        return {
            "success": False,
            "error": f"Cannot create ticket. Customer with ID '{customer_id}' does not exist. Please verify customer ID."
        }

    valid_priorities = ["low", "medium", "high", "urgent"]
    norm_priority = priority.lower().strip() if priority else "medium"
    if norm_priority not in valid_priorities:
        norm_priority = "medium"

    try:
        ticket_in = TicketCreate(
            customer_id=customer_id,
            issue=issue,
            priority=norm_priority,
            status="open"
        )
        new_ticket = crud.create_ticket(db, ticket_in)
        return {
            "success": True,
            "message": f"Support ticket created successfully with ID {new_ticket.id}.",
            "ticket": {
                "id": new_ticket.id,
                "customer_id": new_ticket.customer_id,
                "issue": new_ticket.issue,
                "priority": new_ticket.priority,
                "status": new_ticket.status,
                "created_at": new_ticket.created_at.isoformat() if new_ticket.created_at else None
            }
        }
    except Exception as e:
        logger.error(f"[Tool: create_support_ticket] Error creating ticket: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to create support ticket: {str(e)}"
        }


# =================================================================
# Tool Definitions for DeepSeek / OpenAI Function Calling
# =================================================================

AGENT_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_customer",
            "description": "Fetch customer account details, subscription plan, notes, and open support tickets by customer ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The unique customer identifier, e.g. 'CUST-1001'"
                    }
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_customer",
            "description": "Update customer contact information, subscription plan, status, or general notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The unique customer identifier, e.g. 'CUST-1001'"
                    },
                    "data": {
                        "type": "object",
                        "description": "Key-value dictionary of fields to update (e.g. {'email': 'new@mail.com', 'phone': '+15550001', 'plan': 'Premium', 'notes': 'Requested callback'})",
                        "properties": {
                            "name": {"type": "string"},
                            "phone": {"type": "string"},
                            "email": {"type": "string"},
                            "plan": {"type": "string"},
                            "status": {"type": "string"},
                            "notes": {"type": "string"}
                        }
                    }
                },
                "required": ["customer_id", "data"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_support_ticket",
            "description": "Create a new support ticket when a customer reports an issue, complaint, technical bug, or requests escalation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "The unique customer identifier, e.g. 'CUST-1001'"
                    },
                    "issue": {
                        "type": "string",
                        "description": "Clear and detailed description of the customer's problem or request."
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "description": "Priority level of the issue. Default is 'medium'."
                    }
                },
                "required": ["customer_id", "issue"]
            }
        }
    }
]


def execute_tool_call(db: Session, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch function call to corresponding Python tool function.
    """
    if tool_name == "get_customer":
        customer_id = arguments.get("customer_id", "")
        return get_customer(db, customer_id)
    elif tool_name == "update_customer":
        customer_id = arguments.get("customer_id", "")
        data = arguments.get("data", {})
        return update_customer(db, customer_id, data)
    elif tool_name == "create_support_ticket":
        customer_id = arguments.get("customer_id", "")
        issue = arguments.get("issue", "")
        priority = arguments.get("priority", "medium")
        return create_support_ticket(db, customer_id, issue, priority)
    else:
        logger.error(f"Unknown tool requested: {tool_name}")
        return {"success": False, "error": f"Tool '{tool_name}' is not recognized."}
