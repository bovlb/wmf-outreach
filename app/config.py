"""Configuration management for the application."""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Redis configuration
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Cache TTL settings (in seconds)
    user_cache_ttl: int = 3600  # 1 hour
    course_cache_ttl: int = 86400  # 24 hours
    course_users_cache_ttl: int = 3600  # 1 hour
    
    # Stale-while-revalidate settings
    stale_ttl_multiplier: float = 2.0  # Serve stale data up to 2x the TTL
    
    # Outreach Dashboard base URL
    outreach_base_url: str = "https://outreachdashboard.wmflabs.org"
    
    # HTTP client settings
    http_timeout: int = 30
    http_max_retries: int = 3
    
    # Application settings
    log_level: str = "INFO"
    
    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
