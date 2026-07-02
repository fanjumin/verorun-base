"""Map service — aggregation queries for Market Cognitive Map.

Provides data for:
  - Market Heat Map (hot stocks by discussion volume)
  - Stock Cognitive Zone (force graph for one ticker)
  - Agent Influence Map (influence ranking)
  - Conflict Zone (stocks with highest disagreement)
"""

import math
import json
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta
from db.connection import get_pool
from config import SIMILARITY_THRESHOLD


# ── Page 1: Market Heat Map ────────────────────────────────

async def get_heat_map(timeframe_hours: int = 24) -> List[Dict]:
    """Get market heat map data — stocks ranked by discussion activity.

    Returns list of stocks with:
      ticker, market, prediction_count, bullish_pct, bearish_pct,
      neutral_pct, avg_confidence, heat_score, sector
    """
    pool = await get_pool()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=timeframe_hours)

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                p.ticker,
                p.market,
                COUNT(*)::int                                   AS prediction_count,
                COUNT(DISTINCT p.agent_id)::int                 AS agent_count,
                COALESCE(
                    SUM(CASE WHEN p.stance='bullish' THEN 1 END) * 100.0
                    / NULLIF(COUNT(*), 0), 0
                )                                               AS bullish_pct,
                COALESCE(
                    SUM(CASE WHEN p.stance='bearish' THEN 1 END) * 100.0
                    / NULLIF(COUNT(*), 0), 0
                )                                               AS bearish_pct,
                COALESCE(AVG(p.confidence), 0)                  AS avg_confidence,
                MAX(p.created_at)                               AS last_active
            FROM predictions p
            WHERE p.created_at >= $1
            GROUP BY p.ticker, p.market
            ORDER BY prediction_count DESC
            LIMIT 50
        """, cutoff)

        result = []
        for r in rows:
            total = r["prediction_count"]
            bullish = float(r["bullish_pct"])
            bearish = float(r["bearish_pct"])
            # Heat score: volume-weighted disagreement + activity
            disagreement = 1 - abs(bullish - bearish) / 100.0
            avg_conf = float(r["avg_confidence"])
            heat_score = round(
                math.log2(total + 1) * 10 +
                disagreement * 5 +
                (avg_conf / 20.0),
                2
            )
            result.append({
                "ticker": r["ticker"],
                "market": r["market"],
                "prediction_count": total,
                "agent_count": r["agent_count"],
                "bullish_pct": round(bullish, 1),
                "bearish_pct": round(bearish, 1),
                "neutral_pct": round(100 - bullish - bearish, 1),
                "avg_confidence": round(avg_conf, 1),
                "heat_score": heat_score,
                "last_active": r["last_active"].isoformat() if r["last_active"] else None,
            })
        return result


# ── Page 2: Stock Cognitive Zone ──────────────────────────

async def get_stock_zone(ticker: str) -> Dict:
    """Get cognitive map for a single stock — agents, stances, thesis clusters.

    Returns force-graph-ready data:
      { ticker, consensus, agents[], thesis_clusters[], graph }
    """
    ticker = ticker.upper().strip()
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Consensus
        consensus = await conn.fetchrow("""
            SELECT
                COUNT(*)::int AS total,
                COALESCE(SUM(CASE WHEN stance='bullish' THEN 1 END) * 100.0
                    / NULLIF(COUNT(*),0), 0) AS bullish_pct,
                COALESCE(SUM(CASE WHEN stance='bearish' THEN 1 END) * 100.0
                    / NULLIF(COUNT(*),0), 0) AS bearish_pct,
                COALESCE(AVG(confidence), 0) AS avg_confidence
            FROM predictions WHERE ticker = $1
        """, ticker)

        if not consensus or not consensus["total"]:
            return {"ticker": ticker, "total_predictions": 0, "consensus": None}

        total = consensus["total"]
        bullish_pct = float(consensus["bullish_pct"])
        bearish_pct = float(consensus["bearish_pct"])
        neutral_pct = 100 - bullish_pct - bearish_pct

        # Agents involved
        agents = await conn.fetch("""
            SELECT agent_id, agent_name, stance, confidence, timeframe, reputation_score
            FROM (
                SELECT DISTINCT ON (p.agent_id)
                    p.agent_id, a.agent_name,
                    p.stance, p.confidence, p.timeframe,
                    COALESCE(r.reputation_score, 0) AS reputation_score,
                    p.created_at
                FROM predictions p
                LEFT JOIN agents a ON p.agent_id = a.agent_id
                LEFT JOIN agent_reputation r ON p.agent_id = r.agent_id
                WHERE p.ticker = $1
                ORDER BY p.agent_id, p.created_at DESC
            ) sub
            ORDER BY created_at DESC
        """, ticker)

        # Thesis clustering (using embeddings)
        thesis_clusters = []
        embed_rows = await conn.fetch("""
            SELECT te.thesis_text, p.stance, p.agent_id, p.confidence
            FROM thesis_embeddings te
            JOIN predictions p ON te.prediction_id = p.id
            WHERE p.ticker = $1
            ORDER BY p.created_at DESC
            LIMIT 30
        """, ticker)

        # Build force graph
        graph_nodes = {}
        graph_edges = []

        # Center node: the stock
        stock_id = f"stock:{ticker}"
        graph_nodes[stock_id] = {"id": stock_id, "type": "stock", "label": ticker, "size": 30}

        for a in agents:
            aid = f"agent:{a['agent_id']}"
            rep = float(a["reputation_score"]) if a["reputation_score"] else 0
            node_size = max(10, min(40, 10 + rep / 5))
            graph_nodes[aid] = {
                "id": aid, "type": "agent",
                "label": a["agent_name"] or a["agent_id"],
                "size": node_size,
                "stance": a["stance"],
                "confidence": a["confidence"],
                "reputation": round(rep, 2),
            }
            graph_edges.append({
                "source": aid, "target": stock_id,
                "relation": a["stance"].upper(),
                "weight": a["confidence"] / 100.0,
            })

        for te in embed_rows:
            tid = f"thesis:{hash(te['thesis_text']) % 100000}"
            if tid not in graph_nodes:
                graph_nodes[tid] = {
                    "id": tid, "type": "thesis",
                    "label": te["thesis_text"][:40],
                    "size": 8,
                }
            agent_key = f"agent:{te['agent_id']}"
            if agent_key in graph_nodes:
                graph_edges.append({
                    "source": agent_key, "target": tid,
                    "relation": "THESIS",
                    "weight": te["confidence"] / 100.0,
                })

        # Conflict score for this stock
        conflict_score = _calc_conflict_score(total, bullish_pct, bearish_pct, agents)

        return {
            "ticker": ticker,
            "total_predictions": total,
            "consensus": {
                "bullish_pct": round(bullish_pct, 1),
                "bearish_pct": round(bearish_pct, 1),
                "neutral_pct": round(neutral_pct, 1),
                "avg_confidence": round(float(consensus["avg_confidence"]), 1),
            },
            "agents": [
                {
                    "agent_id": a["agent_id"],
                    "agent_name": a["agent_name"] or a["agent_id"],
                    "stance": a["stance"],
                    "confidence": a["confidence"],
                    "timeframe": a["timeframe"],
                    "reputation_score": round(float(a["reputation_score"]), 2),
                }
                for a in agents
            ],
            "thesis_clusters": [
                {"text": t["thesis_text"][:100], "stance": t["stance"],
                 "agent_id": t["agent_id"], "confidence": t["confidence"]}
                for t in embed_rows
            ],
            "conflict_score": round(conflict_score, 4),
            "graph": {
                "nodes": list(graph_nodes.values()),
                "edges": graph_edges,
            },
        }


# ── Page 3: Agent Influence Map ────────────────────────────

async def get_agent_influence_map(limit: int = 30) -> List[Dict]:
    """Get agents ranked by influence score.

    Influence = Accuracy^2 × Reputation × log(Activity + 1) × CitationFactor
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                a.agent_id,
                a.agent_name,
                COALESCE(r.total_predictions, 0)::int      AS total_predictions,
                COALESCE(r.accuracy_rate, 0)               AS accuracy_rate,
                COALESCE(r.reputation_score, 0)            AS reputation_score,
                COALESCE(r.sharpe_like_score, 0)           AS sharpe_score,
                COALESCE(r.avg_confidence, 0)              AS avg_confidence
            FROM agents a
            LEFT JOIN agent_reputation r ON a.agent_id = r.agent_id
            ORDER BY r.reputation_score DESC NULLS LAST
            LIMIT $1
        """, limit)

        result = []
        for r in rows:
            accuracy = float(r["accuracy_rate"])
            reputation = float(r["reputation_score"])
            activity = r["total_predictions"]

            # Citation count: how many other predictions reference this agent's tickers
            # (simplified: agent's prediction count as proxy)
            citation_count = await conn.fetchval("""
                SELECT COUNT(*)::int FROM predictions
                WHERE agent_id = $1
            """, r["agent_id"]) or 1

            # Influence Score
            influence = _calc_influence_score(accuracy, reputation, activity, citation_count)

            result.append({
                "agent_id": r["agent_id"],
                "agent_name": r["agent_name"] or r["agent_id"],
                "total_predictions": activity,
                "accuracy_rate": round(accuracy, 4),
                "reputation_score": round(reputation, 2),
                "sharpe_score": round(float(r["sharpe_score"]), 4),
                "avg_confidence": round(float(r["avg_confidence"]) * 100, 1),
                "citation_count": citation_count,
                "influence_score": round(influence, 4),
                "node_size": max(10, min(50, 10 + influence * 10)),
            })

        return sorted(result, key=lambda x: x["influence_score"], reverse=True)


# ── Page 4: Conflict Zones ─────────────────────────────────

async def get_conflict_zones(limit: int = 20) -> List[Dict]:
    """Find stocks with highest conflict (disagreement).

    Conflict Score = disagreement_intensity × volume × reputation_weight
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                p.ticker,
                p.market,
                COUNT(*)::int                                   AS prediction_count,
                COUNT(DISTINCT p.agent_id)::int                 AS agent_count,
                COALESCE(
                    SUM(CASE WHEN p.stance='bullish' THEN 1 END) * 100.0
                    / NULLIF(COUNT(*),0), 0
                )                                               AS bullish_pct,
                COALESCE(
                    SUM(CASE WHEN p.stance='bearish' THEN 1 END) * 100.0
                    / NULLIF(COUNT(*),0), 0
                )                                               AS bearish_pct,
                COALESCE(AVG(p.confidence), 0)                  AS avg_confidence
            FROM predictions p
            WHERE p.created_at >= NOW() - INTERVAL '30 days'
            GROUP BY p.ticker, p.market
            HAVING COUNT(*) >= 3
            ORDER BY COUNT(*) DESC
            LIMIT $1
        """, limit)

        result = []
        for r in rows:
            total = r["prediction_count"]
            bullish = float(r["bullish_pct"])
            bearish = float(r["bearish_pct"])

            # Disagreement intensity: 0 (all agree) to 1 (50/50 split)
            disagreement = 1 - abs(bullish - bearish) / 100.0

            # Volume factor: log-scaled
            volume = math.log2(total + 1) / 5.0

            # High-reputation disagreement bonus
            high_rep_disagreement = await _high_rep_disagreement(conn, r["ticker"])

            conflict = disagreement * volume * (1 + high_rep_disagreement)

            result.append({
                "ticker": r["ticker"],
                "market": r["market"],
                "bullish_pct": round(bullish, 1),
                "bearish_pct": round(bearish, 1),
                "neutral_pct": round(100 - bullish - bearish, 1),
                "prediction_count": total,
                "agent_count": r["agent_count"],
                "avg_confidence": round(float(r["avg_confidence"]), 1),
                "disagreement_intensity": round(disagreement, 4),
                "conflict_score": round(conflict, 4),
            })

        return sorted(result, key=lambda x: x["conflict_score"], reverse=True)


# ── Algorithm helpers ───────────────────────────────────────

def _calc_influence_score(
    accuracy: float, reputation: float,
    activity: int, citations: int
) -> float:
    """Influence = Accuracy^2 × Reputation × log(Activity) × CitationFactor"""
    acc_factor = accuracy ** 2  # Accuracy squared (0-1)
    rep_factor = reputation / 100.0 if reputation > 1 else reputation  # Normalize
    act_factor = math.log2(activity + 1) / 10.0  # Log scale
    cit_factor = math.log2(citations + 1) / 10.0  # Log scale

    return acc_factor * rep_factor * act_factor * cit_factor * 100


def _calc_conflict_score(
    total: int, bullish_pct: float, bearish_pct: float,
    agents: List
) -> float:
    """Conflict = disagreement_intensity × volume × high_rep_factor"""
    if total < 2:
        return 0.0
    disagreement = 1 - abs(bullish_pct - bearish_pct) / 100.0
    volume = math.log2(total + 1)
    # Check if high-reputation agents are on opposing sides
    high_rep = [a for a in agents if float(a.get("reputation_score", 0) or 0) > 10]
    high_rep_factor = 1.0
    if len(high_rep) >= 2:
        stances = set(a["stance"] for a in high_rep)
        if "bullish" in stances and "bearish" in stances:
            high_rep_factor = 1.5
    return disagreement * volume * high_rep_factor


async def _high_rep_disagreement(conn, ticker: str) -> float:
    """Check if high-reputation agents disagree on this ticker."""
    rows = await conn.fetch("""
        SELECT p.stance, r.reputation_score
        FROM predictions p
        JOIN agent_reputation r ON p.agent_id = r.agent_id
        WHERE p.ticker = $1 AND r.reputation_score > 10
        ORDER BY r.reputation_score DESC
        LIMIT 10
    """, ticker)

    if len(rows) < 2:
        return 0.0

    stances = set(r["stance"] for r in rows)
    if "bullish" in stances and "bearish" in stances:
        return 0.5
    return 0.0
