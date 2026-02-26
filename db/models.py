"""SQLAlchemy ORM models for sessions and messages."""

from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import Column, String, DateTime, Boolean, JSON, Integer, ForeignKey, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class SessionRecord(Base):
    """Database model for conversation sessions."""
    
    __tablename__ = "sessions"
    
    id = Column(String(255), primary_key=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    expires_at = Column(DateTime, default=None, index=True)
    is_active = Column(Boolean, default=True, index=True)
    metadata_json = Column(JSON, default={})
    
    # Relationships
    messages = relationship("MessageRecord", cascade="all, delete-orphan", back_populates="session")
    
    def __repr__(self):
        return f"<SessionRecord(id={self.id}, created_at={self.created_at}, is_active={self.is_active})>"
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def reset_ttl(self, ttl_days: int = 7) -> None:
        """Reset TTL - extends expiration by ttl_days."""
        self.expires_at = datetime.utcnow() + timedelta(days=ttl_days)
        self.updated_at = datetime.utcnow()


class MessageRecord(Base):
    """Database model for conversation messages."""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False, index=True)  # 'user', 'assistant', 'tool', 'system'
    content = Column(Text, nullable=False)
    tool_call_id = Column(String(255), nullable=True)  # For tool messages only
    additional_kwargs_json = Column(JSON, default={})  # For storing AIMessage metadata
    sequence_order = Column(Integer, nullable=False)  # Message order in conversation
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    session = relationship("SessionRecord", back_populates="messages")
    
    # Compound index for efficient session message retrieval and ordering
    __table_args__ = (
        Index("idx_session_sequence", "session_id", "sequence_order"),
    )
    
    def __repr__(self):
        return f"<MessageRecord(id={self.id}, session_id={self.session_id}, role={self.role}, seq={self.sequence_order})>"
