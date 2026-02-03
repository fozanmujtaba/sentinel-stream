"""
Fraud Detection Engine with ML Inference and Velocity Checks.
Implements sliding window for velocity-based fraud detection.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
import joblib
from pathlib import Path

from models import Transaction, TransactionFeatures, FraudAlert
from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TransactionWindow:
    """Sliding window for tracking card transaction velocity."""
    timestamps: List[datetime] = field(default_factory=list)
    amounts: List[float] = field(default_factory=list)
    
    def add_transaction(self, timestamp: datetime, amount: float) -> None:
        """Add a transaction to the window."""
        self.timestamps.append(timestamp)
        self.amounts.append(amount)
    
    def cleanup(self, window_seconds: int, current_time: datetime) -> None:
        """Remove transactions outside the sliding window."""
        cutoff = current_time - timedelta(seconds=window_seconds)
        
        # Filter out old transactions
        valid_indices = [
            i for i, ts in enumerate(self.timestamps) 
            if ts >= cutoff
        ]
        
        self.timestamps = [self.timestamps[i] for i in valid_indices]
        self.amounts = [self.amounts[i] for i in valid_indices]
    
    def get_count(self) -> int:
        """Get number of transactions in window."""
        return len(self.timestamps)
    
    def get_total_amount(self) -> float:
        """Get total amount in window."""
        return sum(self.amounts) if self.amounts else 0.0
    
    def get_mean_amount(self) -> float:
        """Get mean amount in window."""
        return np.mean(self.amounts) if self.amounts else 0.0


class FraudDetector:
    """
    Real-time fraud detection engine with:
    - Isolation Forest / XGBoost model inference
    - Sliding window velocity checks
    - Feature engineering on-the-fly
    """
    
    # Merchant category encoding
    MERCHANT_CATEGORIES = {
        "grocery": 0, "gas_station": 1, "restaurant": 2, "online": 3,
        "retail": 4, "travel": 5, "entertainment": 6, "healthcare": 7,
        "education": 8, "utilities": 9, "other": 10
    }
    
    # High-risk locations (simplified for demo)
    HIGH_RISK_LOCATIONS = {
        "unknown", "vpn", "tor", "proxy"
    }
    
    def __init__(self):
        self.settings = get_settings()
        self.model = None
        self.scaler = None
        self.model_loaded = False
        
        # Sliding window storage: card_id -> TransactionWindow
        self.velocity_windows: Dict[str, TransactionWindow] = defaultdict(TransactionWindow)
        
        # Statistics
        self.transactions_processed = 0
        self.alerts_generated = 0
        self.velocity_violations = 0
        
        # Lock for thread-safe window updates
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """
        Initialize the fraud detector with model loading.
        This handles the "cold start" requirement.
        """
        try:
            await self._load_model()
            logger.info("Fraud detector initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize fraud detector: {e}")
            return False
    
    async def _load_model(self) -> None:
        """Load the pre-trained fraud detection model."""
        model_path = Path(self.settings.model_path)
        
        if model_path.exists():
            logger.info(f"Loading model from {model_path}")
            try:
                model_data = joblib.load(model_path)
                
                # Handle both single model and model + scaler dictionary
                if isinstance(model_data, dict):
                    self.model = model_data.get('model')
                    self.scaler = model_data.get('scaler')
                else:
                    self.model = model_data
                    self.scaler = None
                
                self.model_loaded = True
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load model: {e}. Using fallback scoring.")
                self._initialize_fallback_model()
        else:
            logger.warning(f"Model not found at {model_path}. Using fallback scoring.")
            self._initialize_fallback_model()
    
    def _initialize_fallback_model(self) -> None:
        """Initialize a fallback scoring mechanism when no model is available."""
        self.model = None
        self.scaler = None
        self.model_loaded = True  # Mark as loaded so service can run
        logger.info("Fallback rule-based scoring initialized")
    
    async def process_transaction(self, transaction: Transaction) -> Optional[FraudAlert]:
        """
        Process a transaction through the fraud detection pipeline.
        
        Args:
            transaction: Incoming transaction to analyze
            
        Returns:
            FraudAlert if fraud detected, None otherwise
        """
        start_time = datetime.utcnow()
        
        try:
            async with self._lock:
                # 1. Update velocity window
                velocity_triggered, velocity_count = await self._check_velocity(
                    transaction.card_id,
                    transaction.timestamp,
                    transaction.amount
                )
                
                # 2. Engineer features
                features = self._engineer_features(transaction, velocity_count)
                
                # 3. Run model inference
                fraud_score = await self._predict(features)
                
                # 4. Update statistics
                self.transactions_processed += 1
                
                # 5. Determine if alert should be generated
                if fraud_score >= self.settings.fraud_score_threshold or velocity_triggered:
                    if velocity_triggered:
                        self.velocity_violations += 1
                    
                    # Calculate latency
                    latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                    
                    # Determine fraud reason
                    fraud_reason = self._determine_fraud_reason(
                        fraud_score, velocity_triggered, velocity_count, features
                    )
                    
                    # Adjust score if velocity triggered
                    final_score = max(fraud_score, 0.85) if velocity_triggered else fraud_score
                    
                    alert = FraudAlert(
                        transaction_id=transaction.transaction_id,
                        card_id=transaction.card_id,
                        amount=transaction.amount,
                        timestamp=transaction.timestamp,
                        location=transaction.location,
                        merchant_category=transaction.merchant_category,
                        fraud_score=final_score,
                        fraud_reason=fraud_reason,
                        risk_level=self._get_risk_level(final_score),
                        velocity_triggered=velocity_triggered,
                        velocity_count=velocity_count,
                        latency_ms=latency_ms
                    )
                    
                    self.alerts_generated += 1
                    logger.info(
                        f"Fraud detected: {transaction.transaction_id} "
                        f"Score: {final_score:.2f} Reason: {fraud_reason}"
                    )
                    
                    return alert
                
                return None
                
        except Exception as e:
            logger.error(f"Error processing transaction {transaction.transaction_id}: {e}")
            raise
    
    async def _check_velocity(
        self, 
        card_id: str, 
        timestamp: datetime, 
        amount: float
    ) -> Tuple[bool, int]:
        """
        Check transaction velocity for a card.
        
        Returns:
            Tuple of (velocity_triggered, transaction_count)
        """
        window = self.velocity_windows[card_id]
        
        # Cleanup old transactions
        window.cleanup(self.settings.velocity_window_seconds, timestamp)
        
        # Add current transaction
        window.add_transaction(timestamp, amount)
        
        # Check if velocity threshold exceeded
        count = window.get_count()
        triggered = count > self.settings.velocity_threshold
        
        if triggered:
            logger.warning(
                f"Velocity violation for card {card_id[-4:]}: "
                f"{count} transactions in {self.settings.velocity_window_seconds}s window"
            )
        
        return triggered, count
    
    def _engineer_features(
        self, 
        transaction: Transaction, 
        velocity_count: int
    ) -> TransactionFeatures:
        """
        Perform on-the-fly feature engineering.
        """
        # Time-based features
        hour = transaction.timestamp.hour
        day_of_week = transaction.timestamp.weekday()
        is_weekend = day_of_week >= 5
        
        # Amount normalization (simple min-max based on typical ranges)
        amount_normalized = min(transaction.amount / 10000, 1.0)
        
        # Merchant category encoding
        category_lower = transaction.merchant_category.lower()
        merchant_encoded = self.MERCHANT_CATEGORIES.get(
            category_lower, 
            self.MERCHANT_CATEGORIES["other"]
        )
        
        # Location risk assessment
        location_lower = transaction.location.lower()
        location_risk = 0.8 if any(
            risk in location_lower for risk in self.HIGH_RISK_LOCATIONS
        ) else 0.2
        
        # Amount deviation (from window mean if available)
        window = self.velocity_windows.get(transaction.card_id)
        if window and window.get_count() > 1:
            mean_amount = window.get_mean_amount()
            if mean_amount > 0:
                amount_deviation = abs(transaction.amount - mean_amount) / mean_amount
            else:
                amount_deviation = 0.0
        else:
            amount_deviation = 0.0
        
        return TransactionFeatures(
            amount_normalized=amount_normalized,
            hour_of_day=hour,
            day_of_week=day_of_week,
            is_weekend=is_weekend,
            merchant_category_encoded=merchant_encoded,
            velocity_count=velocity_count,
            amount_deviation=min(amount_deviation, 5.0),
            location_risk=location_risk
        )
    
    async def _predict(self, features: TransactionFeatures) -> float:
        """
        Run model inference to get fraud probability.
        """
        if self.model is None:
            # Fallback: Rule-based scoring
            return self._rule_based_score(features)
        
        try:
            # Prepare feature vector
            feature_vector = np.array([[
                features.amount_normalized,
                features.hour_of_day / 23.0,  # Normalize to 0-1
                features.day_of_week / 6.0,
                float(features.is_weekend),
                features.merchant_category_encoded / 10.0,
                min(features.velocity_count / 10.0, 1.0),
                min(features.amount_deviation, 1.0),
                features.location_risk
            ]])
            
            # Apply scaler if available
            if self.scaler is not None:
                feature_vector = self.scaler.transform(feature_vector)
            
            # Get prediction
            if hasattr(self.model, 'predict_proba'):
                # Classifiers with probability
                proba = self.model.predict_proba(feature_vector)[0]
                fraud_score = proba[1] if len(proba) > 1 else proba[0]
            elif hasattr(self.model, 'decision_function'):
                # Isolation Forest style
                score = self.model.decision_function(feature_vector)[0]
                # Convert to 0-1 probability (Isolation Forest returns negative for anomalies)
                fraud_score = 1 / (1 + np.exp(score))
            else:
                # Binary prediction
                prediction = self.model.predict(feature_vector)[0]
                fraud_score = 0.9 if prediction == 1 else 0.1
            
            return float(np.clip(fraud_score, 0, 1))
            
        except Exception as e:
            logger.error(f"Model prediction error: {e}. Using fallback scoring.")
            return self._rule_based_score(features)
    
    def _rule_based_score(self, features: TransactionFeatures) -> float:
        """
        Fallback rule-based fraud scoring when no model is available.
        """
        score = 0.1  # Base score
        
        # High velocity is suspicious
        if features.velocity_count > 3:
            score += 0.3
        elif features.velocity_count > 5:
            score += 0.5
        
        # Unusual hours (2-5 AM)
        if 2 <= features.hour_of_day <= 5:
            score += 0.15
        
        # High amount deviation
        if features.amount_deviation > 2:
            score += 0.2
        
        # High-risk location
        score += features.location_risk * 0.2
        
        # Large normalized amount
        if features.amount_normalized > 0.5:
            score += 0.1
        
        return min(score, 1.0)
    
    def _determine_fraud_reason(
        self,
        fraud_score: float,
        velocity_triggered: bool,
        velocity_count: int,
        features: TransactionFeatures
    ) -> str:
        """Determine the primary reason for fraud detection."""
        reasons = []
        
        if velocity_triggered:
            reasons.append(f"Velocity violation: {velocity_count} txns in 60s")
        
        if features.amount_deviation > 2:
            reasons.append(f"Unusual amount (deviation: {features.amount_deviation:.1f}x)")
        
        if features.location_risk > 0.5:
            reasons.append("High-risk location detected")
        
        if 2 <= features.hour_of_day <= 5:
            reasons.append("Suspicious transaction time")
        
        if fraud_score >= 0.8 and not reasons:
            reasons.append("ML model high confidence fraud prediction")
        
        return "; ".join(reasons) if reasons else "Multiple risk factors detected"
    
    def _get_risk_level(self, score: float) -> str:
        """Map fraud score to risk level."""
        if score >= 0.9:
            return "CRITICAL"
        elif score >= 0.75:
            return "HIGH"
        elif score >= 0.5:
            return "MEDIUM"
        return "LOW"
    
    def get_stats(self) -> dict:
        """Get current statistics."""
        return {
            "transactions_processed": self.transactions_processed,
            "alerts_generated": self.alerts_generated,
            "velocity_violations": self.velocity_violations,
            "active_cards_tracked": len(self.velocity_windows),
            "model_loaded": self.model_loaded
        }
    
    async def cleanup_old_windows(self) -> None:
        """Periodic cleanup of old velocity windows to prevent memory leaks."""
        async with self._lock:
            current_time = datetime.utcnow()
            stale_threshold = timedelta(minutes=5)
            
            cards_to_remove = []
            for card_id, window in self.velocity_windows.items():
                if window.timestamps:
                    latest = max(window.timestamps)
                    if current_time - latest > stale_threshold:
                        cards_to_remove.append(card_id)
            
            for card_id in cards_to_remove:
                del self.velocity_windows[card_id]
            
            if cards_to_remove:
                logger.debug(f"Cleaned up {len(cards_to_remove)} stale velocity windows")
