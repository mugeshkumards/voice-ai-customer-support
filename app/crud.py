"""
Database CRUD operations for Customers, Tickets, and Call Summaries.
"""

from datetime import datetime, timezone
from typing import List, Optional, Union, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import Customer, Ticket, CallSummary, generate_uuid
from app.schemas import (
    CustomerCreate,
    CustomerUpdate,
    TicketCreate,
    TicketUpdate,
    CallSummaryCreate,
)
from app.utils.logger import logger


# =================================================================
# Customer CRUD Operations
# =================================================================

def get_customer(db: Session, customer_id: str) -> Optional[Customer]:
    """Retrieve a customer by exact ID."""
    return db.query(Customer).filter(Customer.id == customer_id).first()


def get_customer_by_phone(db: Session, phone: str) -> Optional[Customer]:
    """
    Retrieve customer by phone number. Normalizes matching by stripping formatting.
    """
    if not phone:
        return None
    
    # Try exact match first
    customer = db.query(Customer).filter(Customer.phone == phone).first()
    if customer:
        return customer

    # Normalize phone: remove '+', '-', ' ', '(', ')'
    clean_digits = "".join([c for c in phone if c.isdigit()])
    if not clean_digits:
        return None

    # Query all and match digits suffix
    candidates = db.query(Customer).all()
    for c in candidates:
        c_digits = "".join([ch for ch in (c.phone or "") if ch.isdigit()])
        if c_digits and (c_digits.endswith(clean_digits) or clean_digits.endswith(c_digits)):
            return c
    return None


def get_customers(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> List[Customer]:
    """Retrieve multiple customers with optional filtering and pagination."""
    query = db.query(Customer)
    if status:
        query = query.filter(Customer.status == status)
    if search:
        search_fmt = f"%{search}%"
        query = query.filter(
            or_(
                Customer.name.ilike(search_fmt),
                Customer.phone.ilike(search_fmt),
                Customer.email.ilike(search_fmt),
                Customer.id.ilike(search_fmt)
            )
        )
    return query.order_by(Customer.created_at.desc()).offset(skip).limit(limit).all()


def create_customer(db: Session, customer_in: CustomerCreate) -> Customer:
    """Create a new customer in the database."""
    customer_id = customer_in.id if customer_in.id else generate_uuid("CUST")
    db_customer = Customer(
        id=customer_id,
        name=customer_in.name,
        phone=customer_in.phone,
        email=customer_in.email,
        plan=customer_in.plan,
        status=customer_in.status,
        notes=customer_in.notes,
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    logger.info(f"Created customer: {db_customer.id} ({db_customer.name})")
    return db_customer


def update_customer(
    db: Session,
    customer_id: str,
    customer_in: Union[CustomerUpdate, Dict[str, Any]]
) -> Optional[Customer]:
    """Update an existing customer's fields."""
    db_customer = get_customer(db, customer_id)
    if not db_customer:
        return None

    update_data = (
        customer_in.model_dump(exclude_unset=True)
        if isinstance(customer_in, CustomerUpdate)
        else customer_in
    )

    for field, value in update_data.items():
        if hasattr(db_customer, field) and value is not None:
            setattr(db_customer, field, value)

    db_customer.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_customer)
    logger.info(f"Updated customer: {customer_id} with data {update_data}")
    return db_customer


def delete_customer(db: Session, customer_id: str) -> bool:
    """Delete a customer by ID."""
    db_customer = get_customer(db, customer_id)
    if not db_customer:
        return False
    db.delete(db_customer)
    db.commit()
    logger.info(f"Deleted customer: {customer_id}")
    return True


# =================================================================
# Ticket CRUD Operations
# =================================================================

def get_ticket(db: Session, ticket_id: str) -> Optional[Ticket]:
    """Retrieve ticket by ID."""
    return db.query(Ticket).filter(Ticket.id == ticket_id).first()


def get_tickets(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None
) -> List[Ticket]:
    """Retrieve tickets with optional filtering."""
    query = db.query(Ticket)
    if customer_id:
        query = query.filter(Ticket.customer_id == customer_id)
    if status:
        query = query.filter(Ticket.status == status)
    if priority:
        query = query.filter(Ticket.priority == priority)
    return query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()


def create_ticket(db: Session, ticket_in: TicketCreate) -> Ticket:
    """Create a support ticket for a customer."""
    ticket_id = ticket_in.id if ticket_in.id else generate_uuid("TICK")
    db_ticket = Ticket(
        id=ticket_id,
        customer_id=ticket_in.customer_id,
        issue=ticket_in.issue,
        priority=ticket_in.priority or "medium",
        status=ticket_in.status or "open",
        resolution_notes=ticket_in.resolution_notes
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    logger.info(f"Created ticket: {db_ticket.id} for customer {db_ticket.customer_id}")
    return db_ticket


def update_ticket(
    db: Session,
    ticket_id: str,
    ticket_in: Union[TicketUpdate, Dict[str, Any]]
) -> Optional[Ticket]:
    """Update ticket fields (status, priority, resolution_notes, issue)."""
    db_ticket = get_ticket(db, ticket_id)
    if not db_ticket:
        return None

    update_data = (
        ticket_in.model_dump(exclude_unset=True)
        if isinstance(ticket_in, TicketUpdate)
        else ticket_in
    )

    for field, value in update_data.items():
        if hasattr(db_ticket, field) and value is not None:
            setattr(db_ticket, field, value)

    db_ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(db_ticket)
    logger.info(f"Updated ticket: {ticket_id} with data {update_data}")
    return db_ticket


def delete_ticket(db: Session, ticket_id: str) -> bool:
    """Delete a ticket by ID."""
    db_ticket = get_ticket(db, ticket_id)
    if not db_ticket:
        return False
    db.delete(db_ticket)
    db.commit()
    logger.info(f"Deleted ticket: {ticket_id}")
    return True


# =================================================================
# Call Summary CRUD Operations
# =================================================================

def get_call_summary(db: Session, summary_id: str) -> Optional[CallSummary]:
    """Retrieve call summary by primary key ID."""
    return db.query(CallSummary).filter(CallSummary.id == summary_id).first()


def get_call_summary_by_sid(db: Session, call_sid: str) -> Optional[CallSummary]:
    """Retrieve call summary by Twilio Call SID."""
    if not call_sid:
        return None
    return db.query(CallSummary).filter(CallSummary.call_sid == call_sid).first()


def get_call_summaries(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    customer_id: Optional[str] = None
) -> List[CallSummary]:
    """Retrieve list of call summaries."""
    query = db.query(CallSummary)
    if customer_id:
        query = query.filter(CallSummary.customer_id == customer_id)
    return query.order_by(CallSummary.created_at.desc()).offset(skip).limit(limit).all()


def create_call_summary(db: Session, summary_in: CallSummaryCreate) -> CallSummary:
    """Create a call summary record."""
    summary_id = summary_in.id if summary_in.id else generate_uuid("CALL")
    db_summary = CallSummary(
        id=summary_id,
        call_sid=summary_in.call_sid,
        customer_id=summary_in.customer_id,
        caller_phone=summary_in.caller_phone,
        transcript=summary_in.transcript or "",
        summary=summary_in.summary or "",
        sentiment=summary_in.sentiment or "neutral",
        action_items=summary_in.action_items,
        duration_seconds=summary_in.duration_seconds or 0,
    )
    db.add(db_summary)
    db.commit()
    db.refresh(db_summary)
    logger.info(f"Created call summary: {db_summary.id} for call_sid {db_summary.call_sid}")
    return db_summary


def upsert_call_summary_by_sid(
    db: Session,
    call_sid: str,
    summary_data: Dict[str, Any]
) -> CallSummary:
    """
    Create or update call summary matching a given Twilio Call SID.
    """
    existing = get_call_summary_by_sid(db, call_sid)
    if existing:
        for key, val in summary_data.items():
            if hasattr(existing, key) and val is not None:
                setattr(existing, key, val)
        db.commit()
        db.refresh(existing)
        logger.info(f"Updated existing call summary {existing.id} for call_sid {call_sid}")
        return existing
    else:
        create_schema = CallSummaryCreate(
            call_sid=call_sid,
            customer_id=summary_data.get("customer_id"),
            caller_phone=summary_data.get("caller_phone"),
            transcript=summary_data.get("transcript", ""),
            summary=summary_data.get("summary", ""),
            sentiment=summary_data.get("sentiment", "neutral"),
            action_items=summary_data.get("action_items"),
            duration_seconds=summary_data.get("duration_seconds", 0)
        )
        return create_call_summary(db, create_schema)


# =================================================================
# Seed Data Helper
# =================================================================

def seed_initial_data(db: Session) -> None:
    """
    Seed initial customer and ticket data if database is empty.
    Provides ready-to-test mock records.
    """
    count = db.query(Customer).count()
    if count > 0:
        return

    logger.info("Seeding initial mock customers and tickets for demo...")

    sample_customers = [
        Customer(
            id="CUST-1001",
            name="Alice Johnson",
            phone="+15551234567",
            email="alice.johnson@example.com",
            plan="Premium",
            status="active",
            notes="VIP Customer. Prefers email updates."
        ),
        Customer(
            id="CUST-1002",
            name="Bob Smith",
            phone="+15559876543",
            email="bob.smith@example.com",
            plan="Standard",
            status="active",
            notes="Recent internet speed inquiry."
        ),
        Customer(
            id="CUST-1003",
            name="Carol Davis",
            phone="+15553334444",
            email="carol.davis@example.com",
            plan="Enterprise",
            status="active",
            notes="Requires dedicated account manager for escalations."
        )
    ]

    for c in sample_customers:
        db.add(c)
    db.commit()

    sample_tickets = [
        Ticket(
            id="TICK-1001",
            customer_id="CUST-1001",
            issue="Billing discrepancy on latest monthly invoice",
            priority="medium",
            status="open",
            resolution_notes=None
        ),
        Ticket(
            id="TICK-1002",
            customer_id="CUST-1002",
            issue="Router rebooting unexpectedly during peak hours",
            priority="high",
            status="in_progress",
            resolution_notes="Technician scheduled"
        )
    ]

    for t in sample_tickets:
        db.add(t)
    db.commit()

    logger.info("Sample database records seeded successfully.")
