from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.events import get_db
from app.db.models import Policy, APIKey
from app.api.models import PolicyUpload
from app.core.security import get_api_key

router = APIRouter()

@router.get("/{tenant_id}/policy")
async def get_policy(
    tenant_id: int,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """Get the active policy for a tenant"""
    if api_key.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")
    
    result = await db.execute(
        select(Policy).filter(
            Policy.tenant_id == tenant_id,
            Policy.is_active == True
        )
    )
    policy = result.scalars().first()
    
    if not policy:
        raise HTTPException(status_code=404, detail="No policy found for this tenant")
    
    return {
        "id": policy.id,
        "name": policy.name,
        "content": policy.content,
        "is_active": policy.is_active,
        "created_at": policy.created_at.isoformat()
    }

@router.post("/{tenant_id}/policy")
async def upload_policy(
    tenant_id: int,
    policy: PolicyUpload,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    if api_key.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized for this tenant")

    # Check if policy exists
    result = await db.execute(select(Policy).filter(Policy.tenant_id == tenant_id))
    existing_policy = result.scalars().first()
    
    if existing_policy:
        existing_policy.content = policy.content
        existing_policy.name = policy.name
    else:
        new_policy = Policy(tenant_id=tenant_id, name=policy.name, content=policy.content)
        db.add(new_policy)
        
    await db.commit()
    return {"status": "policy uploaded", "tenant_id": tenant_id}
