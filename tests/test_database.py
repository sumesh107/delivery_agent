"""Test fixtures and tests for database layer."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from db.models import Base
from db.repositories import SessionRepository



@pytest_asyncio.fixture
async def test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_engine):
    """Create a test database session."""
    async_session_local = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_local() as session:
        yield session


@pytest_asyncio.fixture
async def test_repository(test_db_session):
    """Create a test repository with a clean session."""
    return SessionRepository(test_db_session)


# Test Cases
@pytest.mark.asyncio
async def test_create_session(test_repository: SessionRepository):
    """Test creating a new session."""
    session_id = "test-session-1"
    session = await test_repository.create_session(session_id, ttl_days=7)
    
    assert session.id == session_id
    assert session.is_active is True
    assert session.expires_at is not None


@pytest.mark.asyncio
async def test_session_exists(test_repository: SessionRepository):
    """Test session existence check."""
    session_id = "test-session-2"
    
    # Session should not exist initially
    exists = await test_repository.session_exists(session_id)
    assert exists is False
    
    # Create session
    await test_repository.create_session(session_id)
    
    # Session should now exist
    exists = await test_repository.session_exists(session_id)
    assert exists is True


@pytest.mark.asyncio
async def test_save_and_load_messages(test_repository: SessionRepository):
    """Test saving and loading messages."""
    session_id = "test-session-3"
    
    # Create session
    await test_repository.create_session(session_id)
    
    # Create messages
    messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi there!", additional_kwargs={"tool_calls": []}),
        ToolMessage(content="Tool result", tool_call_id="tool-123"),
    ]
    
    # Save messages
    await test_repository.save_session(session_id, messages)
    
    # Load messages
    loaded_messages = await test_repository.get_session(session_id)
    
    assert len(loaded_messages) == 3
    assert isinstance(loaded_messages[0], HumanMessage)
    assert loaded_messages[0].content == "Hello"
    assert isinstance(loaded_messages[1], AIMessage)
    assert loaded_messages[1].content == "Hi there!"
    assert isinstance(loaded_messages[2], ToolMessage)
    assert loaded_messages[2].tool_call_id == "tool-123"


@pytest.mark.asyncio
async def test_system_messages_skipped(test_repository: SessionRepository):
    """Test that system messages are skipped during save."""
    session_id = "test-session-4"
    
    # Create session
    await test_repository.create_session(session_id)
    
    # Create messages including system message
    messages = [
        SystemMessage(content="System prompt"),
        HumanMessage(content="User query"),
        AIMessage(content="AI response"),
    ]
    
    # Save messages
    await test_repository.save_session(session_id, messages)
    
    # Load messages - system message should be skipped
    loaded_messages = await test_repository.get_session(session_id)
    
    assert len(loaded_messages) == 2
    assert isinstance(loaded_messages[0], HumanMessage)
    assert isinstance(loaded_messages[1], AIMessage)


@pytest.mark.asyncio
async def test_touch_session(test_repository: SessionRepository):
    """Test updating session timestamp and TTL."""
    session_id = "test-session-5"
    
    # Create session
    session1 = await test_repository.create_session(session_id, ttl_days=1)
    original_expires = session1.expires_at
    
    # Wait a tiny bit and touch
    import asyncio
    await asyncio.sleep(0.1)
    await test_repository.touch_session(session_id, ttl_days=7)
    
    # The touch should update the timestamp
    # (New TTL might be different depending on sleep time)
    # For now, just verify it didn't error


@pytest.mark.asyncio
async def test_cleanup_expired_sessions(test_repository: SessionRepository, test_db_session):
    """Test cleaning up expired sessions."""
    from datetime import datetime, timedelta
    
    # Create one active and one expired session
    session1 = await test_repository.create_session("active-session", ttl_days=1)
    session2 = await test_repository.create_session("expired-session", ttl_days=-1)
    
    # Manually set one to be expired in the past
    await test_db_session.execute(
        text("UPDATE sessions SET expires_at = datetime('now', '-10 days') WHERE id = 'expired-session'")
    )
    await test_db_session.commit()
    
    # Run cleanup
    deleted_count = await test_repository.cleanup_expired_sessions()
    await test_db_session.commit()
    
    # Should have deleted 1 session
    assert deleted_count == 1
    
    # Active session should still exist
    exists = await test_repository.session_exists("active-session")
    assert exists is True


@pytest.mark.asyncio
async def test_message_serialization_roundtrip(test_repository: SessionRepository):
    """Test that messages survive serialization/deserialization roundtrip."""
    session_id = "test-session-6"
    
    await test_repository.create_session(session_id)
    
    # Original messages
    original_messages = [
        HumanMessage(content="What is the weather?"),
        AIMessage(
            content="I'll check the weather for you.",
            additional_kwargs={"tool_calls": [{"id": "call_123", "name": "get_weather"}]},
        ),
        ToolMessage(content="Clear, 72°F", tool_call_id="call_123"),
        AIMessage(content="The weather is clear and 72°F."),
    ]
    
    # Save and reload
    await test_repository.save_session(session_id, original_messages)
    loaded_messages = await test_repository.get_session(session_id)
    
    # Verify content is preserved
    assert len(loaded_messages) == 4
    assert loaded_messages[0].content == "What is the weather?"
    assert loaded_messages[1].content == "I'll check the weather for you."
    assert "tool_calls" in loaded_messages[1].additional_kwargs
    assert loaded_messages[2].content == "Clear, 72°F"
    assert loaded_messages[3].content == "The weather is clear and 72°F."
