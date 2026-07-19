import sys
import threading
import tkinter as tk

import customtkinter as ctk

from api import get_coordinates, get_weather, get_air_quality, get_ip_location, WeatherAPIError
from weather_utils import (
    get_condition_full, get_condition_color, get_condition_bg,
    get_aqi_info, format_day_label,
)
from icons import draw_icon
import locations_store

# ---- Palette (calm pastel language, native widgets) ----
BG_COLOR = "#EEECFB"
CARD_COLOR = "#FFFFFF"
CARD_BORDER = "#ECE9F7"
TEXT_PRIMARY = "#2E2A45"
TEXT_SECONDARY = "#6F6A88"
TEXT_TERTIARY = "#A29DBD"
DANGER_BG = "#FBDCE1"
DANGER_TEXT = "#B0455A"
BTN_COLOR = "#2E2A45"
BTN_HOVER = "#43405C"
PILL_INACTIVE = "#F4F2FC"
PILL_ACTIVE = "#2E2A45"

FONT = "Helvetica"


def _wheel_units(event):
    """Normalize a <MouseWheel> event's delta into a small integer number
    of scroll units, accounting for the very different delta scales
    Windows/macOS use (Linux doesn't send <MouseWheel> at all - it sends
    Button-4/5 instead, handled separately below)."""
    if sys.platform == "darwin":
        return -1 * event.delta
    return -1 * int(event.delta / 120) or (-1 if event.delta > 0 else 1)


def wire_scroll(scrollable_frame, orientation="vertical"):
    """Make mouse-wheel / trackpad scrolling work anywhere over a
    CTkScrollableFrame, including over the widgets placed inside it.

    customtkinter's own CTkScrollableFrame binds the wheel with
    `bind_all`, which is global - so with more than one scrollable frame
    on screen, whichever one was created *last* silently steals every
    other frame's scroll events. This rebinds scrolling locally, directly
    on the frame and each of its current children, and returns a
    `rewire()` function that must be called again after adding new child
    widgets (e.g. after repopulating a list) so those new widgets pick up
    the binding too.

    Nested scrollable frames (e.g. a horizontal strip inside a vertical
    page) are left alone when wiring the outer frame, so each one scrolls
    only its own content.
    """
    canvas = scrollable_frame._parent_canvas

    def _scroll(units):
        if orientation == "horizontal":
            canvas.xview_scroll(units, "units")
        else:
            canvas.yview_scroll(units, "units")

    def _on_wheel(event):
        _scroll(_wheel_units(event))
        return "break"

    def _on_button4(_event):
        _scroll(-1)
        return "break"

    def _on_button5(_event):
        _scroll(1)
        return "break"

    def _bind(widget):
        widget.bind("<MouseWheel>", _on_wheel)
        widget.bind("<Button-4>", _on_button4)
        widget.bind("<Button-5>", _on_button5)
        if widget is not scrollable_frame and getattr(widget, "_wire_scroll_owned", False):
            return  # a separately-wired nested scrollable frame - don't override it
        for child in widget.winfo_children():
            _bind(child)

    scrollable_frame._wire_scroll_owned = True
    _bind(scrollable_frame)

    def rewire():
        _bind(scrollable_frame)

    return rewire


class WeatherApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("WeatherOS")
        self.geometry("420x860")
        self.minsize(380, 700)
        self.current_bg = BG_COLOR
        self.configure(fg_color=self.current_bg)

        # ---- state ----
        self.use_imperial = False
        self.ip_location = None
        self.saved_locations = locations_store.load_locations()
        self.active_location = None
        self.pill_buttons = []

        self._build_layout()

        # Wire real mouse-wheel scrolling everywhere (see wire_scroll's
        # docstring for why this can't just be left to customtkinter).
        # Inner/nested scrollable frames must be wired before the outer
        # frame that contains them, so the outer wiring knows to leave
        # their content alone.
        self._rewire_hourly = wire_scroll(self.hourly_row, "horizontal")
        self._rewire_pills = wire_scroll(self.pills_row, "horizontal")
        self._rewire_stage = wire_scroll(self.stage, "vertical")

        self._tick_clock()

        self._rebuild_location_pills()
        self._bootstrap_location()

    # ------------------------------------------------------------------
    # Units
    # ------------------------------------------------------------------
    @property
    def temperature_unit(self):
        return "fahrenheit" if self.use_imperial else "celsius"

    @property
    def wind_speed_unit(self):
        return "mph" if self.use_imperial else "kmh"

    def _toggle_units(self):
        self.use_imperial = not self.use_imperial
        self.unit_button.configure(text="\u00b0F" if self.use_imperial else "\u00b0C")
        if self.active_location:
            self._load_location(self.active_location)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self):
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=20, pady=(20, 0))

        # --- Search row: pill entry + unit toggle -------------------------
        search_row = ctk.CTkFrame(outer, fg_color="transparent")
        search_row.pack(fill="x")

        search_bar = ctk.CTkFrame(
            search_row, corner_radius=999, fg_color=CARD_COLOR,
            border_width=1, border_color=CARD_BORDER,
        )
        search_bar.pack(side="left", fill="x", expand=True)
        self.search_bar = search_bar

        self.city_entry = ctk.CTkEntry(
            search_bar,
            placeholder_text="Search for a city",
            border_width=0,
            fg_color="transparent",
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_TERTIARY,
            font=(FONT, 15),
            height=44,
        )
        self.city_entry.pack(side="left", fill="x", expand=True, padx=(18, 6))
        self.city_entry.bind("<Return>", lambda e: self.search_weather())

        self.search_button = ctk.CTkButton(
            search_bar,
            text="Search",
            width=84,
            height=38,
            corner_radius=999,
            fg_color=BTN_COLOR,
            hover_color=BTN_HOVER,
            text_color="#FFFFFF",
            font=(FONT, 13, "bold"),
            command=self.search_weather,
        )
        self.search_button.pack(side="right", padx=6, pady=6)

        self.unit_button = ctk.CTkButton(
            search_row, text="\u00b0C", width=44, height=44, corner_radius=999,
            fg_color=CARD_COLOR, hover_color=PILL_INACTIVE, text_color=TEXT_PRIMARY,
            border_width=1, border_color=CARD_BORDER, font=(FONT, 13, "bold"),
            command=self._toggle_units,
        )
        self.unit_button.pack(side="left", padx=(8, 0))

        # --- Saved-location pills (horizontal scroll) ----------------------
        self.pills_row = ctk.CTkScrollableFrame(
            outer, orientation="horizontal", height=46, fg_color="transparent",
        )
        self.pills_row.pack(fill="x", pady=(10, 0))

        # --- Error banner -------------------------------------------------
        self.error_frame = ctk.CTkFrame(outer, corner_radius=16, fg_color=DANGER_BG)
        self.error_label = ctk.CTkLabel(
            self.error_frame, text="", text_color=DANGER_TEXT,
            font=(FONT, 12, "bold"), wraplength=320, justify="left",
        )
        self.error_label.pack(padx=14, pady=10, anchor="w")
        # not packed into outer yet - shown/hidden on demand

        # --- Scrollable stage (empty state / result) -----------------------
        self.stage = ctk.CTkScrollableFrame(outer, fg_color="transparent")
        self.stage.pack(fill="both", expand=True, pady=(14, 0))

        self._build_empty_state()
        self._build_result_view()

        # --- Footer ---------------------------------------------------
        self.clock_label = ctk.CTkLabel(
            self, text="--:--", text_color=TEXT_TERTIARY, font=(FONT, 11),
        )
        self.clock_label.pack(side="bottom", pady=(0, 14))

    def _build_empty_state(self):
        self.empty_frame = ctk.CTkFrame(self.stage, fg_color="transparent")
        self.empty_frame.pack(expand=True, pady=(80, 0))

        self.empty_canvas = tk.Canvas(
            self.empty_frame, width=96, height=96,
            bg=self.current_bg, highlightthickness=0,
        )
        self.empty_canvas.pack(pady=(0, 16))
        self.empty_canvas.create_oval(
            8, 8, 88, 88, outline="#C9C3E8", width=2, dash=(4, 6),
        )
        self.empty_canvas.create_oval(
            32, 26, 64, 58, fill="#E4E0F7", outline="",
        )

        ctk.CTkLabel(
            self.empty_frame, text="No location yet",
            font=(FONT, 15, "bold"), text_color=TEXT_PRIMARY,
        ).pack()

        self.empty_status_label = ctk.CTkLabel(
            self.empty_frame, text="Locating you\u2026",
            font=(FONT, 12), text_color=TEXT_TERTIARY,
        )
        self.empty_status_label.pack(pady=(4, 0))

        self.locate_retry_button = ctk.CTkButton(
            self.empty_frame, text="Try locating again", width=160, height=32,
            corner_radius=999, fg_color="transparent", hover_color=PILL_INACTIVE,
            border_width=1, border_color=CARD_BORDER, text_color=TEXT_SECONDARY,
            font=(FONT, 11, "bold"), command=self._retry_locate,
        )
        # not packed yet - only shown if auto-locate fails

    def _build_result_view(self):
        self.result_frame = ctk.CTkFrame(self.stage, fg_color="transparent")
        # packed only when there's data to show

        self.city_label = ctk.CTkLabel(
            self.result_frame, text="\u2014", font=(FONT, 21, "bold"),
            text_color=TEXT_PRIMARY,
        )
        self.city_label.pack(pady=(4, 0))

        self.country_label = ctk.CTkLabel(
            self.result_frame, text="\u2014", font=(FONT, 11),
            text_color=TEXT_TERTIARY,
        )
        self.country_label.pack()

        # --- Hero canvas: the condition icon ----
        self.icon_canvas = tk.Canvas(
            self.result_frame, width=140, height=140,
            bg=self.current_bg, highlightthickness=0,
        )
        self.icon_canvas.pack(pady=(14, 0))

        temp_row = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        temp_row.pack()

        self.temp_value_label = ctk.CTkLabel(
            temp_row, text="--", font=(FONT, 74, "bold"),
            text_color=TEXT_PRIMARY,
        )
        self.temp_value_label.pack(side="left")

        self.temp_unit_label = ctk.CTkLabel(
            temp_row, text="\u00b0", font=(FONT, 30),
            text_color=TEXT_PRIMARY,
        )
        self.temp_unit_label.pack(side="left", anchor="n", pady=(10, 0))

        self.condition_label = ctk.CTkLabel(
            self.result_frame, text="\u2014", font=(FONT, 14),
            text_color=TEXT_SECONDARY,
        )
        self.condition_label.pack(pady=(0, 6))

        self.save_button = ctk.CTkButton(
            self.result_frame, text="+ Save location", width=140, height=30,
            corner_radius=999, fg_color="transparent", hover_color=PILL_INACTIVE,
            border_width=1, border_color=CARD_BORDER, text_color=TEXT_SECONDARY,
            font=(FONT, 11, "bold"), command=self._save_active_location,
        )
        self.save_button.pack(pady=(0, 18))

        # --- Hourly forecast ------------------------------------------------
        ctk.CTkLabel(
            self.result_frame, text="HOURLY FORECAST", font=(FONT, 10, "bold"),
            text_color=TEXT_TERTIARY,
        ).pack(anchor="w", padx=4)

        self.hourly_row = ctk.CTkScrollableFrame(
            self.result_frame, orientation="horizontal", height=104,
            fg_color=CARD_COLOR, corner_radius=22,
        )
        self.hourly_row.pack(fill="x", pady=(6, 12))

        # --- Card 1: feels / humidity / wind ---------------------------
        card1 = ctk.CTkFrame(
            self.result_frame, corner_radius=22, fg_color=CARD_COLOR,
            border_width=1, border_color=CARD_BORDER,
        )
        card1.pack(fill="x", pady=(0, 12))
        card1.grid_columnconfigure((0, 1, 2), weight=1)

        self.feels_value, _ = self._stat_cell(card1, "Feels like")
        self.feels_value.master.grid(row=0, column=0, sticky="nsew", pady=16)

        self.humid_value, _ = self._stat_cell(card1, "Humidity")
        self.humid_value.master.grid(row=0, column=1, sticky="nsew", pady=16)

        self.wind_value, _ = self._stat_cell(card1, "Wind")
        self.wind_value.master.grid(row=0, column=2, sticky="nsew", pady=16)

        # --- Card: air quality ------------------------------------------
        card_aqi = ctk.CTkFrame(
            self.result_frame, corner_radius=22, fg_color=CARD_COLOR,
            border_width=1, border_color=CARD_BORDER,
        )
        card_aqi.pack(fill="x", pady=(0, 12))

        aqi_inner = ctk.CTkFrame(card_aqi, fg_color="transparent")
        aqi_inner.pack(fill="x", padx=18, pady=14)

        self.aqi_dot = tk.Canvas(aqi_inner, width=14, height=14, bg=CARD_COLOR, highlightthickness=0)
        self.aqi_dot.pack(side="left")
        self._aqi_dot_item = self.aqi_dot.create_oval(1, 1, 13, 13, fill=TEXT_TERTIARY, outline="")

        aqi_text = ctk.CTkFrame(aqi_inner, fg_color="transparent")
        aqi_text.pack(side="left", padx=(10, 0), fill="x", expand=True)

        self.aqi_value = ctk.CTkLabel(
            aqi_text, text="Air quality \u2014", font=(FONT, 14, "bold"), text_color=TEXT_PRIMARY,
        )
        self.aqi_value.pack(anchor="w")

        self.aqi_detail = ctk.CTkLabel(
            aqi_text, text="PM2.5 \u2014 \u00b7 PM10 \u2014", font=(FONT, 10), text_color=TEXT_TERTIARY,
        )
        self.aqi_detail.pack(anchor="w", pady=(2, 0))

        # --- Card 2: sunrise / sunset / uv / pressure (2x2) --------------
        card2 = ctk.CTkFrame(
            self.result_frame, corner_radius=22, fg_color=CARD_COLOR,
            border_width=1, border_color=CARD_BORDER,
        )
        card2.pack(fill="x", pady=(0, 12))
        card2.grid_columnconfigure((0, 1), weight=1)

        self.sunrise_value, _ = self._grid_cell(card2, "Sunrise")
        self.sunrise_value.master.grid(row=0, column=0, sticky="w", padx=20, pady=(18, 10))

        self.sunset_value, _ = self._grid_cell(card2, "Sunset")
        self.sunset_value.master.grid(row=0, column=1, sticky="w", padx=20, pady=(18, 10))

        self.uv_value, _ = self._grid_cell(card2, "UV Index")
        self.uv_value.master.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 18))

        self.pressure_value, _ = self._grid_cell(card2, "Pressure")
        self.pressure_value.master.grid(row=1, column=1, sticky="w", padx=20, pady=(0, 18))

        # --- 7-day forecast -----------------------------------------------
        ctk.CTkLabel(
            self.result_frame, text="7-DAY FORECAST", font=(FONT, 10, "bold"),
            text_color=TEXT_TERTIARY,
        ).pack(anchor="w", padx=4)

        self.daily_card = ctk.CTkFrame(
            self.result_frame, corner_radius=22, fg_color=CARD_COLOR,
            border_width=1, border_color=CARD_BORDER,
        )
        self.daily_card.pack(fill="x", pady=(6, 12))

        self.updated_label = ctk.CTkLabel(
            self.result_frame, text="", font=(FONT, 11),
            text_color=TEXT_TERTIARY,
        )
        self.updated_label.pack(pady=(4, 24))

    def _stat_cell(self, parent, label_text):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        value = ctk.CTkLabel(
            frame, text="--", font=(FONT, 16, "bold"), text_color=TEXT_PRIMARY,
        )
        value.pack()
        ctk.CTkLabel(
            frame, text=label_text, font=(FONT, 10), text_color=TEXT_TERTIARY,
        ).pack(pady=(2, 0))
        return value, frame

    def _grid_cell(self, parent, label_text):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        value = ctk.CTkLabel(
            frame, text="--", font=(FONT, 15, "bold"), text_color=TEXT_PRIMARY,
        )
        value.pack(anchor="w")
        ctk.CTkLabel(
            frame, text=label_text, font=(FONT, 10), text_color=TEXT_TERTIARY,
        ).pack(anchor="w", pady=(2, 0))
        return value, frame

    # ------------------------------------------------------------------
    # Location pills
    # ------------------------------------------------------------------
    def _rebuild_location_pills(self):
        for child in self.pills_row.winfo_children():
            child.destroy()
        self.pill_buttons = []

        pills = []
        if self.ip_location:
            pills.append((self.ip_location, "Current location", False))
        for loc in self.saved_locations:
            pills.append((loc, loc["name"], True))

        for loc, label, removable in pills:
            self._add_pill(loc, label, removable)

        self._rewire_pills()

    def _add_pill(self, loc, label, removable):
        is_active = self.active_location is not None and self._same_place(loc, self.active_location)

        pill = ctk.CTkFrame(
            self.pills_row, corner_radius=999,
            fg_color=PILL_ACTIVE if is_active else PILL_INACTIVE,
        )
        pill.pack(side="left", padx=(0, 8))

        btn = ctk.CTkButton(
            pill, text=label, corner_radius=999, height=32,
            fg_color="transparent",
            hover_color=(BTN_HOVER if is_active else "#E7E3F6"),
            text_color=("#FFFFFF" if is_active else TEXT_SECONDARY),
            font=(FONT, 12, "bold"),
            command=lambda l=loc: self._select_pill(l),
        )
        btn.pack(side="left", padx=(14, 4 if removable else 14))

        if removable:
            close_btn = ctk.CTkButton(
                pill, text="\u00d7", width=22, height=22, corner_radius=999,
                fg_color="transparent",
                hover_color=(BTN_HOVER if is_active else "#E7E3F6"),
                text_color=("#FFFFFF" if is_active else TEXT_TERTIARY),
                font=(FONT, 13, "bold"),
                command=lambda l=loc: self._remove_saved_location(l),
            )
            close_btn.pack(side="left", padx=(0, 10))

        self.pill_buttons.append(pill)

    @staticmethod
    def _same_place(a, b):
        if not a or not b:
            return False
        return a.get("name") == b.get("name") and a.get("country") == b.get("country")

    def _select_pill(self, loc):
        self._load_location(loc)

    def _save_active_location(self):
        if not self.active_location:
            return
        loc = dict(self.active_location)
        loc.pop("is_current_location", None)
        if locations_store.contains(self.saved_locations, loc):
            return
        self.saved_locations = locations_store.add_location(self.saved_locations, loc)
        self._rebuild_location_pills()

    def _remove_saved_location(self, loc):
        self.saved_locations = locations_store.remove_location(self.saved_locations, loc)
        self._rebuild_location_pills()

    # ------------------------------------------------------------------
    # Bootstrap / actions
    # ------------------------------------------------------------------
    def _bootstrap_location(self):
        """On launch: try IP geolocation, else fall back to the first saved
        location, else show the empty state with a retry option."""
        self.locate_retry_button.pack_forget()
        self.empty_status_label.configure(text="Locating you\u2026")
        threading.Thread(target=self._fetch_ip_location, daemon=True).start()

    def _fetch_ip_location(self):
        location = get_ip_location()
        self.after(0, self._handle_ip_location, location)

    def _handle_ip_location(self, location):
        if location:
            self.ip_location = location
            self._rebuild_location_pills()
            if self.active_location is None:
                self._load_location(location)
            return

        if self.active_location is not None:
            return

        if self.saved_locations:
            self._load_location(self.saved_locations[0])
            return

        # Auto-locate failed and there's nothing saved to fall back to -
        # let the person know instead of leaving "Locating you..." forever.
        self.empty_status_label.configure(
            text="Couldn't detect your location automatically \u2014 search a city above"
        )
        self.locate_retry_button.pack(pady=(10, 0))

    def _retry_locate(self):
        self._bootstrap_location()

    def search_weather(self):
        city = self.city_entry.get().strip()

        if not city:
            self._show_error("Please enter a city name")
            return

        self._hide_error()
        self._set_loading(True)

        thread = threading.Thread(target=self._geocode_then_load, args=(city,), daemon=True)
        thread.start()

    def _geocode_then_load(self, city):
        try:
            location = get_coordinates(city)
        except WeatherAPIError as err:
            self.after(0, self._show_error, str(err))
            self.after(0, self._set_loading, False)
            return

        if location is None:
            self.after(0, self._show_error, f'No match for "{city}"')
            self.after(0, self._set_loading, False)
            return

        self.after(0, self.city_entry.delete, 0, "end")
        self.after(0, self._load_location, location)

    def _load_location(self, location):
        self.active_location = location
        self._hide_error()
        self._set_loading(True)
        self._rebuild_location_pills()
        thread = threading.Thread(target=self._fetch, args=(location,), daemon=True)
        thread.start()

    def _fetch(self, location):
        try:
            weather = get_weather(
                location["latitude"], location["longitude"],
                temperature_unit=self.temperature_unit,
                wind_speed_unit=self.wind_speed_unit,
            )
            air_quality = get_air_quality(location["latitude"], location["longitude"])
            self.after(0, self._handle_success, location, weather, air_quality)
        except WeatherAPIError as err:
            self.after(0, self._show_error, str(err))
        except Exception:
            self.after(0, self._show_error, "Something unexpected went wrong")
        finally:
            self.after(0, self._set_loading, False)

    def _handle_success(self, location, weather, air_quality):
        label, icon_key = get_condition_full(weather["weathercode"])
        accent = get_condition_color(weather["weathercode"])

        self.empty_frame.pack_forget()
        self.result_frame.pack(fill="both", expand=True)

        self.city_label.configure(text=location["name"])
        self.country_label.configure(text=location.get("country", "").upper())
        self.condition_label.configure(text=label)
        self.temp_unit_label.configure(text="\u00b0F" if self.use_imperial else "\u00b0C")

        already_saved = locations_store.contains(self.saved_locations, {
            "name": location["name"], "country": location.get("country", "")
        })
        self.save_button.configure(
            text="Saved" if already_saved else "+ Save location",
            state="disabled" if already_saved else "normal",
        )

        draw_icon(self.icon_canvas, icon_key, accent)

        self._apply_bg(get_condition_bg(weather["weathercode"]))

        self.temp_value_label.configure(text=str(weather["temperature"]))

        self.feels_value.configure(text=f"{weather['feels_like']}\u00b0")
        self.humid_value.configure(text=f"{weather['humidity']}%")
        self.wind_value.configure(text=f"{weather['wind']} {weather['wind_unit']}")

        self.sunrise_value.configure(text=weather["sunrise"])
        self.sunset_value.configure(text=weather["sunset"])
        self.uv_value.configure(text=self._uv_label(weather["uv_index"]))
        self.pressure_value.configure(text=f"{weather['pressure']} hPa")

        self._render_hourly(weather.get("hourly", []))
        self._render_daily(weather.get("daily", []))
        self._render_air_quality(air_quality)

        now_txt = self._now_hhmm()
        self.updated_label.configure(text=f"Updated at {now_txt}")

    def _render_hourly(self, hours):
        for child in self.hourly_row.winfo_children():
            child.destroy()

        for hour in hours:
            label, icon_key = get_condition_full(hour["weathercode"])
            accent = get_condition_color(hour["weathercode"])

            cell = ctk.CTkFrame(self.hourly_row, fg_color="transparent")
            cell.pack(side="left", padx=10, pady=8)

            ctk.CTkLabel(
                cell, text=hour["time"][:5], font=(FONT, 10), text_color=TEXT_TERTIARY,
            ).pack()

            mini = tk.Canvas(cell, width=34, height=34, bg=CARD_COLOR, highlightthickness=0)
            mini.pack(pady=4)
            draw_icon(mini, icon_key, accent)

            ctk.CTkLabel(
                cell, text=f"{hour['temperature']}\u00b0", font=(FONT, 12, "bold"),
                text_color=TEXT_PRIMARY,
            ).pack()

        self._rewire_hourly()

    def _render_daily(self, days):
        for child in self.daily_card.winfo_children():
            child.destroy()

        for i, day in enumerate(days):
            label, icon_key = get_condition_full(day["weathercode"])
            accent = get_condition_color(day["weathercode"])
            day_label = format_day_label(day["date"], i)

            row = ctk.CTkFrame(self.daily_card, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=(14 if i == 0 else 8, 8 if i < len(days) - 1 else 14))

            ctk.CTkLabel(
                row, text=day_label, font=(FONT, 13, "bold"), text_color=TEXT_PRIMARY, width=90,
                anchor="w",
            ).pack(side="left")

            dot = tk.Canvas(row, width=16, height=16, bg=CARD_COLOR, highlightthickness=0)
            dot.pack(side="left", padx=(0, 10))
            dot.create_oval(1, 1, 15, 15, fill=accent, outline="")

            ctk.CTkLabel(
                row, text=label, font=(FONT, 11), text_color=TEXT_SECONDARY, anchor="w",
            ).pack(side="left", fill="x", expand=True)

            ctk.CTkLabel(
                row, text=f"{day['temp_min']}\u00b0 / {day['temp_max']}\u00b0",
                font=(FONT, 12, "bold"), text_color=TEXT_PRIMARY,
            ).pack(side="right")

            if i < len(days) - 1:
                sep = ctk.CTkFrame(self.daily_card, height=1, fg_color=CARD_BORDER)
                sep.pack(fill="x", padx=18)

        self._rewire_stage()

    def _render_air_quality(self, air_quality):
        if air_quality is None:
            self.aqi_value.configure(text="Air quality unavailable")
            self.aqi_detail.configure(text="")
            self.aqi_dot.itemconfigure(self._aqi_dot_item, fill=TEXT_TERTIARY)
            return

        label, color = get_aqi_info(air_quality["aqi"])
        self.aqi_value.configure(text=f"Air quality \u00b7 {air_quality['aqi']} ({label})")
        self.aqi_detail.configure(
            text=f"PM2.5 {air_quality['pm2_5']} \u00b5g/m\u00b3 \u00b7 PM10 {air_quality['pm10']} \u00b5g/m\u00b3"
        )
        self.aqi_dot.itemconfigure(self._aqi_dot_item, fill=color)

    @staticmethod
    def _now_hhmm():
        import datetime
        return datetime.datetime.now().strftime("%H:%M")

    @staticmethod
    def _uv_label(value):
        if value < 3:
            tier = "Low"
        elif value < 6:
            tier = "Moderate"
        elif value < 8:
            tier = "High"
        elif value < 11:
            tier = "Very High"
        else:
            tier = "Extreme"
        return f"{value} \u00b7 {tier}"

    def _apply_bg(self, hex_color):
        """Set the whole app's background tint instantly (no animation)."""
        self.current_bg = hex_color
        self.configure(fg_color=hex_color)
        self.empty_canvas.configure(bg=hex_color)
        self.icon_canvas.configure(bg=hex_color)

    def _set_loading(self, loading):
        if loading:
            self.search_button.configure(state="disabled", text="...")
            self.city_entry.configure(state="disabled")
        else:
            self.search_button.configure(state="normal", text="Search")
            self.city_entry.configure(state="normal")

    def _show_error(self, message):
        self.error_label.configure(text=message)
        self.error_frame.pack(fill="x", pady=(12, 0), after=self.pills_row)

    def _hide_error(self):
        self.error_frame.pack_forget()

    # ------------------------------------------------------------------
    # Ambient bits
    # ------------------------------------------------------------------
    def _tick_clock(self):
        import datetime
        now = datetime.datetime.now().strftime("%H:%M")
        self.clock_label.configure(text=now)
        self.after(1000, self._tick_clock)