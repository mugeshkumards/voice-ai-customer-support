"""
TwiML (Twilio Markup Language) response generators for voice interactions.
"""

from twilio.twiml.voice_response import VoiceResponse, Gather
from app.config import get_settings

settings = get_settings()


def build_gather_twiml(
    message: str,
    action_url: str = "/process-call",
    voice: str = None,
    language: str = None,
    timeout_message: str = "We did not receive any input. Please call back if you need assistance. Goodbye."
) -> str:
    """
    Generate TwiML with a <Gather> element that prompts the caller and listens for speech.

    Args:
        message: Spoken prompt to play before speech collection.
        action_url: Target URL for Twilio to POST transcribed speech.
        voice: TTS voice name (default from settings).
        language: Speech recognition & TTS language (default from settings).
        timeout_message: Message to play if no speech was detected.

    Returns:
        XML string compliant with Twilio TwiML Voice standard.
    """
    selected_voice = voice or settings.VOICE_NAME
    selected_lang = language or settings.VOICE_LANGUAGE

    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=action_url,
        method="POST",
        speech_timeout=settings.SPEECH_TIMEOUT,
        language=selected_lang,
    )
    gather.say(message, voice=selected_voice, language=selected_lang)
    response.append(gather)

    # Fallback if caller did not speak during Gather
    response.say(timeout_message, voice=selected_voice, language=selected_lang)
    response.hangup()

    return str(response)


def build_say_and_hangup_twiml(
    message: str,
    voice: str = None,
    language: str = None
) -> str:
    """
    Generate TwiML that speaks a final message and hangs up the call.
    """
    selected_voice = voice or settings.VOICE_NAME
    selected_lang = language or settings.VOICE_LANGUAGE

    response = VoiceResponse()
    response.say(message, voice=selected_voice, language=selected_lang)
    response.hangup()

    return str(response)
