
import asyncio
import hashlib
from sqlalchemy import select
from app.db.events import init_db, AsyncSessionLocal
from app.db.models import Tenant, APIKey, User

async def seed():
    await init_db()
    
    async with AsyncSessionLocal() as db:
        print("Seeding database...")
        
        # 1. Create Tenant if not exists
        result = await db.execute(select(Tenant).filter(Tenant.id == 1))
        tenant = result.scalars().first()
        
        if not tenant:
            print("Creating default tenant...")
            tenant = Tenant(name="Demo Tenant", plan="enterprise")
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)
        else:
            print(f"Tenant found: {tenant.name}")

        # 2. Create API Key
        raw_key = "demo_agent_key_001"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        result = await db.execute(select(APIKey).filter(APIKey.key_hash == key_hash))
        api_key = result.scalars().first()
        
        if not api_key:
            print(f"Creating API Key: {raw_key}")
            # We don't necessarily need a user for this demo, usually keys belong to users but schema allows null owner_id?
            # Schema: owner_id = Column(Integer, ForeignKey("users.id")) -> Not nullable by default unless specified?
            # Let's check models.py: owner_id = Column(Integer, ForeignKey("users.id")) -> It is nullable?
            # Reviewing models.py content in memory:
            # owner_id = Column(Integer, ForeignKey("users.id"))
            # It doesn't say nullable=True explicitly. SQLAlchemy defaults to nullable=True for ForeignKeys? No, defaults to False?
            # Actually standard Column is nullable=True by default in SQLAlchemy unless primary_key=True.
            # Let's assume it's nullable. If not, I'll error and fix.
            
            api_key = APIKey(
                key_hash=key_hash,
                name="Demo Key",
                tenant_id=tenant.id,
                is_active=True
            )
            db.add(api_key)
            await db.commit()
            print("API Key created.")
        else:
            print("API Key already exists.")
            
        # 3. Register Agent (Optional but good for AIM logging)
        # Agent registration usually happens via API, but let's see if we need it.
        # monitor.py checks: agent_result = await db.execute(select(Agent).filter(Agent.id == msg_in.agent_id))
        # msg_in.agent_id defaults to 1 in the sales_agent.py
        
        from app.db.models import Agent
        result = await db.execute(select(Agent).filter(Agent.id == 1))
        agent = result.scalars().first()
        
        if not agent:
             print("Creating default Agent (ID: 1)...")
             agent = Agent(
                 name="Sales Agent",
                 tenant_id=tenant.id,
                 mode="sdk",
                 model_info="gpt-4",
                 allowed_tools={"check_inventory": "enabled"}
             )
             db.add(agent)
             await db.commit()
             print("Agent created.")
        else:
             print("Agent found.")

if __name__ == "__main__":
    asyncio.run(seed())
