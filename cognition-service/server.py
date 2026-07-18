"""Cognition Graph Service — FastAPI main entry point"""
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import HOST, PORT
from db.connection import init_db, close_db
from routes.predictions import router as predictions_router
from routes.agents import router as agents_router
from routes.settlements import router as settlements_router
from routes.search import router as search_router
from routes.maps import router as maps_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB pool and run schema on startup."""
    pool = await init_db()
    app.state.pg_pool = pool
    yield
    await close_db()


app = FastAPI(
    title="Cognition Graph Service",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for dev (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(predictions_router)
app.include_router(agents_router)
app.include_router(settlements_router)
app.include_router(search_router)
app.include_router(maps_router)


@app.get("/api/v1/health")
async def health():
    """Health check endpoint."""
    from db.connection import get_pool
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    }


@app.get("/api/v1", include_in_schema=False)
async def api_root():
    """API root — list available endpoints."""
    return {
        "service": "Cognition Graph Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/v1/health",
            "predictions": "POST/GET /api/v1/predictions",
            "consensus": "GET /api/v1/consensus/{ticker}",
            "leaderboard": "GET /api/v1/leaderboard",
            "stats": "GET /api/v1/stats",
            "graph": "GET /api/v1/graph",
            "agents": "POST/GET /api/v1/agents/{agent_id}",
            "settlement": "POST /api/v1/settlement/run",
            "search": "GET /api/v1/search?q=...",
            "clusters": "GET /api/v1/clusters",
            "map/heat": "GET /api/v1/map/heat?hours=24",
            "map/stock": "GET /api/v1/map/stock/{ticker}",
            "map/agents": "GET /api/v1/map/agents",
            "map/conflicts": "GET /api/v1/map/conflicts",
        },
    }


if __name__ == "__main__(":
    import uvicorn
    uvicorn.run(")server:app", host=HOST, port=PORT, reload=True)
