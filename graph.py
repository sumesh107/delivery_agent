import json
from typing import Any, Optional

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


def build_graph(
    llm: Any,
    tools: list[Any],
    callbacks: Optional[list[Any]] = None,
    system_prompt: Optional[str] = None,
) -> Any:
    tool_node = ToolNode(tools)
    llm_with_tools = llm.bind_tools(tools)
    system_message = SystemMessage(
        content=system_prompt
        or (
            "You are a delivery operations assistant. "
            "Use tools to answer questions about weather and sales orders. "
            "Call tools when needed, then summarize results clearly. "
            "Use live weather data for recommendations and do not assume conditions. "
            "Only update delivery records after explicit human approval. "
            "If a tool fails or input is missing, explain and ask for clarification."
        )
    )

    async def assistant(state: MessagesState) -> dict[str, Any]:
        config = {"callbacks": callbacks} if callbacks else None
        response = await llm_with_tools.ainvoke([system_message] + state["messages"], config=config)
        return {"messages": [response]}

    def _summarize_tool_content(content: Any) -> str:
        if not content:
            return ""
        payload = None
        if isinstance(content, str):
            try:
                payload = json.loads(content)
            except json.JSONDecodeError:
                payload = None
        elif isinstance(content, (dict, list)):
            payload = content

        if isinstance(payload, dict) and isinstance(payload.get("value"), list):
            items = payload.get("value") or []
            if len(items) > 3:
                payload["value"] = items[:3]
                payload["note"] = "Showing first 3 items from tool output."
            return json.dumps(payload, indent=2)

        if isinstance(payload, list):
            if len(payload) > 3:
                payload = payload[:3]
            return json.dumps(payload, indent=2)

        if isinstance(content, str) and len(content) > 2000:
            return content[:2000] + "\n...truncated..."
        return json.dumps(payload, indent=2) if payload is not None else str(content)

    async def summarize_tools(state: MessagesState) -> dict[str, Any]:
        messages = state.get("messages") or []
        for message in messages:
            if isinstance(message, ToolMessage):
                message.content = _summarize_tool_content(message.content or "")
        return {"messages": []}

    graph = StateGraph(MessagesState)
    graph.add_node("assistant", assistant)
    graph.add_node("tools", tool_node)
    graph.add_node("summarize_tools", summarize_tools)
    graph.add_conditional_edges("assistant", tools_condition)
    graph.add_edge("tools", "summarize_tools")
    graph.add_edge("summarize_tools", "assistant")
    graph.set_entry_point("assistant")
    return graph
