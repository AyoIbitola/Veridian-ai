from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.events import get_db
from app.db.models import Incident
from app.api.models import WebhookEvent, WebhookResponse
from app.core.security import get_api_key
from app.engines.sdk import sdk

router = APIRouter()

@router.post("/agent_event", response_model=WebhookResponse)
async def handle_agent_event(
    event: WebhookEvent,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    # Logic to check event type and payload
    if event.event_type == "tool_call":
        # Use AIM Engine to evaluate the tool call
        action_data = {
            "tool": event.payload.get("tool"),
            "args": event.payload.get("args", "")
        }
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.events import get_db
from app.db.models import Incident, APIKey, ToolEvent
from app.api.models import WebhookEvent, WebhookResponse
from app.core.security import get_api_key
from app.engines.sdk import sdk

router = APIRouter()

@router.post("/agent_event", response_model=WebhookResponse)
async def handle_agent_event(
    event: WebhookEvent,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    # Update agent last_seen (heartbeat)
    from datetime import datetime
    agent_result = await db.execute(select(Agent).filter(Agent.id == event.agent_id))
    agent = agent_result.scalars().first()
    if agent:
        agent.last_seen = datetime.utcnow()
        await db.commit()
    
    # Logic to check event type and payload
    if event.event_type == "tool_call":
        # Use AIM Engine to evaluate the tool call
        action_data = {
            "tool": event.payload.get("tool"),
            "args": event.payload.get("args", "")
        }
        
        eval_result = sdk.evaluate_action(action_data)
        
        # Log Tool Event
        tool_event = ToolEvent(
            tenant_id=api_key.tenant_id,
            agent_id=event.agent_id,
            tool_name=event.payload.get("tool"),
            tool_args=str(event.payload.get("args", "")),
            allowed=(eval_result["decision"] == "allow")
        )
        db.add(tool_event)
        await db.commit()
        
        if eval_result["decision"] != "allow":
            # Create Incident
            incident = Incident(
                tenant_id=api_key.tenant_id,
                agent_id=event.agent_id, # Keeping original agent_id as it's more dynamic
                severity="critical",
                classification="unsafe_tool_use",
                transcript_ref=f"Tool: {event.payload.get('tool')} | Args: {event.payload.get('args')} | Reason: {eval_result.get('reason', 'N/A')}",
                status="open"
            )
            db.add(incident)
            await db.commit()
            
            # Send Alert
            from app.services.notifications import notification_service
            await notification_service.alert_incident(incident)
            
            return WebhookResponse(status="blocked", incident_id=incident.id)
    
    return WebhookResponse(allowed=True)
