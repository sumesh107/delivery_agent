"""Database initialization and session management."""

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.pool import StaticPool

from config import get_env


# Determine database URL
def get_database_url() -> str:
    """Get database URL from environment or use default SQLite."""
    db_url = get_env("DATABASE_URL")
    if db_url:
        return db_url
    
    # Default to SQLite in repo root
    db_path = os.path.join(os.path.dirname(__file__), "sessions.db")
    return f"sqlite+aiosqlite:///{db_path}"


# Create async engine
def create_engine():
    """Create SQLAlchemy async engine."""
    db_url = get_database_url()
    
    # For SQLite, use StaticPool for testing and simple deployments
    # For production databases, this will be ignored
    if "sqlite" in db_url:
        engine = create_async_engine(
            db_url,
            echo=get_env("SQL_ECHO", "false").lower() == "true",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # PostgreSQL or other databases
        engine = create_async_engine(
            db_url,
            echo=get_env("SQL_ECHO", "false").lower() == "true",
            pool_size=10,
            max_overflow=20,
        )
    
    return engine


# Global engine and session factory (initialized at app startup)
engine = None
async_session_maker: async_sessionmaker = None


async def init_db():
    """Initialize database engine and create tables."""
    global engine, async_session_maker
    
    engine = create_engine()
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Import models to ensure they're registered
    from models import Base
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get DB session."""
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() at app startup.")
    
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def close_db():
    """Close database connections at app shutdown."""
    global engine
    if engine:
        await engine.dispose()


async def health_check() -> bool:
    """Check database connectivity."""
    try:
        async with async_session_maker() as session:
            await session.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database health check failed: {e}")
        return False
