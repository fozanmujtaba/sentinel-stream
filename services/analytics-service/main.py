"""
Sentinel Stream - Analytics Service
Provides aggregated metrics, trends, and reporting
"""

from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncpg
import redis.asyncio as redis
import os
import logging
import json

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("analytics-service")

# ============================================
# CONFIGURATION
# ============================================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sentinel:sentinel_secure_2024@localhost:5432/sentinel_stream")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/2")

# ============================================
# MODELS
# ============================================
class DashboardKPIs(BaseModel):
    transactions_24h: int
    transactions_1h: int
    volume_24h: float
    alerts_24h: int
    critical_alerts_24h: int
    velocity_violations_24h: int
    open_cases: int
    sla_breached: int
    avg_latency_ms: float
    fraud_rate_24h: float

class TrendData(BaseModel):
    timestamp: datetime
    transactions: int
    alerts: int
    fraud_amount: float

class RulePerformance(BaseModel):
    rule_id: UUID
    rule_name: str
    total_triggers: int
    true_positives: int
    false_positives: int
    precision: float

class GeoData(BaseModel):
    location: str
    count: int
    total_amount: float
    fraud_count: int

class TopCard(BaseModel):
    card_id: str
    alert_count: int
    total_amount: float
    risk_level: str

# ============================================
# STATE
# ============================================
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None

# ============================================
# LIFECYCLE
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_client
    
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    logger.info("Database connected")
    
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    await redis_client.ping()
    logger.info("Redis connected")
    
    yield
    
    await db_pool.close()
    await redis_client.close()

# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(
    title="Sentinel Stream - Analytics Service",
    description="Fraud analytics and reporting",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ENDPOINTS
# ============================================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "analytics"}

@app.get("/kpis", response_model=DashboardKPIs)
async def get_dashboard_kpis():
    """Get main dashboard KPIs."""
    cache_key = "analytics:kpis"
    
    # Try cache first
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    async with db_pool.acquire() as conn:
        kpis = await conn.fetchrow("""
            SELECT 
                (SELECT COUNT(*) FROM transactions WHERE created_at >= NOW() - INTERVAL '24 hours') as transactions_24h,
                (SELECT COUNT(*) FROM transactions WHERE created_at >= NOW() - INTERVAL '1 hour') as transactions_1h,
                (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE created_at >= NOW() - INTERVAL '24 hours') as volume_24h,
                (SELECT COUNT(*) FROM fraud_alerts WHERE detected_at >= NOW() - INTERVAL '24 hours') as alerts_24h,
                (SELECT COUNT(*) FROM fraud_alerts WHERE detected_at >= NOW() - INTERVAL '24 hours' AND risk_level = 'CRITICAL') as critical_alerts_24h,
                (SELECT COUNT(*) FROM fraud_alerts WHERE detected_at >= NOW() - INTERVAL '24 hours' AND velocity_triggered = true) as velocity_violations_24h,
                (SELECT COUNT(*) FROM cases WHERE status IN ('open', 'investigating')) as open_cases,
                (SELECT COUNT(*) FROM cases WHERE sla_breached = true AND status NOT IN ('resolved', 'closed')) as sla_breached,
                (SELECT COALESCE(AVG(latency_ms), 0) FROM fraud_alerts WHERE detected_at >= NOW() - INTERVAL '1 hour') as avg_latency_ms
        """)
        
        result = dict(kpis)
        
        # Calculate fraud rate
        if result['transactions_24h'] > 0:
            result['fraud_rate_24h'] = round(result['alerts_24h'] / result['transactions_24h'] * 100, 2)
        else:
            result['fraud_rate_24h'] = 0.0
        
        # Cache for 30 seconds
        await redis_client.setex(cache_key, 30, json.dumps(result))
        
        return result

@app.get("/trends/hourly")
async def get_hourly_trends(hours: int = Query(24, ge=1, le=168)):
    """Get hourly transaction and alert trends."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            WITH hours AS (
                SELECT generate_series(
                    date_trunc('hour', NOW() - INTERVAL '1 hour' * $1),
                    date_trunc('hour', NOW()),
                    INTERVAL '1 hour'
                ) as hour
            )
            SELECT 
                h.hour as timestamp,
                COALESCE(t.transactions, 0) as transactions,
                COALESCE(a.alerts, 0) as alerts,
                COALESCE(a.fraud_amount, 0) as fraud_amount
            FROM hours h
            LEFT JOIN (
                SELECT date_trunc('hour', created_at) as hour, COUNT(*) as transactions
                FROM transactions
                WHERE created_at >= NOW() - INTERVAL '1 hour' * $1
                GROUP BY hour
            ) t ON h.hour = t.hour
            LEFT JOIN (
                SELECT date_trunc('hour', detected_at) as hour, COUNT(*) as alerts, SUM(amount) as fraud_amount
                FROM fraud_alerts
                WHERE detected_at >= NOW() - INTERVAL '1 hour' * $1
                GROUP BY hour
            ) a ON h.hour = a.hour
            ORDER BY h.hour
        """, hours)
        
        return [dict(row) for row in rows]

@app.get("/trends/daily")
async def get_daily_trends(days: int = Query(30, ge=1, le=90)):
    """Get daily transaction and alert trends."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            WITH days AS (
                SELECT generate_series(
                    date_trunc('day', NOW() - INTERVAL '1 day' * $1),
                    date_trunc('day', NOW()),
                    INTERVAL '1 day'
                ) as day
            )
            SELECT 
                d.day as date,
                COALESCE(t.transactions, 0) as transactions,
                COALESCE(t.volume, 0) as volume,
                COALESCE(a.alerts, 0) as alerts,
                COALESCE(a.fraud_amount, 0) as fraud_amount,
                COALESCE(c.cases_opened, 0) as cases_opened,
                COALESCE(c.cases_resolved, 0) as cases_resolved
            FROM days d
            LEFT JOIN (
                SELECT date_trunc('day', created_at) as day, 
                       COUNT(*) as transactions,
                       SUM(amount) as volume
                FROM transactions
                WHERE created_at >= NOW() - INTERVAL '1 day' * $1
                GROUP BY day
            ) t ON d.day = t.day
            LEFT JOIN (
                SELECT date_trunc('day', detected_at) as day, 
                       COUNT(*) as alerts,
                       SUM(amount) as fraud_amount
                FROM fraud_alerts
                WHERE detected_at >= NOW() - INTERVAL '1 day' * $1
                GROUP BY day
            ) a ON d.day = a.day
            LEFT JOIN (
                SELECT date_trunc('day', created_at) as day,
                       COUNT(*) as cases_opened,
                       COUNT(*) FILTER (WHERE resolved_at IS NOT NULL) as cases_resolved
                FROM cases
                WHERE created_at >= NOW() - INTERVAL '1 day' * $1
                GROUP BY day
            ) c ON d.day = c.day
            ORDER BY d.day
        """, days)
        
        return [dict(row) for row in rows]

@app.get("/alerts/by-risk")
async def get_alerts_by_risk(hours: int = Query(24, ge=1, le=168)):
    """Get alert distribution by risk level."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                risk_level,
                COUNT(*) as count,
                SUM(amount) as total_amount,
                AVG(fraud_score) as avg_score
            FROM fraud_alerts
            WHERE detected_at >= NOW() - INTERVAL '1 hour' * $1
            GROUP BY risk_level
            ORDER BY 
                CASE risk_level 
                    WHEN 'CRITICAL' THEN 1 
                    WHEN 'HIGH' THEN 2 
                    WHEN 'MEDIUM' THEN 3 
                    ELSE 4 
                END
        """, hours)
        
        return [dict(row) for row in rows]

@app.get("/alerts/by-category")
async def get_alerts_by_category(hours: int = Query(24, ge=1, le=168)):
    """Get alert distribution by merchant category."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                COALESCE(merchant_category, 'Unknown') as category,
                COUNT(*) as count,
                SUM(amount) as total_amount
            FROM fraud_alerts
            WHERE detected_at >= NOW() - INTERVAL '1 hour' * $1
            GROUP BY merchant_category
            ORDER BY count DESC
            LIMIT 10
        """, hours)
        
        return [dict(row) for row in rows]

@app.get("/alerts/reasons")
async def get_top_fraud_reasons(hours: int = Query(24, ge=1, le=168)):
    """Get top fraud detection reasons."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                fraud_reason,
                COUNT(*) as count,
                SUM(amount) as total_amount,
                AVG(fraud_score) as avg_score
            FROM fraud_alerts
            WHERE detected_at >= NOW() - INTERVAL '1 hour' * $1
            GROUP BY fraud_reason
            ORDER BY count DESC
            LIMIT 10
        """, hours)
        
        return [dict(row) for row in rows]

@app.get("/cards/top-risky")
async def get_top_risky_cards(limit: int = Query(10, ge=1, le=50)):
    """Get cards with most fraud alerts."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                card_id,
                COUNT(*) as alert_count,
                SUM(amount) as total_amount,
                MAX(risk_level) as risk_level,
                MAX(detected_at) as last_alert
            FROM fraud_alerts
            WHERE detected_at >= NOW() - INTERVAL '7 days'
            GROUP BY card_id
            ORDER BY alert_count DESC
            LIMIT $1
        """, limit)
        
        return [dict(row) for row in rows]

@app.get("/customers/risky")
async def get_risky_customers(limit: int = Query(20, ge=1, le=100)):
    """Get high-risk customers."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                id, card_id, customer_name, email,
                risk_score, risk_level,
                total_transactions, total_spent, total_alerts,
                last_transaction_at
            FROM customers
            WHERE risk_level IN ('HIGH', 'CRITICAL') OR total_alerts > 0
            ORDER BY risk_score DESC, total_alerts DESC
            LIMIT $1
        """, limit)
        
        return [dict(row) for row in rows]

@app.get("/rules/performance")
async def get_rules_performance():
    """Get fraud rule performance metrics."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                id as rule_id,
                name as rule_name,
                rule_type,
                total_triggers,
                true_positives,
                false_positives,
                CASE WHEN (true_positives + false_positives) > 0 
                    THEN ROUND(true_positives::numeric / (true_positives + false_positives) * 100, 2)
                    ELSE 0 
                END as precision,
                is_active,
                created_at
            FROM fraud_rules
            ORDER BY total_triggers DESC
        """)
        
        return [dict(row) for row in rows]

@app.get("/performance/latency")
async def get_latency_distribution(hours: int = Query(1, ge=1, le=24)):
    """Get latency distribution for processing times."""
    async with db_pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total,
                AVG(latency_ms) as avg_latency,
                MIN(latency_ms) as min_latency,
                MAX(latency_ms) as max_latency,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY latency_ms) as p50,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95,
                PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99
            FROM fraud_alerts
            WHERE detected_at >= NOW() - INTERVAL '1 hour' * $1
        """, hours)
        
        return dict(stats)

@app.get("/performance/throughput")
async def get_throughput_stats(hours: int = Query(1, ge=1, le=24)):
    """Get throughput statistics."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                date_trunc('minute', created_at) as minute,
                COUNT(*) as transactions,
                COUNT(*) / 60.0 as tps
            FROM transactions
            WHERE created_at >= NOW() - INTERVAL '1 hour' * $1
            GROUP BY minute
            ORDER BY minute
        """, hours)
        
        result = [dict(row) for row in rows]
        
        if result:
            tps_values = [r['tps'] for r in result]
            return {
                "data": result,
                "avg_tps": sum(tps_values) / len(tps_values),
                "max_tps": max(tps_values),
                "min_tps": min(tps_values)
            }
        
        return {"data": [], "avg_tps": 0, "max_tps": 0, "min_tps": 0}

@app.get("/summary")
async def get_executive_summary():
    """Get executive summary for reports."""
    async with db_pool.acquire() as conn:
        summary = await conn.fetchrow("""
            SELECT 
                -- Today's stats
                (SELECT COUNT(*) FROM transactions WHERE created_at >= CURRENT_DATE) as today_transactions,
                (SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE created_at >= CURRENT_DATE) as today_volume,
                (SELECT COUNT(*) FROM fraud_alerts WHERE detected_at >= CURRENT_DATE) as today_alerts,
                (SELECT COALESCE(SUM(amount), 0) FROM fraud_alerts WHERE detected_at >= CURRENT_DATE) as today_fraud_amount,
                
                -- This week's stats
                (SELECT COUNT(*) FROM transactions WHERE created_at >= date_trunc('week', CURRENT_DATE)) as week_transactions,
                (SELECT COUNT(*) FROM fraud_alerts WHERE detected_at >= date_trunc('week', CURRENT_DATE)) as week_alerts,
                (SELECT COUNT(*) FROM cases WHERE created_at >= date_trunc('week', CURRENT_DATE)) as week_cases_opened,
                (SELECT COUNT(*) FROM cases WHERE resolved_at >= date_trunc('week', CURRENT_DATE)) as week_cases_resolved,
                
                -- Overall stats
                (SELECT COUNT(*) FROM customers) as total_customers,
                (SELECT COUNT(*) FROM fraud_rules WHERE is_active = true) as active_rules,
                (SELECT COUNT(*) FROM cases WHERE status NOT IN ('resolved', 'closed')) as pending_cases
        """)
        
        return dict(summary)
