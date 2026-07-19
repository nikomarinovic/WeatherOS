"""Maps raw Open-Meteo weather codes (and AQI values) to display data.

No emoji anywhere - conditions resolve to an `icon` key that icons.py
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

# icon_key -> whole-app background tint, matched to the accent above but
# kept light/desaturated enough that text and white cards stay readable
_BACKGROUNDS = {
    "sun": "#FBF2DE",
    "cloud": "#EEECFB",
    "fog": "#E7ECF1",
    "rain": "#E3EDFB",
    "snow": "#E9F5FB",
    "storm": "#E4E0F4",
}

# (max_aqi_inclusive, label, color) - US AQI scale, ordered low to high
_AQI_TIERS = [
    (50, "Good", "#8FD19E"),
    (100, "Moderate", "#F4E285"),
    (150, "Unhealthy (Sensitive)", "#F3B562"),
    (200, "Unhealthy", "#E88B8B"),
    (300, "Very Unhealthy", "#B39DDB"),
    (500, "Hazardous", "#A9718E"),
]


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


def get_condition_bg(code):
    """Return the whole-app background tint hex color for a weather code."""
    _, icon_key = _CONDITIONS.get(code, ("Unknown", "cloud"))
    return _BACKGROUNDS.get(icon_key, "#EEECFB")


def get_aqi_info(aqi):
    """Return (label, color) for a US AQI value."""
    if aqi is None:
        return "Unknown", "#C7CDDB"
    for ceiling, label, color in _AQI_TIERS:
        if aqi <= ceiling:
            return label, color
    return "Hazardous", "#A9718E"


def format_day_label(iso_date, index):
    """'2026-07-20' -> 'Today' / 'Tomorrow' / 'Mon'."""
    if index == 0:
        return "Today"
    if index == 1:
        return "Tomorrow"
    import datetime
    try:
        d = datetime.date.fromisoformat(iso_date)
        return d.strftime("%a")
    except ValueError:
        return iso_date