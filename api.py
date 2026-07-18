"""Thin client around the free Open-Meteo geocoding + forecast APIs."""

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

REQUEST_TIMEOUT = 8  # seconds


class WeatherAPIError(Exception):
    """Raised when we can't reach Open-Meteo or it returns something unexpected."""


def get_coordinates(city):
    """Look up a city name and return its coordinates, or None if not found.

    Raises WeatherAPIError on network/timeout problems so the UI can show a
    'no connection' message instead of silently failing.
    """
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
        raise WeatherAPIError("The request timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        raise WeatherAPIError("No internet connection.")
    except requests.exceptions.RequestException:
        raise WeatherAPIError("Something went wrong while searching for that city.")

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
    """Fetch current conditions for a coordinate pair.

    Returns temperature, feels-like temperature, humidity, wind speed and a
    weather code. Raises WeatherAPIError on failure.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                   "wind_speed_10m,weather_code",
        "timezone": "auto",
    }

    try:
        response = requests.get(FORECAST_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise WeatherAPIError("The request timed out. Please try again.")
    except requests.exceptions.ConnectionError:
        raise WeatherAPIError("No internet connection.")
    except requests.exceptions.RequestException:
        raise WeatherAPIError("Something went wrong while fetching the weather.")

    data = response.json()

    try:
        current = data["current"]
        return {
            "temperature": round(current["temperature_2m"]),
            "feels_like": round(current["apparent_temperature"]),
            "humidity": round(current["relative_humidity_2m"]),
            "wind": round(current["wind_speed_10m"]),
            "weathercode": current["weather_code"],
        }
    except (KeyError, TypeError):
        raise WeatherAPIError("Received an unexpected response from the weather service.")