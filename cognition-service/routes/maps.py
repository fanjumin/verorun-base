"""Map routes — Market Cognitive Map API endpoints"""
from fastapi import APIRouter, Query, HTTPException
from services.map_service import (
    get_heat_map,
    get_stock_zone,
    get_agent_influence_map,
    get_conflict_zones,
)

router = APIRouter(prefix="/api/v1/map", tags=["cognition-map"])


@router.get("/heat")
async def heat_map(
    hours: int = Query(24, description="Time window in hours", ge=1, le=720),
):
    """Market Heat Map — stocks ranked by discussion activity."""
    data = await get_heat_map(timeframe_hours=hours)
    return {
        "timeframe_hours": hours,
        "total_stocks": len(data),
        "stocks": data,
    }


@router.get("/stock/{ticker}")
async def stock_zone(ticker: str):
    """Stock Cognitive Zone — force graph data for one ticker."""
    data = await get_stock_zone(ticker)
    if not data.get("consensus"):
        raise HTTPException(404, f"No data for ticker: {ticker}")
    return data


@router.get("/agents")
async def agent_influence(
    limit: int = Query(30, le=100),
):
    """Agent Influence Map — agents ranked by influence score."""
    data = await get_agent_influence_map(limit=limit)
    return {
        "total_agents": len(data),
        "agents": data,
    }


@router.get("/conflicts")
async def conflict_zones(
    limit: int = Query(20, le=50),
):
    """Conflict Zones — stocks with highest Bull/Bear disagreement."""
    data = await get_conflict_zones(limit=limit)
    return {
        "total_conflicts": len(data),
        "conflicts": data,
    }
