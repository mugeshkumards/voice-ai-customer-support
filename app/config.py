"""
Application configuration management using Pydantic Settings.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application settings
    APP_NAME: str = "AI Voice Customer Support Agent"
    APP_ENV: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database settings
    DATABASE_URL: str = "sqlite:///./voice_support.db"

    # DeepSeek API settings
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_TIMEOUT: float = 30.0

    # Twilio API settings
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # TwiML Voice settings
    VOICE_NAME: str = "Polly.Amy"  # Amazon Polly voice in Twilio
    VOICE_LANGUAGE: str = "en-US"
    SPEECH_TIMEOUT: str = "auto"
    MAX_GATHER_TIME: int = 10

    @property
    def is_deepseek_configured(self) -> bool:
        """Check if DeepSeek API key is present."""
        return bool(self.DEEPSEEK_API_KEY and self.DEEPSEEK_API_KEY.strip() != "" and not self.DEEPSEEK_API_KEY.startswith("your_"))

    @property
    def is_twilio_configured(self) -> bool:
        """Check if Twilio credentials are configured."""
        return bool(
            self.TWILIO_ACCOUNT_SID
            and not self.TWILIO_ACCOUNT_SID.startswith("your_")
            and self.TWILIO_AUTH_TOKEN
            and not self.TWILIO_AUTH_TOKEN.startswith("your_")
        )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
