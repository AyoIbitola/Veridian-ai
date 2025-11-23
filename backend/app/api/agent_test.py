from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.events import get_db
from app.db.models import Agent, APIKey
from app.core.security import get_api_key
import httpx

router = APIRouter()

@router.post("/test/{agent_id}")
async def test_agent_connection(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """Test connection to an agent's target URL"""
    # Get agent
    result = await db.execute(select(Agent).filter(Agent.id == agent_id))
    agent = result.scalars().first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if agent.tenant_id != api_key.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if agent has target_url
    if not agent.target_url:
        return {
            "status": "success",
            "message": "Agent registered successfully (SDK mode - no URL to test)",
            "connection_type": "sdk"
        }
    
    # Test connection to target_url
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                agent.target_url,
                json={"prompt": "Connection test from Veridian"}
            )
            
            if response.status_code in [200, 201]:
                return {
                    "status": "success",
                    "message": f"Successfully connected to {agent.target_url}",
                    "connection_type": "url",
                    "response_code": response.status_code
                }
            else:
                return {
                    "status": "warning",
                    "message": f"Agent URL returned {response.status_code}",
                    "connection_type": "url",
                    "response_code": response.status_code
                }
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=408,
            detail=f"Connection timeout - Could not reach {agent.target_url}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Connection failed: {str(e)}"
        )
