"""
MediVerse AI — Embedding Engine.
Generates dense vector embeddings using Sentence Transformers.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from config.settings import get_settings
from core.exceptions import EmbeddingError

logger = logging.getLogger("mediverse.ai.embedding")


class EmbeddingEngine:
    """
    Sentence Transformer-based embedding engine.
    Generates 384-dim embeddings for document chunks and search queries.
    Supports batch processing for large document collections.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._model = None
        self._model_name = self._settings.embedding_model
        self._device = self._settings.embedding_device
        self._batch_size = self._settings.embedding_batch_size
        self._initialized = False

    def initialize(self) -> None:
        """Load the embedding model. Called once during app startup."""
        if self._initialized:
            return
        self._load_model()
        self._initialized = True

    def _load_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(
                self._model_name,
                device=self._device,
            )
            dim = self._model.get_sentence_embedding_dimension()
            logger.info(
                f"Embedding model loaded: {self._model_name} "
                f"(dim={dim}, device={self._device})"
            )
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise EmbeddingError(str(e)) from e

    @property
    def embedding_dimension(self) -> int:
        if self._model is None:
            return 384  # Default for all-MiniLM-L6-v2
        return self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: list[str], show_progress: bool = False) -> list[list[float]]:
        """
        Generate embeddings for a list of text strings.
        Returns list of float vectors.
        """
        if not self._initialized:
            self.initialize()
        if not texts:
            return []
        if self._model is None:
            raise EmbeddingError("Embedding model not loaded")

        try:
            embeddings = self._model.encode(
                texts,
                batch_size=self._batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            return embeddings.tolist()
        except Exception as e:
            raise EmbeddingError(str(e)) from e

    def embed_single(self, text: str) -> list[float]:
        """Generate embedding for a single text string."""
        results = self.embed_texts([text])
        return results[0] if results else []

    def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.
        Queries may be prefixed differently from documents in some models.
        """
        return self.embed_single(query)

    def embed_chunks_batch(
        self,
        chunks: list[str],
        on_progress: Optional[callable] = None,
    ) -> list[list[float]]:
        """
        Embed chunks in batches with optional progress callback.
        Callback receives (completed, total) ints.
        """
        if not chunks:
            return []

        all_embeddings: list[list[float]] = []
        total = len(chunks)

        for i in range(0, total, self._batch_size):
            batch = chunks[i: i + self._batch_size]
            batch_embeddings = self.embed_texts(batch)
            all_embeddings.extend(batch_embeddings)
            if on_progress:
                on_progress(min(i + self._batch_size, total), total)

        logger.debug(f"Generated {len(all_embeddings)} embeddings for {total} chunks")
        return all_embeddings

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a = np.array(vec1)
        b = np.array(vec2)
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        return float(dot / norm) if norm > 0 else 0.0
