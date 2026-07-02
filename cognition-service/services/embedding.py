"""Embedding service — generate and search thesis embeddings via pgvector.

Embedding strategy (ranked by availability):
  1. sentence-transformers (all-MiniLM-L6-v2) — best quality, 384-dim
  2. TF-IDF with max_features=384 — deterministic fallback
  3. Character-n-gram hash embedding — last resort

Generates 384-dim vectors configurable via EMBED_DIM in config.py.
"""

import math
import hashlib
import json
import numpy as np
from typing import List, Optional, Tuple
from db.connection import get_pool
from config import EMBED_DIM, SIMILARITY_THRESHOLD

# ── Which embedding backend to use? ────────────────────────

_USE_SBERT = False
_USE_SKLEARN = False
_embedder = None  # lazy init


async def _init_embedder():
    """Try to import the best available embedding backend."""
    global _USE_SBERT, _USE_SKLEARN, _embedder

    if _embedder is not None:
        return

    # Try sentence-transformers first
    try:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
        _USE_SBERT = True
        return
    except ImportError:
        pass

    # Try sklearn TF-IDF
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        # We'll init lazy with a fitting corpus
        _USE_SKLEARN = True
        return
    except ImportError:
        pass

    # No external libs — use hash embedding
    _embedder = "hash"


# ── Public API ─────────────────────────────────────────────

async def embed_text(text: str) -> List[float]:
    """Generate 384-dim embedding vector for a piece of text."""
    await _init_embedder()

    if _USE_SBERT:
        vec = _embedder.encode(text, normalize_embeddings=True)
        return vec.tolist()
    elif _USE_SKLEARN:
        return _tfidf_embed(text)
    else:
        return _hash_embed(text)


async def embed_thesis(thesis_list: List[str]) -> List[float]:
    """Embed a list of thesis strings into a single averaged vector."""
    combined = " ".join(thesis_list)
    return await embed_text(combined)


async def store_embedding(prediction_id: int, thesis_text: str):
    """Generate and store embedding for a prediction's thesis."""
    embedding = await embed_text(thesis_text)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO thesis_embeddings (prediction_id, thesis_text, embedding)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
        """, prediction_id, thesis_text, embedding)


async def search_similar_theses(
    query: str,
    limit: int = 20,
    threshold: float = None,
) -> List[dict]:
    """Find predictions with similar thesis content via vector similarity.

    Uses pgvector cosine similarity (<=> operator).
    Returns list of {prediction_id, thesis_text, similarity, prediction_details}.
    """
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD

    query_vec = await embed_text(query)
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Check if any embeddings exist
        count = await conn.fetchval("SELECT COUNT(*) FROM thesis_embeddings")
        if not count:
            return []

        rows = await conn.fetch("""
            SELECT
                te.prediction_id,
                te.thesis_text,
                1 - (te.embedding <=> $1) AS similarity,
                p.ticker, p.stance, p.confidence, p.timeframe,
                p.agent_id, p.created_at
            FROM thesis_embeddings te
            JOIN predictions p ON te.prediction_id = p.id
            WHERE (te.embedding <=> $1) <= $2
            ORDER BY similarity DESC
            LIMIT $3
        """, query_vec, 1 - threshold, limit)

        return [
            {
                "prediction_id": r["prediction_id"],
                "thesis_text": r["thesis_text"],
                "similarity": round(float(r["similarity"]), 4),
                "ticker": r["ticker"],
                "stance": r["stance"],
                "confidence": r["confidence"],
                "timeframe": r["timeframe"],
                "agent_id": r["agent_id"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]


async def get_clusters(
    min_cluster_size: int = 3,
    limit: int = 200,
) -> List[dict]:
    """Simple topic clustering: group similar theses by cosine similarity.

    Uses a greedy single-linkage approach on recent thesis embeddings.
    Returns list of clusters with centroid thesis and member predictions.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                te.id, te.prediction_id, te.thesis_text, te.embedding,
                p.ticker, p.stance, p.confidence, p.agent_id, p.created_at
            FROM thesis_embeddings te
            JOIN predictions p ON te.prediction_id = p.id
            ORDER BY p.created_at DESC
            LIMIT $1
        """, limit)

    if not rows:
        return []

    # Extract vectors and metadata
    vectors = np.array([r["embedding"] for r in rows])
    metas = [dict(r) for r in rows]

    # Greedy clustering by cosine similarity
    n = len(vectors)
    assigned = [False] * n
    clusters = []

    for i in range(n):
        if assigned[i]:
            continue

        cluster_indices = [i]
        assigned[i] = True

        for j in range(i + 1, n):
            if assigned[j]:
                continue
            cos_sim = np.dot(vectors[i], vectors[j]) / (
                np.linalg.norm(vectors[i]) * np.linalg.norm(vectors[j]) + 1e-8
            )
            if cos_sim >= SIMILARITY_THRESHOLD:
                cluster_indices.append(j)
                assigned[j] = True

        if len(cluster_indices) >= min_cluster_size:
            members = [metas[idx] for idx in cluster_indices]
            # Most common ticker as cluster label
            tickers = [m["ticker"] for m in members]
            top_ticker = max(set(tickers), key=tickers.count)

            # Aggregate stances
            stances = [m["stance"] for m in members]
            bullish = sum(1 for s in stances if s == "bullish")
            bearish = sum(1 for s in stances if s == "bearish")

            clusters.append({
                "size": len(members),
                "ticker": top_ticker,
                "bullish_count": bullish,
                "bearish_count": bearish,
                "thesis_sample": metas[cluster_indices[0]]["thesis_text"][:100],
                "members": [
                    {
                        "prediction_id": m["prediction_id"],
                        "ticker": m["ticker"],
                        "stance": m["stance"],
                        "confidence": m["confidence"],
                        "agent_id": m["agent_id"],
                    }
                    for m in members[:10]  # limit output
                ],
            })

    return sorted(clusters, key=lambda c: c["size"], reverse=True)


# ── Embedding backends ─────────────────────────────────────

def _hash_embed(text: str) -> List[float]:
    """Deterministic hash-based embedding — no ML deps needed.

    Uses character n-gram hashing into a fixed-dim vector.
    """
    vec = np.zeros(EMBED_DIM, dtype=np.float32)
    text = text.lower().strip()

    if not text:
        return vec.tolist()

    # Character bigrams and trigrams
    ngroups = []
    for n in [2, 3, 4]:
        for i in range(len(text) - n + 1):
            ngroups.append(text[i:i + n])

    for ng in ngroups:
        h = int(hashlib.md5(ng.encode()).hexdigest(), 16)
        idx = h % EMBED_DIM
        vec[idx] += 1.0

    # Normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm

    return vec.tolist()


# ── TF-IDF backend (requires sklearn, lazy init) ──────────

_tfidf_vectorizer = None
_tfidf_fitted = False


def _tfidf_embed(text: str) -> List[float]:
    """TF-IDF embedding with max_features=EMBED_DIM."""
    global _tfidf_vectorizer, _tfidf_fitted

    if _tfidf_vectorizer is None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        _tfidf_vectorizer = TfidfVectorizer(
            max_features=EMBED_DIM,
            analyzer="char_wb",
            ngram_range=(2, 4),
        )
        # Fit on initial text
        _tfidf_vectorizer.fit([text])
        _tfidf_fitted = True
        vec = _tfidf_vectorizer.transform([text]).toarray()[0]
    else:
        # Just transform
        try:
            vec = _tfidf_vectorizer.transform([text]).toarray()[0]
        except Exception:
            # Refit if vocabulary mismatch
            _tfidf_vectorizer.fit([text])
            vec = _tfidf_vectorizer.transform([text]).toarray()[0]

    # Pad/truncate to EMBED_DIM
    if len(vec) < EMBED_DIM:
        vec = np.pad(vec, (0, EMBED_DIM - len(vec)), "constant")
    else:
        vec = vec[:EMBED_DIM]

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec.tolist()
