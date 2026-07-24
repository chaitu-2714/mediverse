"""
MediVerse AI — SQLAlchemy Database Connection Manager.
Handles engine creation, session factory, and connection health checks.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from config.settings import get_settings
from core.exceptions import DatabaseConnectionError, DatabaseError

logger = logging.getLogger("mediverse.database")

_engine = None
_SessionLocal = None


def get_engine():
    """Return the singleton SQLAlchemy engine, creating it if needed."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            poolclass=QueuePool,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=settings.debug,
            connect_args={
                "connect_timeout": 10,
                "application_name": "MediVerse AI",
            },
        )

        @event.listens_for(_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            logger.debug("Database connection established")

        logger.info("PostgreSQL engine initialized")
    return _engine


def get_session_factory() -> sessionmaker:
    """Return the singleton session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager that provides a database session with automatic
    commit on success and rollback on exception.
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        if e.__class__.__name__ == "HTTPException":
            raise e
        logger.error(f"Database session error: {e}")
        raise DatabaseError(str(e), original=e) from e
    finally:
        session.close()


def check_database_connection() -> bool:
    """
    Verify database connectivity. Returns True if healthy, raises on failure.
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection health check: OK")
        return True
    except Exception as e:
        settings = get_settings()
        logger.error(f"Database connection failed: {e}")
        raise DatabaseConnectionError(settings.db_host, settings.db_port) from e


def initialize_database() -> None:
    """Create all tables defined in ORM models."""
    from database.base import Base
    # Import all models to register with Base metadata
    import database.models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(engine)
    
    # Programmatic migrations for new fields
    try:
        with engine.connect() as conn:
            # Check supabase_uid
            res = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='users' AND column_name='supabase_uid'"
            )).first()
            if not res:
                # Check if firebase_uid exists to rename it
                fb_res = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='users' AND column_name='firebase_uid'"
                )).first()
                if fb_res:
                    logger.info("Database migration: Renaming firebase_uid to supabase_uid")
                    conn.execute(text("ALTER TABLE users RENAME COLUMN firebase_uid TO supabase_uid"))
                else:
                    logger.info("Database migration: Adding supabase_uid to users table")
                    conn.execute(text("ALTER TABLE users ADD COLUMN supabase_uid VARCHAR(255) DEFAULT NULL"))
                conn.commit()

            # Check auth_provider
            res = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='users' AND column_name='auth_provider'"
            )).first()
            if not res:
                logger.info("Database migration: Adding auth_provider to users table")
                conn.execute(text("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT NULL"))
                conn.commit()

            # Check is_onboarded
            res = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='users' AND column_name='is_onboarded'"
            )).first()
            if not res:
                logger.info("Database migration: Adding is_onboarded to users table")
                conn.execute(text("ALTER TABLE users ADD COLUMN is_onboarded BOOLEAN DEFAULT FALSE NOT NULL"))
                conn.commit()

            # Check login_count
            res = conn.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='users' AND column_name='login_count'"
            )).first()
            if not res:
                logger.info("Database migration: Adding login_count to users table")
                conn.execute(text("ALTER TABLE users ADD COLUMN login_count INTEGER DEFAULT 0 NOT NULL"))
                conn.commit()
    except Exception as e:
        logger.warning(f"Database migration check anomaly: {e}")

    logger.info("Database tables initialized")


def close_engine() -> None:
    """Dispose the engine connection pool."""
    global _engine, _SessionLocal
    if _engine:
        _engine.dispose()
        _engine = None
        _SessionLocal = None
        logger.info("Database engine disposed")
