import json
from typing import Any, Optional

import httpx
from fastmcp.client import Client

from config import get_env


class ToolRegistry:
    def __init__(self) -> None:
        self.odata_base = get_env("ODATA_BASE_URL", "http://127.0.0.1:4004/odata/v4")
        self.mcp_base = get_env("MCP_BASE_URL", "http://127.0.0.1:8000")
        self._mcp_tools_cache: Optional[list[dict[str, Any]]] = None
        self._mcp_transport_suffix: Optional[str] = None

    def _mcp_tool_to_openai(self, tool: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": tool.get("name"),
            "description": tool.get("description") or "",
            "parameters": tool.get("inputSchema") or {"type": "object", "properties": {}},
        }

    async def _list_mcp_tools(self) -> list[dict[str, Any]]:
        if self._mcp_tools_cache is not None:
            return self._mcp_tools_cache

        for suffix in ("/mcp", "/sse"):
            try:
                async with Client(f"{self.mcp_base}{suffix}") as client:
                    tools = await client.list_tools()
                self._mcp_transport_suffix = suffix
                self._mcp_tools_cache = [tool.model_dump() for tool in tools]
                return self._mcp_tools_cache
            except Exception:
                continue

        raise RuntimeError("Failed to connect to MCP server.")

    async def get_tool_schemas(self) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": "list_sales_orders",
                    "description": "List all sales orders from the OData service.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_sales_order",
                    "description": "Fetch a single sales order by ID from the OData service.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sales_order_id": {"type": "string"},
                        },
                        "required": ["sales_order_id"],
                    },
                },
            },
        ]

        mcp_tools = await self._list_mcp_tools()
        for tool in mcp_tools:
            tools.append({"type": "function", "function": self._mcp_tool_to_openai(tool)})

        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        if name == "list_sales_orders":
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.odata_base}/SalesOrders")
                response.raise_for_status()
                return response.text

        if name == "get_sales_order":
            order_id = arguments.get("sales_order_id")
            if not order_id:
                raise ValueError("sales_order_id is required")
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.odata_base}/SalesOrders/{order_id}")
                response.raise_for_status()
                return response.text

        suffixes = [self._mcp_transport_suffix] if self._mcp_transport_suffix else []
        suffixes.extend(["/mcp", "/sse"])

        last_error: Optional[Exception] = None
        for suffix in suffixes:
            if not suffix:
                continue
            try:
                async with Client(f"{self.mcp_base}{suffix}") as client:
                    result = await client.call_tool(name, arguments)
                self._mcp_transport_suffix = suffix
                payload = result.data or result.structured_content or result.content
                if isinstance(payload, str):
                    return payload
                return json.dumps(payload)
            except Exception as exc:
                last_error = exc
                continue

        detail = f" ({last_error})" if last_error else ""
        raise RuntimeError(f"Unknown tool or MCP call failed: {name}{detail}")
