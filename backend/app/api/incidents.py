from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.db.events import get_db
from app.db.models import Incident, Remediation
from app.api.models import IncidentResponse, RemediationRequest
from app.core.security import get_api_key

router = APIRouter()

@router.get("/", response_model=List[IncidentResponse])
async def list_incidents(
    tenant_id: int = None,
    severity: str = None,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    query = select(Incident)
    if tenant_id:
        query = query.filter(Incident.tenant_id == tenant_id)
    if severity:
        query = query.filter(Incident.severity == severity)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    incident = await db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@router.post("/{incident_id}/remediate")
async def remediate_incident(
    incident_id: int,
    remediation_in: RemediationRequest,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    incident = await db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    # Apply remediation logic here (mocked)
    remediation = Remediation(
        incident_id=incident.id,
        suggestion_text=remediation_in.suggestion_text or "Auto-fix applied",
        applied_by="system",
        result="success"
    )
    db.add(remediation)
    incident.status = "resolved"
    await db.commit()
    
    return {"status": "remediation applied"}
