"""Pydantic schemas for cognition service"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


# ── Prediction ────────────────────────────────────────────

class PredictionSubmit(BaseModel):
    """Standardized prediction submission from any Agent"""
    agent_id: str = Field(..., min_length=1, max_length=64)
    agent_name: str = Field(..., min_length=1, max_length=128)
    skill_id: str = Field(default="", max_length=64)
    market: str = Field(...)  # CN|HK|US|CRYPTO|FUTURES
    ticker: str = Field(..., min_length=1, max_length=32)
    stance: str = Field(...)  # bullish|bearish|neutral
    confidence: int = Field(..., ge=0, le=100)
    timeframe: str = Field(...)  # 1d|7d|30d|90d
    thesis: List[str] = Field(..., min_length=1, max_length=5)
    risk_level: str = Field(...)  # low|medium|high
    price_target: Optional[float] = None
    source_type: str = Field(default="Hermes")

    @field_validator('market')
    @classmethod
    def check_market(cls, v):
        if v not in ('CN', 'HK', 'US', 'CRYPTO', 'FUTURES'):
            raise ValueError(f'Invalid market: {v}')
        return v

    @field_validator('stance')
    @classmethod
    def check_stance(cls, v):
        if v not in ('bullish', 'bearish', 'neutral'):
            raise ValueError(f'Invalid stance: {v}')
        return v

    @field_validator('timeframe')
    @classmethod
    def check_timeframe(cls, v):
        if v not in ('1d', '7d', '30d', '90d'):
            raise ValueError(f'Invalid timeframe: {v}')
        return v

    @field_validator('risk_level')
    @classmethod
    def check_risk(cls, v):
        if v not in ('low', 'medium', 'high'):
            raise ValueError(f'Invalid risk_level: {v}')
        return v

    @field_validator('ticker')
    @classmethod
    def format_ticker(cls, v):
        return v.upper().strip()


class PredictionResponse(BaseModel):
    id: int
    agent_id: str
    ticker: str
    stance: str
    confidence: int
    timeframe: str
    thesis: List[str]
    risk_level: str
    price_target: Optional[float] = None
    created_at: datetime
    settlement_status: str


# ── Agent ─────────────────────────────────────────────────

class AgentCreate(BaseModel):
    agent_id: str
    agent_name: str
    owner_id: Optional[int] = None
    source_type: str = "Hermes"


class AgentReputation(BaseModel):
    agent_id: str
    total_predictions: int
    accuracy_rate: float
    avg_confidence: float
    sharpe_like_score: float
    reputation_score: float


# ── Stock Consensus ──────────────────────────────────────

class StockConsensus(BaseModel):
    ticker: str
    total: int
    bullish_pct: float
    bearish_pct: float
    neutral_pct: float
    top_thesis: List[str]
    avg_confidence: float


# ── Graph ────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    data: dict = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str
    weight: float = 1.0


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# ── Stats ────────────────────────────────────────────────

class LeaderboardEntry(BaseModel):
    rank: int
    agent_id: str
    agent_name: str
    accuracy_rate: float
    total_predictions: int
    reputation_score: float


class SystemStats(BaseModel):
    total_predictions: int
    total_agents: int
    resolved_count: int
    overall_accuracy: float
