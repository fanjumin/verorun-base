"""Pydantic schemas"""
from pydantic import BaseModel, Field
from typing import Optional, List


class ShapeHole(BaseModel):
    shape: str
    x: int
    y: int
    w: int
    h: int
    angle: int = 0


class ShapePiece(BaseModel):
    shape: str
    x: int
    y: int
    w: int
    h: int
    imgData: str
    isTarget: bool = False
    angle: int = 0


class ChallengeResponse(BaseModel):
    token: str
    background: str                     # base64 PNG
    hole: ShapeHole
    pieces: List[ShapePiece]


class TracePoint(BaseModel):
    t: int
    x: int
    y: int


class VerifyRequest(BaseModel):
    token: str
    drag_distance: int = 0
    drag_trace: Optional[List[TracePoint]] = None


class VerifyResponse(BaseModel):
    success: bool
    risk_score: float
    next_action: str = "ok"
    detail: Optional[str] = None


class StatsResponse(BaseModel):
    total_requests: int = 0
    pass_rate: float = 0.0
    avg_risk: float = 0.0
    ip_fails: list = []
    last_hour: int = 0
