import json
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from config import get_env


def _normalize_transport(value: str | None) -> str:
    normalized = (value or "http").strip().lower()
    if normalized == "streamable-http":
        return "streamable_http"
    return normalized


def _load_mcp_connections() -> dict[str, Any]:
    raw = get_env("MCP_SERVERS_JSON")
    if raw:
        data = json.loads(raw)
        connections: dict[str, Any] = {}
        for item in data:
            name = item.get("name")
            if not name:
                continue
            connections[name] = {
                "url": item.get("url"),
                "transport": item.get("transport", "http"),
            }
        if connections:
            return connections

    base_url = (get_env("MCP_BASE_URL", "http://127.0.0.1:8000") or "").rstrip("/")
    transport = _normalize_transport(get_env("MCP_TRANSPORT", "http"))

    if base_url.lower().endswith("/mcp"):
        return {
            "weather": {
                "url": base_url,
                "transport": "http",
            }
        }

    if base_url.lower().endswith("/sse"):
        return {
            "weather": {
                "url": base_url,
                "transport": "sse",
            }
        }

    path = "/mcp" if transport in ("http", "streamable_http") else "/sse"
    return {
        "weather": {
            "url": f"{base_url}{path}",
            "transport": transport,
        }
    }


def build_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(_load_mcp_connections())
