"""
Lean MVP Configuration
======================

Central configuration for the Buyer Intelligence backend.
Loads from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Runtime values come from the recipient-selected process environment.


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # =========================================================================
    # Server
    # =========================================================================
    HOST: str = "127.0.0.1"
    PORT: int = 8000  # Standard backend port
    DEBUG: bool = False
    
    # =========================================================================
    # Database (Supabase)
    # =========================================================================
    SUPABASE_URL: str = os.getenv(
        "NEXT_PUBLIC_SUPABASE_URL", 
        ""
    )
    SUPABASE_ANON_KEY: str = os.getenv(
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
        ""
    )
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv(
        "SUPABASE_SERVICE_ROLE_KEY",
        ""
    )
    
    # Direct Postgres connection (for asyncpg)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    
    @property
    def postgres_url(self) -> str:
        """Get Postgres connection URL for asyncpg."""
        if self.DATABASE_URL:
            # Convert postgres:// to postgresql:// if needed
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        # Fallback: Use Supabase REST API instead (no direct DB needed for MVP)
        raise ValueError(
            "DATABASE_URL not set. Get it from Supabase Dashboard → Settings → Database → Connection string (URI)"
        )
    
    # =========================================================================
    # Gemini AI
    # =========================================================================
    GOOGLE_AI_API_KEY: str = os.getenv("GOOGLE_AI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # Use model alias; resolved in `pipeline/gemini_client.py` (avoids hardcoding non-existent names).
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "flash")
    
    @property
    def gemini_key(self) -> str:
        """Get best available Gemini API key."""
        return self.GOOGLE_AI_API_KEY or self.GEMINI_API_KEY
    
    # =========================================================================
    # Scraping
    # =========================================================================
    SCRAPFLY_API_KEY: str = os.getenv("SCRAPFLY_API_KEY", "")
    SCRAPINGDOG_API_KEY: str = os.getenv("SCRAPINGDOG_API_KEY", "")
    SCRAPING_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    CASAFARI_ENABLED: bool = os.getenv("CASAFARI_ENABLED", "true").lower() == "true"
    CASAFARI_REUSE_ONLY: bool = os.getenv("CASAFARI_REUSE_ONLY", "false").lower() == "true"
    
    # =========================================================================
    # Place Curation APIs
    # =========================================================================
    FOURSQUARE_API_KEY: str = os.getenv("FOURSQUARE_API_KEY", "")
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    TRANSITLAND_API_KEY: str = os.getenv("TRANSITLAND_API_KEY", "")
    
    # =========================================================================
    # WhatsApp (Twilio — legacy)
    # =========================================================================
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "")  # e.g. whatsapp:+12025550100
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "")  # e.g. https://abc123.ngrok.io (for image serving)

    # =========================================================================
    # WhatsApp (Meta Cloud API — primary)
    # =========================================================================
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")

    # =========================================================================
    # Comms (Resend inbound email webhooks)
    # =========================================================================
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    # Resend uses Svix-style headers: svix-id, svix-timestamp, svix-signature
    # Secret format typically starts with "whsec_..."
    RESEND_WEBHOOK_SECRET: str = os.getenv("RESEND_WEBHOOK_SECRET", "")
    LEO_PROJECT_EMAIL_DOMAIN: str = os.getenv("LEO_PROJECT_EMAIL_DOMAIN", "")
    
    # =========================================================================
    # CORS
    # =========================================================================
    CORS_ORIGINS: list[str] = ["http://localhost:3002", "http://127.0.0.1:3002"]
    
    model_config = SettingsConfigDict(
        extra="ignore",
    )


# Singleton settings instance
settings = Settings()


# Quick access functions
def get_supabase_url() -> str:
    return settings.SUPABASE_URL


def get_supabase_key() -> str:
    """Get service role key (preferred) or anon key."""
    return settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY


def get_gemini_key() -> str:
    return settings.gemini_key


# Debug logging
if settings.DEBUG:
    print(f"[Config] Loaded settings:")
    print(f"  - SUPABASE_URL: {settings.SUPABASE_URL[:40]}...")
    print(f"  - GEMINI_KEY: {'✓' if settings.gemini_key else '✗'}")
    print(f"  - SCRAPFLY_KEY: {'✓' if settings.SCRAPFLY_API_KEY else '✗'}")
    print(f"  - SCRAPINGDOG_KEY: {'✓' if settings.SCRAPINGDOG_API_KEY else '✗'}")
    print(f"  - FOURSQUARE_KEY: {'✓' if settings.FOURSQUARE_API_KEY else '✗'}")
    print(f"  - GOOGLE_MAPS_KEY: {'✓' if settings.GOOGLE_MAPS_API_KEY else '✗'}")
    print(f"  - TRANSITLAND_KEY: {'✓' if settings.TRANSITLAND_API_KEY else '✗'}")
    print(f"  - TWILIO_SID: {'✓' if settings.TWILIO_ACCOUNT_SID else '✗'}")
    print(f"  - TWILIO_WHATSAPP: {'✓' if settings.TWILIO_WHATSAPP_FROM else '✗'}")

