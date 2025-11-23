from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.events import get_db
from app.db.models import APIKey, User, Workspace
from app.core.security import get_current_user
from pydantic import BaseModel
from datetime import datetime, timedelta
import secrets
import hashlib

router = APIRouter()

class APIKeyCreate(BaseModel):
    name: str
    days_valid: int = 30

class APIKeyResponse(BaseModel):
    id: int
    name: str
    key: str # Only shown once
    created_at: datetime
    expires_at: datetime

class APIKeyList(BaseModel):
    id: int
    name: str
    created_at: datetime
    expires_at: datetime
    is_active: bool

@router.post("/", response_model=APIKeyResponse)
async def create_api_key(
    key_in: APIKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get user's workspace to find tenant_id
    workspace_result = await db.execute(
        select(Workspace).filter(Workspace.owner_id == current_user.id)
    )
    workspace = workspace_result.scalars().first()
    
    if not workspace:
        raise HTTPException(status_code=404, detail="No workspace found for user")
    
    # Generate Key
    raw_key = "vk_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    expires_at = datetime.utcnow() + timedelta(days=key_in.days_valid)
    
    db_key = APIKey(
        key_hash=key_hash,
        name=key_in.name,
        owner_id=current_user.id,
        tenant_id=workspace.tenant_id,
        expires_at=expires_at
    )
    db.add(db_key)
    await db.commit()
    await db.refresh(db_key)
    
    return APIKeyResponse(
        id=db_key.id,
        name=db_key.name,
        key=raw_key,
        created_at=db_key.created_at,
        expires_at=db_key.expires_at
    )

@router.get("/", response_model=list[APIKeyList])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(APIKey).filter(APIKey.owner_id == current_user.id))
    keys = result.scalars().all()
    return keys

@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    key = await db.get(APIKey, key_id)
    if not key or key.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Key not found")
    
    await db.delete(key)
    await db.commit()
    return {"status": "revoked"}
