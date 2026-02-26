
from langchain_core.messages import BaseMessage, ToolMessage
from typing import Any

def serialize_message(message: BaseMessage) -> dict[str, Any]:
	role_map = {
		"human": "user",
		"ai": "assistant",
		"system": "system",
		"tool": "tool",
	}
	role = role_map.get(message.type, message.type)
	payload = {"role": role, "content": message.content}
	if isinstance(message, ToolMessage):
		payload["tool_call_id"] = message.tool_call_id
	return payload
