"""
Twilio Voice Webhook endpoints and call processing logic.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Form, Response, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud
from app.agent.deepseek_agent import run_agent_turn, generate_call_summary
from app.utils.twiml_builder import build_gather_twiml, build_say_and_hangup_twiml
from app.utils.logger import logger
from app.schemas import AgentExecutionResponse

router = APIRouter(tags=["Twilio Voice Webhooks"])

# In-memory conversation state cache for active calls
# key: CallSid -> dict(customer_id, caller_phone, history, transcript_lines, tools_used)
CALL_SESSIONS: Dict[str, Dict[str, Any]] = {}


def _get_or_create_call_session(call_sid: str, caller_phone: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve or initialize in-memory call state for a given CallSid."""
    if call_sid not in CALL_SESSIONS:
        CALL_SESSIONS[call_sid] = {
            "customer_id": None,
            "caller_phone": caller_phone,
            "history": [],
            "transcript_lines": [],
            "tools_used": [],
        }
    elif caller_phone and not CALL_SESSIONS[call_sid]["caller_phone"]:
        CALL_SESSIONS[call_sid]["caller_phone"] = caller_phone
    return CALL_SESSIONS[call_sid]


@router.post("/voice", summary="Twilio Incoming Call Webhook")
async def voice_webhook(
    request: Request,
    CallSid: str = Form(default="SIMULATED_CALL_SID"),
    From: str = Form(default=""),
    To: str = Form(default=""),
    CallStatus: Optional[str] = Form(default="ringing"),
    db: Session = Depends(get_db)
):
    """
    Twilio webhook called when a phone call is received.
    Greets the caller and asks for their request using TwiML <Gather>.
    """
    logger.info(f"[Voice Webhook] Incoming call: CallSid={CallSid}, From={From}, To={To}, Status={CallStatus}")

    session = _get_or_create_call_session(CallSid, caller_phone=From)

    # Check if caller matches an existing customer in CRM
    customer = crud.get_customer_by_phone(db, From) if From else None
    if customer:
        session["customer_id"] = customer.id
        greeting = f"Hello {customer.name}! Thank you for calling Customer Support. How can I help you today?"
        logger.info(f"[Voice Webhook] Matched caller {From} to Customer {customer.id} ({customer.name})")
    else:
        greeting = "Hello! Thank you for calling Customer Support. How can I assist you with your account or service today?"

    session["transcript_lines"].append(f"Agent: {greeting}")
    session["history"].append({"role": "assistant", "content": greeting})

    # Persist initial call record
    crud.upsert_call_summary_by_sid(
        db=db,
        call_sid=CallSid,
        summary_data={
            "customer_id": session["customer_id"],
            "caller_phone": From,
            "transcript": "\n".join(session["transcript_lines"]),
            "summary": "Call initiated.",
            "sentiment": "neutral",
        }
    )

    twiml_xml = build_gather_twiml(message=greeting, action_url="/process-call")
    return Response(content=twiml_xml, media_type="application/xml")


@router.post("/process-call", summary="Twilio Speech Result Webhook")
async def process_call_webhook(
    CallSid: str = Form(default="SIMULATED_CALL_SID"),
    From: str = Form(default=""),
    SpeechResult: Optional[str] = Form(default=None),
    Confidence: Optional[float] = Form(default=None),
    Digits: Optional[str] = Form(default=None),
    db: Session = Depends(get_db)
):
    """
    Twilio webhook called when caller speech is transcribed.
    Dispatches speech to DeepSeek AI agent with tools, updates CRM, and returns next TwiML.
    """
    logger.info(f"[Process Call] CallSid={CallSid}, From={From}, SpeechResult='{SpeechResult}', Confidence={Confidence}")

    session = _get_or_create_call_session(CallSid, caller_phone=From)

    # If caller provided no speech input
    user_speech = (SpeechResult or "").strip()
    if not user_speech:
        if Digits:
            user_speech = f"Customer entered digits: {Digits}"
        else:
            logger.info(f"[Process Call] Empty speech result for CallSid={CallSid}")
            repeat_msg = "I did not hear anything. Could you please state your request or question?"
            twiml_xml = build_gather_twiml(message=repeat_msg, action_url="/process-call")
            return Response(content=twiml_xml, media_type="application/xml")

    # Record user turn in transcript
    session["transcript_lines"].append(f"Customer: {user_speech}")

    # Prepare caller info context
    customer = None
    if session["customer_id"]:
        customer = crud.get_customer(db, session["customer_id"])
    elif From:
        customer = crud.get_customer_by_phone(db, From)
        if customer:
            session["customer_id"] = customer.id

    caller_info = {
        "phone": From or (customer.phone if customer else None),
        "customer_id": customer.id if customer else session.get("customer_id"),
        "name": customer.name if customer else None,
        "plan": customer.plan if customer else None,
    }

    # Execute AI Agent Turn
    agent_response: AgentExecutionResponse = run_agent_turn(
        db=db,
        user_speech=user_speech,
        conversation_history=session["history"],
        caller_info=caller_info,
        customer_id=session["customer_id"]
    )

    # Update session customer_id if discovered/resolved in turn
    if agent_response.customer_id:
        session["customer_id"] = agent_response.customer_id

    # Record any tools executed
    for tool_call in agent_response.tools_called:
        session["tools_used"].append(f"{tool_call.tool_name}({tool_call.tool_args}) -> {tool_call.result.get('message', 'ok')}")

    # Update conversation history and transcript
    session["history"].append({"role": "user", "content": user_speech})
    session["history"].append({"role": "assistant", "content": agent_response.spoken_response})
    session["transcript_lines"].append(f"Agent: {agent_response.spoken_response}")

    full_transcript = "\n".join(session["transcript_lines"])
    tools_summary_str = "; ".join(session["tools_used"]) if session["tools_used"] else None

    # Generate or update Call Summary
    ai_summary = generate_call_summary(
        transcript=full_transcript,
        customer_id=session["customer_id"],
        tools_summary=tools_summary_str
    )

    # Persist summary to SQLite
    crud.upsert_call_summary_by_sid(
        db=db,
        call_sid=CallSid,
        summary_data={
            "customer_id": session["customer_id"],
            "caller_phone": From or (customer.phone if customer else None),
            "transcript": full_transcript,
            "summary": ai_summary.get("summary", ""),
            "sentiment": ai_summary.get("sentiment", "neutral"),
            "action_items": ai_summary.get("action_items") or tools_summary_str,
        }
    )

    # Return appropriate TwiML based on should_hangup flag
    if agent_response.should_hangup:
        logger.info(f"[Process Call] Ending call for CallSid={CallSid}")
        twiml_xml = build_say_and_hangup_twiml(message=agent_response.spoken_response)
        # Clean up session from memory
        CALL_SESSIONS.pop(CallSid, None)
    else:
        twiml_xml = build_gather_twiml(message=agent_response.spoken_response, action_url="/process-call")

    return Response(content=twiml_xml, media_type="application/xml")


@router.post("/voice/simulate", summary="Test AI Voice Conversation via JSON (No Twilio required)")
async def simulate_voice_turn(
    speech: str,
    customer_id: Optional[str] = None,
    call_sid: str = "DEV_SIMULATION_001",
    caller_phone: Optional[str] = "+15551234567",
    db: Session = Depends(get_db)
):
    """
    Developer convenience endpoint to test the Voice AI pipeline with pure JSON without needing Twilio.
    """
    session = _get_or_create_call_session(call_sid, caller_phone=caller_phone)
    if customer_id:
        session["customer_id"] = customer_id

    customer = crud.get_customer(db, session["customer_id"]) if session["customer_id"] else None
    caller_info = {
        "phone": caller_phone,
        "customer_id": customer.id if customer else session.get("customer_id"),
        "name": customer.name if customer else None,
        "plan": customer.plan if customer else None,
    }

    session["transcript_lines"].append(f"Customer: {speech}")

    agent_response = run_agent_turn(
        db=db,
        user_speech=speech,
        conversation_history=session["history"],
        caller_info=caller_info,
        customer_id=session["customer_id"]
    )

    if agent_response.customer_id:
        session["customer_id"] = agent_response.customer_id

    session["history"].append({"role": "user", "content": speech})
    session["history"].append({"role": "assistant", "content": agent_response.spoken_response})
    session["transcript_lines"].append(f"Agent: {agent_response.spoken_response}")

    for t in agent_response.tools_called:
        session["tools_used"].append(f"{t.tool_name} -> {t.result}")

    full_transcript = "\n".join(session["transcript_lines"])
    summary_data = generate_call_summary(
        transcript=full_transcript,
        customer_id=session["customer_id"],
        tools_summary="; ".join(session["tools_used"])
    )

    db_summary = crud.upsert_call_summary_by_sid(
        db=db,
        call_sid=call_sid,
        summary_data={
            "customer_id": session["customer_id"],
            "caller_phone": caller_phone,
            "transcript": full_transcript,
            "summary": summary_data.get("summary"),
            "sentiment": summary_data.get("sentiment"),
            "action_items": summary_data.get("action_items"),
        }
    )

    return {
        "call_sid": call_sid,
        "spoken_response": agent_response.spoken_response,
        "tools_called": [t.model_dump() for t in agent_response.tools_called],
        "should_hangup": agent_response.should_hangup,
        "customer_id": session["customer_id"],
        "call_summary": {
            "id": db_summary.id,
            "summary": db_summary.summary,
            "sentiment": db_summary.sentiment,
            "action_items": db_summary.action_items,
            "transcript": db_summary.transcript,
        }
    }
