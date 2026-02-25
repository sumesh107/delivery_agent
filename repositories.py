"""Repository layer for session and message data access."""

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)

from models import SessionRecord, MessageRecord


class SessionRepository:
    """Data access layer for sessions and messages."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_session(self, session_id: str, ttl_days: int = 7) -> SessionRecord:
        """Create a new session record."""
        session = SessionRecord(
            id=session_id,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=ttl_days),
        )
        self.db.add(session)
        await self.db.flush()
        return session
    
    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists and is active."""
        stmt = select(SessionRecord).where(
            and_(
                SessionRecord.id == session_id,
                SessionRecord.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first() is not None
    
    async def get_session(self, session_id: str) -> List[BaseMessage]:
        """
        Retrieve all messages for a session in order.
        Returns list of LangChain BaseMessage objects.
        """
        stmt = (
            select(MessageRecord)
            .where(MessageRecord.session_id == session_id)
            .order_by(MessageRecord.sequence_order)
        )
        result = await self.db.execute(stmt)
        message_records = result.scalars().all()
        
        # Deserialize to BaseMessage objects
        messages = [self._deserialize_message(record) for record in message_records]
        return messages
    
    async def save_session(self, session_id: str, messages: List[BaseMessage]) -> None:
        """
        Save or update all messages for a session.
        Will replace existing messages for this session.
        """
        # Ensure session exists
        session = await self._get_or_create_session(session_id)
        
        # Delete existing messages for this session (we'll replace them)
        await self.db.execute(
            delete(MessageRecord).where(MessageRecord.session_id == session_id)
        )
        await self.db.flush()
        
        # Insert new messages in order
        for idx, msg in enumerate(messages):
            # Skip system messages - they're added by the workflow at invocation time
            if isinstance(msg, SystemMessage):
                continue
            
            record = self._serialize_message(session_id, msg, sequence_order=idx)
            self.db.add(record)
        
        await self.db.flush()
    
    async def touch_session(self, session_id: str, ttl_days: int = 7) -> None:
        """
        Update session timestamp and reset TTL.
        Called after each interaction to keep session alive.
        """
        stmt = select(SessionRecord).where(SessionRecord.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalars().first()
        
        if session:
            session.updated_at = datetime.utcnow()
            session.expires_at = datetime.utcnow() + timedelta(days=ttl_days)
            await self.db.flush()
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Delete sessions that have expired.
        Returns count of deleted sessions.
        """
        now = datetime.utcnow()
        stmt = delete(SessionRecord).where(
            and_(
                SessionRecord.expires_at < now,
                SessionRecord.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        deleted_count = result.rowcount
        await self.db.flush()
        return deleted_count
    
    async def get_all_expired_sessions(self) -> List[str]:
        """Get list of session IDs that have expired (for monitoring)."""
        now = datetime.utcnow()
        stmt = select(SessionRecord.id).where(
            and_(
                SessionRecord.expires_at < now,
                SessionRecord.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def _get_or_create_session(self, session_id: str, ttl_days: int = 7) -> SessionRecord:
        """Get existing session or create new one."""
        stmt = select(SessionRecord).where(SessionRecord.id == session_id)
        result = await self.db.execute(stmt)
        session = result.scalars().first()
        
        if not session:
            session = await self.create_session(session_id, ttl_days=ttl_days)
        
        return session
    
    def _deserialize_message(self, record: MessageRecord) -> BaseMessage:
        """Convert MessageRecord to LangChain BaseMessage."""
        if record.role == "user":
            return HumanMessage(content=record.content)
        elif record.role == "assistant":
            return AIMessage(
                content=record.content,
                additional_kwargs=record.additional_kwargs_json or {},
            )
        elif record.role == "tool":
            return ToolMessage(
                content=record.content,
                tool_call_id=record.tool_call_id,
            )
        elif record.role == "system":
            return SystemMessage(content=record.content)
        else:
            # Fallback for unknown roles
            return HumanMessage(content=record.content)
    
    def _serialize_message(
        self, session_id: str, message: BaseMessage, sequence_order: int
    ) -> MessageRecord:
        """Convert LangChain BaseMessage to MessageRecord for storage."""
        role = message.type  # 'human', 'ai', 'tool', 'system'
        
        # Normalize role names to table format
        role_map = {
            "human": "user",
            "ai": "assistant",
            "tool": "tool",
            "system": "system",
        }
        role = role_map.get(role, role)
        
        content = message.content if isinstance(message.content, str) else str(message.content)
        tool_call_id = None
        additional_kwargs = {}
        
        if isinstance(message, ToolMessage):
            tool_call_id = message.tool_call_id
        elif isinstance(message, AIMessage):
            additional_kwargs = message.additional_kwargs or {}
        
        return MessageRecord(
            session_id=session_id,
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            additional_kwargs_json=additional_kwargs,
            sequence_order=sequence_order,
        )
