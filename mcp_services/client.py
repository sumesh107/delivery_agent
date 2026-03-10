import json
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from core.config import get_env


def _load_mcp_connections() -> dict[str, Any]:
    """Load MCP server connections from environment configuration."""
    # If explicit JSON config provided, use it
    raw = get_env("MCP_SERVERS_JSON")
    if raw:
        return {
            item["name"]: {"url": item["url"], "transport": item.get("transport", "http")}
            for item in json.loads(raw)
            if item.get("name")
        }

    # Simple default configuration
    base_url = get_env("MCP_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    transport = get_env("MCP_TRANSPORT", "http")

    # Normalize transport name
    if transport == "streamable-http":
        transport = "streamable_http"

    # Determine path based on transport
    path = "/mcp" if transport in ("http", "streamable_http") else "/sse"

    return {
        "weather": {
            "url": f"{base_url}{path}",
            "transport": transport,
        }
    }


def build_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(_load_mcp_connections())
