"""Draws small, soft, pastel weather glyphs directly onto a tkinter Canvas.

No image files, no emoji — every icon is built from basic Canvas
primitives (ovals, lines, polygons) so the whole app stays pure Python /
native widgets with zero external assets.
"""

import tkinter as tk

STROKE = "#3A3552"


def _cloud(canvas, cx, cy, scale, fill):
    """A soft, fluffy cloud made of three overlapping circles + a base."""
    r = 16 * scale
    canvas.create_oval(cx - r * 1.9, cy - r * 0.2, cx - r * 0.3, cy + r * 1.4,
                        fill=fill, outline=STROKE, width=2, tags="icon")
    canvas.create_oval(cx - r * 0.9, cy - r * 1.3, cx + r * 0.9, cy + r * 0.7,
                        fill=fill, outline=STROKE, width=2, tags="icon")
    canvas.create_oval(cx + r * 0.2, cy - r * 0.1, cx + r * 1.8, cy + r * 1.4,
                        fill=fill, outline=STROKE, width=2, tags="icon")
    canvas.create_rectangle(cx - r * 1.9, cy + r * 0.6, cx + r * 1.8, cy + r * 1.4,
                             fill=fill, outline="", tags="icon")
    canvas.create_line(cx - r * 1.9, cy + r * 1.4, cx + r * 1.8, cy + r * 1.4,
                        fill=STROKE, width=2, tags="icon")


def draw_sun(canvas, cx, cy, scale, accent):
    r = 18 * scale
    ray = 10 * scale
    for angle_deg in range(0, 360, 45):
        import math
        a = math.radians(angle_deg)
        x1 = cx + (r + 4) * math.cos(a)
        y1 = cy + (r + 4) * math.sin(a)
        x2 = cx + (r + 4 + ray) * math.cos(a)
        y2 = cy + (r + 4 + ray) * math.sin(a)
        canvas.create_line(x1, y1, x2, y2, fill=STROKE, width=3,
                            capstyle=tk.ROUND, tags="icon")
    canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                        fill=accent, outline="", tags="icon")


def draw_cloud(canvas, cx, cy, scale, accent):
    _cloud(canvas, cx, cy, scale, accent)


def draw_fog(canvas, cx, cy, scale, accent):
    _cloud(canvas, cx, cy - 12 * scale, scale * 0.75, accent)
    widths = [0.9, 0.7, 1.0]
    for i, w in enumerate(widths):
        y = cy + (16 + i * 12) * scale
        half = 34 * scale * w
        canvas.create_line(cx - half, y, cx + half, y,
                            fill=STROKE, width=4, capstyle=tk.ROUND,
                            tags="icon")


def draw_rain(canvas, cx, cy, scale, accent):
    _cloud(canvas, cx, cy - 10 * scale, scale * 0.85, "#D9DCEE")
    for dx in (-14, 0, 14):
        x = cx + dx * scale
        canvas.create_line(x, cy + 14 * scale, x - 4 * scale, cy + 30 * scale,
                            fill=accent, width=4, capstyle=tk.ROUND, tags="icon")


def draw_snow(canvas, cx, cy, scale, accent):
    _cloud(canvas, cx, cy - 10 * scale, scale * 0.85, "#E7ECF5")
    for dx in (-14, 0, 14):
        x = cx + dx * scale
        y = cy + 24 * scale
        r = 3.5 * scale
        canvas.create_oval(x - r, y - r, x + r, y + r, fill=accent,
                            outline="", tags="icon")


def draw_storm(canvas, cx, cy, scale, accent):
    _cloud(canvas, cx, cy - 10 * scale, scale * 0.85, "#CFCBE6")
    points = [
        cx + 6 * scale, cy + 12 * scale,
        cx - 8 * scale, cy + 30 * scale,
        cx, cy + 30 * scale,
        cx - 6 * scale, cy + 46 * scale,
        cx + 10 * scale, cy + 26 * scale,
        cx + 2 * scale, cy + 26 * scale,
    ]
    canvas.create_polygon(points, fill=accent, outline=STROKE, width=1.5,
                           joinstyle=tk.ROUND, tags="icon")


_DRAW_FUNCS = {
    "sun": draw_sun,
    "cloud": draw_cloud,
    "fog": draw_fog,
    "rain": draw_rain,
    "snow": draw_snow,
    "storm": draw_storm,
}


def draw_icon(canvas, key, accent):
    """Clear the canvas and draw the icon for `key`, centered."""
    canvas.delete("icon")
    width = int(canvas["width"])
    height = int(canvas["height"])
    cx, cy = width / 2, height / 2
    scale = min(width, height) / 100.0
    func = _DRAW_FUNCS.get(key, draw_cloud)
    func(canvas, cx, cy, scale, accent)