"""Reusable Kivy widgets for the Clean Slate mobile UI."""
from __future__ import annotations

from datetime import date, timedelta

from kivy.graphics import Color, Ellipse, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import (
    BooleanProperty,
    ListProperty,
    NumericProperty,
)
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import theme


# --------------------------------------------------------------- primitives
class Card(BoxLayout):
    """A rounded panel with a hairline border."""

    fill = ListProperty(theme.rgba(theme.CARD))
    border = ListProperty(theme.rgba(theme.BORDER))
    radius = NumericProperty(dp(18))

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", dp(16))
        kwargs.setdefault("spacing", dp(10))
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        # Cards hug their content so screens can stack them without
        # hand-tuning a height for every combination of children.
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            self._fill_color = Color(*self.fill)
            self._rect = RoundedRectangle(radius=[self.radius])
            self._border_color = Color(*self.border)
            self._line = Line(width=dp(1))
        self.bind(
            pos=self._sync,
            size=self._sync,
            fill=self._sync_fill,
            border=self._sync_border,
            radius=self._sync,
        )

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._rect.radius = [self.radius]
        self._line.rounded_rectangle = (
            self.x, self.y, self.width, self.height, self.radius
        )

    def _sync_fill(self, *_):
        self._fill_color.rgba = self.fill

    def _sync_border(self, *_):
        self._border_color.rgba = self.border


class PillButton(ButtonBehavior, Label):
    """Flat, rounded button with no platform chrome."""

    fill = ListProperty(theme.rgba(theme.CARD_ALT))
    fill_down = ListProperty(theme.rgba(theme.mix(theme.CARD_ALT, theme.BORDER, 0.7)))
    border = ListProperty(theme.rgba(theme.BORDER))
    text_color = ListProperty(theme.rgba(theme.TEXT))
    radius = NumericProperty(dp(14))

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(46))
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("font_size", sp(14))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("markup", False)
        super().__init__(**kwargs)
        self.color = self.text_color
        with self.canvas.before:
            self._fill_color = Color(*self.fill)
            self._rect = RoundedRectangle(radius=[self.radius])
            self._border_color = Color(*self.border)
            self._line = Line(width=dp(1))
        self.bind(
            pos=self._sync,
            size=self._sync,
            fill=self._sync_fill,
            text_color=self._sync_text,
            border=self._sync_border,
            radius=self._sync,
        )

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._rect.radius = [self.radius]
        self._line.rounded_rectangle = (
            self.x, self.y, self.width, self.height, self.radius
        )
        self.text_size = (max(0, self.width - dp(20)), self.height)

    def _sync_fill(self, *_):
        self._fill_color.rgba = self.fill

    def _sync_border(self, *_):
        self._border_color.rgba = self.border

    def _sync_text(self, *_):
        self.color = self.text_color

    def on_press(self):
        self._fill_color.rgba = self.fill_down

    def on_release(self):
        self._fill_color.rgba = self.fill


class SelectPill(PillButton):
    """A pill that can be selected, used for triggers and habit tabs."""

    active = BooleanProperty(False)
    active_fill = ListProperty(theme.rgba(theme.ACCENT_DARK))
    active_border = ListProperty(theme.rgba(theme.ACCENT))
    active_text = ListProperty(theme.rgba(theme.ACCENT))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(active=self._apply_state)
        self._apply_state()

    def _apply_state(self, *_):
        if self.active:
            self.fill = list(self.active_fill)
            self.border = list(self.active_border)
            self.text_color = list(self.active_text)
        else:
            self.fill = list(theme.rgba(theme.CARD_ALT))
            self.border = list(theme.rgba(theme.BORDER))
            self.text_color = list(theme.rgba(theme.MUTED))

    def on_press(self):
        self._fill_color.rgba = (
            self.active_fill if self.active else self.fill_down
        )


class Avatar(Label):
    """Colored circle with a single initial."""

    fill = ListProperty(theme.rgba(theme.ACCENT_DARK))

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(40), dp(40)))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", sp(17))
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("color", theme.rgba(theme.ACCENT))
        super().__init__(**kwargs)
        with self.canvas.before:
            self._fill_color = Color(*self.fill)
            self._ellipse = Ellipse()
        self.bind(pos=self._sync, size=self._sync, fill=self._sync_fill)

    def _sync(self, *_):
        self._ellipse.pos = self.pos
        self._ellipse.size = self.size
        self.text_size = self.size

    def _sync_fill(self, *_):
        self._fill_color.rgba = self.fill


class ColorDot(ButtonBehavior, Widget):
    """Small selectable color swatch."""

    color_value = ListProperty(theme.rgba(theme.ACCENT))
    selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(30), dp(30)))
        super().__init__(**kwargs)
        with self.canvas:
            self._fill_color = Color(*self.color_value)
            self._fill = Ellipse()
            self._ring_color = Color(*theme.rgba(theme.TEXT, 0))
            self._ring = Line(width=dp(2))
        self.bind(
            pos=self._sync,
            size=self._sync,
            color_value=self._sync_fill,
            selected=self._sync,
        )

    def _sync(self, *_):
        self._fill.pos = self.pos
        self._fill.size = self.size
        radius = min(self.width, self.height) / 2
        self._ring.circle = (
            self.center_x,
            self.center_y,
            radius - dp(2),
            0,
            360,
        )
        self._ring_color.a = 1.0 if self.selected else 0.0

    def _sync_fill(self, *_):
        self._fill_color.rgba = self.color_value


class Divider(Widget):
    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(1))
        super().__init__(**kwargs)
        with self.canvas:
            Color(*theme.rgba(theme.BORDER_SOFT))
            self._line = Rectangle()
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._line.pos = self.pos
        self._line.size = self.size


class Field(BoxLayout):
    """Rounded text input."""

    def __init__(self, hint="", multiline=False, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(96) if multiline else dp(48))
        kwargs.setdefault("padding", [dp(12), dp(6) if multiline else 0])
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*theme.rgba(theme.CARD_ALT))
            self._rect = RoundedRectangle(radius=[dp(12)])
            Color(*theme.rgba(theme.BORDER))
            self._line = Line(width=dp(1))
        self.input = TextInput(
            hint_text=hint,
            multiline=multiline,
            background_normal="",
            background_active="",
            background_color=(0, 0, 0, 0),
            foreground_color=theme.rgba(theme.TEXT),
            cursor_color=theme.rgba(theme.ACCENT),
            hint_text_color=theme.rgba(theme.FAINT),
            selection_color=theme.rgba(theme.ACCENT, 0.35),
            font_size=sp(15),
            padding=[dp(2), dp(12) if not multiline else dp(6)],
        )
        self.add_widget(self.input)
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._line.rounded_rectangle = (
            self.x, self.y, self.width, self.height, dp(12)
        )

    @property
    def text(self):
        return self.input.text

    @text.setter
    def text(self, value):
        self.input.text = value


def text_label(text="", size=14, color=None, bold=False, **kwargs):
    kwargs.setdefault("size_hint_y", None)
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    kwargs.setdefault("markup", False)
    height = kwargs.pop("height", None)
    label = Label(
        text=text,
        font_size=sp(size),
        color=theme.rgba(color or theme.TEXT),
        bold=bold,
        height=height or dp(size * 1.7),
        **kwargs,
    )
    label.bind(
        width=lambda *_: setattr(
            label, "text_size", (label.width, label.height)
        )
    )
    return label


def section_title(text):
    return text_label(text, size=13, color=theme.MUTED, bold=True)


# ------------------------------------------------------------------- streak
class StreakRing(Widget):
    progress = NumericProperty(0.0)
    accent = ListProperty(theme.rgba(theme.ACCENT))
    track = ListProperty(theme.rgba(theme.BORDER))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            self._track_color = Color(*self.track)
            self._track = Line(width=dp(10))
            self._arc_color = Color(*self.accent)
            self._arc = Line(width=dp(10))
        self.bind(
            pos=self._sync,
            size=self._sync,
            progress=self._sync,
            accent=self._sync_accent,
        )

    def _sync(self, *_):
        radius = min(self.width, self.height) / 2 - dp(7)
        # Kivy's cached center aliases can lag inside a pos callback, so
        # compute the centre from the raw values.
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        self._track.circle = (cx, cy, radius, 0, 360)
        sweep = max(0.0, min(1.0, self.progress)) * 360
        self._arc.circle = (cx, cy, radius, 90, 90 - sweep)
        self._arc_color.a = 1.0 if sweep > 0.4 else 0.0

    def _sync_accent(self, *_):
        self._arc_color.rgba = self.accent


class StreakCard(Card):
    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)
        self.area = FloatLayout(size_hint_y=None, height=dp(210))
        self.ring = StreakRing(
            size_hint=(None, None),
            size=(dp(196), dp(196)),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.area.add_widget(self.ring)

        self.days = text_label("0", size=52, bold=True, halign="center")
        self.days.size_hint = (1, None)
        self.days.height = dp(64)
        self.days.pos_hint = {"center_x": 0.5, "center_y": 0.59}
        self.area.add_widget(self.days)

        self.caption = text_label(
            "days clean", size=13, color=theme.MUTED, halign="center"
        )
        self.caption.size_hint = (1, None)
        self.caption.height = dp(20)
        self.caption.pos_hint = {"center_x": 0.5, "center_y": 0.41}
        self.area.add_widget(self.caption)

        self.name = text_label(
            "", size=15, color=theme.TEXT, bold=True, halign="center"
        )
        self.name.size_hint = (1, None)
        self.name.height = dp(24)
        self.name.pos_hint = {"center_x": 0.5, "center_y": 0.24}
        self.area.add_widget(self.name)
        self.add_widget(self.area)

        self.footer = text_label(
            "", size=12, color=theme.MUTED, halign="center"
        )
        self.add_widget(self.footer)

    def refresh(self, name, days, progress, accent, footer):
        self.days.text = str(days)
        self.name.text = name
        self.ring.progress = progress
        self.ring.accent = theme.rgba(accent)
        self.footer.text = footer


    def refresh(self, name, days, progress, accent, footer):
        self.days.text = str(days)
        self.name.text = name
        self.ring.progress = progress
        self.ring.accent = theme.rgba(accent)
        self.footer.text = footer


class StatCard(Card):
    def __init__(self, caption, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(78))
        kwargs.setdefault("padding", [dp(12), dp(10)])
        kwargs.setdefault("spacing", dp(0))
        super().__init__(**kwargs)
        self.value = text_label("—", size=22, bold=True)
        self.caption = text_label(caption, size=11, color=theme.MUTED)
        self.add_widget(self.value)
        self.add_widget(self.caption)

    def set(self, value):
        self.value.text = str(value)


# ------------------------------------------------------------------ charts
class Heatmap(Widget):
    weeks = NumericProperty(18)
    slip_dates = ListProperty([])
    quit_date = ListProperty(None)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(115))
        super().__init__(**kwargs)
        self._slips = set()
        self._quit = None
        self.bind(pos=self._redraw, size=self._redraw)

    def refresh(self, slip_dates, quit_date):
        self._slips = set(slip_dates or ())
        self._quit = quit_date
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        cell = dp(13)
        gap = dp(4)
        rows = 7
        weeks = int(self.weeks)
        total_width = weeks * cell + (weeks - 1) * gap
        x0 = self.x + max(0, (self.width - total_width) / 2)
        top = self.y + self.height
        today = date.today()
        start = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)

        with self.canvas:
            for column in range(weeks):
                for row in range(rows):
                    day = start + timedelta(days=column * 7 + row)
                    if day > today:
                        continue
                    if self._quit and day < self._quit:
                        color = theme.rgba(theme.CARD_ALT, 0.55)
                    elif day in self._slips:
                        color = theme.rgba(theme.DANGER)
                    else:
                        color = theme.rgba(theme.ACCENT, 0.88)
                    x = x0 + column * (cell + gap)
                    y = top - (row + 1) * cell - row * gap
                    Color(*color)
                    RoundedRectangle(
                        pos=(x, y), size=(cell, cell), radius=[dp(3)]
                    )


class WeeklyBars(Widget):
    values = ListProperty([])
    bar_color = ListProperty(theme.rgba(theme.ACCENT, 0.85))

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(120))
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw, values=self._redraw)

    def refresh(self, values):
        self.values = list(values or [])
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        values = [int(v) for v in self.values]
        if not values:
            return
        peak = max(values) or 1
        gap = dp(6)
        baseline = self.y + dp(4)
        usable_height = self.height - dp(14)
        bar_width = max(dp(4), (self.width - gap * (len(values) - 1)) / len(values))
        with self.canvas:
            for index, value in enumerate(values):
                height = max(dp(3), usable_height * (value / peak))
                x = self.x + index * (bar_width + gap)
                Color(*theme.rgba(theme.BORDER_SOFT))
                RoundedRectangle(
                    pos=(x, baseline),
                    size=(bar_width, usable_height),
                    radius=[dp(4)],
                )
                Color(*(self.bar_color if value else theme.rgba(theme.BORDER)))
                RoundedRectangle(
                    pos=(x, baseline),
                    size=(bar_width, height),
                    radius=[dp(4)],
                )


class Bar(Widget):
    value = NumericProperty(0.0)
    bar_color = ListProperty(theme.rgba(theme.ACCENT))

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(8))
        super().__init__(**kwargs)
        with self.canvas:
            self._track_color = Color(*theme.rgba(theme.BORDER_SOFT))
            self._track = RoundedRectangle(radius=[dp(4)])
            self._fill_color = Color(*self.bar_color)
            self._fill = RoundedRectangle(radius=[dp(4)])
        self.bind(pos=self._sync, size=self._sync, value=self._sync,
                  bar_color=self._sync_color)

    def _sync(self, *_):
        self._track.pos = self.pos
        self._track.size = self.size
        width = max(dp(3), self.width * max(0.0, min(1.0, self.value)))
        self._fill.pos = self.pos
        self._fill.size = (width, self.height)

    def _sync_color(self, *_):
        self._fill_color.rgba = self.bar_color


class TriggerRow(BoxLayout):
    def __init__(self, name, count, fraction, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(32))
        kwargs.setdefault("spacing", dp(8))
        super().__init__(**kwargs)
        label = text_label(name, size=12, color=theme.TEXT)
        label.size_hint_x = 0.36
        bar = Bar(value=fraction, bar_color=theme.rgba(theme.ACCENT, 0.85))
        bar.size_hint_x = 0.52
        bar.pos_hint = {"center_y": 0.5}
        amount = text_label(str(count), size=12, color=theme.MUTED, halign="right")
        amount.size_hint_x = 0.12
        self.add_widget(label)
        self.add_widget(bar)
        self.add_widget(amount)


class NavButton(ButtonBehavior, Label):
    active = BooleanProperty(False)

    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(56))
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("font_size", sp(12))
        kwargs.setdefault("bold", True)
        super().__init__(**kwargs)
        self.color = theme.rgba(theme.MUTED)
        with self.canvas:
            self._bar_color = Color(*theme.rgba(theme.ACCENT, 0))
            self._bar = Rectangle(size=(0, dp(2)))
        self.bind(pos=self._sync, size=self._sync, active=self._sync,
                  text=self._sync_text)

    def _sync(self, *_):
        self._bar.pos = (self.x, self.top - dp(2))
        self._bar.size = (self.width if self.active else 0, dp(2))
        self._bar_color.a = 1.0 if self.active else 0.0
        self.text_size = self.size

    def _sync_text(self, *_):
        self.color = theme.rgba(theme.ACCENT if self.active else theme.MUTED)
        self._sync()
