
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.events import get_db
from app.db.models import Message, Incident, APIKey, Policy
from app.api.models import MessageInput, MessageResponse
from app.engines.sdk import sdk
from app.services.policy_engine import policy_engine
from app.core.security import get_api_key
from sqlalchemy.future import select

router = APIRouter()

@router.post("/message", response_model=MessageResponse)
async def monitor_message(
    msg_in: MessageInput,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    # Verify tenant
    if msg_in.tenant_id != api_key.tenant_id:
        # In a real scenario we might block this, but for now we trust the API key's tenant
        msg_in.tenant_id = api_key.tenant_id

    # Update agent last_seen (heartbeat)
    from datetime import datetime
    from app.db.models import Agent
    agent_result = await db.execute(select(Agent).filter(Agent.id == msg_in.agent_id))
    agent = agent_result.scalars().first()
    if agent:
        agent.last_seen = datetime.utcnow()
    
    # Log message
    db_msg = Message(
        tenant_id=msg_in.tenant_id,
        agent_id=msg_in.agent_id,
        direction=msg_in.direction,
        payload={"content": msg_in.content}
    )
    db.add(db_msg)
    
    # 1. Policy Check (Fast)
    # Fetch tenant policy from DB
    policy_query = select(Policy).where(Policy.tenant_id == msg_in.tenant_id, Policy.is_active == True)
    policy_obj = (await db.execute(policy_query)).scalars().first()
    
    policy_yaml = policy_obj.content if policy_obj else ""
    
    policy_result = policy_engine.evaluate_policy(msg_in.content, policy_yaml)
    
    if not policy_result["allowed"]:
        # Create incident
        incident = Incident(
            tenant_id=msg_in.tenant_id,
            agent_id=msg_in.agent_id,
            severity="high",
            classification="policy_violation",
            transcript_ref=msg_in.content,
            status="open"
        )
        db.add(incident)
        
        # Update message decision
        db_msg.decision = "block"
        
        await db.commit()
        await db.refresh(incident)
        return MessageResponse(allowed=False, reason=policy_result["reason"], incident_id=incident.id)

    # 2. Engine Evaluation (PRE or OSE)
    incident_id = None
    allowed = True
    reason = None
    
    if msg_in.direction == "in":
        # User -> Agent: Check for Prompt Injection / Jailbreaks (PRE)
        eval_result = sdk.evaluate_prompt(msg_in.content)
        
        if eval_result["risk_level"] != "low":
            allowed = False
            reason = f"Blocked by PRE: {eval_result['risk_level']} risk detected."
            if "remediation_suggestion" in eval_result:
                reason += f" Suggestion: {eval_result['remediation_suggestion']}"
            
            incident = Incident(
                tenant_id=msg_in.tenant_id,
                agent_id=msg_in.agent_id,
                severity="critical" if eval_result["risk_level"] == "critical" else "high",
                classification="jailbreak_attempt",
                transcript_ref=msg_in.content,
                status="open"
            )
            db.add(incident)
            await db.commit()
            await db.refresh(incident)
            incident_id = incident.id
            
            db_msg.decision = "block"

    else:
        # Agent -> User: Check for Harmful Content / PII (OSE)
        # We need the original prompt for context if available, but here we might only have the output
        # For now, we pass "Unknown Prompt" or maybe we should change the API to accept it
        eval_result = sdk.evaluate_output(prompt="[Unknown Prompt]", output=msg_in.content)
        
        if eval_result["decision"] != "allow":
            allowed = False
            reason = "Blocked by OSE: Unsafe content detected."
            
            incident = Incident(
                tenant_id=msg_in.tenant_id,
                agent_id=msg_in.agent_id,
                severity="high",
                classification="unsafe_output",
                transcript_ref=msg_in.content,
                status="open"
            )
            db.add(incident)
            await db.commit()
            await db.refresh(incident)
            incident_id = incident.id
            
            db_msg.decision = "block"

    if allowed:
        db_msg.decision = "allow"
        await db.commit()

    return MessageResponse(allowed=allowed, reason=reason, incident_id=incident_id)
