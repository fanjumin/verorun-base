"""Settlement routes — resolve predictions and trigger batch settlement"""
from fastapi import APIRouter, HTTPException
from services.settlement import settle_due_predictions, settle_prediction
from services.reputation import recalc_all_reputations

router = APIRouter(prefix="/api/v1", tags=["settlement"])


@router.post("/settlement/run")
async def run_settlement(batch_size: int = 50):
    """Batch-settle all pending predictions past their due date."""
    result = await settle_due_predictions(batch_size)
    return result


@router.post("/settlement/resolve/{prediction_id}")
async def resolve_prediction(prediction_id: int):
    """Manually resolve a single pending prediction."""
    result = await settle_prediction(prediction_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.post("/settlement/recalc-reputations")
async def recalc_reputations():
    """Recalculate reputation scores for all agents."""
    await recalc_all_reputations()
    return {"status": "ok", "message": "All reputations recalculated"}
