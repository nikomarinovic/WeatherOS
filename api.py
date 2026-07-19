"""Thin client around the free Open-Meteo geocoding + forecast APIs."""

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

REQUEST_TIMEOUT = 8  # seconds


class WeatherAPIError(Exception):
    """Raised when we can't reach Open-Meteo or it returns something unexpected."""


def get_coordinates(city):
    """Look up a city name and return its coordinates, or None if not found."""
    if not city or not city.strip():
        return None

    params = {
        "name": city.strip(),
        "count": 1,
        "language": "en",
        "format": "json",
    }

    try:
        response = requests.get(GEOCODING_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise WeatherAPIError("Request timed out.")
    except requests.exceptions.ConnectionError:
        raise WeatherAPIError("No connection.")
    except requests.exceptions.RequestException:
        raise WeatherAPIError("City lookup failed.")

    data = response.json()
    results = data.get("results")

    if not results:
        return None

    location = results[0]

    return {
        "name": location["name"],
        "country": location.get("country", ""),
        "latitude": location["latitude"],
        "longitude": location["longitude"],
    }


def get_weather(latitude, longitude):
    """Fetch current conditions plus sunrise/sunset/UV/pressure for a coordinate pair."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                   "wind_speed_10m,weather_code,uv_index,surface_pressure",
        "daily": "sunrise,sunset",
        "timezone": "auto",
    }

    try:
        response = requests.get(FORECAST_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise WeatherAPIError("Request timed out.")
    except requests.exceptions.ConnectionError:
        raise WeatherAPIError("No connection.")
    except requests.exceptions.RequestException:
        raise WeatherAPIError("Forecast fetch failed.")

    data = response.json()

    try:
        current = data["current"]
        daily = data.get("daily", {})

        sunrise_raw = daily.get("sunrise", [None])[0]
        sunset_raw = daily.get("sunset", [None])[0]

        return {
            "temperature": round(current["temperature_2m"]),
            "feels_like": round(current["apparent_temperature"]),
            "humidity": round(current["relative_humidity_2m"]),
            "wind": round(current["wind_speed_10m"]),
            "weathercode": current["weather_code"],
            "uv_index": round(current.get("uv_index", 0), 1),
            "pressure": round(current.get("surface_pressure", 0)),
            "sunrise": _format_time(sunrise_raw),
            "sunset": _format_time(sunset_raw),
        }
    except (KeyError, TypeError):
        raise WeatherAPIError("Unexpected response from weather service.")


def _format_time(iso_string):
    """'2026-07-19T05:52' -> '05:52'. Returns '--:--' if missing/malformed."""
    if not iso_string or "T" not in iso_string:
        return "--:--"
    return iso_string.split("T")[1]