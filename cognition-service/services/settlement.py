"""Settlement engine — resolves predictions when their timeframe expires.

Settlement logic:
  1. Collect all 'pending' predictions past their due date
  2. Fetch closing price at resolution time
  3. Determine:
     - direction_correct:  did price move in the predicted direction?
     - target_hit:         did price reach the price_target?
     - pnl_percent:        simulated return
  4. Record in prediction_results
  5. Recalculate agent reputation
"""

import math
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict

from db.connection import get_pool
from services.price_fetcher import fetch_price, fetch_close_price
from services.reputation import recalc_agent_reputation

logger = logging.getLogger(__name__)

# How far back (in days) and forward to determine if a timeframe has expired
TIMEFRAME_MAP = {
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}

# Tolerance (%) for price_target hit
TARGET_HIT_TOLERANCE = 0.02  # 2%


# ── Public API ─────────────────────────────────────────────

async def settle_due_predictions(batch_size: int = 50) -> Dict:
    """Find and settle all pending predictions past their due date.

    Returns summary dict with counts.
    """
    pool = await get_pool()
    now = datetime.now(timezone.utc)

    due = await _find_due_predictions(pool, now, batch_size)
    settled = []
    errors = []

    for pred in due:
        try:
            result = await _settle_one(pred, now)
            settled.append(result)
        except Exception as e:
            errors.append({"prediction_id": pred["id"], "error": str(e)})
            logger.error(f"Settlement error for prediction {pred['id']}: {e}")

    return {
        "checked": len(due),
        "settled": len(settled),
        "errors": len(errors),
        "details": settled,
    }


async def settle_prediction(prediction_id: int) -> Dict:
    """Settle a single prediction by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM predictions WHERE id = $1 AND settlement_status = 'pending'",
            prediction_id,
        )
        if not row:
            return {"error": f"Prediction {prediction_id} not found or already settled"}

        pred = dict(row)
    now = datetime.now(timezone.utc)
    return await _settle_one(pred, now)


# ── Internal ────────────────────────────────────────────────

async def _find_due_predictions(pool, now: datetime, batch_size: int) -> List[Dict]:
    """Find predictions past their due timeframe."""
    async with pool.acquire() as conn:
        # Build condition: created_at + timeframe < now
        conditions = []
        for tf, delta in TIMEFRAME_MAP.items():
            cutoff = now - delta
            conditions.append(f"(timeframe = '{tf}' AND created_at <= '{cutoff.isoformat()}')")

        where = " OR ".join(conditions)
        rows = await conn.fetch(f"""
            SELECT * FROM predictions
            WHERE settlement_status = 'pending'
              AND ({where})
            ORDER BY created_at ASC
            LIMIT $1
        """, batch_size)
        return [dict(r) for r in rows]


async def _settle_one(pred: Dict, now: datetime) -> Dict:
    """Settle a single prediction.

    Steps:
      1. Fetch current price for the ticker
      2. Determine direction_correct
      3. Determine target_hit
      4. Calculate pnl_percent
      5. Record result
      6. Recalculate reputation
    """
    market = pred["market"]
    ticker = pred["ticker"]
    stance = pred["stance"]
    price_target = pred.get("price_target")

    # Fetch current price
    price_info = await fetch_price(market, ticker)
    if not price_info:
        raise ValueError(f"Cannot fetch price for {market}:{ticker}")

    current_price, change_pct = price_info

    # Determine direction correctness
    direction_correct = _check_direction(stance, change_pct)

    # Check price target hit
    target_hit = False
    if price_target and price_target > 0:
        target_hit = _check_target_hit(stance, current_price, float(price_target))

    # Estimate P&L (simple directional)
    pnl_percent = abs(change_pct) if direction_correct else -abs(change_pct)

    # Record result
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO prediction_results
                (prediction_id, resolved_price, target_hit, direction_correct, pnl_percent)
            VALUES ($1, $2, $3, $4, $5)
        """, pred["id"], current_price, target_hit, direction_correct, pnl_percent)

        await conn.execute("""
            UPDATE predictions SET settlement_status = 'resolved'
            WHERE id = $1
        """, pred["id"])

    # Recalculate agent reputation
    await recalc_agent_reputation(pred["agent_id"])

    return {
        "prediction_id": pred["id"],
        "agent_id": pred["agent_id"],
        "ticker": ticker,
        "stance": stance,
        "current_price": current_price,
        "direction_correct": direction_correct,
        "target_hit": target_hit,
        "pnl_percent": round(pnl_percent, 2),
    }


def _check_direction(stance: str, change_pct: float) -> bool:
    """Check if price moved in the predicted direction."""
    if stance == "bullish":
        return change_pct > 0
    elif stance == "bearish":
        return change_pct < 0
    else:  # neutral
        return abs(change_pct) < 1.0  # <1% movement = neutral correct


def _check_target_hit(stance: str, current_price: float, target_price: float) -> bool:
    """Check if current price hit the target (within tolerance)."""
    if stance == "bullish":
        return current_price >= target_price * (1 - TARGET_HIT_TOLERANCE)
    elif stance == "bearish":
        return current_price <= target_price * (1 + TARGET_HIT_TOLERANCE)
    return False
