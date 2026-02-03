"""
Sentinel Stream - Enhanced FastAPI Consumer Service
With PostgreSQL, Redis, and full transaction processing
"""

import asyncio
import json
import os
import time
import logging
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis
import asyncpg
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from config import settings
from models import Transaction, FraudAlert, HealthResponse, MetricsResponse
from fraud_detector import FraudDetector

# Configure logging
logging.basicConfig(level=settings.log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("main")


class AppState:
    def __init__(self):
        self.kafka_consumer: Optional[AIOKafkaConsumer] = None
        self.kafka_producer: Optional[AIOKafkaProducer] = None
        self.redis_client: Optional[redis.Redis] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        self.fraud_detector: Optional[FraudDetector] = None
        self.websocket_clients: List[WebSocket] = []
        self.metrics_clients: List[WebSocket] = []
        
        self.transactions_processed: int = 0
        self.alerts_generated: int = 0
        self.start_time: float = time.time()
        self.processing_times: List[float] = []
        self.velocity_violations: int = 0
        self.dlq_messages: int = 0


state = AppState()


async def init_database():
    try:
        state.db_pool = await asyncpg.create_pool(settings.database_url, min_size=2, max_size=10)
        logger.info("Database connection pool created")
        return True
    except Exception as e:
        logger.warning(f"Database not available: {e}")
        return False


async def init_redis():
    try:
        state.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        await state.redis_client.ping()
        logger.info("Redis connection established")
        return True
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        return False


async def save_transaction_to_db(txn: Transaction, fraud_score: float, is_fraud: bool, processing_time: float):
    if not state.db_pool:
        return
    try:
        async with state.db_pool.acquire() as conn:
            # Ensure customer exists
            await conn.execute("""
                INSERT INTO customers (card_id, customer_name, risk_level, first_transaction_at)
                VALUES ($1, $2, 'LOW', NOW())
                ON CONFLICT (card_id) DO NOTHING
            """, txn.card_id, f"Customer-{txn.card_id[-6:]}")
            
            # Insert transaction
            await conn.execute("""
                INSERT INTO transactions 
                (transaction_id, card_id, amount, merchant_category, location, timestamp, 
                 fraud_score, is_fraud, processing_time_ms, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (transaction_id) DO NOTHING
            """, txn.transaction_id, txn.card_id, float(txn.amount), 
               txn.merchant_category, txn.location, txn.timestamp,
               fraud_score, is_fraud, processing_time, 'flagged' if is_fraud else 'completed')
    except Exception as e:
        logger.error(f"Failed to save transaction: {e}")


async def save_fraud_alert_to_db(alert: FraudAlert):
    if not state.db_pool:
        return
    try:
        async with state.db_pool.acquire() as conn:
            alert_id = await conn.fetchval("""
                INSERT INTO fraud_alerts 
                (transaction_id, card_id, amount, timestamp, location, merchant_category,
                 fraud_score, fraud_reason, risk_level, velocity_triggered, velocity_count, latency_ms)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
            """, alert.transaction_id, alert.card_id, float(alert.amount),
               alert.timestamp, alert.location, alert.merchant_category,
               alert.fraud_score, alert.fraud_reason, alert.risk_level,
               alert.velocity_triggered, alert.velocity_count, alert.latency_ms)
            
            if alert.risk_level in ['HIGH', 'CRITICAL']:
                await conn.execute("""
                    INSERT INTO cases 
                    (title, description, alert_id, card_id, priority, category, total_amount, potential_loss)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, f"Fraud Alert: {alert.risk_level} - ${alert.amount:.2f}",
                    f"Auto-created for {alert.fraud_reason}",
                    alert_id, alert.card_id,
                    'critical' if alert.risk_level == 'CRITICAL' else 'high',
                    'velocity_fraud' if alert.velocity_triggered else 'suspicious_activity',
                    float(alert.amount), float(alert.amount))
    except Exception as e:
        logger.error(f"Failed to save fraud alert: {e}")


async def process_message(message):
    start_time = time.time()
    try:
        data = json.loads(message.value.decode("utf-8"))
        transaction = Transaction(**data)
        
        alert = await state.fraud_detector.process_transaction(transaction)
        
        processing_time = (time.time() - start_time) * 1000
        state.processing_times.append(processing_time)
        state.transactions_processed += 1
        
        is_fraud = alert is not None
        await save_transaction_to_db(transaction, alert.fraud_score if alert else 0.0, is_fraud, processing_time)
        
        if alert:
            state.alerts_generated += 1
            if alert.velocity_triggered:
                state.velocity_violations += 1
            
            await save_fraud_alert_to_db(alert)
            await broadcast_alert(alert)
            
            if state.kafka_producer:
                await state.kafka_producer.send_and_wait(
                    settings.kafka_alerts_topic,
                    alert.model_dump_json().encode("utf-8")
                )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        state.dlq_messages += 1
    except Exception as e:
        logger.error(f"Processing error: {e}")
        state.dlq_messages += 1


async def kafka_consumer_loop():
    while True:
        try:
            state.kafka_consumer = AIOKafkaConsumer(
                settings.kafka_transactions_topic,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_group_id,
                auto_offset_reset="latest"
            )
            await state.kafka_consumer.start()
            logger.info("Kafka consumer started successfully")
            
            async for message in state.kafka_consumer:
                await process_message(message)
        except Exception as e:
            logger.error(f"Kafka error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        finally:
            if state.kafka_consumer:
                await state.kafka_consumer.stop()


async def broadcast_alert(alert: FraudAlert):
    disconnected = []
    alert_json = alert.model_dump_json()
    
    for client in state.websocket_clients:
        try:
            await client.send_text(alert_json)
        except:
            disconnected.append(client)
    
    for client in disconnected:
        state.websocket_clients.remove(client)


async def broadcast_metrics():
    while True:
        await asyncio.sleep(1)
        
        uptime = time.time() - state.start_time
        metrics = {
            "transactions_processed": state.transactions_processed,
            "alerts_generated": state.alerts_generated,
            "tps": round(state.transactions_processed / uptime if uptime > 0 else 0, 2),
            "avg_latency_ms": round(sum(state.processing_times[-100:]) / len(state.processing_times[-100:]) if state.processing_times else 0, 2),
            "velocity_violations": state.velocity_violations,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        disconnected = []
        for client in state.metrics_clients:
            try:
                await client.send_json(metrics)
            except:
                disconnected.append(client)
        
        for client in disconnected:
            state.metrics_clients.remove(client)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Sentinel Stream Consumer...")
    
    await init_database()
    await init_redis()
    
    state.fraud_detector = FraudDetector()
    await state.fraud_detector.initialize()
    
    state.kafka_producer = AIOKafkaProducer(bootstrap_servers=settings.kafka_bootstrap_servers)
    await state.kafka_producer.start()
    
    asyncio.create_task(kafka_consumer_loop())
    asyncio.create_task(broadcast_metrics())
    
    logger.info("Consumer started successfully!")
    
    yield
    
    if state.kafka_consumer:
        await state.kafka_consumer.stop()
    if state.kafka_producer:
        await state.kafka_producer.stop()
    if state.db_pool:
        await state.db_pool.close()
    if state.redis_client:
        await state.redis_client.close()
    
    logger.info("Consumer shutdown complete")


app = FastAPI(
    title="Sentinel Stream - Fraud Detection Service",
    description="Real-time fraud detection with ML and velocity checks",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    uptime = time.time() - state.start_time
    return HealthResponse(
        status="healthy",
        kafka_connected=state.kafka_consumer is not None,
        model_loaded=state.fraud_detector is not None and state.fraud_detector.model_loaded,
        database_connected=state.db_pool is not None,
        redis_connected=state.redis_client is not None,
        websocket_clients=len(state.websocket_clients),
        transactions_processed=state.transactions_processed,
        alerts_generated=state.alerts_generated,
        uptime_seconds=uptime
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    uptime = time.time() - state.start_time
    avg_latency = sum(state.processing_times[-1000:]) / len(state.processing_times[-1000:]) if state.processing_times else 0
    fraud_rate = (state.alerts_generated / state.transactions_processed * 100) if state.transactions_processed > 0 else 0
    
    return MetricsResponse(
        transactions_per_second=round(state.transactions_processed / uptime if uptime > 0 else 0, 2),
        average_latency_ms=round(avg_latency, 2),
        fraud_rate=round(fraud_rate, 2),
        velocity_violations=state.velocity_violations,
        dlq_messages=state.dlq_messages
    )


@app.get("/alerts/recent")
async def get_recent_alerts(limit: int = Query(50, ge=1, le=200)):
    if not state.db_pool:
        return []
    async with state.db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, transaction_id, card_id, amount, timestamp, location,
                   merchant_category, fraud_score, fraud_reason, risk_level,
                   detected_at, status
            FROM fraud_alerts ORDER BY detected_at DESC LIMIT $1
        """, limit)
        return [dict(row) for row in rows]


@app.get("/transactions/recent")
async def get_recent_transactions(limit: int = Query(100, ge=1, le=500)):
    if not state.db_pool:
        return []
    async with state.db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT transaction_id, card_id, amount, merchant_category, location,
                   timestamp, fraud_score, is_fraud, processing_time_ms, status
            FROM transactions ORDER BY created_at DESC LIMIT $1
        """, limit)
        return [dict(row) for row in rows]


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    state.websocket_clients.append(websocket)
    logger.info(f"Alert WebSocket client connected. Total: {len(state.websocket_clients)}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.websocket_clients.remove(websocket)
        logger.info(f"Alert WebSocket client disconnected. Total: {len(state.websocket_clients)}")


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    await websocket.accept()
    state.metrics_clients.append(websocket)
    logger.info(f"Metrics WebSocket client connected. Total: {len(state.metrics_clients)}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.metrics_clients.remove(websocket)
        logger.info(f"Metrics WebSocket client disconnected. Total: {len(state.metrics_clients)}")
