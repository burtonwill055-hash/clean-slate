"""Headless interaction test for the Kivy mobile UI.

Run with:
    cd mobile && xvfb-run -a -s "-screen 0 420x900x24" \
        .venv/bin/python dev/test_ui.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import traceback
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from kivy.config import Config

SCREEN_W = int(os.environ.get("CS_UI_WIDTH", "420"))
SCREEN_H = int(os.environ.get("CS_UI_HEIGHT", "900"))
Config.set("graphics", "width", str(SCREEN_W))
Config.set("graphics", "height", str(SCREEN_H))

TMP = Path(tempfile.mkdtemp(prefix="cs-mobile-ui-", dir="/tmp/opencode"))
os.environ["CLEAN_SLATE_DB"] = str(TMP / "clean-slate.db")

from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock

import main as app_main
from kivy.core.window import Window

SHOTS = Path("/tmp/opencode/cs-mobile-shots")
SHOTS.mkdir(parents=True, exist_ok=True)
for _old in SHOTS.glob("*.png"):
    _old.unlink()


failures: list[str] = []
current = "start"


class Handler(ExceptionHandler):
    def handle_exception(self, inst):
        failures.append(f"{current}: uncaught {inst!r}")
        traceback.print_exception(type(inst), inst, inst.__traceback__)
        return ExceptionManager.RAISE


ExceptionManager.add_handler(Handler())


def check(condition, message):
    if not condition:
        failures.append(f"{current}: {message}")


def walk(widget):
    yield widget
    for child in widget.children:
        yield from walk(child)


def find_text(root, text):
    return [w for w in walk(root) if getattr(w, "text", None) == text]


def find_button(root, text):
    for widget in walk(root):
        if (
            widget.__class__.__name__ in ("PillButton", "SelectPill", "NavButton")
            and getattr(widget, "text", None) == text
        ):
            return widget
    return None


def click(root, text, what=None):
    button = find_button(root, text)
    check(button is not None, f"no button labelled {text!r} ({what or ''})")
    if button is not None:
        button.dispatch("on_release")
    return button


def shot(name):
    Window.screenshot(name=str(SHOTS / f"{name}.png"))


def screen_box(screen):
    return screen.box


# --------------------------------------------------------------------- steps
quit_date = date.today() - timedelta(days=10)
steps = []


def step(delay=0.3):
    def register(fn):
        steps.append((delay, fn))
        return fn

    return register


@step(0.6)
def s01_welcome():
    app = app_main.CleanSlateApp.get_running_app()
    check(app.root.sm.current == "welcome", "fresh install should open Welcome")
    check(app.root.nav.height == 0, "navigation should be hidden on Welcome")
    check(app.habits() == [], "fresh database should have no habits")
    # Give the first frame time to render before grabbing it, then open the
    # habit dialog after the capture so the screenshot shows Welcome.
    Clock.schedule_once(
        lambda *_: Window.screenshot(name=str(SHOTS / "01-welcome.png")), 0.2
    )
    Clock.schedule_once(
        lambda *_: click(app.root.welcome, "Smoking", "welcome preset"), 0.35
    )


@step(0.4)
def s02_create_habit():
    app = app_main.CleanSlateApp.get_running_app()
    dialog = app.modal
    check(isinstance(dialog, app_main.HabitDialog), "habit dialog should be open")
    if not isinstance(dialog, app_main.HabitDialog):
        return
    dialog._relayout()
    shot("02-habit-dialog")
    check(dialog.card.height > 300, f"dialog card too short: {dialog.card.height}")
    check(
        dialog.card.width >= SCREEN_W * 0.85,
        f"dialog card too narrow: {dialog.card.width}",
    )
    check(
        dialog.card.x >= 0 and dialog.card.right <= app.root.width + 1,
        "dialog card should fit horizontally",
    )
    check(dialog.name_field.text == "Smoking", "preset should fill the name")
    dialog.date_field.text = quit_date.isoformat()
    dialog.cost_field.text = "5"
    dialog.currency_field.text = "$"
    click(dialog, "Save habit", "habit dialog")


@step(0.4)
def s03_main_screen():
    app = app_main.CleanSlateApp.get_running_app()
    shot("03-today")
    habit = app.current_habit()
    check(habit is not None and habit.name == "Smoking", "habit should be saved")
    check(app.root.sm.current == "main", "saving a first habit should open Today")
    check(app.root.nav.height > 0, "navigation should be visible")
    stats = app.db.stats(habit.id)
    check(stats.days_clean == 10, f"expected 10 clean days, got {stats.days_clean}")
    check(stats.money_saved == 50, f"expected $50 saved, got {stats.money_saved}")
    cards = [w for w in walk(app.root.main) if w.__class__.__name__ == "StreakCard"]
    check(bool(cards), "streak card missing")
    if cards:
        card = cards[0]
        check(card.days.text == "10", f"streak card shows {card.days.text}")
        check(card.height >= 250, f"streak card is too short: {card.height}")
        check(
            abs(card.width - (app.root.width - 36)) < 3,
            f"card should fill width: {card.width} vs {app.root.width}",
        )
    undo = find_text(app.root.main, "Undo")
    check(bool(undo), "undo button missing")
    if undo:
        check(undo[0].disabled, "undo should be disabled with no slips")
    click(app.root.main, "I slipped", "today screen")


@step(0.4)
def s04_log_slip():
    app = app_main.CleanSlateApp.get_running_app()
    dialog = app.modal
    check(isinstance(dialog, app_main.SlipDialog), "slip dialog should be open")
    if not isinstance(dialog, app_main.SlipDialog):
        return
    dialog._relayout()
    shot("04-slip-dialog")
    check(dialog.card.height > 300, f"slip dialog too short: {dialog.card.height}")
    click(dialog, "Stress", "slip trigger")
    dialog.note_field.text = "after lunch"
    click(dialog, "Log slip", "slip dialog")


@step(0.4)
def s05_slip_state():
    app = app_main.CleanSlateApp.get_running_app()
    habit = app.current_habit()
    slips = app.db.slips(habit.id)
    check(len(slips) == 1, f"expected 1 slip, got {len(slips)}")
    if slips:
        check(slips[0].trigger == "Stress", "trigger should be saved")
        check(slips[0].note == "after lunch", "note should be saved")
    stats = app.db.stats(habit.id)
    check(stats.days_clean == 0, f"slip today should reset streak, got {stats.days_clean}")
    undo = find_text(app.root.main, "Undo")
    check(bool(undo) and not undo[0].disabled, "undo should be enabled after a slip")
    app.root.go("history")


@step(0.4)
def s06_history():
    app = app_main.CleanSlateApp.get_running_app()
    check(app.root.sm.current == "history", "history screen should be visible")
    shot("05-history")
    box = screen_box(app.root.history)
    check(box.height > app.root.sm.height, "history should be scrollable")
    check(
        len(find_text(app.root.history, "Slip log")) == 1,
        "slip log card missing",
    )
    check(
        any("Stress" in str(getattr(w, "text", "")) for w in walk(app.root.history)),
        "slip row should mention the trigger",
    )
    heatmaps = [w for w in walk(app.root.history) if w.__class__.__name__ == "Heatmap"]
    check(bool(heatmaps), "heatmap missing")
    if heatmaps:
        check(len(heatmaps[0].canvas.children) > 0, "heatmap should draw cells")
        check(heatmaps[0].width > 200, f"heatmap too narrow: {heatmaps[0].width}")
    app.root.nav_buttons["main"].dispatch("on_release")
    check(app.root.sm.current == "main", "nav button should open Today")
    click(app.root.main, "Undo", "today screen")


@step(0.4)
def s07_undo():
    app = app_main.CleanSlateApp.get_running_app()
    dialog = app.modal
    check(isinstance(dialog, app_main.ConfirmDialog), "confirm dialog should open")
    if isinstance(dialog, app_main.ConfirmDialog):
        click(dialog, "Delete", "confirm dialog")
    habit = app.current_habit()
    check(app.db.slips(habit.id) == [], "undo should remove the slip")
    stats = app.db.stats(habit.id)
    check(stats.days_clean == 10, f"streak should recover, got {stats.days_clean}")
    app.open_habit_dialog(preset=("Sugar", "#fcd34d"))


@step(0.4)
def s08_second_habit():
    app = app_main.CleanSlateApp.get_running_app()
    dialog = app.modal
    check(isinstance(dialog, app_main.HabitDialog), "second habit dialog missing")
    if isinstance(dialog, app_main.HabitDialog):
        dialog.date_field.text = date.today().isoformat()
        dialog._save()
    habits = app.habits()
    check(len(habits) == 2, f"expected 2 habits, got {len(habits)}")
    check(
        app.current_habit().name == "Sugar",
        "new habit should become current",
    )
    first = [h for h in habits if h.name == "Smoking"][0]
    app.set_current(first.id)
    check(app.current_habit().name == "Smoking", "switch should change current habit")
    app.open_habit_dialog(habit=app.current_habit())


@step(0.4)
def s09_edit_habit():
    app = app_main.CleanSlateApp.get_running_app()
    dialog = app.modal
    check(isinstance(dialog, app_main.HabitDialog), "edit dialog missing")
    if isinstance(dialog, app_main.HabitDialog):
        check(dialog.name_field.text == "Smoking", "edit should fill the name")
        dialog.name_field.text = "Cigarettes"
        dialog._save()
    names = sorted(h.name for h in app.habits())
    check(names == ["Cigarettes", "Sugar"], f"unexpected habits: {names}")
    app.root.go("habits")


@step(0.4)
def s10_habits_screen():
    app = app_main.CleanSlateApp.get_running_app()
    check(app.root.sm.current == "habits", "habits screen should be visible")
    cards = [
        w for w in app.root.habits.box.children
        if w.__class__.__name__ == "Card"
    ]
    check(len(cards) == 2, f"expected 2 habit cards, got {len(cards)}")
    for card in cards:
        check(card.height >= 120, f"habit card is too short: {card.height}")
    shot("06-habits")
    sugar = [h for h in app.habits() if h.name == "Sugar"][0]
    app.confirm_delete_habit(sugar)


@step(0.4)
def s11_delete_habit():
    app = app_main.CleanSlateApp.get_running_app()
    dialog = app.modal
    check(isinstance(dialog, app_main.ConfirmDialog), "delete confirm missing")
    if isinstance(dialog, app_main.ConfirmDialog):
        dialog._confirm()
    names = [h.name for h in app.habits()]
    check(names == ["Cigarettes"], f"delete failed: {names}")
    check(app.current_habit().name == "Cigarettes", "current habit should survive")


@step(0.4)
def s12_back_button():
    app = app_main.CleanSlateApp.get_running_app()
    check(app.root.sm.current == "main", "deleting a habit should return to Today")
    app.root.go("habits")
    check(app.root.sm.current == "habits", "should be on Habits")
    Window.dispatch("on_keyboard", 27, 0, None, [])
    check(app.root.sm.current == "main", "back should return to Today")
    click(app.root.main, "I slipped", "today screen")
    check(app.modal is not None, "slip dialog should open before back test")
    Window.dispatch("on_keyboard", 27, 0, None, [])
    check(app.modal is None, "back should close an open dialog")
    check(app.root.sm.current == "main", "closing a dialog should stay on Today")


@step(0.4)
def s13_final():
    app = app_main.CleanSlateApp.get_running_app()
    habit = app.current_habit()
    stats = app.db.stats(habit.id)
    check(stats.days_clean == 10, "streak should still be 10")
    check(app.root.nav.height == 58, f"nav height {app.root.nav.height}")
    check(
        app.root.toast.y <= app.root.height - app.root.nav.height,
        "toast should float above the navigation bar",
    )
    app.stop()


def run_next(*_):
    if not steps:
        return
    delay, fn = steps.pop(0)
    global current
    current = fn.__name__
    try:
        fn()
    except Exception as exc:  # noqa: BLE001 - report instead of crashing
        failures.append(f"{current}: {exc!r}")
        traceback.print_exc()
    Clock.schedule_once(run_next, delay)


def analyze_shots():
    from PIL import Image

    expected = {
        "01-welcome": 15,
        "02-habit-dialog": 500,
        "03-today": 1000,
        "04-slip-dialog": 0,
        "05-history": 1000,
        "06-habits": 300,
    }
    for name, minimum_accent in expected.items():
        matches = sorted(SHOTS.glob(f"{name}*.png"))
        if not matches:
            failures.append(f"shots: missing {name}.png")
            continue
        path = matches[0]
        image = Image.open(path).convert("RGB")
        check(
            image.size == (SCREEN_W, SCREEN_H),
            f"{name}: unexpected size {image.size}",
        )
        colors = image.getcolors(maxcolors=1_000_000) or []
        check(len(colors) > 20, f"{name}: frame looks blank ({len(colors)} colors)")
        accent = 0
        for count, (red, green, blue) in colors:
            if green > 120 and green > red + 20 and green > blue + 5:
                accent += count
        print(f"shot {name}: {len(colors)} colors, {accent} accent px")
        check(
            accent >= minimum_accent,
            f"{name}: too few accent pixels ({accent} < {minimum_accent})",
        )


def main():
    app = app_main.CleanSlateApp()
    Clock.schedule_once(run_next, 0.5)
    try:
        app.run()
    finally:
        analyze_shots()
        if failures:
            print("\nFAILURES")
            for failure in failures:
                print(" -", failure)
        else:
            print("\nALL MOBILE UI CHECKS PASSED")
        print(f"screenshots: {SHOTS}")
        print(f"database: {TMP / 'clean-slate.db'}")
        shutil.rmtree(TMP, ignore_errors=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
