from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.events import get_db
from app.db.models import Workspace, User, Tenant
from app.core.security import get_current_user
from pydantic import BaseModel
from typing import List

router = APIRouter()

class WorkspaceResponse(BaseModel):
    id: int
    name: str
    tenant_id: int

@router.get("/", response_model=List[WorkspaceResponse])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Workspace).filter(Workspace.owner_id == current_user.id))
    return result.scalars().all()

@router.post("/", response_model=WorkspaceResponse)
async def create_workspace(
    name: str, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Create a new tenant for this workspace (1:1 mapping for simplicity in this version)
    tenant = Tenant(name=f"{name} Org")
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    
    workspace = Workspace(name=name, owner_id=current_user.id, tenant_id=tenant.id)
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace
