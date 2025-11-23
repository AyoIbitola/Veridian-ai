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
    """List all agents for a tenant with metrics"""
    from sqlalchemy import func
    from app.db.models import Message, ToolEvent
    from datetime import datetime, timedelta
    
    result = await db.execute(
        select(Agent).filter(Agent.tenant_id == tenant_id)
    )
    agents = result.scalars().all()
    
    # Enhance with metrics
    agent_list = []
    for agent in agents:
        # Get message count (last 24h)
        msg_result = await db.execute(
            select(func.count(Message.id)).filter(
                Message.agent_id == agent.id,
                Message.timestamp >= datetime.utcnow() - timedelta(hours=24)
            )
        )
        calls_24h = msg_result.scalar() or 0
        
        # Get risk score (% of blocked messages in last 24h)
        blocked_result = await db.execute(
            select(func.count(Message.id)).filter(
                Message.agent_id == agent.id,
                Message.timestamp >= datetime.utcnow() - timedelta(hours=24),
                Message.decision.in_(["block", "flag"])
            )
        )
        blocked_count = blocked_result.scalar() or 0
        risk_score = int((blocked_count / calls_24h * 100)) if calls_24h > 0 else 0
        
        # Get live actions count (recent tool calls)
        tool_result = await db.execute(
            select(func.count(ToolEvent.id)).filter(
                ToolEvent.agent_id == agent.id,
                ToolEvent.timestamp >= datetime.utcnow() - timedelta(hours=1)
            )
        )
        live_actions = tool_result.scalar() or 0
        
        agent_list.append({
            "id": agent.id,
            "name": agent.name,
            "model_info": agent.model_info,
            "allowed_tools": agent.allowed_tools,
            "tenant_id": agent.tenant_id,
            "created_at": agent.created_at,
            "risk_score": risk_score,
            "calls": calls_24h,
            "live_actions": live_actions
        })
    
    return agent_list

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
        target_url=agent_in.target_url,
        allowed_tools=agent_in.allowed_tools
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent
