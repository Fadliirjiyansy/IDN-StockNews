"""
config.py — IDX Event Tracker Configuration
Reads from environment variables. Use .env file for local dev.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── PostgreSQL ──────────────────────────────────────────
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "n8n")
    DB_USER: str = os.getenv("DB_USER", "n8n")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    # ── Flask API ────────────────────────────────────────────
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "5055"))
    API_DEBUG: bool = os.getenv("API_DEBUG", "false").lower() == "true"

    # ── Scraper Settings ─────────────────────────────────────
    SCRAPER_TIMEOUT: int = int(os.getenv("SCRAPER_TIMEOUT", "30"))
    SCRAPER_MAX_RETRIES: int = int(os.getenv("SCRAPER_MAX_RETRIES", "3"))

    # ── Notification Window ──────────────────────────────────
    # Hours to look back when fetching "new" events for alerting
    NEW_EVENTS_WINDOW_HOURS: int = int(os.getenv("NEW_EVENTS_WINDOW_HOURS", "7"))

    # ── IDX Ecosystem Endpoints ──────────────────────────────
    IDX_BASE_URL: str = "https://www.idx.co.id"
    IDX_API_BASE: str = "https://www.idx.co.id/primary"
    EIPO_BASE_URL: str = "https://www.e-ipo.co.id"
    KSEI_BASE_URL: str = "https://web.ksei.co.id"

    @classmethod
    def dsn(cls) -> str:
        """Return PostgreSQL DSN string."""
        return (
            f"host={cls.DB_HOST} "
            f"port={cls.DB_PORT} "
            f"dbname={cls.DB_NAME} "
            f"user={cls.DB_USER} "
            f"password={cls.DB_PASSWORD}"
        )


config = Config()
