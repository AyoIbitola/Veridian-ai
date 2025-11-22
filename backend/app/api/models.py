from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class AgentRegister(BaseModel):
    name: str
    tenant_id: int
    model_info: str
    allowed_tools: List[str]

class AgentResponse(AgentRegister):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class MessageInput(BaseModel):
    agent_id: int
    tenant_id: int
    content: str
    direction: str = "in" # in or out

class MessageResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None
    incident_id: Optional[int] = None

class CampaignStart(BaseModel):
    agent_ids: List[int]
    tenant_id: int
    templates: List[str]
    mutators: List[str]
    run_config: Dict[str, Any]

class CampaignResponse(BaseModel):
    campaign_id: int
    status: str

class IncidentResponse(BaseModel):
    id: int
    tenant_id: int
    agent_id: int
    severity: str
    classification: str
    transcript_ref: str
    created_at: datetime
    status: str

    class Config:
        from_attributes = True

class RemediationRequest(BaseModel):
    suggestion_text: Optional[str] = None
    apply: bool = True

class WebhookEvent(BaseModel):
    agent_id: int
    event_type: str
    payload: Dict[str, Any]

class WebhookResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None

class PolicyUpload(BaseModel):
    policy_content: str # YAML or JSON string
    format: str = "yaml"

class MetricsResponse(BaseModel):
    tenant_id: int
    date: datetime
    exploit_success_rate: float
    mttd: float
    fp_rate: float
    remediation_efficacy: float

    class Config:
        from_attributes = True
