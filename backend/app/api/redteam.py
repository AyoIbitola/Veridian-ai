from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.events import get_db
from app.db.models import Campaign
from app.api.models import CampaignStart, CampaignResponse
from app.core.security import get_api_key
from app.services.redteam_runner import redteam_runner

router = APIRouter()

@router.post("/campaign", response_model=CampaignResponse)
async def start_campaign(
    campaign_in: CampaignStart,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    campaign = Campaign(
        tenant_id=campaign_in.tenant_id,
        name="Red Team Campaign", # Could be dynamic
        status="running",
        config=campaign_in.model_dump()
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    
    background_tasks.add_task(redteam_runner.run_campaign, campaign.id)
    
    return CampaignResponse(campaign_id=campaign.id, status="running")
