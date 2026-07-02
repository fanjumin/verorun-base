"""Cognition Service — configuration"""
import os

HOST = os.getenv("COG_HOST", "0.0.0.0")
PORT = int(os.getenv("COG_PORT", "8091"))

# PostgreSQL
PG_HOST = os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_USER = os.getenv("PG_USER", "easykai")
PG_PASSWORD = os.getenv("PG_PASSWORD", "***REMOVED***")
PG_DATABASE = os.getenv("PG_DATABASE", "cognition")

# Embedding
EMBED_DIM = 384  # all-MiniLM-L6-v2 dimension, or use simple TF-IDF fallback
SIMILARITY_THRESHOLD = 0.75

# Settlement
SETTLEMENT_CHECK_HOURS = [0, 12]  # check at UTC midnight and noon
