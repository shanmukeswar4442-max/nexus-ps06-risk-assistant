"""
Centralized Configuration Module (NexusTiq24 PS06).
Eliminates magic strings across the codebase.
"""

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Transaction Risk Investigation Assistant"
    TRACK_ID: str = "PS06"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # Gemini Configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"
    DEFAULT_GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")
    LLM_TIMEOUT_SECONDS: int = 10
    LLM_MAX_RETRIES: int = 3
    
    # Financial Baseline Thresholds (INR Defaults)
    DEFAULT_CURRENCY: str = "INR"
    LARGE_TRANSFER_P90_MULTIPLIER: float = 3.0
    LARGE_TRANSFER_MIN_AMOUNT: float = 100000.0
    PAYEE_BURST_WINDOW_HOURS: float = 48.0
    PAYEE_BURST_MIN_TOTAL: float = 150000.0
    ODD_HOURS_START: int = 1
    ODD_HOURS_END: int = 4
    ODD_HOURS_MIN_AMOUNT: float = 25000.0
    VELOCITY_BURST_MIN_AMOUNT: float = 100000.0


settings = Settings()
