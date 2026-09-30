"""
CRM REST API routes for managing Customers, Tickets, and Call Summaries.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud
from app.schemas import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerWithRelations,
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    CallSummaryCreate,
    CallSummaryResponse,
)
from app.utils.logger import logger

router = APIRouter(prefix="/api", tags=["CRM Management"])


# =================================================================
# Customer Endpoints
# =================================================================

@router.get("/customers", response_model=List[CustomerResponse], summary="List all customers")
def list_customers(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Limit records returned"),
    status: Optional[str] = Query(None, description="Filter by status (active, suspended, pending)"),
    search: Optional[str] = Query(None, description="Search by name, phone, email, or ID"),
    db: Session = Depends(get_db)
):
    """Retrieve customers with optional filtering, search, and pagination."""
    return crud.get_customers(db, skip=skip, limit=limit, status=status, search=search)


@router.get("/customers/{customer_id}", response_model=CustomerWithRelations, summary="Get customer by ID")
def get_customer_by_id(customer_id: str, db: Session = Depends(get_db)):
    """Retrieve single customer record including associated tickets and call summaries."""
    customer = crud.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' was not found."
        )
    return customer


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED, summary="Create customer")
def create_new_customer(customer_in: CustomerCreate, db: Session = Depends(get_db)):
    """Register a new customer in the CRM."""
    # Check if ID already exists if provided
    if customer_in.id:
        existing = crud.get_customer(db, customer_in.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Customer with ID '{customer_in.id}' already exists."
            )
    return crud.create_customer(db, customer_in)


@router.put("/customers/{customer_id}", response_model=CustomerResponse, summary="Update customer")
def update_existing_customer(
    customer_id: str,
    customer_in: CustomerUpdate,
    db: Session = Depends(get_db)
):
    """Update customer details (contact information, subscription plan, status, notes)."""
    updated = crud.update_customer(db, customer_id, customer_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' was not found."
        )
    return updated


@router.delete("/customers/{customer_id}", summary="Delete customer")
def delete_existing_customer(customer_id: str, db: Session = Depends(get_db)):
    """Delete a customer and cascaded records from the CRM."""
    deleted = crud.delete_customer(db, customer_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID '{customer_id}' was not found."
        )
    return {"status": "success", "message": f"Customer '{customer_id}' deleted successfully."}


# =================================================================
# Support Ticket Endpoints
# =================================================================

@router.get("/tickets", response_model=List[TicketResponse], summary="List support tickets")
def list_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    status: Optional[str] = Query(None, description="Filter by status (open, in_progress, resolved, closed)"),
    priority: Optional[str] = Query(None, description="Filter by priority (low, medium, high, urgent)"),
    db: Session = Depends(get_db)
):
    """Retrieve support tickets with optional filters."""
    return crud.get_tickets(
        db,
        skip=skip,
        limit=limit,
        customer_id=customer_id,
        status=status,
        priority=priority
    )


@router.get("/tickets/{ticket_id}", response_model=TicketResponse, summary="Get ticket by ID")
def get_ticket_by_id(ticket_id: str, db: Session = Depends(get_db)):
    """Retrieve ticket details by ID."""
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' was not found."
        )
    return ticket


@router.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED, summary="Create support ticket")
def create_new_ticket(ticket_in: TicketCreate, db: Session = Depends(get_db)):
    """Create a new support ticket linked to a valid customer."""
    customer = crud.get_customer(db, ticket_in.customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create ticket. Customer '{ticket_in.customer_id}' does not exist."
        )
    return crud.create_ticket(db, ticket_in)


@router.put("/tickets/{ticket_id}", response_model=TicketResponse, summary="Update support ticket")
def update_existing_ticket(
    ticket_id: str,
    ticket_in: TicketUpdate,
    db: Session = Depends(get_db)
):
    """Update ticket status, priority, issue details, or resolution notes."""
    updated = crud.update_ticket(db, ticket_id, ticket_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' was not found."
        )
    return updated


@router.delete("/tickets/{ticket_id}", summary="Delete support ticket")
def delete_existing_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """Delete a support ticket by ID."""
    deleted = crud.delete_ticket(db, ticket_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket with ID '{ticket_id}' was not found."
        )
    return {"status": "success", "message": f"Ticket '{ticket_id}' deleted successfully."}


# =================================================================
# Call Summary Endpoints
# =================================================================

@router.get("/call-summaries", response_model=List[CallSummaryResponse], summary="List call summaries")
def list_call_summaries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    db: Session = Depends(get_db)
):
    """Retrieve historical call summaries."""
    return crud.get_call_summaries(db, skip=skip, limit=limit, customer_id=customer_id)


@router.get("/call-summaries/{summary_id}", response_model=CallSummaryResponse, summary="Get call summary by ID")
def get_call_summary_by_id(summary_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed call summary, transcript, and sentiment analysis."""
    summary = crud.get_call_summary(db, summary_id)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call summary with ID '{summary_id}' was not found."
        )
    return summary


@router.post("/call-summaries", response_model=CallSummaryResponse, status_code=status.HTTP_201_CREATED, summary="Create call summary")
def create_new_call_summary(summary_in: CallSummaryCreate, db: Session = Depends(get_db)):
    """Manually record a call summary."""
    return crud.create_call_summary(db, summary_in)
