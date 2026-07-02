"""Captcha API routes"""
from fastapi import APIRouter, Request, HTTPException

from models.schemas import ChallengeResponse, VerifyRequest, VerifyResponse
from captcha.generator import generate_puzzle
from captcha.security import generate_token, verify_token
from captcha.store import (
    save_challenge, consume_challenge, peek_challenge,
    check_rate_limit, record_fail, check_ip_blocked, record_stat
)
from captcha.behavior import analyze_trajectory, compute_risk
from config import TOLERANCE, RISK_THRESHOLD

router = APIRouter(prefix="/api/captcha", tags=["captcha"])


@router.get("/generate", response_model=ChallengeResponse)
async def captcha_generate(request: Request):
    """Generate a new captcha challenge.
    
    Returns background image, puzzle piece, and HMAC-signed token.
    """
    # Check IP blocklist
    ip = request.client.host if request.client else "unknown"
    if check_ip_blocked(ip):
        raise HTTPException(403, "IP blocked")

    # Check rate limit
    rate = check_rate_limit(ip)
    if not rate["allowed"]:
        raise HTTPException(429, f"Too many attempts, retry in {rate['reset_after']}s")

    try:
        puzzle = generate_puzzle()
    except Exception as e:
        raise HTTPException(500, f"Puzzle generation failed: {str(e)}")

    # Token payload: just track the image_id and expiry
    token = generate_token(
        puzzle["hole"]["x"], puzzle["hole"]["y"],
        puzzle["image_id"],
        puzzle["hole"]["w"], puzzle["hole"]["h"]
    )

    save_challenge(token,
                   puzzle["hole"]["x"], puzzle["hole"]["y"],
                   puzzle["image_id"],
                   puzzle["hole"]["w"], puzzle["hole"]["h"])

    return {
        "token": token,
        "background": puzzle["background_b64"],
        "hole": puzzle["hole"],
        "pieces": puzzle["pieces"],
    }


@router.post("/verify", response_model=VerifyResponse)
async def captcha_verify(req: VerifyRequest, request: Request):
    """Verify captcha solution.
    
    Validates position, consumes one-time token, analyzes trajectory,
    checks rate limits.
    """
    ip = request.client.host if request.client else "unknown"

    # Check blocklist
    if check_ip_blocked(ip):
        return VerifyResponse(success=False, risk_score=0, 
                             next_action="block", detail="IP blocked")

    # Rate limit
    rate = check_rate_limit(ip)
    if not rate["allowed"]:
        return VerifyResponse(success=False, risk_score=0,
                             next_action="block", detail="Rate limited")

    # Verify token
    payload = verify_token(req.token)
    if payload is None:
        record_fail(ip)
        return VerifyResponse(success=False, risk_score=0,
                             next_action="refresh", detail="Invalid or expired token")

    # Peek challenge (read without consuming — consume happens in /consume)
    stored = peek_challenge(req.token)
    if stored is None:
        record_fail(ip)
        return VerifyResponse(success=False, risk_score=0,
                             next_action="refresh", detail="Token not found or already used")

    target_x = int(stored.get("target_x", -1))
    target_y = int(stored.get("y_position", 0))

    # For shape-matching: check if trail endpoint is near the hole
    position_match = False
    if req.drag_trace and len(req.drag_trace) >= 2:
        last = req.drag_trace[-1]
        dx = abs(last.x - target_x)
        dy = abs(last.y - target_y)
        position_match = dx <= 20 and dy <= 20  # generous for shape matching
    elif abs(req.drag_distance - target_x) <= TOLERANCE:
        position_match = True  # legacy slider mode

    # Behavior analysis
    behavior = {"human_score": 0.5, "risk_level": "medium"}
    if req.drag_trace and len(req.drag_trace) >= 3:
        behavior = analyze_trajectory(req.drag_trace, target_x)

    # Final risk score
    risk = compute_risk(position_match, behavior)
    passed = risk >= RISK_THRESHOLD

    # Record
    record_stat(passed, risk, ip)
    if not passed:
        record_fail(ip)

    if passed:
        return VerifyResponse(success=True, risk_score=risk, next_action="ok")
    elif behavior.get("risk_level") == "high":
        return VerifyResponse(success=False, risk_score=risk,
                             next_action="refresh", detail="Suspicious activity detected")
    else:
        return VerifyResponse(success=False, risk_score=risk,
                             next_action="refresh", detail="Position mismatch, try again")


@router.post("/consume")
async def captcha_consume(req: VerifyRequest, request: Request):
    """Internal endpoint: consume a token after the main login form submits.
    Called by the Flask backend to verify the captcha was completed.
    """
    ip = request.client.host if request.client else "unknown"
    payload = verify_token(req.token)
    if payload is None:
        return {"valid": False, "reason": "invalid_token"}
    stored = consume_challenge(req.token)
    if stored is None:
        return {"valid": False, "reason": "already_used_or_expired"}
    return {"valid": True}
