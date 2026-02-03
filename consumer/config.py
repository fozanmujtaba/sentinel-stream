"""
Configuration management for Sentinel Stream Consumer.
Uses Pydantic settings for type-safe configuration with environment variable support.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Kafka Configuration
    kafka_bootstrap_servers: str = Field(
        default="localhost:9092",
        description="Kafka broker addresses"
    )
    kafka_group_id: str = Field(
        default="sentinel-fraud-detection",
        description="Consumer group ID"
    )
    kafka_transactions_topic: str = Field(
        default="transactions",
        description="Topic for incoming transactions"
    )
    kafka_alerts_topic: str = Field(
        default="fraud_alerts",
        description="Topic for fraud alerts"
    )
    kafka_dlq_topic: str = Field(
        default="dead_letter_queue",
        description="Dead letter queue topic for malformed messages"
    )
    kafka_auto_offset_reset: str = Field(
        default="latest",
        description="Offset reset policy"
    )
    
    # Model Configuration
    model_path: str = Field(
        default="/app/models/fraud_model.joblib",
        description="Path to the trained fraud detection model"
    )
    
    # Velocity Check Configuration
    velocity_window_seconds: int = Field(
        default=60,
        description="Time window for velocity checks (seconds)"
    )
    velocity_threshold: int = Field(
        default=5,
        description="Maximum transactions per card in the time window"
    )
    
    # Fraud Detection Thresholds
    fraud_score_threshold: float = Field(
        default=0.7,
        description="Minimum fraud score to trigger an alert"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Application
    app_name: str = Field(
        default="Sentinel Stream Consumer",
        description="Application name"
    )
    debug: bool = Field(
        default=False,
        description="Debug mode"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
