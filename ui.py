import threading

import customtkinter as ctk

from api import get_coordinates, get_weather, WeatherAPIError
from weather_utils import get_condition_full, get_condition_color


# ---- Palette -----------------------------------------------------------
BG_COLOR = "#EAF2FB"
CARD_COLOR = "#FFFFFF"
TEXT_MAIN = "#1B2431"
TEXT_MUTED = "#6B7684"
ACCENT = "#3E7BFA"
ACCENT_HOVER = "#2E63D8"
ERROR_COLOR = "#E74C3C"

FONT_FAMILY = "Helvetica"


class WeatherApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("Weather")
        self.geometry("420x640")
        self.minsize(380, 600)
        self.configure(fg_color=BG_COLOR)

        self._build_layout()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self):
        # Outer padding wrapper
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=24, pady=24)

        # --- Title -----------------------------------------------------
        ctk.CTkLabel(
            container,
            text="Weather",
            font=(FONT_FAMILY, 28, "bold"),
            text_color=TEXT_MAIN,
        ).pack(anchor="w", pady=(0, 18))

        # --- Search row --------------------------------------------------
        search_row = ctk.CTkFrame(container, fg_color="transparent")
        search_row.pack(fill="x")

        self.city_entry = ctk.CTkEntry(
            search_row,
            placeholder_text="Search for a city...",
            height=46,
            corner_radius=12,
            border_width=0,
            fg_color=CARD_COLOR,
            text_color=TEXT_MAIN,
            font=(FONT_FAMILY, 15),
        )
        self.city_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.city_entry.bind("<Return>", lambda e: self.search_weather())

        self.search_button = ctk.CTkButton(
            search_row,
            text="Search",
            width=90,
            height=46,
            corner_radius=12,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=(FONT_FAMILY, 14, "bold"),
            command=self.search_weather,
        )
        self.search_button.pack(side="right")

        # --- Status / error line ---------------------------------------
        self.status_label = ctk.CTkLabel(
            container,
            text="",
            font=(FONT_FAMILY, 13),
            text_color=ERROR_COLOR,
        )
        self.status_label.pack(anchor="w", pady=(8, 0))

        # --- Main card ---------------------------------------------------
        self.card = ctk.CTkFrame(
            container,
            corner_radius=20,
            fg_color=CARD_COLOR,
        )
        self.card.pack(fill="both", expand=True, pady=(20, 0))

        # City name
        self.city_label = ctk.CTkLabel(
            self.card,
            text="Search a city to begin",
            font=(FONT_FAMILY, 18, "bold"),
            text_color=TEXT_MAIN,
            wraplength=320,
        )
        self.city_label.pack(pady=(36, 0))

        # Weather icon
        self.icon_label = ctk.CTkLabel(
            self.card,
            text="🌍",
            font=(FONT_FAMILY, 64),
        )
        self.icon_label.pack(pady=(10, 0))

        # Temperature
        self.temperature_label = ctk.CTkLabel(
            self.card,
            text="--°",
            font=(FONT_FAMILY, 56, "bold"),
            text_color=TEXT_MAIN,
        )
        self.temperature_label.pack(pady=(0, 0))

        # Condition text
        self.condition_label = ctk.CTkLabel(
            self.card,
            text="",
            font=(FONT_FAMILY, 16),
            text_color=TEXT_MUTED,
        )
        self.condition_label.pack(pady=(0, 24))

        # Divider
        divider = ctk.CTkFrame(self.card, height=1, fg_color="#EDEFF2")
        divider.pack(fill="x", padx=30)

        # Stats row (feels like / humidity / wind)
        stats_row = ctk.CTkFrame(self.card, fg_color="transparent")
        stats_row.pack(fill="x", pady=28, padx=20)
        stats_row.grid_columnconfigure((0, 1, 2), weight=1)

        self.feels_like_value, self.feels_like_frame = self._make_stat(
            stats_row, "🌡️", "Feels like", "--°"
        )
        self.feels_like_frame.grid(row=0, column=0, sticky="nsew")

        self.humidity_value, self.humidity_frame = self._make_stat(
            stats_row, "💧", "Humidity", "--%"
        )
        self.humidity_frame.grid(row=0, column=1, sticky="nsew")

        self.wind_value, self.wind_frame = self._make_stat(
            stats_row, "💨", "Wind", "-- km/h"
        )
        self.wind_frame.grid(row=0, column=2, sticky="nsew")

    def _make_stat(self, parent, emoji, label, value):
        frame = ctk.CTkFrame(parent, fg_color="transparent")

        ctk.CTkLabel(frame, text=emoji, font=(FONT_FAMILY, 20)).pack()
        value_label = ctk.CTkLabel(
            frame, text=value, font=(FONT_FAMILY, 15, "bold"), text_color=TEXT_MAIN
        )
        value_label.pack(pady=(4, 0))
        ctk.CTkLabel(
            frame, text=label, font=(FONT_FAMILY, 11), text_color=TEXT_MUTED
        ).pack()

        return value_label, frame

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def search_weather(self):
        city = self.city_entry.get().strip()

        if not city:
            self._show_status("Please enter a city name.")
            return

        self._set_loading(True)
        self._show_status("")

        # Run the network calls off the main thread so the UI stays responsive.
        thread = threading.Thread(target=self._fetch_weather, args=(city,), daemon=True)
        thread.start()

    def _fetch_weather(self, city):
        try:
            location = get_coordinates(city)

            if location is None:
                self.after(0, self._handle_not_found)
                return

            weather = get_weather(location["latitude"], location["longitude"])
            self.after(0, self._handle_success, location, weather)

        except WeatherAPIError as err:
            self.after(0, self._handle_error, str(err))
        except Exception:
            self.after(0, self._handle_error, "Something unexpected went wrong.")

    # ------------------------------------------------------------------
    # UI state updates (always run on the main thread via `after`)
    # ------------------------------------------------------------------
    def _handle_not_found(self):
        self._set_loading(False)
        self._show_status(f'No city found matching "{self.city_entry.get().strip()}".')

    def _handle_error(self, message):
        self._set_loading(False)
        self._show_status(message)

    def _handle_success(self, location, weather):
        self._set_loading(False)

        description, emoji = get_condition_full(weather["weathercode"])
        accent = get_condition_color(weather["weathercode"])

        self.city_label.configure(text=f"{location['name']}, {location['country']}")
        self.icon_label.configure(text=emoji)
        self.temperature_label.configure(
            text=f"{weather['temperature']}°C", text_color=accent
        )
        self.condition_label.configure(text=description)

        self.feels_like_value.configure(text=f"{weather['feels_like']}°C")
        self.humidity_value.configure(text=f"{weather['humidity']}%")
        self.wind_value.configure(text=f"{weather['wind']} km/h")

    def _set_loading(self, loading):
        if loading:
            self.search_button.configure(state="disabled", text="...")
            self.city_entry.configure(state="disabled")
        else:
            self.search_button.configure(state="normal", text="Search")
            self.city_entry.configure(state="normal")

    def _show_status(self, message):
        self.status_label.configure(text=message)