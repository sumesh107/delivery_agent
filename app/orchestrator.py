import os
from pathlib import Path
from traceback import format_exception
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.debug_callbacks import DebugCallbackHandler
from core.graph import build_graph
from core.llm import build_llm
from core.serialization import serialize_message
from core.config import is_db_enabled, get_session_ttl_days
from db.database import init_db, close_db, get_session as get_db_session
from db.repositories import SessionRepository
from mcp_services.client import build_mcp_client
from tools.odata_tools import get_odata_tools



app = FastAPI()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    messages: list[dict[str, Any]]


sessions: Dict[str, list[BaseMessage]] = {}


@app.on_event("startup")
async def startup() -> None:
    """Initialize database on app startup."""
    if is_db_enabled():
        try:
            await init_db()
            print("✓ Database initialized successfully")
        except Exception as e:
            print(f"⚠ Database initialization failed: {e}")
            print("⚠ Falling back to in-memory sessions")


@app.on_event("shutdown")
async def shutdown() -> None:
    """Close database on app shutdown."""
    if is_db_enabled():
        try:
            await close_db()
            print("✓ Database closed successfully")
        except Exception as e:
            print(f"⚠ Database shutdown error: {e}")



async def _get_workflow() -> Any:
    if hasattr(app.state, "workflow"):
        return app.state.workflow

    mcp_client = build_mcp_client()
    mcp_tools = await mcp_client.get_tools()
    tools = get_odata_tools() + mcp_tools

    callbacks = [DebugCallbackHandler()] if os.getenv("ORCH_DEBUG", "0") == "1" else None
    checkpointer = InMemorySaver()
    workflow = build_graph(build_llm(), tools, callbacks=callbacks).compile(checkpointer=checkpointer)
    app.state.workflow = workflow
    return workflow


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Optional[AsyncSession] = Depends(get_db_session)) -> ChatResponse:
    """Process a chat message with optional database persistence."""
    # Load session history (try DB first, then fallback to Dict)
    history: list[BaseMessage] = []
    
    if is_db_enabled() and db is not None:
        try:
            repository = SessionRepository(db)
            if await repository.session_exists(request.session_id):
                history = await repository.get_session(request.session_id)
            else:
                # Create new session in DB
                await repository.create_session(
                    request.session_id,
                    ttl_days=get_session_ttl_days()
                )
                await db.commit()
        except Exception as e:
            print(f"⚠ Failed to load session from DB: {e}")
            # Fallback to in-memory sessions
            history = sessions.get(request.session_id, [])
    else:
        history = sessions.get(request.session_id, [])
    
    messages = _coerce_messages(history)
    messages.append(HumanMessage(content=request.message))

    try:
        workflow = await _get_workflow()
        result = await workflow.ainvoke(
            {"messages": messages},
            config={"configurable": {"thread_id": request.session_id}},
        )
    except Exception as exc:
        detail = _format_exception(exc)
        raise HTTPException(status_code=500, detail=detail) from exc

    updated_messages = _coerce_messages(result["messages"])
    
    # Dual-write to both Dict and DB (for backward compatibility and resilience)
    sessions[request.session_id] = updated_messages
    
    if is_db_enabled() and db is not None:
        try:
            repository = SessionRepository(db)
            await repository.save_session(request.session_id, updated_messages)
            await repository.touch_session(
                request.session_id,
                ttl_days=get_session_ttl_days()
            )
            await db.commit()
        except Exception as e:
            print(f"⚠ Failed to save session to DB: {e}")
            # Session still in Dict, so not a critical failure

    reply = ""
    for message in reversed(updated_messages):
        if isinstance(message, AIMessage):
            reply = message.content or ""
            break

    if not reply:
        for message in reversed(updated_messages):
            if isinstance(message, ToolMessage):
                reply = message.content or ""
                break

    serialized = [serialize_message(message) for message in updated_messages]
    return ChatResponse(session_id=request.session_id, reply=reply, messages=serialized)


@app.get("/health")
async def health(db: Optional[AsyncSession] = Depends(get_db_session)) -> dict[str, Any]:
    """Health check including database connectivity."""
    health_status: dict[str, Any] = {"status": "ok"}
    
    if is_db_enabled() and db is not None:
        try:
            repository = SessionRepository(db)
            # Simple connectivity test
            await db.execute("SELECT 1")
            health_status["database"] = "connected"
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
    else:
        health_status["database"] = "disabled"
    
    return health_status


@app.get("/chat-ui")
async def chat_ui() -> FileResponse:
    return FileResponse(PROJECT_ROOT / "chat_ui.html")


def _format_exception(exc: Exception) -> str:
    debug = os.getenv("ORCH_DEBUG", "0") == "1"
    if isinstance(exc, ExceptionGroup):
        messages = []
        for child in exc.exceptions:
            messages.append(_format_exception(child))
        return " | ".join(messages)
    if debug:
        return "".join(format_exception(exc))
    return str(exc)


def _coerce_messages(items: list[Any]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in items:
        if isinstance(item, BaseMessage):
            messages.append(item)
            continue
        if not isinstance(item, dict):
            continue
        role = item.get("role") or item.get("type")
        content = item.get("content") or ""
        if role in ("user", "human"):
            messages.append(HumanMessage(content=content))
        elif role in ("assistant", "ai"):
            messages.append(AIMessage(content=content, additional_kwargs=item.get("additional_kwargs", {})))
        elif role == "system":
            messages.append(SystemMessage(content=content))
        elif role == "tool":
            tool_call_id = item.get("tool_call_id") or "unknown"
            messages.append(ToolMessage(content=content, tool_call_id=tool_call_id))
    return messages

