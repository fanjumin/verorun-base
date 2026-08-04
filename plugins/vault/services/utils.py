#!/usr/bin/env python3
"""
Vault Utilities — Shared helpers for backup/restore services.

Provides common functions to eliminate code duplication across modules.
"""

import os
from typing import Dict

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
BACKUP_DIR = os.path.join(BASE_DIR, 'data', 'vault')


def get_pg_env() -> Dict[str, str]:
    """Read .env for PostgreSQL connection info."""
    env = {}
    env_path = os.path.join(BASE_DIR, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env
