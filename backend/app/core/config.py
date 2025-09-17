"""
Application configuration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """
    Application settings
    """
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://myapp_user:secure_password_123@localhost:5432/myapp_db"
    )
    
    # Redis
    REDIS_URL: str = os.getenv(
        "REDIS_URL",
        "redis://:your_redis_password_here@localhost:6379/0"
    )
    
    # API Keys
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("API_KEY")
    REDDIT_CLIENT_ID: Optional[str] = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: Optional[str] = os.getenv("REDDIT_CLIENT_SECRET")
    
    # Security (for later)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "development-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    
    # Data Collection Settings
    DATA_COLLECTION_ENABLED: bool = os.getenv("DATA_COLLECTION_ENABLED", "true").lower() == "true"
    COLLECTION_INTERVAL_MINUTES: int = int(os.getenv("COLLECTION_INTERVAL_MINUTES", "15"))
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Ignore extra fields in .env file


# Create settings instance
settings = Settings()