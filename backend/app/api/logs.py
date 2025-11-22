from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

@router.get("/")
async def get_logs(agentId: int, limit: int = 100):
    return [
        {"timestamp": "2025-11-20T10:00:00Z", "level": "INFO", "message": "Agent started"},
        {"timestamp": "2025-11-20T10:05:00Z", "level": "WARN", "message": "High latency detected"}
    ]

@router.get("/search")
async def search_logs(query: str):
    return [{"match": f"Found log for {query}"}]
