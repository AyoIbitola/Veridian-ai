from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.events import get_db
from app.db.models import APIKey, User
from app.core.security import get_api_key
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
    # In real app, get current user from auth token
    # For demo, we assume user_id=1 (created in auth.py)
    user_id: int = 1 
):
    # Generate Key
    raw_key = "vk_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    expires_at = datetime.utcnow() + timedelta(days=key_in.days_valid)
    
    db_key = APIKey(
        key_hash=key_hash,
        name=key_in.name,
        owner_id=user_id,
        tenant_id=1, # Default tenant
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
    user_id: int = 1
):
    result = await db.execute(select(APIKey).filter(APIKey.owner_id == user_id))
    keys = result.scalars().all()
    return keys

@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = 1
):
    key = await db.get(APIKey, key_id)
    if not key or key.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Key not found")
    
    await db.delete(key)
    await db.commit()
    return {"status": "revoked"}
