import threading
import tkinter as tk

import customtkinter as ctk

from api import get_coordinates, get_weather, WeatherAPIError
from weather_utils import get_condition_full, get_condition_color
from icons import draw_icon

# ---- Palette (same calm pastel language as before, native widgets now) ----
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

FONT = "Helvetica"


class WeatherApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("WeatherOS")
        self.geometry("400x780")
        self.minsize(360, 660)
        self.configure(fg_color=BG_COLOR)

        self._float_phase = 0.0
        self._current_icon_key = None
        self._current_accent = None

        self._build_layout()
        self._tick_clock()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_layout(self):
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=20, pady=(20, 12))

        # --- Search bar (pill) -----------------------------------------
        search_bar = ctk.CTkFrame(
            outer, corner_radius=999, fg_color=CARD_COLOR,
            border_width=1, border_color=CARD_BORDER,
        )
        search_bar.pack(fill="x")
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

        # --- Error banner -------------------------------------------------
        self.error_frame = ctk.CTkFrame(
            outer, corner_radius=16, fg_color=DANGER_BG,
        )
        self.error_label = ctk.CTkLabel(
            self.error_frame, text="", text_color=DANGER_TEXT,
            font=(FONT, 12, "bold"), wraplength=320, justify="left",
        )
        self.error_label.pack(padx=14, pady=10, anchor="w")
        # not packed into outer yet — shown/hidden on demand

        # --- Stage (empty state / result) --------------------------------
        self.stage = ctk.CTkFrame(outer, fg_color="transparent")
        self.stage.pack(fill="both", expand=True, pady=(16, 0))

        self._build_empty_state()
        self._build_result_view()

        # --- Footer ---------------------------------------------------
        self.clock_label = ctk.CTkLabel(
            self, text="--:--", text_color=TEXT_TERTIARY, font=(FONT, 11),
        )
        self.clock_label.pack(side="bottom", pady=(0, 14))

    def _build_empty_state(self):
        self.empty_frame = ctk.CTkFrame(self.stage, fg_color="transparent")
        self.empty_frame.place(relx=0.5, rely=0.5, anchor="center")

        self.empty_canvas = tk.Canvas(
            self.empty_frame, width=96, height=96,
            bg=BG_COLOR, highlightthickness=0,
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

        ctk.CTkLabel(
            self.empty_frame, text="Search a city to see the current weather",
            font=(FONT, 12), text_color=TEXT_TERTIARY,
        ).pack(pady=(4, 0))

    def _build_result_view(self):
        self.result_frame = ctk.CTkFrame(self.stage, fg_color="transparent")
        # placed (not packed) only when there's data to show

        self.city_label = ctk.CTkLabel(
            self.result_frame, text="—", font=(FONT, 21, "bold"),
            text_color=TEXT_PRIMARY,
        )
        self.city_label.pack(pady=(4, 0))

        self.country_label = ctk.CTkLabel(
            self.result_frame, text="—", font=(FONT, 11),
            text_color=TEXT_TERTIARY,
        )
        self.country_label.pack()

        self.icon_canvas = tk.Canvas(
            self.result_frame, width=110, height=110,
            bg=BG_COLOR, highlightthickness=0,
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
            temp_row, text="°", font=(FONT, 30),
            text_color=TEXT_PRIMARY,
        )
        self.temp_unit_label.pack(side="left", anchor="n", pady=(10, 0))

        self.condition_label = ctk.CTkLabel(
            self.result_frame, text="—", font=(FONT, 14),
            text_color=TEXT_SECONDARY,
        )
        self.condition_label.pack(pady=(0, 18))

        # --- Card 1: feels / humidity / wind ---
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

        # --- Card 2: sunrise / sunset / uv / pressure (2x2) ---
        card2 = ctk.CTkFrame(
            self.result_frame, corner_radius=22, fg_color=CARD_COLOR,
            border_width=1, border_color=CARD_BORDER,
        )
        card2.pack(fill="x")
        card2.grid_columnconfigure((0, 1), weight=1)

        self.sunrise_value, _ = self._grid_cell(card2, "Sunrise")
        self.sunrise_value.master.grid(row=0, column=0, sticky="w", padx=20, pady=(18, 10))

        self.sunset_value, _ = self._grid_cell(card2, "Sunset")
        self.sunset_value.master.grid(row=0, column=1, sticky="w", padx=20, pady=(18, 10))

        self.uv_value, _ = self._grid_cell(card2, "UV Index")
        self.uv_value.master.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 18))

        self.pressure_value, _ = self._grid_cell(card2, "Pressure")
        self.pressure_value.master.grid(row=1, column=1, sticky="w", padx=20, pady=(0, 18))

        self.updated_label = ctk.CTkLabel(
            self.result_frame, text="", font=(FONT, 11),
            text_color=TEXT_TERTIARY,
        )
        self.updated_label.pack(pady=(12, 0))

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
    # Actions
    # ------------------------------------------------------------------
    def search_weather(self):
        city = self.city_entry.get().strip()

        if not city:
            self._show_error("Please enter a city name")
            return

        self._hide_error()
        self._set_loading(True)

        thread = threading.Thread(target=self._fetch, args=(city,), daemon=True)
        thread.start()

    def _fetch(self, city):
        try:
            location = get_coordinates(city)

            if location is None:
                self.after(0, self._show_error, f'No match for "{city}"')
                self.after(0, self._set_loading, False)
                return

            weather = get_weather(location["latitude"], location["longitude"])
            self.after(0, self._handle_success, location, weather)

        except WeatherAPIError as err:
            self.after(0, self._show_error, str(err))
        except Exception:
            self.after(0, self._show_error, "Something unexpected went wrong")
        finally:
            self.after(0, self._set_loading, False)

    def _handle_success(self, location, weather):
        label, icon_key = get_condition_full(weather["weathercode"])
        accent = get_condition_color(weather["weathercode"])

        self.empty_frame.place_forget()
        self.result_frame.pack(fill="both", expand=True)

        self.city_label.configure(text=location["name"])
        self.country_label.configure(text=location["country"].upper())
        self.condition_label.configure(text=label)

        self._current_icon_key = icon_key
        self._current_accent = accent
        draw_icon(self.icon_canvas, icon_key, accent)

        self._animate_temp(weather["temperature"])

        self.feels_value.configure(text=f"{weather['feels_like']}°")
        self.humid_value.configure(text=f"{weather['humidity']}%")
        self.wind_value.configure(text=f"{weather['wind']} km/h")

        self.sunrise_value.configure(text=weather["sunrise"])
        self.sunset_value.configure(text=weather["sunset"])
        self.uv_value.configure(text=self._uv_label(weather["uv_index"]))
        self.pressure_value.configure(text=f"{weather['pressure']} hPa")

        now_txt = self._now_hhmm()
        self.updated_label.configure(text=f"Updated at {now_txt}")

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
        return f"{value} · {tier}"

    def _animate_temp(self, target, step=0, steps=20):
        # simple ease-out count-up over ~400ms
        progress = step / steps
        eased = 1 - (1 - progress) ** 3
        current = round(eased * target)
        self.temp_value_label.configure(text=str(current))
        if step < steps:
            self.after(20, lambda: self._animate_temp(target, step + 1, steps))

    def _set_loading(self, loading):
        if loading:
            self.search_button.configure(state="disabled", text="...")
            self.city_entry.configure(state="disabled")
        else:
            self.search_button.configure(state="normal", text="Search")
            self.city_entry.configure(state="normal")

    def _show_error(self, message):
        self.error_label.configure(text=message)
        self.error_frame.pack(fill="x", pady=(12, 0), after=self.search_bar)

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