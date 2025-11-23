from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.events import get_db
from app.db.models import Agent, APIKey
from app.core.security import get_api_key
from pydantic import BaseModel
from typing import List
from collections import defaultdict

router = APIRouter()

class ModelResponse(BaseModel):
    name: str
    agent_count: int
    agents: List[str] = []
    risk_score: int = 0
    calls: int = 0

@router.get("/", response_model=List[ModelResponse])
async def list_models(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """List all models used by agents in this tenant with metrics"""
    from sqlalchemy import func
    from app.db.models import Message
    from datetime import datetime, timedelta
    
    result = await db.execute(
        select(Agent).filter(Agent.tenant_id == tenant_id)
    )
    agents = result.scalars().all()
    
    # Group agents by model
    models_map = defaultdict(lambda: {"agents": [], "agent_ids": []})
    for agent in agents:
        model_name = agent.model_info or "Unknown"
        models_map[model_name]["agents"].append(agent.name)
        models_map[model_name]["agent_ids"].append(agent.id)
    
    # Enhance with metrics
    models = []
    for model_name, data in models_map.items():
        agent_ids = data["agent_ids"]
        
        # Get total calls (last 24h) for all agents using this model
        msg_result = await db.execute(
            select(func.count(Message.id)).filter(
                Message.agent_id.in_(agent_ids),
                Message.timestamp >= datetime.utcnow() - timedelta(hours=24)
            )
        )
        calls_24h = msg_result.scalar() or 0
        
        # Get risk score
        blocked_result = await db.execute(
            select(func.count(Message.id)).filter(
                Message.agent_id.in_(agent_ids),
                Message.timestamp >= datetime.utcnow() - timedelta(hours=24),
                Message.decision.in_(["block", "flag"])
            )
        )
        blocked_count = blocked_result.scalar() or 0
        risk_score = int((blocked_count / calls_24h * 100)) if calls_24h > 0 else 0
        
        models.append({
            "name": model_name,
            "agent_count": len(data["agents"]),
            "agents": data["agents"],
            "risk_score": risk_score,
            "calls": calls_24h
        })
    
    return models

@router.get("/{model_name}/agents")
async def get_model_agents(
    model_name: str,
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """List all agents using a specific model"""
    result = await db.execute(
        select(Agent).filter(
            Agent.tenant_id == tenant_id,
            Agent.model_info == model_name
        )
    )
    agents = result.scalars().all()
    return [{"id": a.id, "name": a.name} for a in agents]
