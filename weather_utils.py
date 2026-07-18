"""Helpers for turning raw Open-Meteo weather codes into human-friendly text."""

# WMO weather codes -> (description, emoji)
_CONDITIONS = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),

    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),

    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Dense drizzle", "🌧️"),
    56: ("Light freezing drizzle", "🌧️"),
    57: ("Dense freezing drizzle", "🌧️"),

    61: ("Slight rain", "🌧️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Light freezing rain", "🌧️"),
    67: ("Heavy freezing rain", "🌧️"),

    71: ("Slight snow", "🌨️"),
    73: ("Snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "❄️"),

    80: ("Slight rain showers", "🌦️"),
    81: ("Rain showers", "🌧️"),
    82: ("Violent rain showers", "⛈️"),

    85: ("Slight snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),

    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with hail", "⛈️"),
    99: ("Thunderstorm with heavy hail", "⛈️"),
}


def get_condition(code):
    """Return just the text description (kept for backwards compatibility)."""
    description, _ = _CONDITIONS.get(code, ("Unknown", "❓"))
    return description


def get_condition_full(code):
    """Return (description, emoji) for a weather code."""
    return _CONDITIONS.get(code, ("Unknown", "❓"))


def get_condition_color(code):
    """Return an accent color that roughly matches the condition, for UI theming."""
    if code == 0:
        return "#F5A623"        # sunny gold
    if code in (1, 2):
        return "#5DADE2"        # soft blue sky
    if code == 3:
        return "#8395A7"        # grey overcast
    if code in (45, 48):
        return "#A9B4BC"        # foggy grey
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "#3498DB"        # rain blue
    if code in (71, 73, 75, 77, 85, 86):
        return "#AED6F1"        # snow pale blue
    if code in (95, 96, 99):
        return "#8E44AD"        # storm purple
    return "#5DADE2"