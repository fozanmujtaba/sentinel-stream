"""
Pydantic models for data validation and serialization.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID
import re


class Transaction(BaseModel):
    """Incoming transaction schema from the Kafka stream."""
    
    transaction_id: str = Field(..., description="Unique transaction identifier (UUID)")
    card_id: str = Field(..., description="Card identifier for windowing")
    amount: float = Field(..., ge=0, description="Transaction amount")
    timestamp: datetime = Field(..., description="Transaction timestamp (ISO-8601)")
    location: str = Field(..., description="Transaction location (lat/long or city)")
    merchant_category: str = Field(..., description="Merchant category code")
    
    @field_validator('transaction_id')
    @classmethod
    def validate_transaction_id(cls, v: str) -> str:
        """Validate transaction_id is a valid UUID string."""
        try:
            UUID(v)
        except ValueError:
            raise ValueError(f"Invalid transaction_id: {v}")
        return v
    
    @field_validator('card_id')
    @classmethod
    def validate_card_id(cls, v: str) -> str:
        """Validate card_id is not empty."""
        if not v or not v.strip():
            raise ValueError("card_id cannot be empty")
        return v.strip()
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """Validate amount is reasonable."""
        if v < 0:
            raise ValueError("Amount cannot be negative")
        if v > 1_000_000:
            raise ValueError("Amount exceeds maximum limit")
        return round(v, 2)


class TransactionFeatures(BaseModel):
    """Engineered features for model inference."""
    
    amount_normalized: float = Field(..., description="Normalized transaction amount")
    hour_of_day: int = Field(..., ge=0, le=23, description="Hour of transaction")
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday)")
    is_weekend: bool = Field(..., description="Whether transaction occurred on weekend")
    merchant_category_encoded: int = Field(..., description="Encoded merchant category")
    velocity_count: int = Field(..., ge=0, description="Transaction count in window")
    amount_deviation: float = Field(..., description="Deviation from mean amount")
    location_risk: float = Field(..., ge=0, le=1, description="Location risk score")


class FraudAlert(BaseModel):
    """Fraud alert schema for WebSocket broadcast and Kafka."""
    
    transaction_id: str = Field(..., description="Original transaction ID")
    card_id: str = Field(..., description="Card identifier")
    amount: float = Field(..., description="Transaction amount")
    timestamp: datetime = Field(..., description="Original transaction timestamp")
    location: str = Field(..., description="Transaction location")
    merchant_category: str = Field(..., description="Merchant category")
    
    fraud_score: float = Field(..., ge=0, le=1, description="ML model fraud probability")
    fraud_reason: str = Field(..., description="Primary reason for fraud detection")
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        ..., description="Risk classification"
    )
    velocity_triggered: bool = Field(..., description="Whether velocity check was triggered")
    velocity_count: int = Field(..., description="Number of transactions in window")
    
    detected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the fraud was detected"
    )
    latency_ms: float = Field(..., description="Processing latency in milliseconds")
    
    def get_risk_level(self) -> str:
        """Determine risk level based on fraud score."""
        if self.fraud_score >= 0.9:
            return "CRITICAL"
        elif self.fraud_score >= 0.75:
            return "HIGH"
        elif self.fraud_score >= 0.5:
            return "MEDIUM"
        return "LOW"


class DeadLetterMessage(BaseModel):
    """Schema for messages sent to the dead letter queue."""
    
    original_message: str = Field(..., description="Original raw message")
    error_type: str = Field(..., description="Type of error that occurred")
    error_message: str = Field(..., description="Detailed error message")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred"
    )
    topic: str = Field(..., description="Source topic")
    partition: Optional[int] = Field(None, description="Source partition")
    offset: Optional[int] = Field(None, description="Source offset")


class HealthResponse(BaseModel):
    """Health check response schema."""
    
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ..., description="Overall health status"
    )
    kafka_connected: bool = Field(..., description="Kafka connection status")
    model_loaded: bool = Field(..., description="ML model loaded status")
    websocket_clients: int = Field(..., description="Number of connected WebSocket clients")
    transactions_processed: int = Field(..., description="Total transactions processed")
    alerts_generated: int = Field(..., description="Total alerts generated")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")


class MetricsResponse(BaseModel):
    """Metrics response schema."""
    
    transactions_per_second: float = Field(..., description="Current TPS")
    average_latency_ms: float = Field(..., description="Average processing latency")
    fraud_rate: float = Field(..., description="Percentage of fraudulent transactions")
    velocity_violations: int = Field(..., description="Total velocity violations")
    dlq_messages: int = Field(..., description="Messages in dead letter queue")
