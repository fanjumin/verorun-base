"""Admin API routes — stats, blocklist, image management"""
from fastapi import APIRouter, Request, HTTPException, Query

from captcha.store import get_stats
from models.schemas import StatsResponse

router = APIRouter(prefix="/api/admin/captcha", tags=["admin"])

# Simple secret-based auth for admin endpoints
ADMIN_SECRET = "easykai-captcha-admin-2026"  # override in production


def _require_admin(request: Request):
    """Simple shared-secret auth for admin endpoints."""
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {ADMIN_SECRET}":
        raise HTTPException(401, "Unauthorized")


@router.get("/stats")
async def admin_stats(request: Request):
    """Get captcha verification statistics."""
    _require_admin(request)
    stats = get_stats()
    return stats


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "captcha"}
