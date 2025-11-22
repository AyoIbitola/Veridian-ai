from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from app.db.events import get_db
from app.db.models import Message
from typing import List, Dict, Any
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/threat-score")
async def get_threat_score(agentId: int, db: AsyncSession = Depends(get_db)):
    # Calculate score based on blocked/flagged ratio in last 24h
    since = datetime.utcnow() - timedelta(hours=24)
    
    total_query = select(func.count()).where(
        Message.agent_id == agentId,
        Message.timestamp >= since
    )
    total = (await db.execute(total_query)).scalar() or 0
    
    if total == 0:
        return {"score": 0, "level": "low"}
        
    unsafe_query = select(func.count()).where(
        Message.agent_id == agentId,
        Message.timestamp >= since,
        Message.decision.in_(["block", "flag"])
    )
    unsafe = (await db.execute(unsafe_query)).scalar() or 0
    
    score = int((unsafe / total) * 100)
    level = "low"
    if score > 30: level = "medium"
    if score > 70: level = "high"
    
    return {"score": score, "level": level}

@router.get("/incidents/timeline")
async def get_incident_timeline(agentId: int, period: str = "24h", db: AsyncSession = Depends(get_db)):
    hours = 24
    if period == "7d": hours = 168
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # Group by hour
    # Note: SQLite date truncation is tricky, simplifying to raw fetch for now
    # In production Postgres: func.date_trunc('hour', Message.timestamp)
    
    query = select(Message.timestamp).where(
        Message.agent_id == agentId,
        Message.timestamp >= since,
        Message.decision != "allow"
    )
    result = await db.execute(query)
    timestamps = result.scalars().all()
    
    # Aggregate in python for database agnosticism (SQLite vs Postgres)
    timeline = {}
    for ts in timestamps:
        key = ts.replace(minute=0, second=0, microsecond=0).isoformat()
        timeline[key] = timeline.get(key, 0) + 1
        
    return [{"time": k, "count": v} for k, v in timeline.items()]

@router.get("/violations/categories")
async def get_violation_categories(agentId: int, period: str = "24h", db: AsyncSession = Depends(get_db)):
    # This would require parsing the 'risks' JSON column or having a separate categories table
    # For now, we'll return a placeholder as implementing JSON querying in SQLite is complex
    return {
        "prompt_injection": 0,
        "pii_leak": 0,
        "toxic_content": 0
    }

@router.get("/responses/heatmap")
async def get_response_heatmap(agentId: int, db: AsyncSession = Depends(get_db)):
    # Heatmap of activity (allow vs block) over last 7 days
    since = datetime.utcnow() - timedelta(days=7)
    query = select(Message.timestamp).where(
        Message.agent_id == agentId,
        Message.timestamp >= since
    )
    result = await db.execute(query)
    timestamps = result.scalars().all()
    
    # 7 days x 24 hours grid
    grid = [[0 for _ in range(24)] for _ in range(7)]
    
    for ts in timestamps:
        day_idx = (datetime.utcnow() - ts).days
        if 0 <= day_idx < 7:
            grid[day_idx][ts.hour] += 1
            
    return grid

@router.get("/behaviour-drift")
async def get_behaviour_drift(agentId: int):
    # Placeholder: Drift detection requires vector DB or statistical analysis of embeddings
    return {"drift_detected": False, "magnitude": 0.0}

@router.get("/incidents")
async def get_incidents_analytics(agentId: int, db: AsyncSession = Depends(get_db)):
    total = (await db.execute(select(func.count()).where(Message.agent_id == agentId))).scalar()
    blocked = (await db.execute(select(func.count()).where(Message.agent_id == agentId, Message.decision == "block"))).scalar()
    flagged = (await db.execute(select(func.count()).where(Message.agent_id == agentId, Message.decision == "flag"))).scalar()
    
    return {
        "total": total,
        "open": flagged, # Treating flagged as 'open' incidents
        "resolved": blocked # Treating blocked as 'resolved' (stopped)
    }
