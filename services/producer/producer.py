"""
Sentinel Stream - High-Velocity Transaction Producer
Simulates a firehose of JSON transactions for fraud detection testing.
"""

import json
import os
import random
import time
import uuid
import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, asdict
from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient
from faker import Faker

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Initialize Faker
fake = Faker()
Faker.seed(42)  # Reproducibility

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "transactions")
TRANSACTIONS_PER_SECOND = int(os.getenv("TRANSACTIONS_PER_SECOND", "50"))
FRAUD_PROBABILITY = float(os.getenv("FRAUD_PROBABILITY", "0.05"))
VELOCITY_ATTACK_PROBABILITY = float(os.getenv("VELOCITY_ATTACK_PROBABILITY", "0.02"))

# Merchant categories with weights
MERCHANT_CATEGORIES = [
    ("grocery", 0.25),
    ("gas_station", 0.15),
    ("restaurant", 0.20),
    ("online", 0.15),
    ("retail", 0.10),
    ("travel", 0.05),
    ("entertainment", 0.05),
    ("healthcare", 0.03),
    ("utilities", 0.02),
]

# High-risk locations for fraud simulation
HIGH_RISK_LOCATIONS = [
    "Unknown VPN",
    "TOR Exit Node",
    "Proxy Server",
    "International - High Risk",
    "Suspicious IP",
    "Known Fraud Region"
]

# Card pool for realistic simulation
CARD_POOL_SIZE = 1000
card_pool = [f"CARD-{fake.uuid4()[:8].upper()}" for _ in range(CARD_POOL_SIZE)]

# Track cards for velocity attacks
velocity_attack_cards = set()

# Fraud pattern types for diversity
FRAUD_PATTERNS = [
    "velocity_attack",      # Rapid fire transactions
    "high_value",           # Unusually high amounts
    "location_anomaly",     # High-risk location
    "time_anomaly",         # Late night transaction
    "multiple_factors",     # Combined patterns
    "test_charge",          # Small test charges
]

# Shutdown flag
running = True


@dataclass
class Transaction:
    """Transaction data class matching the consumer schema."""
    transaction_id: str
    card_id: str
    amount: float
    timestamp: str
    location: str
    merchant_category: str
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self))


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info("Received shutdown signal, stopping producer...")
    running = False


def wait_for_kafka(bootstrap_servers: str, max_attempts: int = 30) -> bool:
    """Wait for Kafka to be available."""
    logger.info(f"Waiting for Kafka at {bootstrap_servers}...")
    
    for attempt in range(max_attempts):
        try:
            admin = AdminClient({"bootstrap.servers": bootstrap_servers})
            admin.list_topics(timeout=5)
            logger.info("Kafka is ready!")
            return True
        except Exception as e:
            logger.debug(f"Attempt {attempt + 1}/{max_attempts}: Kafka not ready - {e}")
            time.sleep(2)
    
    logger.error("Failed to connect to Kafka after maximum attempts")
    return False


def create_producer(bootstrap_servers: str) -> Producer:
    """Create and configure Kafka producer."""
    config = {
        "bootstrap.servers": bootstrap_servers,
        "client.id": "sentinel-producer",
        "acks": "all",
        "retries": 3,
        "retry.backoff.ms": 100,
        "batch.size": 16384,
        "linger.ms": 5,
        "compression.type": "gzip",
        "enable.idempotence": True,
    }
    
    return Producer(config)


def delivery_callback(err, msg):
    """Callback for message delivery confirmation."""
    if err:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")


def select_merchant_category() -> str:
    """Weighted random selection of merchant category."""
    categories, weights = zip(*MERCHANT_CATEGORIES)
    return random.choices(categories, weights=weights, k=1)[0]


def generate_location(is_fraud: bool = False) -> str:
    """Generate a location string."""
    if is_fraud and random.random() < 0.3:
        return random.choice(HIGH_RISK_LOCATIONS)
    
    # Generate realistic lat/long or city
    if random.random() < 0.5:
        lat = round(random.uniform(25, 48), 6)
        lng = round(random.uniform(-125, -70), 6)
        return f"{lat},{lng}"
    else:
        return f"{fake.city()}, {fake.state_abbr()}"


def generate_amount(is_fraud: bool = False, is_velocity: bool = False) -> float:
    """Generate transaction amount with fraud patterns."""
    if is_fraud:
        # Fraudulent transactions often have unusual amounts
        fraud_patterns = [
            lambda: random.uniform(1000, 5000),  # High value
            lambda: random.uniform(0.01, 1.00),  # Tiny test charges
            lambda: round(random.uniform(99, 999), 0) + 0.99,  # Just under limits
        ]
        return round(random.choice(fraud_patterns)(), 2)
    
    if is_velocity:
        # Velocity attacks often use similar small amounts
        return round(random.uniform(10, 50), 2)
    
    # Normal transaction amounts
    normal_ranges = [
        (0.20, lambda: random.uniform(1, 25)),     # Small purchases
        (0.40, lambda: random.uniform(25, 100)),   # Medium purchases
        (0.30, lambda: random.uniform(100, 500)),  # Larger purchases
        (0.10, lambda: random.uniform(500, 2000)), # Big purchases
    ]
    
    rand = random.random()
    cumulative = 0
    for prob, generator in normal_ranges:
        cumulative += prob
        if rand < cumulative:
            return round(generator(), 2)
    
    return round(random.uniform(1, 100), 2)


def generate_velocity_attack_burst(card_id: str) -> list[Transaction]:
    """Generate a burst of transactions to trigger velocity detection.
    Varies the burst size to produce different risk levels.
    """
    # Varied burst sizes for different risk levels:
    # 3-5: Borderline (LOW)
    # 6-7: Moderate (MEDIUM)  
    # 8-9: Significant (HIGH)
    # 10+: Rapid fire (CRITICAL)
    burst_sizes = [
        (3, 0.15),   # 15% - small bursts (LOW risk)
        (4, 0.15),   # 15% - small bursts (LOW risk)
        (5, 0.15),   # 15% - small bursts (LOW-MEDIUM)
        (6, 0.15),   # 15% - medium bursts (MEDIUM)
        (7, 0.10),   # 10% - medium bursts (MEDIUM)
        (8, 0.10),   # 10% - high bursts (HIGH)
        (9, 0.10),   # 10% - high bursts (HIGH)
        (10, 0.05),  # 5% - critical bursts (CRITICAL)
        (12, 0.05),  # 5% - extreme bursts (CRITICAL)
    ]
    
    # Weighted selection of burst size
    sizes, weights = zip(*burst_sizes)
    count = random.choices(sizes, weights=weights, k=1)[0]
    
    transactions = []
    base_time = datetime.utcnow()
    
    for i in range(count):
        # Transactions within a 60-second window
        offset_seconds = random.uniform(0, 55)
        timestamp = base_time + timedelta(seconds=offset_seconds)
        
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            card_id=card_id,
            amount=generate_amount(is_velocity=True),
            timestamp=timestamp.isoformat() + "Z",
            location=generate_location(),
            merchant_category="online" if random.random() < 0.7 else select_merchant_category()
        )
        transactions.append(transaction)
    
    risk_label = "CRITICAL" if count >= 10 else "HIGH" if count >= 8 else "MEDIUM" if count >= 6 else "LOW"
    logger.warning(f"Generated velocity attack ({risk_label}): card {card_id[-8:]} - {count} transactions")
    return transactions


def generate_transaction(is_fraud: bool = False, fraud_type: str = None) -> Transaction:
    """Generate a single transaction with specific fraud patterns."""
    card_id = random.choice(card_pool)
    
    # Determine fraud type for varied risk levels
    if is_fraud and fraud_type is None:
        fraud_type = random.choice(FRAUD_PATTERNS[:5])  # Skip velocity_attack (handled separately)
    
    # Generate timestamp based on fraud type
    if is_fraud and fraud_type == "time_anomaly":
        # Late night transaction (2-5 AM)
        hour = random.randint(2, 5)
        timestamp = datetime.utcnow().replace(hour=hour, minute=random.randint(0, 59))
    else:
        jitter_ms = random.randint(-1000, 1000)
        timestamp = datetime.utcnow() + timedelta(milliseconds=jitter_ms)
    
    # Generate location based on fraud type
    if is_fraud and fraud_type == "location_anomaly":
        location = random.choice(HIGH_RISK_LOCATIONS)
    else:
        location = generate_location(is_fraud=is_fraud)
    
    # Generate amount based on fraud type
    if is_fraud:
        if fraud_type == "high_value":
            amount = round(random.uniform(2000, 9999), 2)  # Very high amount
        elif fraud_type == "test_charge":
            amount = round(random.uniform(0.01, 2.00), 2)  # Tiny test charges
        elif fraud_type == "multiple_factors":
            amount = round(random.uniform(500, 3000), 2)  # Combined with other factors
        else:
            amount = generate_amount(is_fraud=True)
    else:
        amount = generate_amount(is_fraud=False)
    
    return Transaction(
        transaction_id=str(uuid.uuid4()),
        card_id=card_id,
        amount=amount,
        timestamp=timestamp.isoformat() + "Z",
        location=location,
        merchant_category=select_merchant_category()
    )


def generate_malformed_message() -> str:
    """Generate intentionally malformed messages for DLQ testing."""
    malformed_types = [
        lambda: "not valid json at all {{{",
        lambda: json.dumps({"incomplete": True}),  # Missing required fields
        lambda: json.dumps({
            "transaction_id": "invalid-uuid",
            "card_id": "",  # Empty card
            "amount": -100,  # Negative amount
            "timestamp": "not-a-date",
            "location": None,
            "merchant_category": None
        }),
    ]
    return random.choice(malformed_types)()


def main():
    """Main producer loop."""
    global running
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 60)
    logger.info("🚀 Sentinel Stream Transaction Producer Starting")
    logger.info("=" * 60)
    logger.info(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"Topic: {KAFKA_TOPIC}")
    logger.info(f"Target TPS: {TRANSACTIONS_PER_SECOND}")
    logger.info(f"Fraud Probability: {FRAUD_PROBABILITY * 100}%")
    logger.info(f"Velocity Attack Probability: {VELOCITY_ATTACK_PROBABILITY * 100}%")
    logger.info("=" * 60)
    
    # Wait for Kafka
    if not wait_for_kafka(KAFKA_BOOTSTRAP_SERVERS):
        sys.exit(1)
    
    # Create producer
    producer = create_producer(KAFKA_BOOTSTRAP_SERVERS)
    
    # Calculate sleep time for target TPS
    sleep_time = 1.0 / TRANSACTIONS_PER_SECOND
    
    # Statistics
    total_sent = 0
    fraud_sent = 0
    velocity_attacks = 0
    start_time = time.time()
    last_report_time = start_time
    
    try:
        while running:
            loop_start = time.time()
            
            # Occasionally trigger a velocity attack
            if random.random() < VELOCITY_ATTACK_PROBABILITY:
                attack_card = random.choice(card_pool)
                burst = generate_velocity_attack_burst(attack_card)
                
                for txn in burst:
                    producer.produce(
                        KAFKA_TOPIC,
                        key=txn.card_id.encode("utf-8"),
                        value=txn.to_json().encode("utf-8"),
                        callback=delivery_callback
                    )
                    total_sent += 1
                    fraud_sent += 1
                
                velocity_attacks += 1
                producer.poll(0)
            else:
                # Normal transaction generation
                is_fraud = random.random() < FRAUD_PROBABILITY
                
                # Occasionally send malformed message (for DLQ testing)
                if random.random() < 0.001:  # 0.1% malformed
                    message = generate_malformed_message()
                    producer.produce(
                        KAFKA_TOPIC,
                        value=message.encode("utf-8"),
                        callback=delivery_callback
                    )
                else:
                    transaction = generate_transaction(is_fraud=is_fraud)
                    producer.produce(
                        KAFKA_TOPIC,
                        key=transaction.card_id.encode("utf-8"),
                        value=transaction.to_json().encode("utf-8"),
                        callback=delivery_callback
                    )
                    
                    if is_fraud:
                        fraud_sent += 1
                
                total_sent += 1
            
            # Poll for callbacks
            producer.poll(0)
            
            # Report statistics every 10 seconds
            current_time = time.time()
            if current_time - last_report_time >= 10:
                elapsed = current_time - start_time
                actual_tps = total_sent / elapsed
                fraud_rate = (fraud_sent / total_sent * 100) if total_sent > 0 else 0
                
                logger.info(
                    f"📊 Stats | Total: {total_sent:,} | TPS: {actual_tps:.1f} | "
                    f"Fraud: {fraud_sent:,} ({fraud_rate:.1f}%) | "
                    f"Velocity Attacks: {velocity_attacks}"
                )
                last_report_time = current_time
            
            # Rate limiting
            elapsed_in_loop = time.time() - loop_start
            if elapsed_in_loop < sleep_time:
                time.sleep(sleep_time - elapsed_in_loop)
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        # Flush remaining messages
        logger.info("Flushing remaining messages...")
        producer.flush(timeout=10)
        
        # Final statistics
        elapsed = time.time() - start_time
        actual_tps = total_sent / elapsed if elapsed > 0 else 0
        
        logger.info("=" * 60)
        logger.info("📈 Final Statistics")
        logger.info(f"Total transactions sent: {total_sent:,}")
        logger.info(f"Fraudulent transactions: {fraud_sent:,}")
        logger.info(f"Velocity attacks: {velocity_attacks}")
        logger.info(f"Average TPS: {actual_tps:.2f}")
        logger.info(f"Runtime: {elapsed:.1f} seconds")
        logger.info("=" * 60)
        
        logger.info("Producer shutdown complete")


if __name__ == "__main__":
    main()
