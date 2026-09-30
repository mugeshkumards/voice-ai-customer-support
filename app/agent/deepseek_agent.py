"""
DeepSeek AI Agent with Tool Calling and Call Summarization for Voice Support.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from openai import OpenAI

from app.config import get_settings
from app.agent.tools import AGENT_TOOLS_SCHEMA, execute_tool_call
from app.schemas import AgentToolResult, AgentExecutionResponse
from app.utils.logger import logger

settings = get_settings()


def get_deepseek_client() -> Optional[OpenAI]:
    """Return configured OpenAI client targeting DeepSeek API endpoint."""
    if not settings.is_deepseek_configured:
        return None
    return OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
        timeout=settings.DEEPSEEK_TIMEOUT,
    )


VOICE_AGENT_SYSTEM_PROMPT = """You are a helpful, empathetic, and efficient AI Voice Customer Support Agent.
You are speaking directly with a customer over a live phone call.

IMPORTANT VOICE GUIDELINES:
1. Speak in concise, natural, and conversational sentences suitable for Text-to-Speech (TTS).
2. NEVER use markdown formatting, bullet points, asterisks (* or **), tables, or emojis in your speech.
3. Keep responses brief (1-3 sentences) so the caller is not overwhelmed listening over the phone.
4. When you perform an action (like creating a ticket or updating an account), clearly tell the caller what you did (including ticket ID).
5. If the caller asks a question or has an issue, ask clarifying questions or call the appropriate tool.
6. If the caller says goodbye, expresses they have no further questions, or thanks you to end the call, provide a warm closing (e.g., "Thank you for calling. Have a wonderful day! Goodbye.").

AVAILABLE TOOLS:
- get_customer: Retrieve customer details and existing support tickets using customer_id.
- update_customer: Update customer details (email, phone, plan, status, notes) using customer_id and data dictionary.
- create_support_ticket: File a new support ticket when an issue or complaint is reported using customer_id and issue description.

CONTEXT:
{context_str}
"""


def format_context_prompt(caller_info: Optional[Dict[str, Any]] = None, customer_id: Optional[str] = None) -> str:
    """Format contextual caller info into system prompt."""
    lines = []
    if caller_info:
        if caller_info.get("phone"):
            lines.append(f"Caller Phone Number: {caller_info['phone']}")
        if caller_info.get("customer_id") or customer_id:
            cid = caller_info.get("customer_id") or customer_id
            lines.append(f"Identified Customer ID: {cid}")
        if caller_info.get("name"):
            lines.append(f"Customer Name: {caller_info['name']}")
        if caller_info.get("plan"):
            lines.append(f"Subscription Plan: {caller_info['plan']}")
    else:
        lines.append("Caller identity: Not yet verified. Ask for their Customer ID or Name if needed.")
    return "\n".join(lines)


def run_agent_turn(
    db: Session,
    user_speech: str,
    conversation_history: List[Dict[str, str]],
    caller_info: Optional[Dict[str, Any]] = None,
    customer_id: Optional[str] = None
) -> AgentExecutionResponse:
    """
    Execute one turn of the AI voice conversation with DeepSeek function calling.

    Args:
        db: Active SQLAlchemy Session
        user_speech: Transcribed speech from caller
        conversation_history: List of previous messages [{"role": "user"|"assistant", "content": "..."}]
        caller_info: Optional dictionary with caller phone/account context
        customer_id: Optional verified customer ID

    Returns:
        AgentExecutionResponse with spoken response, tools executed, and hangup flag.
    """
    logger.info(f"[Agent] Processing turn for user_speech: '{user_speech}' (customer_id: {customer_id})")

    context_str = format_context_prompt(caller_info, customer_id)
    system_prompt = VOICE_AGENT_SYSTEM_PROMPT.format(context_str=context_str)

    client = get_deepseek_client()

    # Fallback mode if DeepSeek API key is not configured or in test mode
    if not client:
        logger.warning("[Agent] DeepSeek API key not configured. Using intelligent mock fallback agent.")
        return _mock_agent_turn(db, user_speech, caller_info, customer_id)

    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": user_speech})

    tools_called: List[AgentToolResult] = []
    max_tool_iterations = 4
    iteration = 0

    try:
        while iteration < max_tool_iterations:
            iteration += 1
            response = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                tools=AGENT_TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.3,
            )

            response_message = response.choices[0].message
            tool_calls = getattr(response_message, "tool_calls", None)

            if not tool_calls:
                # No more tools needed, we have our final text response
                spoken_text = response_message.content or "I understand. How else may I assist you today?"
                should_hangup = _detect_hangup_intent(user_speech, spoken_text)
                return AgentExecutionResponse(
                    spoken_response=spoken_text,
                    tools_called=tools_called,
                    should_hangup=should_hangup,
                    customer_id=customer_id
                )

            # Append the assistant's message with tool calls
            messages.append(response_message)

            for tool_call in tool_calls:
                func_name = tool_call.function.name
                raw_args = tool_call.function.arguments or "{}"
                try:
                    args = json.loads(raw_args)
                except json.JSONDecodeError:
                    args = {}

                logger.info(f"[Agent] Tool call requested: {func_name} with arguments: {args}")

                # If customer_id is provided in context and missing in args, fill it
                if "customer_id" in args and not args["customer_id"] and customer_id:
                    args["customer_id"] = customer_id

                tool_output = execute_tool_call(db, func_name, args)

                # If we fetched or updated a customer, track the customer_id
                if func_name in ["get_customer", "update_customer", "create_support_ticket"]:
                    if tool_output.get("success"):
                        if "customer" in tool_output and "id" in tool_output["customer"]:
                            customer_id = tool_output["customer"]["id"]
                        elif "ticket" in tool_output and "customer_id" in tool_output["ticket"]:
                            customer_id = tool_output["ticket"]["customer_id"]

                tools_called.append(
                    AgentToolResult(
                        tool_name=func_name,
                        tool_args=args,
                        result=tool_output,
                        success=tool_output.get("success", False),
                        error_message=tool_output.get("error")
                    )
                )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_output)
                })

        # Fallback if loop exceeded
        return AgentExecutionResponse(
            spoken_response="I have processed your request. Is there anything else I can help you with?",
            tools_called=tools_called,
            should_hangup=False,
            customer_id=customer_id
        )

    except Exception as e:
        logger.error(f"[Agent] Error during DeepSeek LLM execution: {str(e)}", exc_info=True)
        return AgentExecutionResponse(
            spoken_response="I apologize, but I encountered a temporary technical glitch. Could you please repeat that?",
            tools_called=tools_called,
            should_hangup=False,
            customer_id=customer_id
        )


def _detect_hangup_intent(user_speech: str, spoken_text: str) -> bool:
    """Determine if the conversation reached a natural conclusion."""
    lower_user = user_speech.lower().strip()
    hangup_phrases = [
        "goodbye", "bye", "that is all", "that's all", "nothing else",
        "no more questions", "have a good day", "have a nice day", "thank you bye"
    ]
    for phrase in hangup_phrases:
        if phrase in lower_user:
            return True
    return False


def _mock_agent_turn(
    db: Session,
    user_speech: str,
    caller_info: Optional[Dict[str, Any]] = None,
    customer_id: Optional[str] = None
) -> AgentExecutionResponse:
    """
    Fallback agent when DeepSeek API key is not yet set.
    Provides deterministic tool dispatching so the application works out-of-the-box in development.
    """
    lower = user_speech.lower()
    tools_called: List[AgentToolResult] = []
    effective_cid = customer_id or (caller_info.get("customer_id") if caller_info else None) or "CUST-1001"

    # 1. Customer inquiry
    if any(k in lower for k in ["my account", "customer details", "who am i", "check my plan", "get customer"]):
        result = execute_tool_call(db, "get_customer", {"customer_id": effective_cid})
        tools_called.append(AgentToolResult(tool_name="get_customer", tool_args={"customer_id": effective_cid}, result=result))
        if result.get("success"):
            cust = result["customer"]
            msg = f"Hello {cust['name']}, I found your account {cust['id']}. You are currently on the {cust['plan']} plan. How can I assist you today?"
        else:
            msg = f"I could not locate an account for ID {effective_cid}. Could you please verify your customer ID?"
        return AgentExecutionResponse(spoken_response=msg, tools_called=tools_called, customer_id=effective_cid)

    # 2. Support ticket creation
    elif any(k in lower for k in ["ticket", "issue", "problem", "broken", "complaint", "error", "not working", "billing"]):
        issue_text = user_speech
        result = execute_tool_call(db, "create_support_ticket", {"customer_id": effective_cid, "issue": issue_text, "priority": "medium"})
        tools_called.append(AgentToolResult(tool_name="create_support_ticket", tool_args={"customer_id": effective_cid, "issue": issue_text}, result=result))
        if result.get("success"):
            tick = result["ticket"]
            msg = f"I have logged support ticket {tick['id']} for your issue. Our technical team is reviewing it. Is there anything else I can help with?"
        else:
            msg = f"I was unable to create the ticket because: {result.get('error')}. Please verify your customer ID."
        return AgentExecutionResponse(spoken_response=msg, tools_called=tools_called, customer_id=effective_cid)

    # 3. Update customer
    elif any(k in lower for k in ["update my", "change my email", "change my phone", "upgrade plan"]):
        update_data = {}
        if "email" in lower:
            update_data["email"] = "updated_caller@example.com"
        if "premium" in lower or "upgrade" in lower:
            update_data["plan"] = "Premium"
        if not update_data:
            update_data["notes"] = f"Caller requested update: {user_speech}"

        result = execute_tool_call(db, "update_customer", {"customer_id": effective_cid, "data": update_data})
        tools_called.append(AgentToolResult(tool_name="update_customer", tool_args={"customer_id": effective_cid, "data": update_data}, result=result))
        if result.get("success"):
            msg = f"I have successfully updated your account information for {effective_cid}. What else can I do for you?"
        else:
            msg = f"I encountered an issue updating your account: {result.get('error')}."
        return AgentExecutionResponse(spoken_response=msg, tools_called=tools_called, customer_id=effective_cid)

    # 4. Goodbye / Hangup
    elif _detect_hangup_intent(user_speech, ""):
        return AgentExecutionResponse(
            spoken_response="Thank you for calling customer support. Have a wonderful day! Goodbye.",
            tools_called=[],
            should_hangup=True,
            customer_id=effective_cid
        )

    # 5. Default conversational fallback
    else:
        return AgentExecutionResponse(
            spoken_response=f"I heard you say: {user_speech}. How would you like me to assist with your account or support request?",
            tools_called=[],
            should_hangup=False,
            customer_id=effective_cid
        )


def generate_call_summary(
    transcript: str,
    customer_id: Optional[str] = None,
    tools_summary: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate an AI summary, sentiment, and action items from the call transcript.
    """
    client = get_deepseek_client()

    if not transcript:
        return {
            "summary": "Call ended without significant speech input.",
            "sentiment": "neutral",
            "action_items": "None"
        }

    if not client:
        # Fallback summary generation
        return {
            "summary": f"Customer interaction recorded. Conversation transcript: {transcript[:200]}...",
            "sentiment": "neutral",
            "action_items": tools_summary or "No follow-up action items specified."
        }

    prompt = f"""Analyze the following customer support phone call transcript and return a JSON object with:
- summary: A concise 2-sentence summary of what the customer called about and how it was handled.
- sentiment: One of 'positive', 'neutral', 'frustrated', 'negative'.
- action_items: Follow-up actions, created tickets, or account changes.

Customer ID: {customer_id or 'Unknown'}
Tools executed during call: {tools_summary or 'None'}

Transcript:
{transcript}

Return ONLY valid JSON matching:
{{"summary": "...", "sentiment": "...", "action_items": "..."}}
"""

    try:
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return {
            "summary": data.get("summary", "Summary unavailable."),
            "sentiment": data.get("sentiment", "neutral"),
            "action_items": data.get("action_items", "None")
        }
    except Exception as e:
        logger.error(f"[Summary] Error generating AI call summary: {str(e)}")
        return {
            "summary": f"Call completed. Transcript length: {len(transcript)} chars.",
            "sentiment": "neutral",
            "action_items": tools_summary or "None"
        }
