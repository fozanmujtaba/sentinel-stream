"""
Sentinel Stream - Enhanced Pydantic Models
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID
from dataclasses import dataclass


class Transaction(BaseModel):
    """Incoming transaction data."""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    card_id: str = Field(..., min_length=1, max_length=50)
    amount: float = Field(..., gt=0)
    timestamp: datetime
    location: str = Field(..., min_length=1)
    merchant_category: str = Field(..., min_length=1)


@dataclass
class TransactionFeatures:
    """Engineered features for ML model inference."""
    amount_normalized: float
    hour_of_day: int
    day_of_week: int
    is_weekend: bool
    merchant_category_encoded: int
    velocity_count: int
    amount_deviation: float
    location_risk: float


class FraudDetectionResult(BaseModel):
    """Result from fraud detection engine."""
    fraud_score: float = Field(..., ge=0, le=1)
    fraud_reason: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    velocity_triggered: bool = False
    velocity_count: int = 0


class FraudAlert(BaseModel):
    """Fraud alert for WebSocket broadcast and storage."""
    transaction_id: str
    card_id: str
    amount: float
    timestamp: datetime
    location: str
    merchant_category: str
    fraud_score: float
    fraud_reason: str
    risk_level: str
    velocity_triggered: bool = False
    velocity_count: int = 0
    detected_at: Optional[datetime] = None
    latency_ms: float = 0.0


class HealthResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "degraded", "unhealthy"]
    kafka_connected: bool
    model_loaded: bool
    database_connected: bool = False
    redis_connected: bool = False
    websocket_clients: int
    transactions_processed: int
    alerts_generated: int
    uptime_seconds: float


class MetricsResponse(BaseModel):
    """Metrics response."""
    transactions_per_second: float
    average_latency_ms: float
    fraud_rate: float
    velocity_violations: int
    dlq_messages: int


class CustomerProfile(BaseModel):
    """Customer profile for 360 view."""
    id: UUID
    card_id: str
    customer_name: Optional[str]
    email: Optional[str]
    risk_score: float
    risk_level: str
    total_transactions: int
    total_spent: float
    total_alerts: int
    created_at: datetime
    last_transaction_at: Optional[datetime]


class CaseResponse(BaseModel):
    """Case response model."""
    id: UUID
    case_number: str
    title: str
    description: Optional[str]
    priority: str
    status: str
    category: Optional[str]
    total_amount: float
    assigned_to: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class DashboardKPIs(BaseModel):
    """Dashboard KPI metrics."""
    transactions_24h: int
    volume_24h: float
    alerts_24h: int
    critical_alerts_24h: int
    open_cases: int
    sla_breached: int
    avg_latency_ms: float
