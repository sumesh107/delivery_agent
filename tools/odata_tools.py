from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional
import json

import httpx
from langchain_core.tools import tool

from core.config import get_env


def _odata_base() -> str:
    return get_env("ODATA_BASE_URL", "http://127.0.0.1:4004/odata/v4")


def _weather_api_base() -> str:
    return get_env("WEATHER_API_URL", "https://api.open-meteo.com/v1/forecast")


def _weather_category(weather_code: Optional[int], windspeed: Optional[float]) -> str:
    if windspeed is not None and windspeed >= 15:
        return "Wind"
    if weather_code is None:
        return "Unknown"
    if weather_code == 0:
        return "Clear"
    if weather_code in (1, 2, 3):
        return "Cloudy"
    if weather_code in (45, 48):
        return "Fog"
    if weather_code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "Rain"
    if weather_code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if weather_code in (95, 96, 99):
        return "Storm"
    return "Unknown"


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _build_date_suggestion(delivery_date: Optional[str], category: str) -> dict[str, Any]:
    base_date = _parse_iso_date(delivery_date)
    if not base_date:
        return {
            "proposed_delivery_date": None,
            "delay_days": None,
            "note": "DeliveryDate is missing or invalid; cannot compute a suggested change.",
        }

    if category in ("Storm", "Snow"):
        delay_days = 2
    elif category in ("Rain", "Fog", "Wind"):
        delay_days = 1
    else:
        delay_days = 0

    proposed_date = base_date + timedelta(days=delay_days)
    return {
        "proposed_delivery_date": proposed_date.isoformat(),
        "delay_days": delay_days,
        "note": "No change suggested." if delay_days == 0 else "Delay suggested due to conditions.",
    }


def _trim_sales_orders_payload(payload: dict[str, Any], limit: int) -> str:
    items = payload.get("value")
    if isinstance(items, list) and limit > 0:
        payload = dict(payload)
        payload["value"] = items[:limit]
        payload["note"] = f"Showing first {limit} sales orders."
    return json.dumps(payload, indent=2)


@tool
async def list_sales_orders(limit: int = 3) -> str:
    """List sales orders from the OData service, defaulting to the first 3."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{_odata_base()}/SalesOrders")
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError:
            return response.text
        return _trim_sales_orders_payload(payload, limit)


@tool
async def get_sales_order(sales_order_id: str) -> str:
    """Fetch a single sales order by ID from the OData service."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(f"{_odata_base()}/SalesOrders/{sales_order_id}")
        response.raise_for_status()
        return response.text


@tool
async def update_sales_order(
    sales_order_id: str,
    updates: Optional[dict[str, Any]] = None,
    Customer: Optional[str] = None,
    OrderDate: Optional[str] = None,
    DeliveryDate: Optional[str] = None,
    Status: Optional[str] = None,
    Weather: Optional[str] = None,
) -> str:
    """Update a sales order by ID. Use only after a human confirms the change."""
    payload: dict[str, Any] = dict(updates or {})
    if Customer is not None:
        payload["Customer"] = Customer
    if OrderDate is not None:
        payload["OrderDate"] = OrderDate
    if DeliveryDate is not None:
        payload["DeliveryDate"] = DeliveryDate
    if Status is not None:
        payload["Status"] = Status
    if Weather is not None:
        payload["Weather"] = Weather

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.patch(
            f"{_odata_base()}/SalesOrders/{sales_order_id}",
            json=payload,
        )
        response.raise_for_status()
        return response.text


@tool
async def suggest_delivery_change(
    sales_order_id: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    units: Optional[str] = None,
) -> str:
    """Suggest delivery adjustments using live weather data without changing any records."""
    async with httpx.AsyncClient(timeout=10) as client:
        order_response = await client.get(f"{_odata_base()}/SalesOrders/{sales_order_id}")
        order_response.raise_for_status()
        order = order_response.json()

        order_lat = order.get("Latitude")
        order_lon = order.get("Longitude")
        if latitude is None:
            latitude = order_lat
        if longitude is None:
            longitude = order_lon

        if latitude is None or longitude is None:
            return json.dumps(
                {
                    "sales_order_id": sales_order_id,
                    "current_order": order,
                    "error": "Missing latitude/longitude. Provide coordinates or update the order location.",
                },
                indent=2,
            )

        weather_params: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": True,
        }
        if units:
            normalized = units.lower()
            if normalized == "metric":
                normalized = "celsius"
            elif normalized == "imperial":
                normalized = "fahrenheit"
            weather_params["temperature_unit"] = normalized

        weather_response = await client.get(_weather_api_base(), params=weather_params)
        weather_response.raise_for_status()
        weather_data = weather_response.json()

    current_weather = weather_data.get("current_weather") or {}
    temperature = current_weather.get("temperature")
    windspeed = current_weather.get("windspeed")
    weather_code = current_weather.get("weathercode")
    timestamp = current_weather.get("time")

    category = _weather_category(weather_code, windspeed)
    suggestion = _build_date_suggestion(order.get("DeliveryDate"), category)

    proposed_updates = {}
    if suggestion.get("delay_days"):
        proposed_updates = {
            "DeliveryDate": suggestion.get("proposed_delivery_date"),
            "Status": "Planned",
        }

    result = {
        "sales_order_id": sales_order_id,
        "current_order": order,
        "weather_observation": {
            "category": category,
            "temperature": temperature,
            "windspeed": windspeed,
            "weather_code": weather_code,
            "observed_at": timestamp,
            "source": "open-meteo",
        },
        "suggestion": {
            "delay_days": suggestion.get("delay_days"),
            "proposed_delivery_date": suggestion.get("proposed_delivery_date"),
            "note": suggestion.get("note"),
            "proposed_updates": proposed_updates,
            "human_decision_required": True,
        },
        "next_step": "If you approve, call update_sales_order with the proposed_updates.",
    }

    return json.dumps(result, indent=2)


def get_odata_tools() -> list[Any]:
    return [list_sales_orders, get_sales_order, suggest_delivery_change, update_sales_order]
