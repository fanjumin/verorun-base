#!/usr/bin/env python3
"""Embedding service: wraps the AI-engine kernel embedding capability."""

import logging

logger = logging.getLogger('memory_engine.embedding')


class EmbeddingService:
    """Resolve an embedding-capable model through the kernel and embed texts."""

    def __init__(self, config: dict):
        self._config = config or {}
        self._model_id = None  # provider_models.id of the embedding model
        self._dim = int(self._config.get('embedding_dim', 1536))

    def _resolve_model_id(self):
        """Pick the embedding model from provider_models (capabilities contains 'embedding')."""
        if self._model_id:
            return self._model_id
        try:
            from agent_matrix.models import get_db
            with get_db() as conn:
                row = conn.execute(
                    "SELECT id FROM provider_models"
                    " WHERE capabilities LIKE '%embedding%' AND is_active = 1"
                    " ORDER BY id LIMIT 1"
                ).fetchone()
            if row:
                self._model_id = row['id']
        except Exception as e:
            logger.warning('embedding model resolution failed: %s', e)
        return self._model_id

    def is_ready(self) -> bool:
        """True when an embedding model is configured and reachable at runtime."""
        return bool(self._config.get('embedding_model') or self._resolve_model_id())

    def embed(self, text: str):
        """Return embedding vector as a list of floats, or None on failure."""
        try:
            from agent_matrix.engine import UnifiedLLM
            llm = UnifiedLLM()
            # Kernel patch A: get_embedding() resolves model + key via provider_models.
            return llm.get_embedding(text, module='memory_engine')
        except Exception as e:
            logger.error('embedding call failed: %s', e)
            return None
