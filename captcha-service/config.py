"""Configuration — captcha service"""
import os

# Server
HOST = os.getenv("CAPTCHA_HOST", "0.0.0.0")
PORT = int(os.getenv("CAPTCHA_PORT", "8090"))

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CAPTCHA_TTL = 120          # challenge expires in 2 min
RATE_LIMIT_TTL = 300       # IP window 5 min
MAX_FAILS = 5              # max fails per IP in window

# Puzzle
IMAGE_DIR = os.getenv("IMAGE_DIR", os.path.join(os.path.dirname(__file__), "images"))
TOLERANCE = 4              # ±px
PIECE_MIN_X = 40           # min piece position
TRACK_WIDTH = 340          # canvas width (must match frontend)
CANVAS_HEIGHT = 190        # canvas height

# Security
SECRET_KEY = os.getenv("CAPTCHA_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "CAPTCHA_SECRET_KEY environment variable is required. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
HASH_ALGO = "sha256"

# Risk scoring
RISK_THRESHOLD = 0.7       # score >= → pass
