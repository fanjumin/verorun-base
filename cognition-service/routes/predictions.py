"""Prediction routes — submit, query, consensus"""
import json
from fastapi import APIRouter, HTTPException, Query
from db.connection import get_pool
from models.schemas import (
    PredictionSubmit, PredictionResponse,
    StockConsensus, LeaderboardEntry, SystemStats
)
from services.validator import validate_prediction
from services.embedding import store_embedding

router = APIRouter(prefix="/api/v1", tags=["predictions"])


@router.post("/predictions", response_model=PredictionResponse)
async def submit_prediction(p: PredictionSubmit):
    """Submit a standardized prediction from any Agent."""
    err = validate_prediction(p)
    if err:
        raise HTTPException(422, err)

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Upsert agent
        await conn.execute("""
            INSERT INTO agents (agent_id, agent_name, source_type)
            VALUES ($1, $2, $3)
            ON CONFLICT (agent_id) DO UPDATE SET agent_name=$2
        """, p.agent_id, p.agent_name, p.source_type)

        # Upsert skill if provided
        if p.skill_id:
            await conn.execute("""
                INSERT INTO skills (skill_id, skill_name)
                VALUES ($1, $2)
                ON CONFLICT (skill_id) DO NOTHING
            """, p.skill_id, p.skill_id)

        # Insert prediction
        row = await conn.fetchrow("""
            INSERT INTO predictions
                (agent_id, skill_id, market, ticker, stance, confidence,
                 timeframe, thesis_json, risk_level, price_target, source_type)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            RETURNING id, agent_id, ticker, stance, confidence, timeframe,
                      thesis_json, risk_level, price_target, created_at, settlement_status
        """,
            p.agent_id, p.skill_id or None, p.market, p.ticker, p.stance,
            p.confidence, p.timeframe, json.dumps(p.thesis),
            p.risk_level, p.price_target, p.source_type
        )

        # Build graph edges
        pred_id = row['id']
        edges = [
            ("prediction", str(pred_id), "agent", p.agent_id, "ANALYZES"),
            ("prediction", str(pred_id), "stock", p.ticker,
             "SUPPORTS" if p.stance == 'bullish' else "OPPOSES" if p.stance == 'bearish' else "ANALYZES"),
        ]
        for src_t, src_id, tgt_t, tgt_id, rel in edges:
            await conn.execute("""
                INSERT INTO graph_edges (source_type, source_id, target_type, target_id, relation)
                VALUES ($1,$2,$3,$4,$5)
            """, src_t, src_id, tgt_t, tgt_id, rel)

        # Init reputation if not exists
        await conn.execute("""
            INSERT INTO agent_reputation (agent_id, total_predictions)
            VALUES ($1, 1)
            ON CONFLICT (agent_id) DO UPDATE SET
                total_predictions = agent_reputation.total_predictions + 1,
                updated_at = NOW()
        """, p.agent_id)

        # Store thesis embeddings
        thesis_text = " ".join(p.thesis)
        await store_embedding(pred_id, thesis_text)

        return PredictionResponse(
            id=row['id'], agent_id=row['agent_id'], ticker=row['ticker'],
            stance=row['stance'], confidence=row['confidence'],
            timeframe=row['timeframe'], thesis=json.loads(row['thesis_json']),
            risk_level=row['risk_level'], price_target=row['price_target'],
            created_at=row['created_at'], settlement_status=row['settlement_status'],
        )


@router.get("/predictions")
async def list_predictions(
    ticker: str = Query(None),
    agent_id: str = Query(None),
    market: str = Query(None),
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    """Query predictions with filters."""
    pool = await get_pool()
    conditions = []
    params = []
    i = 1
    if ticker:
        conditions.append(f"ticker=${i}"); params.append(ticker.upper()); i += 1
    if agent_id:
        conditions.append(f"agent_id=${i}"); params.append(agent_id); i += 1
    if market:
        conditions.append(f"market=${i}"); params.append(market); i += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.extend([limit, offset])
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM predictions {where} ORDER BY created_at DESC LIMIT ${i} OFFSET ${i+1}",
            *params
        )
        return [
            {
                "id": r['id'], "agent_id": r['agent_id'],
                "ticker": r['ticker'], "stance": r['stance'],
                "confidence": r['confidence'], "timeframe": r['timeframe'],
                "thesis": json.loads(r['thesis_json']),
                "risk_level": r['risk_level'], "price_target": float(r['price_target']) if r['price_target'] else None,
                "created_at": r['created_at'].isoformat(),
                "settlement_status": r['settlement_status'],
            }
            for r in rows
        ]


@router.get("/consensus/{ticker}", response_model=StockConsensus)
async def stock_consensus(ticker: str):
    """Get consensus for a specific stock."""
    ticker = ticker.upper().strip()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COALESCE(SUM(CASE WHEN stance='bullish' THEN 1 END) * 100.0 / NULLIF(COUNT(*),0), 0) as bullish_pct,
                COALESCE(SUM(CASE WHEN stance='bearish' THEN 1 END) * 100.0 / NULLIF(COUNT(*),0), 0) as bearish_pct,
                COALESCE(SUM(CASE WHEN stance='neutral' THEN 1 END) * 100.0 / NULLIF(COUNT(*),0), 0) as neutral_pct,
                COALESCE(AVG(confidence), 0) as avg_confidence
            FROM predictions WHERE ticker=$1 AND settlement_status='pending'
        """, ticker)

        # Top thesis
        thesis_rows = await conn.fetch("""
            SELECT thesis_json FROM predictions
            WHERE ticker=$1 ORDER BY created_at DESC LIMIT 20
        """, ticker)
        all_thesis = []
        for tr in thesis_rows:
            all_thesis.extend(json.loads(tr['thesis_json']))

        return StockConsensus(
            ticker=ticker,
            total=row['total'] or 0,
            bullish_pct=round(row['bullish_pct'], 1),
            bearish_pct=round(row['bearish_pct'], 1),
            neutral_pct=round(row['neutral_pct'], 1),
            top_thesis=all_thesis[:10],
            avg_confidence=round(row['avg_confidence'], 1),
        )


@router.get("/leaderboard")
async def leaderboard(limit: int = 20):
    """Agent reputation leaderboard."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT a.agent_id, a.agent_name,
                   COALESCE(r.accuracy_rate, 0) as accuracy_rate,
                   COALESCE(r.total_predictions, 0) as total_predictions,
                   COALESCE(r.reputation_score, 0) as reputation_score
            FROM agents a
            LEFT JOIN agent_reputation r ON a.agent_id = r.agent_id
            ORDER BY reputation_score DESC, total_predictions DESC
            LIMIT $1
        """, limit)
        return [
            {"rank": i+1, "agent_id": r['agent_id'], "agent_name": r['agent_name'],
             "accuracy_rate": round(float(r['accuracy_rate']), 3),
             "total_predictions": r['total_predictions'],
             "reputation_score": round(float(r['reputation_score']), 2)}
            for i, r in enumerate(rows)
        ]


@router.get("/stats")
async def stats():
    """System-wide statistics."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        total_p = await conn.fetchval("SELECT COUNT(*) FROM predictions")
        total_a = await conn.fetchval("SELECT COUNT(*) FROM agents")
        resolved = await conn.fetchval("SELECT COUNT(*) FROM predictions WHERE settlement_status='resolved'")
        accuracy = await conn.fetchval("""
            SELECT COALESCE(
                SUM(CASE WHEN direction_correct THEN 1 END) * 100.0 / NULLIF(COUNT(*),0), 0
            ) FROM prediction_results
        """)
        return {
            "total_predictions": total_p,
            "total_agents": total_a,
            "resolved_count": resolved,
            "overall_accuracy": round(float(accuracy or 0), 1),
        }


@router.get("/graph")
async def graph_data(limit: int = 200):
    """Get cognition graph data for visualization."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        edges = await conn.fetch(
            "SELECT * FROM graph_edges ORDER BY created_at DESC LIMIT $1", limit
        )
        nodes_set = {}
        result_edges = []
        for e in edges:
            sid = f"{e['source_type']}:{e['source_id']}"
            tid = f"{e['target_type']}:{e['target_id']}"
            nodes_set[sid] = {"id": sid, "type": e['source_type'], "label": e['source_id']}
            nodes_set[tid] = {"id": tid, "type": e['target_type'], "label": e['target_id']}
            result_edges.append({
                "source": sid, "target": tid,
                "relation": e['relation'], "weight": float(e['weight']),
            })

        # Enrich agent nodes with names
        agent_ids = [v['label'] for v in nodes_set.values() if v['type'] == 'agent']
        if agent_ids:
            agent_rows = await conn.fetch(
                "SELECT agent_id, agent_name FROM agents WHERE agent_id = ANY($1)",
                agent_ids
            )
            name_map = {a['agent_id']: a['agent_name'] for a in agent_rows}
            for v in nodes_set.values():
                if v['type'] == 'agent' and v['label'] in name_map:
                    v['label'] = name_map[v['label']]

        return {
            "nodes": list(nodes_set.values()),
            "edges": result_edges,
        }
