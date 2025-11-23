from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    plan = Column(String, default="free")
    notification_config = Column(JSON, default={}) # {"slack_webhook": "", "email_recipients": []}
    created_at = Column(DateTime, default=datetime.utcnow)
    
    agents = relationship("Agent", back_populates="tenant")
    policies = relationship("Policy", back_populates="tenant")
    api_keys = relationship("APIKey", back_populates="tenant")

class Policy(Base):
    __tablename__ = "policies"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    name = Column(String)
    content = Column(Text) # YAML content
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="policies")

class Agent(Base):
    __tablename__ = "agents"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    name = Column(String)
    model_info = Column(String)
    allowed_tools = Column(JSON)
    target_url = Column(String, nullable=True) # For Option 1 (URL Mode)
    api_key = Column(String, nullable=True) # For Option 2 (SDK Mode) & Rotation
    mode = Column(String, default="sdk") # "url" or "sdk"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    tenant = relationship("Tenant", back_populates="agents")
    messages = relationship("Message", back_populates="agent")
    incidents = relationship("Incident", back_populates="agent")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    direction = Column(String) # "in" or "out"
    payload = Column(JSON)
    decision = Column(String, default="allow") # allow, block, flag
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    agent = relationship("Agent", back_populates="messages")

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    name = Column(String)
    status = Column(String) # running, completed, failed
    config = Column(JSON)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    severity = Column(String) # low, medium, high, critical
    classification = Column(String)
    transcript_ref = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    detected_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="open")
    
    agent = relationship("Agent", back_populates="incidents")
    remediations = relationship("Remediation", back_populates="incident")

class Remediation(Base):
    __tablename__ = "remediations"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"))
    suggestion_text = Column(Text)
    applied_by = Column(String, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    result = Column(String, nullable=True)
    
    incident = relationship("Incident", back_populates="remediations")

class Metrics(Base):
    __tablename__ = "metrics"
    tenant_id = Column(Integer, ForeignKey("tenants.id"), primary_key=True)
    date = Column(DateTime, default=datetime.utcnow, primary_key=True)
    exploit_success_rate = Column(Integer) # Percentage 0-100
    mttd = Column(Integer) # Mean Time To Detect in seconds
    fp_rate = Column(Integer) # False Positive Rate 0-100
    remediation_efficacy = Column(Integer) # Percentage 0-100

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    password_hash = Column(String)
    provider = Column(String, default="local") # local, github
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workspaces = relationship("Workspace", back_populates="owner")
    api_keys = relationship("APIKey", back_populates="owner")

class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    tenant_id = Column(Integer, ForeignKey("tenants.id")) # Link to existing Tenant concept
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="workspaces")
    tenant = relationship("Tenant")

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String, index=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    owner = relationship("User", back_populates="api_keys")
    tenant = relationship("Tenant", back_populates="api_keys")
