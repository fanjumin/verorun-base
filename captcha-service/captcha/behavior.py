"""Behavioral trajectory analysis + risk scoring"""
import math
from typing import List, Optional
from models.schemas import TracePoint


def analyze_trajectory(trace: List[TracePoint], expected_distance: int) -> dict:
    """Analyze drag trajectory for human-like patterns.
    
    Returns dict with {human_score (0-1), risk_level (low/medium/high), details}
    """
    if not trace or len(trace) < 3:
        return {"human_score": 0.0, "risk_level": "high",
                "detail": "insufficient_data"}

    n = len(trace)
    pts = [(p.t, p.x, p.y) for p in trace]

    # ── 1. Duration ──
    duration_ms = pts[-1][0] - pts[0][0]
    duration_ok = 300 < duration_ms < 8000

    # ── 2. Speed profile ──
    speeds = []
    for i in range(1, n):
        dt = (pts[i][0] - pts[i-1][0]) / 1000.0
        dx = pts[i][1] - pts[i-1][1]
        dy = pts[i][2] - pts[i-1][2]
        if dt > 0.001:
            speeds.append(math.sqrt(dx*dx + dy*dy) / dt)

    if len(speeds) < 2:
        return {"human_score": 0.0, "risk_level": "high",
                "detail": "too_few_speed_samples"}

    avg_speed = sum(speeds) / len(speeds)
    speed_var = sum((s - avg_speed)**2 for s in speeds) / len(speeds)

    # ── 3. Acceleration ──
    accels = []
    for i in range(1, len(speeds)):
        dt = (pts[i+1][0] - pts[i][0]) / 1000.0
        if dt > 0.001:
            accels.append((speeds[i] - speeds[i-1]) / dt)

    accel_var = 0.0
    if len(accels) >= 2:
        avg_a = sum(accels) / len(accels)
        accel_var = sum((a - avg_a)**2 for a in accels) / len(accels)

    # ── 4. Y-axis wobble ──
    y_vals = [p[2] for p in pts]
    y_mean = sum(y_vals) / len(y_vals)
    y_var = sum((y - y_mean)**2 for y in y_vals) / len(y_vals)

    # ── 5. Backtracking ──
    backtracks = 0
    for i in range(2, n):
        if pts[i][1] < pts[i-1][1]:
            backtracks += 1

    # ── 6. Pauses ──
    pauses = 0
    for i in range(1, n):
        dt = pts[i][0] - pts[i-1][0]
        dx = abs(pts[i][1] - pts[i-1][1])
        if dt > 150 and dx < 3:
            pauses += 1

    # ── 7. Linearity ──
    x_deltas = [pts[i][1] - pts[i-1][1] for i in range(1, n)]
    dx_var = 0.0
    if len(x_deltas) >= 2:
        dx_mean = sum(x_deltas) / len(x_deltas)
        dx_var = sum((d - dx_mean)**2 for d in x_deltas) / len(x_deltas)

    # ── Scoring ──
    scores = []

    # Duration: too fast or too slow
    scores.append(1.0 if duration_ok else 0.3)

    # Speed variance: humans vary speed
    sv_score = min(1.0, speed_var / 50.0) if speed_var > 1 else 0.2
    scores.append(sv_score)

    # Y wobble: some vertical movement is human
    y_score = min(1.0, y_var / 5.0) if y_var > 0.1 else 0.1
    scores.append(y_score)

    # Backtracks: small corrections are human
    bt_score = min(1.0, backtracks / 3.0) if backtracks > 0 else 0.6
    scores.append(bt_score)

    # Pauses: at least one is human-like
    pause_score = 0.8 if 1 <= pauses <= 5 else (0.4 if pauses == 0 else 0.5)
    scores.append(pause_score)

    # Linearity: too consistent = bot
    lin_score = 0.3 if dx_var < 20 else (0.7 if dx_var < 100 else 1.0)
    scores.append(lin_score)

    human_score = sum(scores) / len(scores)

    risk = "low" if human_score >= 0.65 else ("medium" if human_score >= 0.4 else "high")

    return {
        "human_score": round(human_score, 4),
        "risk_level": risk,
        "details": {
            "duration_ms": duration_ms,
            "avg_speed": round(avg_speed, 1),
            "speed_var": round(speed_var, 1),
            "y_var": round(y_var, 2),
            "backtracks": backtracks,
            "pauses": pauses,
            "dx_var": round(dx_var, 1),
        }
    }


def compute_risk(position_match: bool, behavior: dict) -> float:
    """Compute final risk score (0-1, higher = more human)."""
    if not position_match:
        return 0.0
    
    pos_weight = 0.25
    behavior_weight = 0.75
    
    pos_score = 1.0 if position_match else 0.0
    beh_score = behavior.get("human_score", 0.0)
    
    return round(pos_weight * pos_score + behavior_weight * beh_score, 4)
