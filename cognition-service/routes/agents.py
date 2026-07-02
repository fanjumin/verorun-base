"""Agent routes — register, profile, reputation"""
from fastapi import APIRouter, HTTPException
from models.schemas import AgentCreate, AgentReputation
from db.connection import get_pool

router = APIRouter(prefix="/api/v1", tags=["agents"])


@router.post("/agents", status_code=201)
async def register_agent(a: AgentCreate):
    """Register a new agent in the cognition system."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO agents (agent_id, agent_name, owner_id, source_type)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (agent_id) DO UPDATE SET
                agent_name = EXCLUDED.agent_name
        """, a.agent_id, a.agent_name, a.owner_id, a.source_type)

        # Ensure reputation row exists
        await conn.execute("""
            INSERT INTO agent_reputation (agent_id, total_predictions)
            VALUES ($1, 0)
            ON CONFLICT (agent_id) DO NOTHING
        """, a.agent_id)

    return {"status": "ok", "agent_id": a.agent_id, "agent_name": a.agent_name}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent profile with reputation and recent predictions."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        agent = await conn.fetchrow(
            "SELECT * FROM agents WHERE agent_id = $1", agent_id
        )
        if not agent:
            raise HTTPException(404, f"Agent {agent_id} not found")

        rep = await conn.fetchrow(
            "SELECT * FROM agent_reputation WHERE agent_id = $1", agent_id
        )

        recent = await conn.fetch("""
            SELECT id, ticker, stance, confidence, timeframe, risk_level,
                   price_target, created_at, settlement_status
            FROM predictions
            WHERE agent_id = $1
            ORDER BY created_at DESC
            LIMIT 20
        """, agent_id)

    return {
        "agent_id": agent["agent_id"],
        "agent_name": agent["agent_name"],
        "owner_id": agent["owner_id"],
        "source_type": agent["source_type"],
        "created_at": agent["created_at"].isoformat() if agent["created_at"] else None,
        "reputation": {
            "total_predictions": rep["total_predictions"] if rep else 0,
            "accuracy_rate": round(float(rep["accuracy_rate"]) * 100, 1) if rep and rep["accuracy_rate"] else 0,
            "avg_confidence": round(float(rep["avg_confidence"]) * 100, 1) if rep and rep["avg_confidence"] else 0,
            "sharpe_like_score": round(float(rep["sharpe_like_score"]), 4) if rep else 0,
            "reputation_score": round(float(rep["reputation_score"]), 2) if rep else 0,
        } if rep else None,
        "recent_predictions": [
            {
                "id": r["id"],
                "ticker": r["ticker"],
                "stance": r["stance"],
                "confidence": r["confidence"],
                "timeframe": r["timeframe"],
                "risk_level": r["risk_level"],
                "price_target": float(r["price_target"]) if r["price_target"] else None,
                "created_at": r["created_at"].isoformat(),
                "settlement_status": r["settlement_status"],
            }
            for r in recent
        ],
    }
