"""
MediVerse AI — ChromaDB Client Manager.
Singleton client that manages persistent ChromaDB connection.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

from config.settings import get_settings
from core.exceptions import ChromaDBConnectionError

logger = logging.getLogger("mediverse.vector_db")

_client: Optional[chromadb.ClientAPI] = None


def get_chroma_client() -> chromadb.ClientAPI:
    """Return singleton ChromaDB client (persistent local storage)."""
    global _client
    if _client is None:
        settings = get_settings()
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)

        try:
            _client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            logger.info(f"ChromaDB initialized at {persist_dir}")
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            raise ChromaDBConnectionError() from e
    return _client


def check_chroma_connection() -> bool:
    """Health check for ChromaDB. Returns True if healthy."""
    try:
        client = get_chroma_client()
        client.heartbeat()
        logger.info("ChromaDB health check: OK")
        return True
    except Exception as e:
        logger.error(f"ChromaDB health check failed: {e}")
        raise ChromaDBConnectionError() from e


def close_chroma_client() -> None:
    """Reset the singleton client."""
    global _client
    _client = None
    logger.info("ChromaDB client reset")
