import os
from pathlib import Path
from traceback import format_exception
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

from debug_callbacks import DebugCallbackHandler
from graph import build_graph
from llm import build_llm
from mcp_client import build_mcp_client
from odata_tools import get_odata_tools
from serialization import serialize_message


app = FastAPI()
ROOT_DIR = Path(__file__).resolve().parent


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    messages: list[dict[str, Any]]


sessions: Dict[str, list[BaseMessage]] = {}


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
async def chat(request: ChatRequest) -> ChatResponse:
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
    sessions[request.session_id] = updated_messages

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
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/chat-ui")
async def chat_ui() -> FileResponse:
    return FileResponse(ROOT_DIR / "chat_ui.html")


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

