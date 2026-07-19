"""Maps raw Open-Meteo weather codes to display data for WeatherOS.

No emoji anywhere — conditions resolve to an `icon` key that icons.py
draws on a Canvas, plus a soft pastel accent color.
"""

# code -> (label, icon_key)
_CONDITIONS = {
    0: ("Clear sky", "sun"),
    1: ("Mostly clear", "sun"),
    2: ("Partly cloudy", "cloud"),
    3: ("Overcast", "cloud"),

    45: ("Foggy", "fog"),
    48: ("Freezing fog", "fog"),

    51: ("Light drizzle", "rain"),
    53: ("Drizzle", "rain"),
    55: ("Dense drizzle", "rain"),
    56: ("Freezing drizzle", "rain"),
    57: ("Freezing drizzle", "rain"),

    61: ("Light rain", "rain"),
    63: ("Rain", "rain"),
    65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "rain"),
    67: ("Heavy freezing rain", "rain"),

    71: ("Light snow", "snow"),
    73: ("Snow", "snow"),
    75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"),

    80: ("Rain showers", "rain"),
    81: ("Heavy showers", "rain"),
    82: ("Violent showers", "storm"),

    85: ("Snow showers", "snow"),
    86: ("Heavy snow showers", "snow"),

    95: ("Thunderstorm", "storm"),
    96: ("Storm with hail", "storm"),
    99: ("Severe storm", "storm"),
}

# icon_key -> soft pastel accent color (calm, premium palette)
_ACCENTS = {
    "sun": "#FFD98E",
    "cloud": "#C7CDDB",
    "fog": "#B9C4D6",
    "rain": "#8EC5FF",
    "snow": "#B9E4F5",
    "storm": "#B39DDB",
}


def get_condition(code):
    label, _ = _CONDITIONS.get(code, ("Unknown", "cloud"))
    return label


def get_condition_full(code):
    """Return (label, icon_key) for a weather code."""
    return _CONDITIONS.get(code, ("Unknown", "cloud"))


def get_condition_color(code):
    """Return a soft pastel accent hex color for a weather code."""
    _, icon_key = _CONDITIONS.get(code, ("Unknown", "cloud"))
    return _ACCENTS.get(icon_key, "#C7CDDB")
