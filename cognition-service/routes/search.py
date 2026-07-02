"""Embedding and search routes — semantic search, clustering"""
from fastapi import APIRouter, Query
from services.embedding import search_similar_theses, get_clusters, embed_text

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search")
async def semantic_search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, le=50),
    threshold: float = Query(0.75, ge=0, le=1),
):
    """Semantic search across all thesis content using pgvector."""
    results = await search_similar_theses(q, limit=limit, threshold=threshold)
    return {
        "query": q,
        "count": len(results),
        "results": results,
    }


@router.get("/clusters")
async def topic_clusters(
    min_size: int = Query(3, ge=2, description="Minimum cluster size"),
    limit: int = Query(200, le=500),
):
    """Get topic clusters from recent thesis embeddings."""
    clusters = await get_clusters(min_cluster_size=min_size, limit=limit)
    return {
        "total_clusters": len(clusters),
        "clusters": clusters,
    }
