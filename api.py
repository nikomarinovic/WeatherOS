"""Thin client around the free Open-Meteo (+ IP-geolocation) APIs."""

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

REQUEST_TIMEOUT = 8  # seconds

# A browser-like User-Agent avoids the bot-filtering some free geolocation
# services apply to the default python-requests one.
_UA = {"User-Agent": "Mozilla/5.0 (compatible; WeatherOS/1.0)"}


class WeatherAPIError(Exception):
    """Raised when we can't reach a weather service or it returns something unexpected."""


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


def get_ip_location():
    """Best-effort guess of the user's city from their IP address.

    Free IP-geolocation services are flaky (rate limits, WAFs, corporate
    proxies), so this tries a few independent providers in turn and only
    gives up if all of them fail. Never raises - this is a startup
    convenience, not a hard requirement, and the caller falls back to
    manual search either way.
    """
    for provider in (_ip_from_ipapi_co, _ip_from_ipwho, _ip_from_geojs):
        try:
            location = provider()
            if location:
                return location
        except Exception:
            continue
    return None


def _ip_from_ipapi_co():
    response = requests.get("https://ipapi.co/json/", timeout=REQUEST_TIMEOUT, headers=_UA)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        return None
    city = data.get("city") or data.get("region")
    return _normalize_ip_location(city, data.get("country_name"), data.get("latitude"), data.get("longitude"))


def _ip_from_ipwho():
    response = requests.get("https://ipwho.is/", timeout=REQUEST_TIMEOUT, headers=_UA)
    response.raise_for_status()
    data = response.json()
    if data.get("success") is False:
        return None
    return _normalize_ip_location(data.get("city"), data.get("country"), data.get("latitude"), data.get("longitude"))


def _ip_from_geojs():
    response = requests.get("https://get.geojs.io/v1/ip/geo.json", timeout=REQUEST_TIMEOUT, headers=_UA)
    response.raise_for_status()
    data = response.json()
    city = data.get("city") or data.get("region")
    return _normalize_ip_location(city, data.get("country"), data.get("latitude"), data.get("longitude"))


def _normalize_ip_location(city, country, latitude, longitude):
    if latitude is None or longitude is None:
        return None
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return None
    return {
        "name": city or "Your location",
        "country": country or "",
        "latitude": latitude,
        "longitude": longitude,
        "is_current_location": True,
    }


def get_weather(latitude, longitude, temperature_unit="celsius", wind_speed_unit="kmh"):
    """Fetch current conditions, next-24h hourly, and a 7-day daily forecast."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                   "wind_speed_10m,weather_code,uv_index,surface_pressure",
        "hourly": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset",
        "forecast_days": 7,
        "temperature_unit": temperature_unit,
        "wind_speed_unit": wind_speed_unit,
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
        hourly = data.get("hourly", {})

        sunrise_raw = daily.get("sunrise", [None])[0]
        sunset_raw = daily.get("sunset", [None])[0]

        return {
            "temperature": round(current["temperature_2m"]),
            "feels_like": round(current["apparent_temperature"]),
            "humidity": round(current["relative_humidity_2m"]),
            "wind": round(current["wind_speed_10m"]),
            "wind_unit": "mph" if wind_speed_unit == "mph" else "km/h",
            "weathercode": current["weather_code"],
            "uv_index": round(current.get("uv_index", 0), 1),
            "pressure": round(current.get("surface_pressure", 0)),
            "sunrise": _format_time(sunrise_raw),
            "sunset": _format_time(sunset_raw),
            "hourly": _build_hourly(hourly),
            "daily": _build_daily(daily),
        }
    except (KeyError, TypeError):
        raise WeatherAPIError("Unexpected response from weather service.")


def _build_hourly(hourly):
    """Return up to the next 24 hourly entries as [{time, temperature, weathercode}]."""
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    codes = hourly.get("weather_code", [])

    import datetime
    now = datetime.datetime.now()

    start = 0
    for i, t in enumerate(times):
        try:
            hour_dt = datetime.datetime.fromisoformat(t)
        except ValueError:
            continue
        if hour_dt >= now.replace(minute=0, second=0, microsecond=0):
            start = i
            break

    entries = []
    for t, temp, code in list(zip(times, temps, codes))[start:start + 24]:
        entries.append({
            "time": t.split("T")[1] if "T" in t else t,
            "temperature": round(temp),
            "weathercode": code,
        })
    return entries


def _build_daily(daily):
    """Return up to 7 daily entries as [{date, weathercode, temp_max, temp_min}]."""
    dates = daily.get("time", [])
    codes = daily.get("weather_code", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])

    entries = []
    for date, code, hi, lo in zip(dates, codes, tmax, tmin):
        entries.append({
            "date": date,
            "weathercode": code,
            "temp_max": round(hi),
            "temp_min": round(lo),
        })
    return entries


def get_air_quality(latitude, longitude):
    """Fetch current US AQI + particulate levels. Returns None on failure
    (air quality is a bonus card, not worth blocking the whole screen on)."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "us_aqi,pm2_5,pm10",
        "timezone": "auto",
    }

    try:
        response = requests.get(AIR_QUALITY_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        current = response.json()["current"]
        return {
            "aqi": round(current["us_aqi"]),
            "pm2_5": round(current.get("pm2_5", 0), 1),
            "pm10": round(current.get("pm10", 0), 1),
        }
    except Exception:
        return None


def _format_time(iso_string):
    """'2026-07-19T05:52' -> '05:52'. Returns '--:--' if missing/malformed."""
    if not iso_string or "T" not in iso_string:
        return "--:--"
    return iso_string.split("T")[1]