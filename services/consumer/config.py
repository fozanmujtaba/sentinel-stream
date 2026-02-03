"""
Sentinel Stream - Enhanced Configuration with Database and Redis
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(default="localhost:9092")
    kafka_group_id: str = Field(default="sentinel-fraud-detection")
    kafka_transactions_topic: str = Field(default="transactions")
    kafka_alerts_topic: str = Field(default="fraud_alerts")
    kafka_dlq_topic: str = Field(default="dead_letter_queue")
    
    # Database Configuration
    database_url: str = Field(default="postgresql://sentinel:sentinel_secure_2024@localhost:5432/sentinel_stream")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # ML Model Configuration
    model_path: str = Field(default="/app/models/fraud_model.joblib")
    fraud_score_threshold: float = Field(default=0.5)  # Lower to catch all risk levels
    fraud_threshold: float = Field(default=0.5)  # Alias
    
    # Velocity Check Configuration
    velocity_window_seconds: int = Field(default=60)
    velocity_threshold: int = Field(default=3)  # Trigger at 3+ transactions in window
    
    # Application Configuration
    log_level: str = Field(default="INFO")
    secret_key: str = Field(default="change-me-in-production")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = Settings()
