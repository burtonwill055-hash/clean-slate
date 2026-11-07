"""Colors, sizes and small helpers for the mobile UI."""
from __future__ import annotations

BG = "#0f1115"
SIDEBAR = "#13161b"
CARD = "#181c22"
CARD_ALT = "#1d222a"
BORDER = "#262c36"
BORDER_SOFT = "#20252d"
TEXT = "#e9eef5"
MUTED = "#8d98a8"
FAINT = "#5c6675"
ACCENT = "#6ee7a8"
ACCENT_DARK = "#0b2a1c"
DANGER = "#ff7a7a"
DANGER_SOFT = "#ff9a9a"
DANGER_BG = "#2a181c"
WARN = "#f6c177"

HABIT_COLORS = [
    "#6ee7a8",
    "#7dd3fc",
    "#c4b5fd",
    "#fcd34d",
    "#f9a8d4",
    "#93c5fd",
    "#fca5a5",
    "#a3e635",
]

MILESTONES = [1, 3, 7, 14, 21, 30, 45, 60, 90, 120, 180, 270, 365, 500, 730]

PRESETS = [
    ("Smoking", "#6ee7a8"),
    ("Social media", "#7dd3fc"),
    ("Sugar", "#fcd34d"),
    ("Alcohol", "#c4b5fd"),
    ("Gambling", "#fca5a5"),
    ("Something else", "#a3e635"),
]

TRIGGERS = ["Stress", "Boredom", "Craving", "Social", "Habit", "Other"]


def rgba(value: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    """#rrggbb -> a Kivy-friendly RGBA tuple."""
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return (
        int(value[0:2], 16) / 255.0,
        int(value[2:4], 16) / 255.0,
        int(value[4:6], 16) / 255.0,
        alpha,
    )


def mix(first: str, second: str, amount: float) -> str:
    """Blend two hex colors; amount 0 returns first, 1 returns second."""
    a = rgba(first)
    b = rgba(second)
    out = [round((a[i] + (b[i] - a[i]) * amount) * 255) for i in range(3)]
    return "#" + "".join(f"{channel:02x}" for channel in out)
