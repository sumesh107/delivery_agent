import os
from typing import Optional

from fastmcp import FastMCP

os.environ.setdefault("FASTMCP_HOST", "127.0.0.1")
os.environ.setdefault("FASTMCP_PORT", "8000")

try:
    mcp = FastMCP("WeatherServer", host="127.0.0.1", port=8000)
except TypeError:
    mcp = FastMCP("WeatherServer")

try:
    from .weather import fetch_weather
except ImportError:  # Fallback when running as a script
    from mcp_services.weather import fetch_weather

@mcp.tool()
async def get_weather(latitude: float, longitude: float, units: Optional[str] = None) -> str:
    return fetch_weather(latitude, longitude, units)


if __name__ == "__main__":
    try:
        mcp.run(transport="streamable-http")
    except ValueError:
        mcp.run(transport="sse")
