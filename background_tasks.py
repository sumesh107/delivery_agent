"""Background tasks for session management (cleanup, etc)."""

import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from config import is_db_enabled, get_session_ttl_days
from database import async_session_maker
from repositories import SessionRepository

logger = logging.getLogger(__name__)


async def cleanup_expired_sessions() -> dict:
    """
    Clean up expired sessions from database.
    Returns dict with cleanup statistics.
    """
    if not is_db_enabled():
        return {"status": "disabled", "deleted_count": 0}
    
    if async_session_maker is None:
        logger.warning("Database not initialized for cleanup task")
        return {"status": "error", "message": "Database not initialized", "deleted_count": 0}
    
    try:
        async with async_session_maker() as session:
            repository = SessionRepository(session)
            deleted_count = await repository.cleanup_expired_sessions()
            await session.commit()
            
            logger.info(f"Cleanup job completed: deleted {deleted_count} expired sessions")
            return {
                "status": "success",
                "deleted_count": deleted_count,
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        logger.error(f"Cleanup job failed: {e}")
        return {
            "status": "error",
            "message": str(e),
            "deleted_count": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }


async def get_expired_sessions_info() -> dict:
    """
    Get list of sessions that are about to expire (for monitoring).
    Returns dict with session IDs and expiration times.
    """
    if not is_db_enabled():
        return {"status": "disabled", "sessions": []}
    
    if async_session_maker is None:
        logger.warning("Database not initialized for monitoring")
        return {"status": "error", "message": "Database not initialized", "sessions": []}
    
    try:
        async with async_session_maker() as session:
            repository = SessionRepository(session)
            expired_sessions = await repository.get_all_expired_sessions()
            
            return {
                "status": "success",
                "expired_session_count": len(expired_sessions) if expired_sessions else 0,
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        logger.error(f"Failed to get expired sessions info: {e}")
        return {
            "status": "error",
            "message": str(e),
            "sessions": [],
        }


# Optional: Scheduled cleanup using APScheduler
async def start_cleanup_scheduler(app) -> None:
    """
    Start a background scheduler for periodic cleanup.
    This should be called at app startup.
    
    Requires: pip install apscheduler
    """
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        
        scheduler = AsyncIOScheduler()
        
        # Schedule cleanup to run daily at 2 AM
        scheduler.add_job(
            cleanup_expired_sessions,
            "cron",
            hour=2,
            minute=0,
            job_id="cleanup_expired_sessions",
        )
        
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("✓ Cleanup scheduler started (daily at 2 AM)")
        
    except ImportError:
        logger.warning(
            "APScheduler not installed. Install with: pip install apscheduler"
        )
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


async def stop_cleanup_scheduler(app) -> None:
    """Stop the background scheduler.
    This should be called at app shutdown.
    """
    if hasattr(app.state, "scheduler"):
        try:
            app.state.scheduler.shutdown()
            logger.info("✓ Cleanup scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
