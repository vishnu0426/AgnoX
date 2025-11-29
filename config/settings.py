"""
Configuration Settings for Customer Service Voice Agent
Includes inbound and outbound call configurations
Complete version with all variables
"""

from typing import Optional, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation"""

    # ==================== LIVEKIT CONFIGURATION ====================
    livekit_url: str = Field(..., env="LIVEKIT_URL")
    livekit_api_key: str = Field(..., env="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(..., env="LIVEKIT_API_SECRET")

    # ==================== SIP TRUNK CONFIGURATION ====================
    # Inbound trunk (from your screenshot: ST_UE2fnCs4yxSo)
    default_inbound_trunk_id: Optional[str] = Field(
        None,
        env="DEFAULT_INBOUND_TRUNK_ID",
        description="Default inbound SIP trunk ID",
    )

    # Outbound trunk (from your screenshot: ST_SXWwu7ArVEYE)
    default_outbound_trunk_id: Optional[str] = Field(
        None,
        env="DEFAULT_OUTBOUND_TRUNK_ID",
        description="Default outbound SIP trunk ID for making calls",
    )

    # Caller ID for outbound calls
    default_caller_id: Optional[str] = Field(
        None,
        env="DEFAULT_CALLER_ID",
        description="Default phone number to use as caller ID (E.164 format)",
    )

    # Phone numbers (stored as string, parsed to list)
    company_phone_numbers: str = Field(
        "",
        env="COMPANY_PHONE_NUMBERS",
        description="Comma-separated list of company phone numbers",
    )

    # ==================== OPENAI CONFIGURATION ====================
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-realtime-preview-2024-12-17", env="OPENAI_MODEL")
    openai_voice: str = Field("alloy", env="OPENAI_VOICE")
    openai_temperature: float = Field(0.8, env="OPENAI_TEMPERATURE")

    # ==================== DATABASE CONFIGURATION ====================
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_min_size: int = Field(5, env="DATABASE_POOL_MIN_SIZE")
    database_pool_max_size: int = Field(20, env="DATABASE_POOL_MAX_SIZE")

    # ==================== REDIS CONFIGURATION ====================
    redis_url: Optional[str] = Field(
        "redis://localhost:6379/0",
        env="REDIS_URL",
        description="Redis connection URL",
    )

    # ==================== API CONFIGURATION ====================
    api_secret_key: str = Field(..., env="API_SECRET_KEY")
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    allowed_origins: str = Field(
        "http://localhost:3000,http://localhost:8000",
        env="ALLOWED_ORIGINS",
    )

    # ==================== CALL HANDLING CONFIGURATION ====================
    max_call_duration_seconds: int = Field(
        3600,
        env="MAX_CALL_DURATION_SECONDS",
        description="Maximum call duration (1 hour default)",
    )

    call_recording_enabled: bool = Field(
        True,
        env="CALL_RECORDING_ENABLED",
    )

    sentiment_analysis_enabled: bool = Field(
        True,
        env="SENTIMENT_ANALYSIS_ENABLED",
    )

    auto_transfer_on_negative_sentiment: bool = Field(
        False,
        env="AUTO_TRANSFER_ON_NEGATIVE_SENTIMENT",
    )

    # ==================== QUEUE CONFIGURATION ====================
    queue_enabled: bool = Field(True, env="QUEUE_ENABLED")
    queue_check_interval_seconds: int = Field(2, env="QUEUE_CHECK_INTERVAL_SECONDS")
    max_queue_wait_time_minutes: int = Field(30, env="MAX_QUEUE_WAIT_TIME_MINUTES")

    # ==================== NOTIFICATION CONFIGURATION ====================
    notification_enabled: bool = Field(False, env="NOTIFICATION_ENABLED")
    notification_webhook_url: Optional[str] = Field(
        None,
        env="NOTIFICATION_WEBHOOK_URL",
    )

    # ==================== LOGGING CONFIGURATION ====================
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file_path: str = Field("logs/agent.log", env="LOG_FILE_PATH")

    # ==================== MONITORING CONFIGURATION ====================
    sentry_dsn: Optional[str] = Field(None, env="SENTRY_DSN")
    metrics_enabled: bool = Field(True, env="METRICS_ENABLED")

    # ==================== DEVELOPMENT/PRODUCTION ====================
    debug: bool = Field(False, env="DEBUG")
    environment: str = Field("production", env="ENVIRONMENT")
    max_workers: int = Field(
        4,
        env="MAX_WORKERS",
        description="Number of worker processes",
    )

    # ==================== FEATURE FLAGS ====================
    enable_video: bool = Field(False, env="ENABLE_VIDEO")
    enable_chat: bool = Field(True, env="ENABLE_CHAT")
    enable_recordings: bool = Field(True, env="ENABLE_RECORDINGS")
    auto_transfer_timeout: Optional[int] = Field(
        None,
        env="AUTO_TRANSFER_TIMEOUT",
        description="Timeout (in seconds) before automatically transferring the call",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow extra fields in case user has custom variables
        extra = "ignore"

    # ==================== VALIDATORS & HELPERS ====================

    @field_validator("allowed_origins")
    @classmethod
    def parse_allowed_origins(cls, v: str) -> str:
        """Ensure allowed origins is a non-empty comma-separated string."""
        if not v:
            return "http://localhost:3000,http://localhost:8000"
        return v

    @field_validator("auto_transfer_timeout", mode="before")
    @classmethod
    def empty_str_timeout_to_none(cls, v):
        """Treat empty AUTO_TRANSFER_TIMEOUT as None instead of failing int parsing."""
        if v == "":
            return None
        return v

    @property
    def parsed_allowed_origins(self) -> List[str]:
        """Parse comma-separated origins into list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def parsed_company_phone_numbers(self) -> List[str]:
        """Parse comma-separated phone numbers into list."""
        if not self.company_phone_numbers:
            return []
        return [num.strip() for num in self.company_phone_numbers.split(",") if num.strip()]

    @property
    def enable_metrics(self) -> bool:
        """Compatibility alias for main.py (settings.enable_metrics)."""
        return self.metrics_enabled

    def validate_required_fields(self) -> None:
        """
        Ensure critical settings are present.
        Raise a clear error if anything important is missing.
        """
        required_fields = [
            "livekit_url",
            "livekit_api_key",
            "livekit_api_secret",
            "database_url",
            "api_secret_key",
        ]

        missing = []
        for field_name in required_fields:
            value = getattr(self, field_name, None)
            if value in (None, ""):
                missing.append(field_name)

        if missing:
            raise ValueError(
                f"Missing required settings: {', '.join(missing)}. "
                "Check your environment variables / .env file."
            )


# Global settings instance
settings = Settings()
