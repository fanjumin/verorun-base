#!/usr/bin/env python3
# VeroRon 维洛智能 (verorun.com / verorun.cn)
# 版权所有 (c) 2026 樊聚民 (fanjumin). All Rights Reserved.

"""Captcha Service — FastAPI server for slider puzzle CAPTCHA.

Architecture:
  Port 8090 (independent service)
  Redis for challenge storage + rate limiting
  Pillow for puzzle image generation
  HMAC-SHA256 for token signing

Endpoints:
  GET  /api/captcha/generate   → challenge
  POST /api/captcha/verify     → verify solution
  POST /api/captcha/consume    → internal token consumption
  GET  /captcha-widget.js      → Vue3 widget script
  GET  /captcha-widget.css     → widget styles
  GET  /api/admin/captcha/stats → statistics (admin)
  GET  /health                  → health check
"""
import sys, os, uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

sys.path.insert(0, os.path.dirname(__file__))

from config import HOST, PORT
from routes.captcha import router as captcha_router
from routes.admin import router as admin_router

app = FastAPI(
    title="Captcha Service",
    version="2.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# CORS — allow the main site to call this service
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(captcha_router)
app.include_router(admin_router)

# Static files served as routes (more reliable than StaticFiles mount)
_BASE = os.path.dirname(__file__)

@app.get("/puzzle-captcha.js")
async def puzzle_js():
    path = os.path.join(_BASE, "puzzle-captcha.js")
    if os.path.exists(path):
        with open(path) as f:
            return Response(f.read(), media_type="application/javascript")
    return Response("/* not found */", status_code=404)

@app.get("/puzzle-captcha.css")
async def puzzle_css():
    path = os.path.join(_BASE, "puzzle-captcha.css")
    if os.path.exists(path):
        with open(path) as f:
            return Response(f.read(), media_type="text/css")
    return Response("/* not found */", status_code=404)

@app.get("/captcha-widget.js")
async def widget_js():
    path = os.path.join(_BASE, "captcha-widget.js")
    if os.path.exists(path):
        with open(path) as f:
            return Response(f.read(), media_type="application/javascript")
    return Response("/* not found */", status_code=404, media_type="application/javascript")

@app.get("/captcha-widget.css")
async def widget_css():
    path = os.path.join(_BASE, "captcha-widget.css")
    if os.path.exists(path):
        with open(path) as f:
            return Response(f.read(), media_type="text/css")
    return Response("/* not found */", status_code=404, media_type="text/css")


@app.get("/health")
async def api_health():
    return {"status": "ok", "service": "captcha", "version": "2.0.0"}


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    uvicorn.run(app, host=HOST, port=port, log_level="info")
