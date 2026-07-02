"""Reputation scoring engine for Agent cognition system.

Scoring components:
  - accuracy_rate:  directional correctness rate
  - sharpe_like:     risk-adjusted confidence efficiency
  - activity_bonus:  logarithmic reward for volume
  - recency_factor:  decay weight over time (newer predictions weighted higher)
"""

import math
from typing import Optional
from db.connection import get_pool


# ── Configuration ──────────────────────────────────────────

# Weights for composite reputation score
W_ACCURACY = 0.50
W_SHARPE = 0.25
W_ACTIVITY = 0.15
W_RECENCY = 0.10

# Decay half-life in days (newer predictions matter more)
RECENCY_HALF_LIFE_DAYS = 30


# ── Core functions ─────────────────────────────────────────

async def recalc_all_reputations():
    """Recompute reputation for every agent that has resolved predictions."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Collect all agents with resolved results
        rows = await conn.fetch("""
            SELECT DISTINCT p.agent_id
            FROM predictions p
            JOIN prediction_results pr ON p.id = pr.prediction_id
        """)
        for row in rows:
            await recalc_agent_reputation(row["agent_id"])


async def recalc_agent_reputation(agent_id: str):
    """Calculate and update reputation for a single agent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # ── 1. Accuracy rate ─────────────────────────────
        result = await conn.fetchrow("""
            SELECT
                COUNT(*)::int                                           AS total_resolved,
                COALESCE(SUM(CASE WHEN pr.direction_correct THEN 1 END), 0)::int AS correct,
                COALESCE(SUM(CASE WHEN pr.direction_correct THEN 1 END) * 100.0
                    / NULLIF(COUNT(*), 0), 0)                          AS accuracy_rate,
                COALESCE(AVG(p.confidence), 0)                         AS avg_confidence
            FROM predictions p
            JOIN prediction_results pr ON p.id = pr.prediction_id
            WHERE p.agent_id = $1
        """, agent_id)

        total_resolved = result["total_resolved"] or 0
        correct = result["correct"] or 0
        accuracy_rate = float(result["accuracy_rate"] or 0)
        avg_confidence = float(result["avg_confidence"] or 0)

        # ── 2. Sharpe-like score ─────────────────────────
        sharpe_like = await _calc_sharpe_like(conn, agent_id)

        # ── 3. Activity bonus ────────────────────────────
        # Also count pending predictions for total activity
        total_preds = await conn.fetchval(
            "SELECT COUNT(*)::int FROM predictions WHERE agent_id = $1",
            agent_id,
        ) or 0
        activity_bonus = math.log2(total_preds + 1) / 20.0  # ~0-0.5 range

        # ── 4. Recency score ─────────────────────────────
        recency = await _calc_recency(conn, agent_id)

        # ── 5. Composite ─────────────────────────────────
        reputation_score = (
            W_ACCURACY * (accuracy_rate / 100.0) +
            W_SHARPE * max(0, min(1, sharpe_like / 30.0)) +
            W_ACTIVITY * activity_bonus +
            W_RECENCY * recency
        ) * 100  # Scale to 0-100

        # ── Upsert ───────────────────────────────────────
        await conn.execute("""
            INSERT INTO agent_reputation
                (agent_id, total_predictions, accuracy_rate,
                 avg_confidence, sharpe_like_score, reputation_score,
                 updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (agent_id) DO UPDATE SET
                total_predictions = EXCLUDED.total_predictions,
                accuracy_rate    = EXCLUDED.accuracy_rate,
                avg_confidence   = EXCLUDED.avg_confidence,
                sharpe_like_score = EXCLUDED.sharpe_like_score,
                reputation_score = EXCLUDED.reputation_score,
                updated_at       = NOW()
        """,
            agent_id,
            total_preds,
            round(accuracy_rate / 100.0, 4),
            round(avg_confidence / 100.0, 4),
            round(sharpe_like, 4),
            round(reputation_score, 4),
        )

        return {
            "agent_id": agent_id,
            "total_preds": total_preds,
            "total_resolved": total_resolved,
            "correct": correct,
            "accuracy_rate": round(accuracy_rate, 1),
            "avg_confidence": round(avg_confidence, 1),
            "sharpe_like": round(sharpe_like, 4),
            "activity_bonus": round(activity_bonus, 4),
            "recency": round(recency, 4),
            "reputation_score": round(reputation_score, 2),
        }


# ── Internal helpers ────────────────────────────────────────

async def _calc_sharpe_like(conn, agent_id: str) -> float:
    """Sharpe-like score: reward high confidence when right, penalize when wrong.

    Formula:
      mean_correct_confidence - mean_incorrect_confidence
      ────────────────────────────────────────────────────
            std_of_all_confidence_values

    Returns 0 if insufficient data (<2 resolved predictions).
    """
    rows = await conn.fetch("""
        SELECT p.confidence, pr.direction_correct
        FROM predictions p
        JOIN prediction_results pr ON p.id = pr.prediction_id
        WHERE p.agent_id = $1
    """, agent_id)

    if len(rows) < 2:
        return 0.0

    correct_confs = []
    incorrect_confs = []
    all_confs = []

    for r in rows:
        conf = r["confidence"]
        all_confs.append(conf)
        if r["direction_correct"]:
            correct_confs.append(conf)
        else:
            incorrect_confs.append(conf)

    mean_correct = sum(correct_confs) / len(correct_confs) if correct_confs else 50
    mean_incorrect = sum(incorrect_confs) / len(incorrect_confs) if incorrect_confs else 50

    # Population std
    n = len(all_confs)
    mean_all = sum(all_confs) / n
    variance = sum((c - mean_all) ** 2 for c in all_confs) / n
    std = math.sqrt(variance) if variance > 0 else 1

    return (mean_correct - mean_incorrect) / std


async def _calc_recency(conn, agent_id: str) -> float:
    """Recency score — higher if the agent has recent activity.

    Uses exponential decay: weight = 2^(-days_since / half_life)
    Normalised to 0-1 by taking the average of all prediction weights.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    rows = await conn.fetch("""
        SELECT created_at FROM predictions
        WHERE agent_id = $1
        ORDER BY created_at DESC
    """, agent_id)

    if not rows:
        return 0.0

    total_weight = 0.0
    for r in rows:
        delta_days = (now - r["created_at"]).total_seconds() / 86400.0
        weight = 2 ** (-delta_days / RECENCY_HALF_LIFE_DAYS)
        total_weight += weight

    return total_weight / len(rows)
