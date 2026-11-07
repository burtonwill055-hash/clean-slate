"""Clean Slate for Android — a small, local-first habit quitting tracker.

Run on the desktop for development with:
    cd mobile && .venv/bin/python main.py
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

from kivy.config import Config
from kivy.utils import platform

if platform not in ("android", "ios"):
    Config.set("graphics", "width", os.environ.get("CS_UI_WIDTH", "420"))
    Config.set("graphics", "height", os.environ.get("CS_UI_HEIGHT", "900"))
    Config.set("graphics", "resizable", "1")

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

import storage
import theme
import widgets as ui


APP_VERSION = "1.0.0"


# ------------------------------------------------------------------ helpers
def money(habit, value):
    return f"{habit.currency}{value:,.0f}"


def when(value: datetime) -> str:
    today = date.today()
    delta = (today - value.date()).days
    clock = value.strftime("%H:%M")
    if delta == 0:
        return f"Today, {clock}"
    if delta == 1:
        return f"Yesterday, {clock}"
    if delta < 7:
        return f"{delta} days ago, {clock}"
    return value.strftime("%b %d, %Y")


def ago(value: datetime) -> str:
    days = (date.today() - value.date()).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    if days < 365:
        months = max(1, days // 30)
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = max(1, days // 365)
    return f"{years} year{'s' if years != 1 else ''} ago"


def milestone_state(days):
    """Return (previous, next, fraction, days remaining)."""
    if days >= theme.MILESTONES[-1]:
        return theme.MILESTONES[-1], theme.MILESTONES[-1], 1.0, 0
    previous = 0
    upcoming = theme.MILESTONES[-1]
    for value in theme.MILESTONES:
        if days < value:
            upcoming = value
            break
        previous = value
    span = max(1, upcoming - previous)
    fraction = max(0.0, min(1.0, (days - previous) / span))
    return previous, upcoming, fraction, upcoming - days


def avatar_for(habit):
    return (habit.name.strip() or "?").lstrip()[:1].upper()


# ------------------------------------------------------------------- dialogs
class HabitDialog(ModalView):
    def __init__(self, app, habit=None, preset=None, **kwargs):
        kwargs.setdefault("auto_dismiss", False)
        kwargs.setdefault("background_color", (0, 0, 0, 0.68))
        kwargs.setdefault("size_hint", (0.92, None))
        super().__init__(**kwargs)
        self.app = app
        self.habit = habit
        self.color = (
            habit.color
            if habit
            else (preset[1] if preset else theme.HABIT_COLORS[0])
        )

        self.card = ui.Card(size_hint=(1, None), padding=dp(18), spacing=dp(11))
        self.card.bind(minimum_height=self.card.setter("height"))
        self.add_widget(self.card)

        self.card.add_widget(
            ui.text_label(
                "Edit habit" if habit else "New habit",
                size=22,
                bold=True,
                height=dp(32),
            )
        )
        self.card.add_widget(
            ui.text_label(
                "No judgement. Just the habit and the date.",
                size=12,
                color=theme.MUTED,
                height=dp(20),
            )
        )

        self.name_field = ui.Field(hint="Habit name")
        if habit:
            self.name_field.text = habit.name
        elif preset and preset[0] != "Something else":
            self.name_field.text = preset[0]
        self.card.add_widget(self.name_field)

        self.date_field = ui.Field(hint="Quit date (YYYY-MM-DD)")
        self.date_field.text = (
            habit.quit_date.isoformat()
            if habit
            else date.today().isoformat()
        )
        self.card.add_widget(self.date_field)

        money_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.cost_field = ui.Field(hint="Daily cost")
        self.cost_field.size_hint_x = 0.64
        self.cost_field.input.input_filter = "float"
        self.cost_field.input.input_type = "number"
        self.currency_field = ui.Field(hint="Currency")
        self.currency_field.size_hint_x = 0.36
        if habit:
            self.cost_field.text = (
                f"{habit.daily_cost:g}" if habit.daily_cost else ""
            )
            self.currency_field.text = habit.currency
        else:
            self.currency_field.text = "$"
        money_row.add_widget(self.cost_field)
        money_row.add_widget(self.currency_field)
        self.card.add_widget(money_row)

        self.card.add_widget(
            ui.text_label(
                "Color", size=11, color=theme.MUTED, height=dp(16)
            )
        )
        colors = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8))
        self.dots = []
        for color in theme.HABIT_COLORS:
            dot = ui.ColorDot(
                color_value=theme.rgba(color), selected=(color == self.color)
            )
            dot.bind(on_release=lambda _dot, value=color: self._pick(value))
            self.dots.append((color, dot))
            colors.add_widget(dot)
        self.card.add_widget(colors)

        self.error = ui.text_label("", size=12, color=theme.DANGER, height=dp(16))
        self.card.add_widget(self.error)

        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        cancel = ui.PillButton(
            text="Cancel",
            fill=theme.rgba(theme.CARD_ALT),
            border=theme.rgba(theme.BORDER),
            text_color=theme.rgba(theme.MUTED),
        )
        cancel.bind(on_release=lambda *_: self.dismiss())
        save = ui.PillButton(
            text="Save habit",
            fill=theme.rgba(theme.ACCENT_DARK),
            border=theme.rgba(theme.ACCENT),
            text_color=theme.rgba(theme.ACCENT),
        )
        save.bind(on_release=lambda *_: self._save())
        actions.add_widget(cancel)
        actions.add_widget(save)
        self.card.add_widget(actions)

        self.bind(on_open=self._size)

    def _pick(self, color):
        self.color = color
        for value, dot in self.dots:
            dot.selected = value == color

    def _size(self, *_):
        Clock.schedule_once(self._relayout, 0.02)

    def _relayout(self, *_):
        self.card.width = max(dp(260), self.width)
        self.card.do_layout()
        self.height = min(self.card.height + dp(4), Window.height * 0.92)
        self.pos = (
            (Window.width - self.width) / 2,
            (Window.height - self.height) / 2,
        )

    def _save(self):
        name = self.name_field.text.strip()
        if not name:
            self.error.text = "Give this habit a name."
            return
        try:
            quit_date = date.fromisoformat(self.date_field.text.strip())
        except ValueError:
            self.error.text = "Use a date like 2026-11-07."
            return
        if quit_date > date.today():
            self.error.text = "The quit date can't be in the future."
            return
        try:
            cost = float(self.cost_field.text.strip() or 0)
        except ValueError:
            self.error.text = "Daily cost must be a number."
            return
        currency = self.currency_field.text.strip() or "$"
        try:
            if self.habit:
                self.app.db.update_habit(
                    self.habit.id,
                    name,
                    self.habit.emoji,
                    self.color,
                    quit_date,
                    cost,
                    currency,
                )
                self.app.show_toast("Habit updated.")
            else:
                habit_id = self.app.db.add_habit(
                    name,
                    "",
                    self.color,
                    quit_date,
                    cost,
                    currency,
                )
                self.app.current_id = habit_id
                self.app.save_settings()
                self.app.show_toast("Habit created. Day one.")
        except Exception as exc:  # noqa: BLE001 - show it instead of crashing
            self.error.text = f"Could not save: {exc}"
            return
        self.dismiss()
        self.app.refresh_all()
        self.app.root.go("main")


class SlipDialog(ModalView):
    def __init__(self, app, habit, on_save, **kwargs):
        kwargs.setdefault("auto_dismiss", False)
        kwargs.setdefault("background_color", (0, 0, 0, 0.68))
        kwargs.setdefault("size_hint", (0.92, None))
        super().__init__(**kwargs)
        self.app = app
        self.habit = habit
        self.on_save = on_save
        self.selected_trigger = ""

        self.card = ui.Card(size_hint=(1, None), padding=dp(18), spacing=dp(11))
        self.card.bind(minimum_height=self.card.setter("height"))
        self.add_widget(self.card)

        self.card.add_widget(
            ui.text_label("Log a slip", size=22, bold=True, height=dp(32))
        )
        self.card.add_widget(
            ui.text_label(
                "A slip is data, not failure. What happened?",
                size=12,
                color=theme.MUTED,
                height=dp(20),
            )
        )
        self.card.add_widget(
            ui.text_label("Trigger", size=11, color=theme.MUTED, height=dp(16))
        )
        grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None)
        rows = (len(theme.TRIGGERS) + 2) // 3
        grid.height = rows * dp(40) + (rows - 1) * dp(8)
        self.chips = []
        for trigger in theme.TRIGGERS:
            chip = ui.SelectPill(text=trigger, height=dp(40), font_size=sp(12))
            chip.bind(
                on_release=lambda _chip, value=trigger: self._choose(value)
            )
            self.chips.append((trigger, chip))
            grid.add_widget(chip)
        self.card.add_widget(grid)

        self.card.add_widget(
            ui.text_label("Note (optional)", size=11, color=theme.MUTED,
                          height=dp(16))
        )
        self.note_field = ui.Field(
            hint="What led to it?", multiline=True
        )
        self.note_field.height = dp(92)
        self.card.add_widget(self.note_field)

        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        cancel = ui.PillButton(
            text="Cancel",
            fill=theme.rgba(theme.CARD_ALT),
            border=theme.rgba(theme.BORDER),
            text_color=theme.rgba(theme.MUTED),
        )
        cancel.bind(on_release=lambda *_: self.dismiss())
        save = ui.PillButton(
            text="Log slip",
            fill=theme.rgba(theme.DANGER_BG),
            border=theme.rgba(theme.DANGER),
            text_color=theme.rgba(theme.DANGER_SOFT),
        )
        save.bind(on_release=lambda *_: self._save())
        actions.add_widget(cancel)
        actions.add_widget(save)
        self.card.add_widget(actions)

        self.bind(on_open=self._size)

    def _choose(self, trigger):
        self.selected_trigger = "" if self.selected_trigger == trigger else trigger
        for value, chip in self.chips:
            chip.active = value == self.selected_trigger

    def _size(self, *_):
        Clock.schedule_once(self._relayout, 0.02)

    def _relayout(self, *_):
        self.card.width = max(dp(260), self.width)
        self.card.do_layout()
        self.height = min(self.card.height + dp(4), Window.height * 0.92)
        self.pos = (
            (Window.width - self.width) / 2,
            (Window.height - self.height) / 2,
        )

    def _save(self):
        self.dismiss()
        self.on_save(self.selected_trigger, self.note_field.text.strip())


class ConfirmDialog(ModalView):
    def __init__(self, app, title, message, on_confirm, ok_text="Delete",
                 **kwargs):
        kwargs.setdefault("auto_dismiss", False)
        kwargs.setdefault("background_color", (0, 0, 0, 0.68))
        kwargs.setdefault("size_hint", (0.9, None))
        super().__init__(**kwargs)
        self.app = app
        self.on_confirm = on_confirm

        self.card = ui.Card(size_hint=(1, None), padding=dp(18), spacing=dp(11))
        self.card.bind(minimum_height=self.card.setter("height"))
        self.add_widget(self.card)

        self.card.add_widget(
            ui.text_label(title, size=20, bold=True, height=dp(30))
        )
        message_label = ui.text_label(
            message, size=13, color=theme.MUTED, height=dp(54),
            halign="left", valign="top",
        )
        self.card.add_widget(message_label)

        actions = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        cancel = ui.PillButton(
            text="Cancel",
            fill=theme.rgba(theme.CARD_ALT),
            border=theme.rgba(theme.BORDER),
            text_color=theme.rgba(theme.MUTED),
        )
        cancel.bind(on_release=lambda *_: self.dismiss())
        confirm = ui.PillButton(
            text=ok_text,
            fill=theme.rgba(theme.DANGER_BG),
            border=theme.rgba(theme.DANGER),
            text_color=theme.rgba(theme.DANGER_SOFT),
        )
        confirm.bind(on_release=lambda *_: self._confirm())
        actions.add_widget(cancel)
        actions.add_widget(confirm)
        self.card.add_widget(actions)

        self.bind(on_open=self._size)

    def _size(self, *_):
        Clock.schedule_once(self._relayout, 0.02)

    def _relayout(self, *_):
        self.card.width = max(dp(260), self.width)
        self.card.do_layout()
        self.height = min(self.card.height + dp(4), Window.height * 0.92)
        self.pos = (
            (Window.width - self.width) / 2,
            (Window.height - self.height) / 2,
        )

    def _confirm(self):
        self.dismiss()
        self.on_confirm()


# ------------------------------------------------------------------- screens
class WelcomeScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

        outer = BoxLayout(orientation="vertical")
        scroll = ScrollView()
        box = BoxLayout(
            orientation="vertical",
            padding=[dp(22), dp(26)],
            spacing=dp(14),
            size_hint_y=None,
        )
        box.bind(minimum_height=box.setter("height"))

        logo = AnchorLayout(
            anchor_x="center", anchor_y="center",
            size_hint_y=None, height=dp(104),
        )
        logo.add_widget(
            Image(
                source=str(Path(__file__).parent / "assets" / "icon.png"),
                size_hint=(None, None),
                size=(dp(96), dp(96)),
            )
        )
        box.add_widget(logo)

        box.add_widget(
            ui.text_label(
                "Clean Slate", size=30, bold=True, halign="center",
                height=dp(40),
            )
        )
        box.add_widget(
            ui.text_label(
                "Quit one habit at a time.",
                size=15, color=theme.MUTED, halign="center", height=dp(24),
            )
        )
        intro = ui.text_label(
            "Track clean days, notice your triggers, and watch the money add up. "
            "Everything stays on this device.",
            size=13, color=theme.MUTED, halign="center", height=dp(64),
        )
        box.add_widget(intro)

        box.add_widget(
            ui.text_label(
                "Start with", size=12, color=theme.MUTED, bold=True,
                height=dp(22),
            )
        )
        grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None)
        rows = (len(theme.PRESETS) + 1) // 2
        grid.height = rows * dp(46) + (rows - 1) * dp(10)
        for name, color in theme.PRESETS:
            button = ui.PillButton(
                text=name,
                height=dp(46),
                font_size=sp(13),
                fill=theme.rgba(theme.CARD),
                border=theme.rgba(theme.BORDER),
                text_color=theme.rgba(theme.TEXT),
            )
            button.bind(
                on_release=lambda _b, n=name, c=color: self.app.open_habit_dialog(
                    preset=(n, c)
                )
            )
            grid.add_widget(button)
        box.add_widget(grid)

        box.add_widget(
            ui.text_label(
                "No account. No cloud. No shame.",
                size=11, color=theme.FAINT, halign="center", height=dp(20),
            )
        )
        box.add_widget(Widget(size_hint_y=None, height=dp(8)))

        scroll.add_widget(box)
        outer.add_widget(scroll)
        self.add_widget(outer)


class MainScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.scroll = ScrollView()
        self.box = BoxLayout(
            orientation="vertical",
            padding=[dp(18), dp(16)],
            spacing=dp(12),
            size_hint_y=None,
        )
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        self.add_widget(self.scroll)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        habit = self.app.current_habit()
        if habit is None:
            return
        stats = self.app.db.stats(habit.id)
        self.box.clear_widgets()

        header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        header.add_widget(
            ui.text_label("Today", size=26, bold=True, height=dp(36))
        )
        add_wrap = AnchorLayout(
            anchor_x="right", anchor_y="center",
            size_hint=(None, 1), width=dp(92),
        )
        add_button = ui.PillButton(
            text="+ Habit",
            size_hint=(None, None),
            size=(dp(92), dp(38)),
            font_size=sp(12),
            fill=theme.rgba(theme.CARD_ALT),
            border=theme.rgba(theme.BORDER),
            text_color=theme.rgba(theme.MUTED),
        )
        add_button.bind(on_release=lambda *_: self.app.open_habit_dialog())
        add_wrap.add_widget(add_button)
        header.add_widget(add_wrap)
        self.box.add_widget(header)

        self.box.add_widget(self._habit_switcher(habit))

        previous, upcoming, fraction, remaining = milestone_state(stats.days_clean)
        if remaining == 0:
            footer = f"Best {stats.best_streak} days · all milestones reached"
        else:
            footer = (
                f"Best {stats.best_streak} days · next stop {upcoming} days"
            )
        streak = ui.StreakCard()
        streak.refresh(
            habit.name,
            stats.days_clean,
            fraction,
            habit.color,
            footer,
        )
        self.box.add_widget(streak)

        cards = BoxLayout(size_hint_y=None, height=dp(78), spacing=dp(10))
        best = ui.StatCard("best streak")
        best.set(f"{stats.best_streak}d")
        slips = ui.StatCard("slips logged")
        slips.set(f"{stats.total_slips}")
        saved = ui.StatCard("money saved")
        saved.set(money(habit, stats.money_saved))
        for card in (best, slips, saved):
            cards.add_widget(card)
        self.box.add_widget(cards)

        actions = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        slip = ui.PillButton(
            text="I slipped",
            font_size=sp(15),
            fill=theme.rgba(theme.DANGER_BG),
            border=theme.rgba(theme.DANGER),
            text_color=theme.rgba(theme.DANGER_SOFT),
            fill_down=theme.rgba(theme.mix(theme.DANGER_BG, theme.DANGER, 0.18)),
        )
        slip.bind(
            on_release=lambda *_: self.app.open_slip_dialog(
                habit, self.app.refresh_all
            )
        )
        undo = ui.PillButton(
            text="Undo",
            size_hint=(None, 1),
            width=dp(88),
            font_size=sp(13),
            fill=theme.rgba(theme.CARD_ALT),
            border=theme.rgba(theme.BORDER),
            text_color=theme.rgba(theme.MUTED),
        )
        last_slip = self.app.db.last_slip(habit.id)
        undo.disabled = last_slip is None
        undo.opacity = 0.45 if last_slip is None else 1.0
        if last_slip is not None:
            undo.bind(
                on_release=lambda *_: self.app.confirm_delete_slip(
                    last_slip, self.app.refresh_all
                )
            )
        actions.add_widget(slip)
        actions.add_widget(undo)
        self.box.add_widget(actions)

        milestone = ui.Card(size_hint_y=None, height=dp(118))
        milestone.add_widget(
            ui.text_label(
                f"Next milestone · {upcoming} days",
                size=12,
                color=theme.MUTED,
                height=dp(18),
            )
        )
        row = BoxLayout(size_hint_y=None, height=dp(22))
        row.add_widget(
            ui.text_label(
                "All milestones reached" if remaining == 0
                else f"{remaining} more day{'s' if remaining != 1 else ''}",
                size=15,
                bold=True,
                height=dp(22),
            )
        )
        row.add_widget(
            ui.text_label(
                f"{stats.days_clean} / {upcoming}",
                size=12,
                color=theme.MUTED,
                halign="right",
                height=dp(22),
            )
        )
        milestone.add_widget(row)
        bar = ui.Bar(value=fraction, bar_color=theme.rgba(habit.color))
        milestone.add_widget(bar)
        self.box.add_widget(milestone)

        last = ui.Card(size_hint_y=None, height=dp(96))
        last.add_widget(
            ui.text_label(
                "Last slip", size=12, color=theme.MUTED, height=dp(18)
            )
        )
        if stats.last_slip is None:
            last_text = "None yet. Every clean day counts."
        else:
            label = (
                last_slip.trigger.strip() if last_slip else ""
            ) or "no trigger noted"
            last_text = (
                f"{ago(stats.last_slip).capitalize()} · {label}"
            )
        last.add_widget(
            ui.text_label(last_text, size=15, bold=True, height=dp(24))
        )
        last.add_widget(
            ui.text_label(
                f"Tracking since {storage.fmt_date(habit.quit_date)}",
                size=11,
                color=theme.FAINT,
                height=dp(18),
            )
        )
        self.box.add_widget(last)

    def _habit_switcher(self, current):
        scroll = ScrollView(
            size_hint_y=None,
            height=dp(44),
            do_scroll_y=False,
            bar_width=0,
        )
        row = BoxLayout(size_hint=(None, 1), spacing=dp(8))
        row.bind(minimum_width=row.setter("width"))
        for habit in self.app.habits():
            width = max(dp(76), min(dp(190), dp(34) + len(habit.name) * dp(8.2)))
            chip = ui.SelectPill(
                text=f"[color={habit.color}]•[/color]  {habit.name}",
                markup=True,
                size_hint=(None, 1),
                width=width,
                font_size=sp(13),
                active=(habit.id == current.id),
            )
            chip.bind(
                on_release=lambda _chip, value=habit.id: self.app.set_current(
                    value
                )
            )
            row.add_widget(chip)
        new_chip = ui.SelectPill(
            text="+ New",
            size_hint=(None, 1),
            width=dp(78),
            font_size=sp(12),
        )
        new_chip.bind(on_release=lambda *_: self.app.open_habit_dialog())
        row.add_widget(new_chip)
        scroll.add_widget(row)
        return scroll


class HistoryScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.scroll = ScrollView()
        self.box = BoxLayout(
            orientation="vertical",
            padding=[dp(18), dp(16)],
            spacing=dp(12),
            size_hint_y=None,
        )
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        self.add_widget(self.scroll)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        habit = self.app.current_habit()
        if habit is None:
            return
        stats = self.app.db.stats(habit.id)
        self.box.clear_widgets()

        self.box.add_widget(
            ui.text_label("History", size=26, bold=True, height=dp(36))
        )
        self.box.add_widget(
            ui.text_label(
                f"{habit.name} · tracking since {storage.fmt_date(habit.quit_date)}",
                size=12,
                color=theme.MUTED,
                height=dp(20),
            )
        )

        calendar = ui.Card(size_hint_y=None, height=dp(212))
        calendar.add_widget(
            ui.text_label("Clean calendar", size=13, color=theme.MUTED,
                          bold=True, height=dp(18))
        )
        calendar.add_widget(
            ui.text_label(
                "Last 18 weeks", size=11, color=theme.FAINT, height=dp(16)
            )
        )
        heat = ui.Heatmap()
        heat.refresh(stats.slip_dates, habit.quit_date)
        calendar.add_widget(heat)
        legend = BoxLayout(size_hint_y=None, height=dp(18), spacing=dp(12))
        legend.add_widget(
            ui.text_label(
                f"[color={theme.ACCENT}]•[/color]  clean",
                markup=True, size=11, color=theme.MUTED, height=dp(18),
            )
        )
        legend.add_widget(
            ui.text_label(
                f"[color={theme.DANGER}]•[/color]  slip",
                markup=True, size=11, color=theme.MUTED, height=dp(18),
            )
        )
        calendar.add_widget(legend)
        self.box.add_widget(calendar)

        weekly = ui.Card(size_hint_y=None, height=dp(196))
        weekly.add_widget(
            ui.text_label("Slips per week", size=13, color=theme.MUTED,
                          bold=True, height=dp(18))
        )
        weekly.add_widget(
            ui.text_label(
                "Last 12 weeks", size=11, color=theme.FAINT, height=dp(16)
            )
        )
        bars = ui.WeeklyBars()
        bars.refresh(stats.weekly_slips)
        weekly.add_widget(bars)
        scale = BoxLayout(size_hint_y=None, height=dp(16))
        scale.add_widget(
            ui.text_label("12 weeks ago", size=10, color=theme.FAINT,
                          height=dp(16))
        )
        scale.add_widget(
            ui.text_label("now", size=10, color=theme.FAINT,
                          halign="right", height=dp(16))
        )
        weekly.add_widget(scale)
        self.box.add_widget(weekly)

        trig_rows = len(stats.triggers)
        triggers = ui.Card(
            size_hint_y=None,
            height=dp(66 + max(1, trig_rows) * 32 + 12),
        )
        triggers.add_widget(
            ui.text_label("What sets you off", size=13, color=theme.MUTED,
                          bold=True, height=dp(18))
        )
        if not stats.triggers:
            triggers.add_widget(
                ui.text_label(
                    "No slips logged yet, so there is nothing to analyze.",
                    size=12, color=theme.FAINT, height=dp(40),
                )
            )
        else:
            peak = max(count for _, count in stats.triggers)
            for name, count in stats.triggers:
                triggers.add_widget(
                    ui.TriggerRow(name, count, count / peak)
                )
        self.box.add_widget(triggers)

        slips = self.app.db.slips(habit.id, limit=25)
        log = ui.Card(
            size_hint_y=None,
            height=dp(62 + max(1, min(len(slips), 25)) * 58 + 8),
        )
        log.add_widget(
            ui.text_label("Slip log", size=13, color=theme.MUTED,
                          bold=True, height=dp(18))
        )
        if not slips:
            log.add_widget(
                ui.text_label(
                    "No slips yet. Keep going.",
                    size=12, color=theme.FAINT, height=dp(40),
                )
            )
        else:
            for slip in slips:
                log.add_widget(self._slip_row(slip))
        self.box.add_widget(log)

        bottom = ui.text_label(
            f"v{APP_VERSION} · local-only data",
            size=10, color=theme.FAINT, halign="center", height=dp(20),
        )
        self.box.add_widget(bottom)

    def _slip_row(self, slip):
        row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(8))
        info = BoxLayout(orientation="vertical", spacing=dp(1))
        info.add_widget(
            ui.text_label(
                f"{when(slip.at)} · {slip.trigger.strip() or 'Not noted'}",
                size=12, bold=True, height=dp(20),
            )
        )
        note = ui.text_label(
            slip.note.strip() or "No note",
            size=11, color=theme.MUTED, height=dp(18), shorten=True,
        )
        info.add_widget(note)
        row.add_widget(info)

        remove = ui.PillButton(
            text="×",
            size_hint=(None, 1),
            width=dp(38),
            font_size=sp(19),
            fill=theme.rgba(theme.CARD_ALT),
            border=theme.rgba(theme.BORDER),
            text_color=theme.rgba(theme.MUTED),
        )
        remove.bind(
            on_release=lambda *_, entry=slip: self.app.confirm_delete_slip(
                entry, self.app.refresh_all
            )
        )
        row.add_widget(remove)
        return row


class HabitsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.scroll = ScrollView()
        self.box = BoxLayout(
            orientation="vertical",
            padding=[dp(18), dp(16)],
            spacing=dp(12),
            size_hint_y=None,
        )
        self.box.bind(minimum_height=self.box.setter("height"))
        self.scroll.add_widget(self.box)
        self.add_widget(self.scroll)

    def on_pre_enter(self, *_):
        self.refresh()

    def refresh(self):
        self.box.clear_widgets()
        header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        header.add_widget(
            ui.text_label("Habits", size=26, bold=True, height=dp(36))
        )
        add_wrap = AnchorLayout(
            anchor_x="right", anchor_y="center",
            size_hint=(None, 1), width=dp(92),
        )
        add_button = ui.PillButton(
            text="+ New",
            size_hint=(None, None),
            size=(dp(92), dp(38)),
            font_size=sp(12),
            fill=theme.rgba(theme.ACCENT_DARK),
            border=theme.rgba(theme.ACCENT),
            text_color=theme.rgba(theme.ACCENT),
        )
        add_button.bind(on_release=lambda *_: self.app.open_habit_dialog())
        add_wrap.add_widget(add_button)
        header.add_widget(add_wrap)
        self.box.add_widget(header)

        habits = self.app.habits()
        if not habits:
            self.box.add_widget(
                ui.text_label(
                    "No habits yet.", size=14, color=theme.MUTED,
                    halign="center", height=dp(40),
                )
            )
            return

        current = self.app.current_habit()
        for habit in habits:
            stats = self.app.db.stats(habit.id)
            card = ui.Card()
            row = BoxLayout(
                size_hint_y=None, height=dp(60), spacing=dp(12)
            )
            avatar = ui.Avatar(
                text=avatar_for(habit),
                fill=theme.rgba(habit.color, 0.16),
                color=theme.rgba(habit.color),
            )
            avatar_wrap = AnchorLayout(
                anchor_x="center",
                anchor_y="center",
                size_hint=(None, 1),
                width=dp(40),
            )
            avatar_wrap.add_widget(avatar)
            row.add_widget(avatar_wrap)
            text = BoxLayout(orientation="vertical", spacing=dp(2))
            text.add_widget(
                ui.text_label(habit.name, size=16, bold=True, height=dp(22))
            )
            text.add_widget(
                ui.text_label(
                    f"{stats.days_clean} days clean · best {stats.best_streak}",
                    size=12,
                    color=theme.MUTED,
                    height=dp(18),
                )
            )
            if current and habit.id == current.id:
                text.add_widget(
                    ui.text_label(
                        "Currently viewing", size=10, color=theme.ACCENT,
                        height=dp(16),
                    )
                )
            else:
                text.add_widget(
                    ui.text_label(
                        f"Since {storage.fmt_date(habit.quit_date)}",
                        size=10, color=theme.FAINT, height=dp(16),
                    )
                )
            row.add_widget(text)
            card.add_widget(row)

            actions = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(8))
            view = ui.PillButton(
                text="View",
                height=dp(34),
                font_size=sp(11),
                fill=theme.rgba(theme.CARD_ALT),
                border=theme.rgba(theme.BORDER),
                text_color=theme.rgba(theme.TEXT),
            )
            view.bind(
                on_release=lambda _b, value=habit.id: self._view(value)
            )
            edit = ui.PillButton(
                text="Edit",
                height=dp(34),
                font_size=sp(11),
                fill=theme.rgba(theme.CARD_ALT),
                border=theme.rgba(theme.BORDER),
                text_color=theme.rgba(theme.TEXT),
            )
            edit.bind(
                on_release=lambda _b, value=habit: self.app.open_habit_dialog(
                    habit=value
                )
            )
            delete = ui.PillButton(
                text="Delete",
                height=dp(34),
                font_size=sp(11),
                fill=theme.rgba(theme.DANGER_BG),
                border=theme.rgba(theme.DANGER),
                text_color=theme.rgba(theme.DANGER_SOFT),
            )
            delete.bind(
                on_release=lambda _b, value=habit: self.app.confirm_delete_habit(
                    value
                )
            )
            actions.add_widget(view)
            actions.add_widget(edit)
            actions.add_widget(delete)
            card.add_widget(actions)
            self.box.add_widget(card)

        self.box.add_widget(
            ui.text_label(
                "All data is stored on this device.",
                size=11, color=theme.FAINT, halign="center", height=dp(24),
            )
        )

    def _view(self, habit_id):
        self.app.set_current(habit_id)
        self.app.root.go("main")


# ---------------------------------------------------------------------- root
class Root(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.body = BoxLayout(orientation="vertical", size_hint=(1, 1))
        self.sm = ScreenManager(transition=NoTransition())
        self.welcome = WelcomeScreen(app, name="welcome")
        self.main = MainScreen(app, name="main")
        self.history = HistoryScreen(app, name="history")
        self.habits = HabitsScreen(app, name="habits")
        for screen in (self.welcome, self.main, self.history, self.habits):
            self.sm.add_widget(screen)
        self.body.add_widget(self.sm)

        self.nav = BoxLayout(size_hint_y=None, height=dp(58))
        with self.nav.canvas.before:
            from kivy.graphics import Color, Rectangle

            Color(*theme.rgba(theme.SIDEBAR))
            self._nav_bg = Rectangle()
            Color(*theme.rgba(theme.BORDER_SOFT))
            self._nav_line = Rectangle()
        self.nav.bind(pos=self._nav_sync, size=self._nav_sync)
        self.nav_buttons = {}
        for key, label in (("main", "Today"), ("history", "History"),
                           ("habits", "Habits")):
            button = ui.NavButton(text=label, active=(key == "main"))
            button.bind(on_release=lambda _b, value=key: self.go(value))
            self.nav_buttons[key] = button
            self.nav.add_widget(button)
        self.body.add_widget(self.nav)
        self.add_widget(self.body)

        self.toast = ui.Card(
            size_hint=(None, None),
            size=(dp(300), dp(44)),
            padding=[dp(10), dp(4)],
            opacity=0,
        )
        self.toast_label = ui.text_label(
            "", size=12, halign="center", height=dp(28)
        )
        self.toast.add_widget(self.toast_label)
        self.add_widget(self.toast)
        self._toast_event = None

        self.bind(size=self._place_toast, pos=self._place_toast)
        self.go("main" if self.app.habits() else "welcome")

    def _nav_sync(self, *_):
        self._nav_bg.pos = self.nav.pos
        self._nav_bg.size = self.nav.size
        self._nav_line.pos = (self.nav.x, self.nav.top - dp(1))
        self._nav_line.size = (self.nav.width, dp(1))

    def _place_toast(self, *_):
        self.toast.width = min(self.width - dp(28), dp(420))
        self.toast.x = (self.width - self.toast.width) / 2
        base = self.nav.height if self.nav.opacity else 0
        self.toast.y = base + dp(12)

    def go(self, name):
        if name != "welcome" and not self.app.habits():
            name = "welcome"
        self.sm.current = name
        for key, button in self.nav_buttons.items():
            button.active = key == name
        visible = name != "welcome"
        self.nav.opacity = 1 if visible else 0
        self.nav.disabled = not visible
        self.nav.height = dp(58) if visible else 0
        self._place_toast()

    def show_toast(self, text):
        self.toast_label.text = text
        self.toast.opacity = 1
        if self._toast_event is not None:
            self._toast_event.cancel()
        self._toast_event = Clock.schedule_once(self._hide_toast, 2.4)

    def _hide_toast(self, *_):
        Animation(opacity=0, d=0.28).start(self.toast)
        self._toast_event = None


# ----------------------------------------------------------------------- app
class CleanSlateApp(App):
    name = "clean-slate"
    title = "Clean Slate"

    def build(self):
        Window.clearcolor = theme.rgba(theme.BG)
        Window.softinput_mode = "below_target"
        self.data_dir = Path(self.user_data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        override = os.environ.get("CLEAN_SLATE_DB")
        if override:
            db_path = Path(override)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.data_dir = db_path.parent
        else:
            db_path = self.data_dir / "clean-slate.db"
        self.db = storage.Database(db_path)
        self.settings_path = self.data_dir / "settings.json"
        self.current_id = None
        self._load_settings()
        self.modal = None
        self.root = Root(self)
        Window.bind(on_keyboard=self._on_key)
        return self.root

    # ------------------------------------------------------------- settings
    def _load_settings(self):
        try:
            data = json.loads(self.settings_path.read_text())
            self.current_id = data.get("current_habit_id")
        except (OSError, ValueError):
            self.current_id = None

    def save_settings(self):
        try:
            self.settings_path.write_text(
                json.dumps({"current_habit_id": self.current_id})
            )
        except OSError:
            pass

    # ----------------------------------------------------------------- data
    def habits(self):
        return self.db.habits()

    def current_habit(self):
        habits = self.habits()
        if not habits:
            self.current_id = None
            return None
        for habit in habits:
            if habit.id == self.current_id:
                return habit
        self.current_id = habits[0].id
        self.save_settings()
        return habits[0]

    def set_current(self, habit_id):
        self.current_id = habit_id
        self.save_settings()
        self.refresh_all()

    def refresh_all(self):
        self.root.main.refresh()
        self.root.history.refresh()
        self.root.habits.refresh()

    # --------------------------------------------------------------- dialogs
    def open_habit_dialog(self, habit=None, preset=None):
        dialog = HabitDialog(self, habit=habit, preset=preset)
        self._show_modal(dialog)

    def open_slip_dialog(self, habit, after):
        def save(trigger, note):
            self.db.add_slip(habit.id, datetime.now(), trigger, note)
            after()
            self.show_toast("Slip logged. Day one starts again.")

        dialog = SlipDialog(self, habit, on_save=save)
        self._show_modal(dialog)

    def confirm(self, title, message, on_confirm, ok_text="Delete"):
        dialog = ConfirmDialog(
            self, title, message, on_confirm, ok_text=ok_text
        )
        self._show_modal(dialog)

    def confirm_delete_slip(self, slip, after):
        def remove():
            self.db.delete_slip(slip.id)
            after()
            self.show_toast("Slip removed.")

        self.confirm(
            "Delete this slip?",
            f"{when(slip.at)} · {slip.trigger.strip() or 'Not noted'}. "
            "The streak will be recalculated.",
            remove,
        )

    def confirm_delete_habit(self, habit):
        count = len(self.db.slips(habit.id))

        def remove():
            self.db.delete_habit(habit.id)
            if self.current_id == habit.id:
                self.current_id = None
                self.save_settings()
            self.refresh_all()
            self.root.go("main" if self.habits() else "welcome")
            self.show_toast("Habit deleted.")

        self.confirm(
            f"Delete {habit.name}?",
            f"This also removes {count} logged slip{'s' if count != 1 else ''}. "
            "This cannot be undone.",
            remove,
        )

    def _show_modal(self, dialog):
        self.modal = dialog

        def cleared(*_):
            if self.modal is dialog:
                self.modal = None

        dialog.bind(on_dismiss=cleared)
        dialog.open()

    def show_toast(self, text):
        self.root.show_toast(text)

    # -------------------------------------------------------------- keyboard
    def _on_key(self, _window, key, *_args):
        if key == 27:
            if self.modal is not None:
                self.modal.dismiss()
                return True
            if self.habits() and self.root.sm.current != "main":
                self.root.go("main")
                return True
        return False

    def on_stop(self):
        self.save_settings()
        self.db.close()


if __name__ == "__main__":
    CleanSlateApp().run()
