from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.events import get_db
from app.db.models import User, Workspace, Tenant
from app.core import security
from app.core.config import settings
from pydantic import BaseModel
from datetime import timedelta
import httpx

router = APIRouter()

class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str
    organization_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str = None
    provider: str

@router.post("/register", response_model=Token)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(select(User).filter(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create User
    hashed_password = security.get_password_hash(user_in.password)
    user = User(
        email=user_in.email, 
        password_hash=hashed_password, 
        full_name=user_in.full_name,
        provider="local"
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Create Tenant with provided Organization Name
    tenant = Tenant(name=user_in.organization_name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    
    workspace = Workspace(name="Default Workspace", owner_id=user.id, tenant_id=tenant.id)
    db.add(workspace)
    await db.commit()
    
    access_token = security.create_access_token(subject=user.email)
    return {"access_token": access_token, "token_type": "bearer"}

from fastapi.security import OAuth2PasswordRequestForm

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # OAuth2PasswordRequestForm uses 'username', so we treat it as email
    result = await db.execute(select(User).filter(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    access_token = security.create_access_token(subject=user.email)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(security.get_current_user)): 
    return {
        "id": current_user.id, 
        "email": current_user.email, 
        "full_name": current_user.full_name,
        "provider": current_user.provider
    }

# GitHub OAuth
@router.get("/github/login")
async def github_login():
    return {"url": f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}"}

@router.get("/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code
            }
        )
        response.raise_for_status()
        data = response.json()
        access_token = data.get("access_token")
        
        # Get User Info
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = user_resp.json()
        email = user_data.get("email")
        name = user_data.get("name") or email.split("@")[0]
        
        # Find or Create User
        result = await db.execute(select(User).filter(User.email == email))
        user = result.scalars().first()
        
        if not user:
            user = User(email=email, full_name=name, password_hash="", provider="github")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # Create Default Tenant
            tenant = Tenant(name=f"{name}'s Org")
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
            
            workspace = Workspace(name="Default Workspace", owner_id=user.id, tenant_id=tenant.id)
            db.add(workspace)
            await db.commit()
            
        jwt_token = security.create_access_token(subject=user.email)
        return {"access_token": jwt_token, "token_type": "bearer"}

# Google OAuth
@router.get("/google/login")
async def google_login():
    return {"url": f"https://accounts.google.com/o/oauth2/v2/auth?client_id={settings.GOOGLE_CLIENT_ID}&response_type=code&scope=openid%20email%20profile&redirect_uri=http://localhost:8000/auth/google/callback"}

@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "http://localhost:8000/auth/google/callback"
            }
        )
        data = response.json()
        access_token = data.get("access_token")
        
        user_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = user_resp.json()
        email = user_data.get("email")
        name = user_data.get("name") or email.split("@")[0]
        
        result = await db.execute(select(User).filter(User.email == email))
        user = result.scalars().first()
        
        if not user:
            user = User(email=email, full_name=name, password_hash="", provider="google")
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            tenant = Tenant(name=f"{name}'s Org")
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
            
            workspace = Workspace(name="Default Workspace", owner_id=user.id, tenant_id=tenant.id)
            db.add(workspace)
            await db.commit()
            
        jwt_token = security.create_access_token(subject=user.email)
        return {"access_token": jwt_token, "token_type": "bearer"}
