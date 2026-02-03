"""
Sentinel Stream - Case Management Service
Handles fraud investigation cases, assignments, and workflow
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncpg
import redis.asyncio as redis
import os
import logging

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("case-service")

# ============================================
# CONFIGURATION
# ============================================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sentinel:sentinel_secure_2024@localhost:5432/sentinel_stream")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")

# ============================================
# MODELS
# ============================================
class CaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    alert_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    card_id: Optional[str] = None
    priority: str = Field(default="medium")
    category: Optional[str] = None
    total_amount: float = Field(default=0.0)

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    assigned_to: Optional[UUID] = None
    resolution: Optional[str] = None
    resolution_notes: Optional[str] = None

class CaseResponse(BaseModel):
    id: UUID
    case_number: str
    title: str
    description: Optional[str]
    priority: str
    status: str
    category: Optional[str]
    card_id: Optional[str]
    total_amount: float
    potential_loss: float
    recovered_amount: float
    assigned_to: Optional[UUID]
    assigned_name: Optional[str] = None
    sla_due_at: Optional[datetime]
    sla_breached: bool
    created_at: datetime
    updated_at: datetime

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1)
    is_internal: bool = True

class CommentResponse(BaseModel):
    id: UUID
    case_id: UUID
    user_id: UUID
    user_name: str
    content: str
    is_internal: bool
    created_at: datetime

class CaseStats(BaseModel):
    total_cases: int
    open_cases: int
    investigating: int
    resolved: int
    sla_breached: int
    avg_resolution_hours: float

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
    
    # Initialize database
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    logger.info("Database connected")
    
    # Initialize Redis
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    await redis_client.ping()
    logger.info("Redis connected")
    
    yield
    
    # Cleanup
    await db_pool.close()
    await redis_client.close()
    logger.info("Case service shutdown")

# ============================================
# FASTAPI APP
# ============================================
app = FastAPI(
    title="Sentinel Stream - Case Management Service",
    description="Fraud investigation case management",
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
# HELPER FUNCTIONS
# ============================================
def calculate_sla(priority: str) -> datetime:
    """Calculate SLA due date based on priority."""
    sla_hours = {
        "critical": 2,
        "high": 8,
        "medium": 24,
        "low": 72
    }
    hours = sla_hours.get(priority, 24)
    return datetime.utcnow() + timedelta(hours=hours)

async def log_activity(case_id: UUID, user_id: Optional[UUID], action: str, old_value: str = None, new_value: str = None):
    """Log case activity for audit trail."""
    await db_pool.execute("""
        INSERT INTO case_activities (case_id, user_id, action, old_value, new_value)
        VALUES ($1, $2, $3, $4, $5)
    """, case_id, user_id, action, old_value, new_value)

# ============================================
# ENDPOINTS
# ============================================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "case-management"}

@app.get("/cases", response_model=List[CaseResponse])
async def list_cases(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assigned_to: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """List all cases with optional filters."""
    query = """
        SELECT c.*, u.full_name as assigned_name
        FROM cases c
        LEFT JOIN users u ON c.assigned_to = u.id
        WHERE 1=1
    """
    params = []
    param_count = 0
    
    if status:
        param_count += 1
        query += f" AND c.status = ${param_count}"
        params.append(status)
    
    if priority:
        param_count += 1
        query += f" AND c.priority = ${param_count}"
        params.append(priority)
    
    if assigned_to:
        param_count += 1
        query += f" AND c.assigned_to = ${param_count}"
        params.append(assigned_to)
    
    query += f" ORDER BY c.created_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
    params.extend([limit, offset])
    
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

@app.get("/cases/stats", response_model=CaseStats)
async def get_case_stats():
    """Get case statistics."""
    async with db_pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_cases,
                COUNT(*) FILTER (WHERE status = 'open') as open_cases,
                COUNT(*) FILTER (WHERE status = 'investigating') as investigating,
                COUNT(*) FILTER (WHERE status IN ('resolved', 'closed')) as resolved,
                COUNT(*) FILTER (WHERE sla_breached = true AND status NOT IN ('resolved', 'closed')) as sla_breached,
                COALESCE(AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600) 
                    FILTER (WHERE resolved_at IS NOT NULL), 0) as avg_resolution_hours
            FROM cases
        """)
        return dict(stats)

@app.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(case_id: UUID):
    """Get a specific case by ID."""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT c.*, u.full_name as assigned_name
            FROM cases c
            LEFT JOIN users u ON c.assigned_to = u.id
            WHERE c.id = $1
        """, case_id)
        
        if not row:
            raise HTTPException(status_code=404, detail="Case not found")
        
        return dict(row)

@app.post("/cases", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(case: CaseCreate):
    """Create a new investigation case."""
    sla_due = calculate_sla(case.priority)
    
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO cases (title, description, alert_id, customer_id, card_id, 
                             priority, category, total_amount, potential_loss, sla_due_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $8, $9)
            RETURNING *
        """, case.title, case.description, case.alert_id, case.customer_id,
           case.card_id, case.priority, case.category, case.total_amount, sla_due)
        
        await log_activity(row['id'], None, 'created')
        
        return dict(row)

@app.patch("/cases/{case_id}", response_model=CaseResponse)
async def update_case(case_id: UUID, update: CaseUpdate):
    """Update a case."""
    async with db_pool.acquire() as conn:
        # Get current case
        current = await conn.fetchrow("SELECT * FROM cases WHERE id = $1", case_id)
        if not current:
            raise HTTPException(status_code=404, detail="Case not found")
        
        # Build update query
        updates = []
        params = []
        param_count = 0
        
        for field, value in update.dict(exclude_unset=True).items():
            if value is not None:
                param_count += 1
                updates.append(f"{field} = ${param_count}")
                params.append(value)
                
                # Log status changes
                if field == 'status':
                    await log_activity(case_id, None, 'status_changed', current['status'], value)
                elif field == 'assigned_to':
                    await log_activity(case_id, None, 'assigned', str(current['assigned_to']), str(value))
        
        if updates:
            params.append(case_id)
            query = f"UPDATE cases SET {', '.join(updates)}, updated_at = NOW() WHERE id = ${len(params)} RETURNING *"
            row = await conn.fetchrow(query, *params)
            return dict(row)
        
        return dict(current)

@app.post("/cases/{case_id}/assign")
async def assign_case(case_id: UUID, user_id: UUID):
    """Assign a case to a user."""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE cases 
            SET assigned_to = $1, assigned_at = NOW(), status = 'investigating'
            WHERE id = $2
        """, user_id, case_id)
        
        await log_activity(case_id, user_id, 'assigned')
        
        return {"message": "Case assigned successfully"}

@app.post("/cases/{case_id}/resolve")
async def resolve_case(case_id: UUID, resolution: str, notes: Optional[str] = None):
    """Resolve a case."""
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE cases 
            SET status = 'resolved', resolution = $1, resolution_notes = $2,
                resolved_at = NOW()
            WHERE id = $3
        """, resolution, notes, case_id)
        
        await log_activity(case_id, None, 'resolved', None, resolution)
        
        return {"message": "Case resolved successfully"}

@app.get("/cases/{case_id}/comments", response_model=List[CommentResponse])
async def get_case_comments(case_id: UUID):
    """Get all comments for a case."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT cc.*, u.full_name as user_name
            FROM case_comments cc
            JOIN users u ON cc.user_id = u.id
            WHERE cc.case_id = $1
            ORDER BY cc.created_at DESC
        """, case_id)
        return [dict(row) for row in rows]

@app.post("/cases/{case_id}/comments", response_model=CommentResponse)
async def add_case_comment(case_id: UUID, comment: CommentCreate):
    """Add a comment to a case."""
    # For demo, use admin user
    admin_id = None
    async with db_pool.acquire() as conn:
        admin = await conn.fetchrow("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        if admin:
            admin_id = admin['id']
        
        row = await conn.fetchrow("""
            INSERT INTO case_comments (case_id, user_id, content, is_internal)
            VALUES ($1, $2, $3, $4)
            RETURNING *
        """, case_id, admin_id, comment.content, comment.is_internal)
        
        await log_activity(case_id, admin_id, 'commented')
        
        result = dict(row)
        result['user_name'] = 'System Admin'
        return result

@app.get("/cases/{case_id}/timeline")
async def get_case_timeline(case_id: UUID):
    """Get the activity timeline for a case."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT ca.*, u.full_name as user_name
            FROM case_activities ca
            LEFT JOIN users u ON ca.user_id = u.id
            WHERE ca.case_id = $1
            ORDER BY ca.created_at DESC
        """, case_id)
        return [dict(row) for row in rows]

@app.get("/users/analysts")
async def get_analysts():
    """Get list of analysts for case assignment."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, full_name, email, department
            FROM users
            WHERE role IN ('analyst', 'admin') AND is_active = true
            ORDER BY full_name
        """)
        return [dict(row) for row in rows]
