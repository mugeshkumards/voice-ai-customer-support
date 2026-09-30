"""
Pydantic schemas for data validation, API requests, and responses.
"""

from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


# =================================================================
# Customer Schemas
# =================================================================

class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Customer full name")
    phone: str = Field(..., min_length=3, max_length=30, description="Phone number with country code")
    email: Optional[str] = Field(None, max_length=120, description="Customer email address")
    plan: str = Field(default="Standard", max_length=50, description="Subscription plan name")
    status: str = Field(default="active", description="Account status: active, suspended, pending")
    notes: Optional[str] = Field(None, description="General customer notes")


class CustomerCreate(CustomerBase):
    id: Optional[str] = Field(None, description="Optional custom customer ID (e.g. CUST-1001)")


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone: Optional[str] = Field(None, min_length=3, max_length=30)
    email: Optional[str] = Field(None, max_length=120)
    plan: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None)
    notes: Optional[str] = Field(None)


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


# =================================================================
# Ticket Schemas
# =================================================================

class TicketBase(BaseModel):
    customer_id: str = Field(..., description="Customer ID associated with this ticket")
    issue: str = Field(..., min_length=3, description="Detailed description of the customer issue")
    priority: str = Field(default="medium", description="Priority level: low, medium, high, urgent")
    status: str = Field(default="open", description="Ticket status: open, in_progress, resolved, closed")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes once resolved")


class TicketCreate(TicketBase):
    id: Optional[str] = Field(None, description="Optional custom ticket ID")


class TicketUpdate(BaseModel):
    issue: Optional[str] = Field(None, min_length=3)
    priority: Optional[str] = Field(None, description="Priority: low, medium, high, urgent")
    status: Optional[str] = Field(None, description="Status: open, in_progress, resolved, closed")
    resolution_notes: Optional[str] = Field(None)


class TicketResponse(TicketBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


# =================================================================
# Call Summary Schemas
# =================================================================

class CallSummaryBase(BaseModel):
    call_sid: Optional[str] = Field(None, description="Twilio Call SID")
    customer_id: Optional[str] = Field(None, description="Matched Customer ID")
    caller_phone: Optional[str] = Field(None, description="Caller's phone number")
    transcript: str = Field(default="", description="Full dialogue transcript")
    summary: str = Field(default="", description="AI-generated summary of the call")
    sentiment: Optional[str] = Field(default="neutral", description="Customer sentiment: positive, neutral, frustrated, negative")
    action_items: Optional[str] = Field(None, description="Follow-up action items or tickets created")
    duration_seconds: Optional[int] = Field(default=0, description="Call duration in seconds")


class CallSummaryCreate(CallSummaryBase):
    id: Optional[str] = Field(None, description="Optional custom call summary ID")


class CallSummaryResponse(CallSummaryBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class CustomerWithRelations(CustomerResponse):
    tickets: List[TicketResponse] = []
    call_summaries: List[CallSummaryResponse] = []


# =================================================================
# Twilio & Voice Agent Schemas
# =================================================================

class TwilioVoiceWebhook(BaseModel):
    """Parsed fields from Twilio's incoming call webhook."""
    CallSid: str
    From: str
    To: str
    CallStatus: Optional[str] = None
    Direction: Optional[str] = None
    CallerName: Optional[str] = None


class TwilioProcessCallWebhook(BaseModel):
    """Parsed fields from Twilio's Gather / SpeechResult webhook."""
    CallSid: str
    From: str
    To: Optional[str] = None
    SpeechResult: Optional[str] = None
    Confidence: Optional[float] = None
    Digits: Optional[str] = None
    CallStatus: Optional[str] = None


class AgentToolResult(BaseModel):
    tool_name: str
    tool_args: Dict[str, Any]
    result: Dict[str, Any]
    success: bool = True
    error_message: Optional[str] = None


class AgentExecutionResponse(BaseModel):
    spoken_response: str
    tools_called: List[AgentToolResult] = []
    should_hangup: bool = False
    customer_id: Optional[str] = None
    summary: Optional[str] = None
