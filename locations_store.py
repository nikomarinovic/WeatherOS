"""Tiny JSON-file persistence for the user's saved locations.

Lives at ~/.weatheros/locations.json. Failures here are non-fatal -
saved locations are a convenience, not something worth crashing over.
"""

import json
from pathlib import Path

STORE_PATH = Path.home() / ".weatheros" / "locations.json"


def load_locations():
    try:
        if STORE_PATH.exists():
            return json.loads(STORE_PATH.read_text())
    except Exception:
        pass
    return []


def save_locations(locations):
    try:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STORE_PATH.write_text(json.dumps(locations, indent=2))
    except Exception:
        pass


def _key(location):
    return (location.get("name", ""), location.get("country", ""))


def add_location(locations, location):
    """Append a location if it's not already saved. Returns the new list."""
    if not any(_key(loc) == _key(location) for loc in locations):
        locations = locations + [location]
        save_locations(locations)
    return locations


def remove_location(locations, location):
    """Remove a location by (name, country). Returns the new list."""
    locations = [loc for loc in locations if _key(loc) != _key(location)]
    save_locations(locations)
    return locations


def contains(locations, location):
    return any(_key(loc) == _key(location) for loc in locations)