"""
Tests for DeepSeek Agent LLM loop with mocked OpenAI completions.
"""

from unittest.mock import MagicMock, patch
from app.agent.deepseek_agent import run_agent_turn, generate_call_summary, _detect_hangup_intent
from app.schemas import AgentExecutionResponse


def test_detect_hangup_intent():
    """Verify hangup phrase detection."""
    assert _detect_hangup_intent("Thank you, that's all. Goodbye!", "") is True
    assert _detect_hangup_intent("no more questions", "") is True
    assert _detect_hangup_intent("I need help with my bill", "") is False


def test_deepseek_tool_calling_flow(db):
    """
    Test the DeepSeek function calling loop where LLM returns a tool call
    followed by the final conversational response.
    """
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_abc123"
    mock_tool_call.function.name = "get_customer"
    mock_tool_call.function.arguments = '{"customer_id": "CUST-TEST-001"}'

    # First LLM response: emits tool call
    first_response = MagicMock()
    first_msg = MagicMock()
    first_msg.tool_calls = [mock_tool_call]
    first_msg.content = None
    first_response.choices = [MagicMock(message=first_msg)]

    # Second LLM response: emits final spoken text after tool output is provided
    second_response = MagicMock()
    second_msg = MagicMock()
    second_msg.tool_calls = None
    second_msg.content = "Hello Test User, I see your Premium account is active. How can I help you today?"
    second_response.choices = [MagicMock(message=second_msg)]

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [first_response, second_response]

    with patch("app.agent.deepseek_agent.get_deepseek_client", return_value=mock_client):
        result: AgentExecutionResponse = run_agent_turn(
            db=db,
            user_speech="Can you check my account status?",
            conversation_history=[],
            caller_info={"phone": "+15550001111"},
            customer_id="CUST-TEST-001"
        )

        assert len(result.tools_called) == 1
        assert result.tools_called[0].tool_name == "get_customer"
        assert result.tools_called[0].result["success"] is True
        assert "Hello Test User" in result.spoken_response
        assert result.should_hangup is False


def test_deepseek_summary_generation():
    """Test AI Call Summary generation with structured JSON response."""
    mock_response = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = '{"summary": "Caller asked about account plan and verified active status.", "sentiment": "positive", "action_items": "None"}'
    mock_response.choices = [MagicMock(message=mock_msg)]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("app.agent.deepseek_agent.get_deepseek_client", return_value=mock_client):
        summary_res = generate_call_summary(
            transcript="Customer: Check my account\nAgent: Your account is active.",
            customer_id="CUST-TEST-001"
        )

        assert "Caller asked about account plan" in summary_res["summary"]
        assert summary_res["sentiment"] == "positive"
        assert summary_res["action_items"] == "None"
