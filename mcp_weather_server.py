import os
import sys
from typing import Optional

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from fastmcp import FastMCP
from weather import fetch_weather

os.environ.setdefault("FASTMCP_HOST", "127.0.0.1")
os.environ.setdefault("FASTMCP_PORT", "8000")

try:
    mcp = FastMCP("WeatherServer", host="127.0.0.1", port=8000)
except TypeError:
    mcp = FastMCP("WeatherServer")

@mcp.tool()
async def get_weather(latitude: float, longitude: float, units: Optional[str] = None) -> str:
    return fetch_weather(latitude, longitude, units)


if __name__ == "__main__":
    try:
        mcp.run(transport="streamable-http")
    except ValueError:
        mcp.run(transport="sse")
