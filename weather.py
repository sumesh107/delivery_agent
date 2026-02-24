
import requests
from typing import Optional

def fetch_weather(latitude: float, longitude: float, units: Optional[str] = None) -> str:
	params = {
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
		params["temperature_unit"] = normalized

	try:
		response = requests.get(
			"https://api.open-meteo.com/v1/forecast",
			params=params,
			timeout=10,
		)
		response.raise_for_status()
	except requests.RequestException as exc:
		return f"Weather lookup failed: {exc}"

	data = response.json()
	current = data.get("current_weather") or {}

	parts = []
	temperature = current.get("temperature")
	windspeed = current.get("windspeed")
	weather_code = current.get("weathercode")
	timestamp = current.get("time")

	if temperature is not None:
		parts.append(f"temperature: {temperature}")
	if windspeed is not None:
		parts.append(f"wind: {windspeed}")
	if weather_code is not None:
		parts.append(f"weathercode: {weather_code}")
	if timestamp:
		parts.append(f"time: {timestamp}")

	if not parts:
		return "No weather data available."

	return "Current weather - " + ", ".join(parts)
