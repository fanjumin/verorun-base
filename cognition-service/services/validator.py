"""Validator — enforce prediction schema, reject invalid submissions"""
import json, re, time, hashlib
from typing import Optional
from models.schemas import PredictionSubmit


# Reject cache (simple in-memory, 5-min window for duplicate detection)
_recent_hashes = {}


def validate_prediction(p: PredictionSubmit) -> Optional[str]:
    """Validate a prediction. Returns None if valid, error message if invalid."""
    errors = []

    # thesis count
    if len(p.thesis) < 1:
        errors.append("thesis: 至少需要1条理由")
    if len(p.thesis) > 5:
        errors.append("thesis: 最多5条理由")

    # thesis content
    for i, t in enumerate(p.thesis):
        if not t or len(t.strip()) < 3:
            errors.append(f"thesis[{i}]: 理由太短")
        if len(t) > 500:
            errors.append(f"thesis[{i}]: 理由超长(>500字)")

    # confidence
    if p.confidence < 0 or p.confidence > 100:
        errors.append("confidence: 必须在0-100之间")

    # ticker format
    ticker = p.ticker.upper().strip()
    if not re.match(r'^[A-Z0-9.\-^]+$', ticker):
        errors.append("ticker: 格式无效")
    if len(ticker) < 1 or len(ticker) > 20:
        errors.append("ticker: 长度无效")

    # agent_id
    if not p.agent_id or len(p.agent_id.strip()) < 2:
        errors.append("agent_id: 必须提供")

    # agent_name
    if not p.agent_name or len(p.agent_name.strip()) < 1:
        errors.append("agent_name: 必须提供")

    # duplicate detection (exact same prediction within 5 min)
    key = hashlib.md5(
        f"{p.agent_id}:{p.ticker}:{p.stance}:{p.timeframe}:{p.confidence}".encode()
    ).hexdigest()
    now = time.time()
    if key in _recent_hashes and now - _recent_hashes[key] < 300:
        errors.append("duplicate: 相同预测5分钟内已提交")
    _recent_hashes[key] = now
    # Clean old entries
    for k in list(_recent_hashes.keys()):
        if now - _recent_hashes[k] > 600:
            del _recent_hashes[k]

    return "; ".join(errors) if errors else None
