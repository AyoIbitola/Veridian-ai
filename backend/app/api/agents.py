from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.events import get_db
from app.db.models import Agent
from app.api.models import AgentRegister, AgentResponse
from app.core.security import get_api_key

router = APIRouter()

@router.post("/register", response_model=AgentResponse)
async def register_agent(
    agent_in: AgentRegister,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
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
