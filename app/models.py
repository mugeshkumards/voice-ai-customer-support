"""
SQLAlchemy database models for CRM and Voice Support.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid(prefix: str = "") -> str:
    """Generate a readable unique identifier with optional prefix."""
    raw_id = uuid.uuid4().hex[:8].upper()
    return f"{prefix}-{raw_id}" if prefix else raw_id


class Customer(Base):
    """Customer entity model."""
    __tablename__ = "customers"

    id = Column(String(32), primary_key=True, default=lambda: generate_uuid("CUST"), index=True)
    name = Column(String(100), nullable=False, index=True)
    phone = Column(String(30), nullable=False, index=True)
    email = Column(String(120), nullable=True, index=True)
    plan = Column(String(50), nullable=False, default="Standard")
    status = Column(String(30), nullable=False, default="active")  # active, suspended, pending
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    tickets = relationship("Ticket", back_populates="customer", cascade="all, delete-orphan")
    call_summaries = relationship("CallSummary", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer id={self.id} name={self.name} phone={self.phone}>"


class Ticket(Base):
    """Support Ticket model."""
    __tablename__ = "tickets"

    id = Column(String(32), primary_key=True, default=lambda: generate_uuid("TICK"), index=True)
    customer_id = Column(String(32), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    issue = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="medium")  # low, medium, high, urgent
    status = Column(String(30), nullable=False, default="open")      # open, in_progress, resolved, closed
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    customer = relationship("Customer", back_populates="tickets")

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} customer_id={self.customer_id} status={self.status}>"


class CallSummary(Base):
    """Post-call summary model."""
    __tablename__ = "call_summaries"

    id = Column(String(32), primary_key=True, default=lambda: generate_uuid("CALL"), index=True)
    call_sid = Column(String(64), nullable=True, index=True)
    customer_id = Column(String(32), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    caller_phone = Column(String(30), nullable=True)
    transcript = Column(Text, nullable=False, default="")
    summary = Column(Text, nullable=False, default="")
    sentiment = Column(String(30), nullable=True, default="neutral")  # positive, neutral, frustrated, negative
    action_items = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="call_summaries")

    def __repr__(self) -> str:
        return f"<CallSummary id={self.id} call_sid={self.call_sid} customer_id={self.customer_id}>"
