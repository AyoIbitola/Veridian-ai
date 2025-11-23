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

@router.get("/", response_model=List[ModelResponse])
async def list_models(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """List all models used by agents in this tenant"""
    result = await db.execute(
        select(Agent).filter(Agent.tenant_id == tenant_id)
    )
    agents = result.scalars().all()
    
    # Group agents by model
    models_map = defaultdict(list)
    for agent in agents:
        model_name = agent.model_info or "Unknown"
        models_map[model_name].append(agent.name)
    
    # Convert to response format
    models = [
        ModelResponse(
            name=model_name,
            agent_count=len(agent_names),
            agents=agent_names
        )
        for model_name, agent_names in models_map.items()
    ]
    
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
