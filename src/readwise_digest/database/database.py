"""Database connection and session management."""

import os
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..logging_config import get_logger
from .models import Base

logger = get_logger(__name__)

# Global engine and session factory
_engine: Engine = None
_SessionLocal: sessionmaker = None


def get_database_url() -> str:
    """Get the database URL from environment or default to local SQLite."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    # Default to SQLite in the project directory
    project_root = Path(__file__).parent.parent.parent.parent
    db_path = project_root / "readwise_digest.db"
    return f"sqlite:///{db_path}"


def get_engine() -> Engine:
    """Get or create the database engine."""
    global _engine

    if _engine is None:
        database_url = get_database_url()
        logger.info(f"Creating database engine for: {database_url}")

        # SQLite-specific configuration
        if database_url.startswith("sqlite"):
            _engine = create_engine(
                database_url,
                poolclass=StaticPool,
                connect_args={
                    "check_same_thread": False,  # Allow multiple threads
                    "timeout": 20,  # 20 second timeout
                },
                echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
            )
        else:
            # PostgreSQL or other databases
            _engine = create_engine(
                database_url,
                echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
            )

    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory."""
    global _SessionLocal

    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    return _SessionLocal


def get_session() -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup."""
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        logger.error(f"Database session error: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize the database by creating all tables."""
    logger.info("Initializing database...")
    engine = get_engine()

    # Create all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized successfully")


def reset_db() -> None:
    """Reset the database by dropping and recreating all tables."""
    logger.warning("Resetting database - all data will be lost!")
    engine = get_engine()

    # Drop all tables
    Base.metadata.drop_all(bind=engine)

    # Recreate tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database reset completed")


def get_db_stats() -> dict:
    """Get basic statistics about the database."""
    from .models import Book, Highlight, SyncStatus, Tag

    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        stats = {
            "books": session.query(Book).count(),
            "highlights": session.query(Highlight).count(),
            "tags": session.query(Tag).count(),
            "sync_records": session.query(SyncStatus).count(),
        }

        # Get last sync info
        last_sync = (
            session.query(SyncStatus)
            .filter(
                SyncStatus.status == "completed",
            )
            .order_by(SyncStatus.completed_at.desc())
            .first()
        )

        if last_sync:
            stats["last_sync"] = {
                "completed_at": last_sync.completed_at,
                "type": last_sync.sync_type,
                "highlights_synced": last_sync.highlights_synced,
                "books_synced": last_sync.books_synced,
            }
        else:
            stats["last_sync"] = None

    return stats
