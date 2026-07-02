#!/usr/bin/env python3
"""CAPTCHA Service — 行为式滑动拼图验证码 (Behavioral Slider CAPTCHA)

升级点：
1. 前端采集拖拽轨迹 [{t, x, y}, ...]
2. 服务端行为分析模型 — 综合位置+轨迹+速度+加速度+停顿评分
3. 前端使用随机实景图替代 Canvas 渐变背景
4. 可扩展为极验(GEETEST)风格的第三方接口

No external dependencies. Pure Python stdlib.
"""
import time
import hashlib
import random
import threading
import math

# ═══════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════
TRACK_WIDTH = 280              # slider track total width in px
PIECE_SIZE = 56                # puzzle piece width in px
PIECE_HEIGHT = 170             # puzzle piece height in px
TOLERANCE = 4                  # allowed position error ±px
CAPTCHA_EXPIRE = 180           # 3 minutes
CLEANUP_INTERVAL = 300         # cleanup every 5 min

# Behavioral thresholds
MIN_DRAG_TIME_MS = 300         # minimum drag time (too fast = bot)
MAX_DRAG_TIME_MS = 10000       # maximum drag time (too slow = suspicious)
MIN_TRAJECTORY_POINTS = 5      # minimum data points required
PAUSE_THRESHOLD_MS = 150       # stationary time to count as a "pause"
MIN_PAUSES = 0                 # minimum expected pauses (humans often pause)
MAX_PAUSES = 8                 # too many pauses = suspicious
JITTER_THRESHOLD_PX = 1.5      # minimum jitter (perfectly straight line = bot)
SPEED_VARIANCE_MIN = 0.08      # minimum speed variance (constant speed = bot)
ACCEL_VARIANCE_MIN = 0.0005    # minimum acceleration variance
Y_VARIANCE_MIN = 0.3           # minimum vertical deviation (pixel-perfect horizontal = bot)
Y_VARIANCE_HARD_MIN = 0.05     # HARD minimum — if y_variance below this, it's almost certainly a bot
TIMING_UNIFORMITY_MAX = 0.15   # max timing relative std dev (perfectly uniform intervals = bot)

# Weights for combined score
WEIGHT_POSITION = 0.30         # did they hit the right spot?
WEIGHT_TRAJECTORY = 0.35       # velocity/accel pattern
WEIGHT_BEHAVIOR = 0.35         # pauses, jitter, timing
PASS_THRESHOLD = 0.65          # combined score >= this → pass

# ═══════════════════════════════════════════════════════════
# In-memory store
# ═══════════════════════════════════════════════════════════
_store = {}  # {captcha_id: {offset_x, expires_at, used, bg_index}}
_store_lock = threading.Lock()


def _cleanup():
    now = time.time()
    with _store_lock:
        expired = [k for k, v in _store.items() if v['expires_at'] < now]
        for k in expired:
            del _store[k]


# ═══════════════════════════════════════════════════════════
# Behavioral Scoring Engine
# ═══════════════════════════════════════════════════════════

def _analyze_trajectory(trajectory: list, expected_distance: float) -> dict:
    """Analyze a trajectory for human-like behavior patterns.

    Args:
        trajectory: list of {t, x, y} dicts in order
        expected_distance: the pixel distance the piece should travel

    Returns:
        dict with {trajectory_score, behavior_score, details}
    """
    if not trajectory or len(trajectory) < MIN_TRAJECTORY_POINTS:
        return {
            'trajectory_score': 0.0,
            'behavior_score': 0.0,
            'details': {'error': 'too_few_points', 'count': len(trajectory) if trajectory else 0}
        }

    pts = trajectory
    n = len(pts)

    # ── 1. Drag duration ──
    duration_ms = pts[-1]['t'] - pts[0]['t']
    duration_score = 1.0
    if duration_ms < MIN_DRAG_TIME_MS:
        duration_score = max(0.0, duration_ms / MIN_DRAG_TIME_MS)
    elif duration_ms > MAX_DRAG_TIME_MS:
        duration_score = max(0.0, 1.0 - (duration_ms - MAX_DRAG_TIME_MS) / 5000)

    # ── 2. Speed computation (frame-by-frame) ──
    speeds = []
    distances = []
    for i in range(1, n):
        dt = (pts[i]['t'] - pts[i-1]['t']) / 1000.0  # seconds
        dx = pts[i]['x'] - pts[i-1]['x']
        dy = pts[i]['y'] - pts[i-1]['y']
        dist = math.sqrt(dx*dx + dy*dy)
        if dt > 0.001:
            speeds.append(dist / dt)  # px/s
            distances.append(dist)

    if len(speeds) < 2:
        return {
            'trajectory_score': 0.0,
            'behavior_score': 0.0,
            'details': {'error': 'not_enough_speed_samples'}
        }

    avg_speed = sum(speeds) / len(speeds)

    # Speed variance (humans vary speed; bots are constant or purely linear)
    speed_var = sum((s - avg_speed)**2 for s in speeds) / len(speeds)
    speed_std = math.sqrt(speed_var)

    # ── 3. Acceleration computation ──
    accels = []
    for i in range(1, len(speeds)):
        dt = (pts[i+1]['t'] - pts[i]['t']) / 1000.0
        if dt > 0.001:
            accels.append((speeds[i] - speeds[i-1]) / dt)

    accel_var = 0.0
    if len(accels) >= 2:
        avg_accel = sum(accels) / len(accels)
        accel_var = sum((a - avg_accel)**2 for a in accels) / len(accels)

    # ── 4. Pause detection ──
    pauses = 0
    total_pause_ms = 0
    for i in range(1, n):
        dt = pts[i]['t'] - pts[i-1]['t']
        dx = abs(pts[i]['x'] - pts[i-1]['x'])
        if dt > PAUSE_THRESHOLD_MS and dx < 3:
            pauses += 1
            total_pause_ms += dt

    # ── 5. Y-axis jitter (vertical wobble) ──
    y_values = [p['y'] for p in pts]
    if len(y_values) >= 2:
        y_mean = sum(y_values) / len(y_values)
        y_variance = sum((y - y_mean)**2 for y in y_values) / len(y_values)
    else:
        y_variance = 0.0

    # ── 6. X-axis linearity (is the trajectory too straight?) ──
    # Perfectly straight x-movement with zero y-deviation suggests automation
    # Compute differences between consecutive x positions
    x_deltas = [pts[i]['x'] - pts[i-1]['x'] for i in range(1, n)]
    if len(x_deltas) >= 2:
        dx_mean = sum(x_deltas) / len(x_deltas)
        dx_variance = sum((dx - dx_mean)**2 for dx in x_deltas) / len(x_deltas)
    else:
        dx_variance = 0.0

    # ── 7. Backtracking detection ──
    # Humans sometimes slightly overshoot and correct; bots rarely backtrack
    backtracks = 0
    max_backtrack = 0
    for i in range(2, n):
        if pts[i]['x'] < pts[i-1]['x']:
            backtrack = pts[i-1]['x'] - pts[i]['x']
            backtracks += 1
            max_backtrack = max(max_backtrack, backtrack)

    # ── 8. Timing uniformity check ──
    # Perfectly uniform intervals = bot. Humans have natural variation.
    time_deltas = [pts[i]['t'] - pts[i-1]['t'] for i in range(1, n)]
    if len(time_deltas) >= 3:
        td_mean = sum(time_deltas) / len(time_deltas)
        td_variance = sum((td - td_mean)**2 for td in time_deltas) / len(time_deltas)
        td_std = math.sqrt(td_variance)
        timing_cv = td_std / max(td_mean, 1.0)  # coefficient of variation
    else:
        timing_cv = 0.0

    # ── Scoring ──

    # Speed variance score: higher is more human
    speed_var_score = min(1.0, speed_var / (SPEED_VARIANCE_MIN * 50))
    if speed_var < SPEED_VARIANCE_MIN:
        speed_var_score = speed_var / SPEED_VARIANCE_MIN * 0.3  # partial credit

    # Acceleration variance score
    accel_var_score = 0.0
    if accel_var > ACCEL_VARIANCE_MIN:
        accel_var_score = min(1.0, accel_var / (ACCEL_VARIANCE_MIN * 100))
    elif accel_var > ACCEL_VARIANCE_MIN * 0.1:
        accel_var_score = 0.3  # tiny accel variation = suspicious

    # Pause score (at least one small pause is human-like)
    pause_score = 1.0
    if pauses == 0 and duration_ms > 500:
        pause_score = 0.4  # no pauses at all = bot-like
    elif pauses > MAX_PAUSES:
        pause_score = max(0.0, 1.0 - (pauses - MAX_PAUSES) * 0.25)

    duration_ratio = total_pause_ms / max(duration_ms, 1)
    if duration_ratio > 0.7:
        pause_score *= 0.5  # spent 70%+ pausing = suspicious

    # Y-variance score (some vertical wobble is human)
    # HARD penalty: zero vertical movement = almost certain bot
    if y_variance < Y_VARIANCE_HARD_MIN:
        y_var_score = 0.0
    else:
        y_var_score = min(1.0, y_variance / (Y_VARIANCE_MIN * 20))

    # Backtrack score
    backtrack_score = 1.0
    if backtracks > 0 and max_backtrack < 10:
        backtrack_score = 1.0  # small corrections are human
    elif backtracks == 0 and duration_ms > 800:
        backtrack_score = 0.7  # no corrections at all = slightly suspicious

    # X-linearity score (too consistent = bot)
    linearity_score = 1.0
    if dx_variance < 50 and n > 8:
        linearity_score = 0.3  # suspiciously consistent step size
    elif dx_variance < 200:
        linearity_score = 0.7

    # Timing uniformity score (perfect intervals = bot)
    timing_score = max(0.0, min(1.0, timing_cv / TIMING_UNIFORMITY_MAX))
    if timing_cv < 0.02:
        timing_score = 0.0  # essentially perfect timing = bot
    elif timing_cv < TIMING_UNIFORMITY_MAX:
        timing_score = timing_cv / TIMING_UNIFORMITY_MAX * 0.5  # partial credit

    # ── Compute scores ──
    trajectory_score = (
        speed_var_score * 0.25 +
        accel_var_score * 0.20 +
        linearity_score * 0.25 +
        backtrack_score * 0.15 +
        timing_score * 0.15
    )

    behavior_score = (
        duration_score * 0.25 +
        pause_score * 0.25 +
        y_var_score * 0.50
    )

    return {
        'trajectory_score': round(trajectory_score, 4),
        'behavior_score': round(behavior_score, 4),
        'duration_score': round(duration_score, 4),
        'pause_score': round(pause_score, 4),
        'details': {
            'duration_ms': int(duration_ms),
            'avg_speed': round(avg_speed, 2),
            'speed_var': round(speed_var, 2),
            'speed_var_score': round(speed_var_score, 4),
            'accel_var': round(accel_var, 6),
            'accel_var_score': round(accel_var_score, 4),
            'pauses': pauses,
            'total_pause_ms': int(total_pause_ms),
            'y_variance': round(y_variance, 4),
            'y_var_score': round(y_var_score, 4),
            'backtracks': backtracks,
            'max_backtrack': round(max_backtrack, 2),
            'linearity_score': round(linearity_score, 4),
            'timing_cv': round(timing_cv, 4),
            'timing_score': round(timing_score, 4),
            'point_count': n,
            'expected_distance': round(expected_distance, 1),
        }
    }


def _combined_verdict(
    position_match: bool,
    trajectory_score: float,
    behavior_score: float
) -> dict:
    """Compute final pass/fail verdict combining all signals.

    Returns:
        dict with {pass, combined_score, ...}
    """
    pos_score = 1.0 if position_match else 0.0

    combined = (
        WEIGHT_POSITION * pos_score +
        WEIGHT_TRAJECTORY * trajectory_score +
        WEIGHT_BEHAVIOR * behavior_score
    )

    # Position MUST be correct (non-negotiable)
    if not position_match:
        return {
            'pass': False,
            'combined_score': round(combined, 4),
            'reason': 'position_mismatch',
            'pos_score': 0.0,
            'trajectory_score': trajectory_score,
            'behavior_score': behavior_score,
        }

    # If position is correct but trajectory is obviously a bot
    if trajectory_score < 0.25:
        return {
            'pass': False,
            'combined_score': round(combined, 4),
            'reason': 'bot_like_trajectory',
            'pos_score': 1.0,
            'trajectory_score': trajectory_score,
            'behavior_score': behavior_score,
        }

    # Hard human-likeness gate: must have some behavioral signal
    # Perfectly horizontal + perfectly uniform timing = almost certainly a bot
    if behavior_score < 0.45:
        return {
            'pass': False,
            'combined_score': round(combined, 4),
            'reason': 'missing_human_behavior',
            'pos_score': 1.0,
            'trajectory_score': trajectory_score,
            'behavior_score': behavior_score,
        }

    # Final verdict
    return {
        'pass': combined >= PASS_THRESHOLD,
        'combined_score': round(combined, 4),
        'reason': 'ok' if combined >= PASS_THRESHOLD else 'below_threshold',
        'pos_score': 1.0,
        'trajectory_score': trajectory_score,
        'behavior_score': behavior_score,
    }


# ═══════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════

def generate_slider(bg_count: int = 20) -> dict:
    """Generate a sliding puzzle challenge.

    Returns:
        dict with:
            captcha_id, track_width, piece_size,
            offset_x, bg_index (which background image to use)
    """
    _cleanup()

    # Random offset
    min_x = 10
    max_x = TRACK_WIDTH - PIECE_SIZE - 10
    offset_x = random.randint(min_x, max_x)

    # Random background image index
    bg_index = random.randint(0, max(0, bg_count - 1))

    # Create captcha_id
    raw = f"{offset_x}:{time.time()}:{random.randint(100000, 999999)}"
    captcha_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    with _store_lock:
        _store[captcha_id] = {
            'offset_x': offset_x,
            'expires_at': time.time() + CAPTCHA_EXPIRE,
            'used': False,
            'bg_index': bg_index,
        }

    return {
        'captcha_id': captcha_id,
        'track_width': TRACK_WIDTH,
        'piece_size': PIECE_SIZE,
        'piece_height': PIECE_HEIGHT,
        'offset_x': offset_x,
        'bg_index': bg_index,
    }


def verify_slider_behavioral(
    captcha_id: str,
    user_x: int,
    trajectory: list = None
) -> dict:
    """Phase 1: Behavioral verification. Marks as 'behavior_verified' but does NOT consume.

    The captcha remains in the store for the SMS/password endpoint to consume.
    Expiry still applies.

    Args:
        captcha_id: challenge ID
        user_x: final piece X position
        trajectory: optional [{t: ms, x: px, y: px}, ...]

    Returns:
        dict with {valid, pass, combined_score, details, ...}
    """
    if not captcha_id or user_x is None:
        return {'valid': False, 'pass': False, 'reason': 'missing_params'}

    with _store_lock:
        entry = _store.get(captcha_id)
        if not entry:
            return {'valid': False, 'pass': False, 'reason': 'not_found'}
        if entry.get('used'):
            return {'valid': False, 'pass': False, 'reason': 'already_used'}
        if entry['expires_at'] < time.time():
            del _store[captcha_id]
            return {'valid': False, 'pass': False, 'reason': 'expired'}

        expected_offset = entry['offset_x']

    position_match = abs(int(user_x) - expected_offset) <= TOLERANCE

    # Legacy mode: no trajectory data → pure position check
    if not trajectory or len(trajectory) < MIN_TRAJECTORY_POINTS:
        with _store_lock:
            entry = _store.get(captcha_id)
            if entry:
                entry['behavior_verified'] = position_match
        result = {
            'valid': position_match,
            'pass': position_match,
            'reason': 'position_only' if position_match else 'position_mismatch',
            'mode': 'legacy',
        }
        return result

    # Behavioral mode
    expected_distance = abs(expected_offset - 0)  # piece starts at x=0
    analysis = _analyze_trajectory(trajectory, expected_distance)
    verdict = _combined_verdict(position_match, analysis['trajectory_score'], analysis['behavior_score'])

    # Mark as behavior-verified (but not consumed)
    with _store_lock:
        entry = _store.get(captcha_id)
        if entry:
            entry['behavior_verified'] = verdict['pass']
            entry['behavior_score'] = verdict['combined_score']
            entry['behavior_details'] = analysis['details']

    return {
        'valid': position_match,
        'pass': verdict['pass'],
        'mode': 'behavioral',
        'combined_score': verdict['combined_score'],
        'pos_score': verdict['pos_score'],
        'trajectory_score': verdict['trajectory_score'],
        'behavior_score': verdict['behavior_score'],
        'reason': verdict['reason'],
        'details': analysis['details'],
    }


def consume_captcha(captcha_id: str) -> bool:
    """Phase 2: Called by SMS/password endpoints.
    Checks that the captcha was behavior-verified, then consumes it.

    Returns True if captcha was previously verified and is now consumed.
    """
    if not captcha_id:
        return False
    with _store_lock:
        entry = _store.get(captcha_id)
        if not entry:
            return False
        if entry.get('used'):
            return False
        if entry['expires_at'] < time.time():
            del _store[captcha_id]
            return False
        if not entry.get('behavior_verified'):
            return False
        # Consume
        entry['used'] = True
        del _store[captcha_id]
        return True


def verify_slider(captcha_id: str, user_x: int) -> bool:
    """Legacy-compatible simple position check.

    For backward compatibility when behavioral isn't needed.
    """
    result = verify_slider_behavioral(captcha_id, user_x)
    return result.get('valid', False)


def get_background_count() -> int:
    """Get the count of available background images."""
    # This is determined by what's in static/captcha/bg_*.jpg
    # Default to 20; the frontend will verify actual availability
    return 20


def start_cleanup_thread():
    """Start background cleanup thread."""
    def _loop():
        while True:
            time.sleep(CLEANUP_INTERVAL)
            _cleanup()
    t = threading.Thread(target=_loop, daemon=True)
    t.start()
