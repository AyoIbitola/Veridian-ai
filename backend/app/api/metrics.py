from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime, timedelta
import random
from app.db.events import get_db
from app.db.models import Metrics
from app.api.models import MetricsResponse
from app.core.security import get_api_key

router = APIRouter()

@router.get("/", response_model=List[MetricsResponse])
async def get_metrics(
    tenant_id: int = None,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(get_api_key)
):
    query = select(Metrics)
    if tenant_id:
        query = query.filter(Metrics.tenant_id == tenant_id)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/autonomy-drift")
async def get_autonomy_drift(agentId: int, time_range: str = Query("24h", alias="range")):
    # Mock sparkline data
    timestamps = [(datetime.utcnow() - timedelta(hours=i)).isoformat() for i in range(10)]
    timestamps.reverse()
    
    return {
        "timestamps": timestamps,
        "drift_score": [random.uniform(0, 0.6) for _ in range(10)],
        "current_status": "rising",
        "confidence": 0.82
    }
