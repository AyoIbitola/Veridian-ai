from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.events import get_db
from app.db.models import Tenant, User
from app.core.security import get_current_user
from pydantic import BaseModel, HttpUrl, EmailStr
from typing import List, Optional

router = APIRouter()

class NotificationConfig(BaseModel):
    slack_webhook: Optional[str] = None
    email_recipients: List[EmailStr] = []

@router.get("/config", response_model=NotificationConfig)
async def get_notification_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get user's tenant (assuming 1:1 for now, or first workspace's tenant)
    # In a real app, we'd need to know which workspace context the user is in.
    # For simplicity, we'll fetch the tenant associated with the user's first workspace.
    if not current_user.workspaces:
        raise HTTPException(status_code=404, detail="No workspace found for user")
    
    tenant_id = current_user.workspaces[0].tenant_id
    
    result = await db.execute(select(Tenant).filter(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    config = tenant.notification_config or {}
    return NotificationConfig(
        slack_webhook=config.get("slack_webhook"),
        email_recipients=config.get("email_recipients", [])
    )

@router.post("/config", response_model=NotificationConfig)
async def update_notification_config(
    config: NotificationConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.workspaces:
        raise HTTPException(status_code=404, detail="No workspace found for user")
    
    tenant_id = current_user.workspaces[0].tenant_id
    
    result = await db.execute(select(Tenant).filter(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    tenant.notification_config = {
        "slack_webhook": config.slack_webhook,
        "email_recipients": config.email_recipients
    }
    
    await db.commit()
    await db.refresh(tenant)
    
    return config
