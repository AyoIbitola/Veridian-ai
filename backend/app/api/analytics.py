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
    
    # Group by hour using Postgres date_trunc
    query = select(
        func.date_trunc('hour', Message.timestamp).label('hour'), 
        func.count(Message.id)
    ).where(
        Message.agent_id == agentId,
        Message.timestamp >= since,
        Message.decision != "allow"
    ).group_by('hour').order_by('hour')
    
    result = await db.execute(query)
    rows = result.all()
    
    return [{"time": row[0].isoformat(), "count": row[1]} for row in rows]

@router.get("/usage")
async def get_model_usage(agentId: int, period: str = "30d", db: AsyncSession = Depends(get_db)):
    days = 30
    if period == "7d": days = 7
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Count messages per day using Postgres date_trunc
    query = select(
        func.date_trunc('day', Message.timestamp).label('day'),
        func.count(Message.id)
    ).where(
        Message.agent_id == agentId,
        Message.timestamp >= since
    ).group_by('day').order_by('day')
    
    result = await db.execute(query)
    rows = result.all()
    
    return [{"date": row[0].strftime("%Y-%m-%d"), "count": row[1]} for row in rows]

@router.get("/threat-score/history")
async def get_risk_score_history(agentId: int, period: str = "30d", db: AsyncSession = Depends(get_db)):
    days = 30
    since = datetime.utcnow() - timedelta(days=days)
    
    # Group by day and decision
    query = select(
        func.date_trunc('day', Message.timestamp).label('day'),
        Message.decision,
        func.count(Message.id)
    ).where(
        Message.agent_id == agentId,
        Message.timestamp >= since
    ).group_by('day', Message.decision).order_by('day')
    
    result = await db.execute(query)
    rows = result.all()
    
    # Process results in Python to calculate score per day
    daily_stats = {}
    for day, decision, count in rows:
        date_key = day.strftime("%Y-%m-%d")
        if date_key not in daily_stats:
            daily_stats[date_key] = {"total": 0, "unsafe": 0}
        
        daily_stats[date_key]["total"] += count
        if decision in ["block", "flag"]:
            daily_stats[date_key]["unsafe"] += count
            
    history = []
    for date_key, stats in sorted(daily_stats.items()):
        score = 0
        if stats["total"] > 0:
            score = int((stats["unsafe"] / stats["total"]) * 100)
        history.append({"date": date_key, "score": score})
        
    return history

@router.get("/actions")
async def get_agent_actions(agentId: int, period: str = "24h", db: AsyncSession = Depends(get_db)):
    from app.db.models import ToolEvent
    hours = 24
    since = datetime.utcnow() - timedelta(hours=hours)
    
    query = select(ToolEvent.tool_name, func.count(ToolEvent.id)).where(
        ToolEvent.agent_id == agentId,
        ToolEvent.timestamp >= since
    ).group_by(ToolEvent.tool_name)
    
    result = await db.execute(query)
    rows = result.all()
    
    return [{"name": row[0], "count": row[1]} for row in rows]

@router.get("/violations/categories")
async def get_violation_categories(agentId: int, period: str = "30d", db: AsyncSession = Depends(get_db)):
    from app.db.models import Incident
    days = 30
    since = datetime.utcnow() - timedelta(days=days)
    
    # Incident model uses created_at
    query = select(Incident.classification, func.count(Incident.id)).where(
        Incident.agent_id == agentId,
        Incident.created_at >= since
    ).group_by(Incident.classification)
    
    result = await db.execute(query)
    rows = result.all()
    
    categories = {
        "prompt_injection": 0,
        "pii_leak": 0,
        "toxic_content": 0,
        "unsafe_tool_use": 0,
        "policy_violation": 0
    }
    
    for classification, count in rows:
        categories[classification] = count
        
    return categories
