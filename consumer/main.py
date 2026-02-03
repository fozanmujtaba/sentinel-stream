"""
Sentinel Stream Consumer - FastAPI Application
Real-time fraud detection service with Kafka consumer and WebSocket broadcasting.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from contextlib import asynccontextmanager
from typing import List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from config import get_settings
from models import Transaction, FraudAlert, DeadLetterMessage, HealthResponse, MetricsResponse
from fraud_detector import FraudDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/app/logs/consumer.log", mode="a")
    ]
)
logger = logging.getLogger(__name__)

# Global state
settings = get_settings()
fraud_detector = FraudDetector()
kafka_consumer: AIOKafkaConsumer = None
kafka_producer: AIOKafkaProducer = None
websocket_clients: Set[WebSocket] = set()
service_start_time: datetime = None

# Metrics
metrics = {
    "latencies": [],
    "dlq_count": 0
}


class WebSocketManager:
    """Manage WebSocket connections for real-time alerts."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected WebSocket."""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message, default=str)
        disconnected = set()
        
        async with self._lock:
            for websocket in self.active_connections:
                try:
                    await websocket.send_text(message_json)
                except Exception as e:
                    logger.warning(f"Failed to send to WebSocket: {e}")
                    disconnected.add(websocket)
            
            # Clean up disconnected clients
            self.active_connections -= disconnected
    
    @property
    def client_count(self) -> int:
        """Get number of connected clients."""
        return len(self.active_connections)


ws_manager = WebSocketManager()


async def send_to_dead_letter_queue(
    message: str,
    error_type: str,
    error_message: str,
    topic: str = None,
    partition: int = None,
    offset: int = None
) -> None:
    """Send malformed messages to the dead letter queue."""
    if kafka_producer is None:
        logger.error("Kafka producer not available for DLQ")
        return
    
    try:
        dlq_message = DeadLetterMessage(
            original_message=message[:1000],  # Truncate large messages
            error_type=error_type,
            error_message=error_message,
            topic=topic or settings.kafka_transactions_topic,
            partition=partition,
            offset=offset
        )
        
        await kafka_producer.send_and_wait(
            settings.kafka_dlq_topic,
            value=dlq_message.model_dump_json().encode("utf-8")
        )
        
        metrics["dlq_count"] += 1
        logger.warning(f"Message sent to DLQ: {error_type} - {error_message}")
        
    except Exception as e:
        logger.error(f"Failed to send to DLQ: {e}")


async def publish_fraud_alert(alert: FraudAlert) -> None:
    """Publish fraud alert to Kafka topic and broadcast via WebSocket."""
    try:
        # Publish to Kafka fraud_alerts topic
        if kafka_producer:
            await kafka_producer.send_and_wait(
                settings.kafka_alerts_topic,
                key=alert.card_id.encode("utf-8"),
                value=alert.model_dump_json().encode("utf-8")
            )
            logger.debug(f"Alert published to Kafka: {alert.transaction_id}")
        
        # Broadcast to WebSocket clients
        await ws_manager.broadcast(alert.model_dump())
        
    except Exception as e:
        logger.error(f"Failed to publish fraud alert: {e}")


async def process_message(msg) -> None:
    """Process a single Kafka message through the fraud detection pipeline."""
    try:
        # Decode message
        raw_message = msg.value.decode("utf-8")
        
        try:
            # Parse JSON
            data = json.loads(raw_message)
        except json.JSONDecodeError as e:
            await send_to_dead_letter_queue(
                message=raw_message,
                error_type="JSONDecodeError",
                error_message=str(e),
                partition=msg.partition,
                offset=msg.offset
            )
            return
        
        try:
            # Validate transaction schema
            transaction = Transaction(**data)
        except Exception as e:
            await send_to_dead_letter_queue(
                message=raw_message,
                error_type="ValidationError",
                error_message=str(e),
                partition=msg.partition,
                offset=msg.offset
            )
            return
        
        # Process through fraud detector
        alert = await fraud_detector.process_transaction(transaction)
        
        if alert:
            # Track latency
            metrics["latencies"].append(alert.latency_ms)
            if len(metrics["latencies"]) > 1000:
                metrics["latencies"] = metrics["latencies"][-500:]
            
            # Publish alert
            await publish_fraud_alert(alert)
    
    except Exception as e:
        logger.error(f"Unexpected error processing message: {e}")
        await send_to_dead_letter_queue(
            message=str(msg.value)[:500],
            error_type="ProcessingError",
            error_message=str(e),
            partition=msg.partition if msg else None,
            offset=msg.offset if msg else None
        )


async def consume_transactions() -> None:
    """Main Kafka consumer loop."""
    global kafka_consumer
    
    logger.info(f"Starting Kafka consumer for topic: {settings.kafka_transactions_topic}")
    
    while True:
        try:
            kafka_consumer = AIOKafkaConsumer(
                settings.kafka_transactions_topic,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_group_id,
                auto_offset_reset=settings.kafka_auto_offset_reset,
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                value_deserializer=lambda x: x  # Raw bytes, decode in processor
            )
            
            await kafka_consumer.start()
            logger.info("Kafka consumer started successfully")
            
            async for msg in kafka_consumer:
                await process_message(msg)
                
        except KafkaError as e:
            logger.error(f"Kafka error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Consumer error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
        finally:
            if kafka_consumer:
                try:
                    await kafka_consumer.stop()
                except Exception:
                    pass


async def cleanup_velocity_windows() -> None:
    """Periodic task to clean up stale velocity windows."""
    while True:
        await asyncio.sleep(60)  # Run every minute
        try:
            await fraud_detector.cleanup_old_windows()
        except Exception as e:
            logger.error(f"Error cleaning up velocity windows: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global kafka_producer, service_start_time
    
    logger.info("=" * 50)
    logger.info("Starting Sentinel Stream Consumer")
    logger.info("=" * 50)
    
    service_start_time = datetime.utcnow()
    
    # Initialize fraud detector (cold start - load model)
    logger.info("Initializing fraud detector (loading ML model)...")
    await fraud_detector.initialize()
    
    # Wait for Kafka to be ready
    logger.info("Waiting for Kafka to be ready...")
    await asyncio.sleep(5)
    
    # Initialize Kafka producer for alerts and DLQ
    try:
        kafka_producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            acks="all",
            enable_idempotence=True
        )
        await kafka_producer.start()
        logger.info("Kafka producer started")
    except Exception as e:
        logger.error(f"Failed to start Kafka producer: {e}")
    
    # Start background tasks
    consumer_task = asyncio.create_task(consume_transactions())
    cleanup_task = asyncio.create_task(cleanup_velocity_windows())
    
    logger.info("Sentinel Stream Consumer is ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sentinel Stream Consumer...")
    
    consumer_task.cancel()
    cleanup_task.cancel()
    
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    if kafka_consumer:
        await kafka_consumer.stop()
    
    if kafka_producer:
        await kafka_producer.stop()
    
    logger.info("Shutdown complete")


# FastAPI Application
app = FastAPI(
    title="Sentinel Stream Consumer",
    description="Real-time fraud detection streaming service",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# REST API ENDPOINTS
# ============================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    stats = fraud_detector.get_stats()
    uptime = (datetime.utcnow() - service_start_time).total_seconds() if service_start_time else 0
    
    kafka_connected = kafka_consumer is not None and kafka_producer is not None
    
    status = "healthy"
    if not kafka_connected:
        status = "degraded"
    if not stats["model_loaded"]:
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        kafka_connected=kafka_connected,
        model_loaded=stats["model_loaded"],
        websocket_clients=ws_manager.client_count,
        transactions_processed=stats["transactions_processed"],
        alerts_generated=stats["alerts_generated"],
        uptime_seconds=uptime
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Get service metrics."""
    stats = fraud_detector.get_stats()
    uptime = (datetime.utcnow() - service_start_time).total_seconds() if service_start_time else 1
    
    tps = stats["transactions_processed"] / uptime if uptime > 0 else 0
    avg_latency = sum(metrics["latencies"]) / len(metrics["latencies"]) if metrics["latencies"] else 0
    fraud_rate = (stats["alerts_generated"] / stats["transactions_processed"] * 100) if stats["transactions_processed"] > 0 else 0
    
    return MetricsResponse(
        transactions_per_second=round(tps, 2),
        average_latency_ms=round(avg_latency, 2),
        fraud_rate=round(fraud_rate, 2),
        velocity_violations=stats["velocity_violations"],
        dlq_messages=metrics["dlq_count"]
    )


@app.get("/stats")
async def get_stats():
    """Get detailed statistics."""
    stats = fraud_detector.get_stats()
    return {
        **stats,
        "websocket_clients": ws_manager.client_count,
        "dlq_count": metrics["dlq_count"],
        "latency_samples": len(metrics["latencies"]),
        "avg_latency_ms": sum(metrics["latencies"]) / len(metrics["latencies"]) if metrics["latencies"] else 0
    }


# ============================================
# WEBSOCKET ENDPOINT
# ============================================

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time fraud alerts.
    Clients connect here to receive live fraud notifications.
    """
    await ws_manager.connect(websocket)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to Sentinel Stream fraud alerts",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for any client messages (ping/pong, etc.)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # Handle ping
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await ws_manager.disconnect(websocket)


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket endpoint for real-time metrics streaming."""
    await websocket.accept()
    
    try:
        while True:
            stats = fraud_detector.get_stats()
            uptime = (datetime.utcnow() - service_start_time).total_seconds() if service_start_time else 1
            
            await websocket.send_json({
                "type": "metrics",
                "data": {
                    "transactions_processed": stats["transactions_processed"],
                    "alerts_generated": stats["alerts_generated"],
                    "velocity_violations": stats["velocity_violations"],
                    "tps": round(stats["transactions_processed"] / uptime, 2),
                    "avg_latency_ms": round(
                        sum(metrics["latencies"]) / len(metrics["latencies"]), 2
                    ) if metrics["latencies"] else 0,
                    "websocket_clients": ws_manager.client_count
                },
                "timestamp": datetime.utcnow().isoformat()
            })
            
            await asyncio.sleep(1)  # Update every second
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Metrics WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
