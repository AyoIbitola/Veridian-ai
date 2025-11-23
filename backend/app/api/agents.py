from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.events import get_db
from app.db.models import Agent, APIKey
from app.api.models import AgentRegister, AgentResponse
from app.core.security import get_api_key
from typing import List

router = APIRouter()

@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """List all agents for a tenant"""
    result = await db.execute(
        select(Agent).filter(Agent.tenant_id == tenant_id)
    )
    agents = result.scalars().all()
    return agents

@router.post("/register", response_model=AgentResponse)
async def register_agent(
    agent_in: AgentRegister,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    agent = Agent(
        name=agent_in.name,
        tenant_id=agent_in.tenant_id,
        model_info=agent_in.model_info,
        allowed_tools=agent_in.allowed_tools
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent
