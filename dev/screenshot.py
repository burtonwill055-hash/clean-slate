"""Render the app offscreen with demo data for visual checks.

Usage: python3 dev/screenshot.py
Screenshots land in /tmp/opencode/clean-slate-shots/
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from clean_slate import theme
from clean_slate.app import MainWindow
from clean_slate.db import Database
from clean_slate.dialogs import HabitDialog, SlipDialog

OUT = Path("/tmp/opencode/clean-slate-shots")
DB_DIR = Path("/tmp/opencode/clean-slate-demo")


def make_db(with_data: bool = True) -> int | None:
    if DB_DIR.exists():
        shutil.rmtree(DB_DIR)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    db = Database(DB_DIR / "demo.db")
    if not with_data:
        return None

    today = date.today()

    def add(name, emoji, color, days_ago, cost, currency, slips):
        habit_id = db.add_habit(
            name, emoji, color, today - timedelta(days=days_ago),
            daily_cost=cost, currency=currency,
        )
        for slip_days, hour, trigger, note in slips:
            db.add_slip(
                habit_id,
                datetime.combine(today - timedelta(days=slip_days), time(hour, 20)),
                trigger, note,
            )
        return habit_id

    smoking = add(
        "Smoking", "🚬", "#6ee7a8", 96, 7.5, "$",
        [
            (84, 18, "Stress", "Deadline at work, went out with the usual group"),
            (61, 21, "Social situation", "Drinks after the football match"),
            (32, 22, "Craving", "Couldn't sleep, walked to the corner shop"),
            (4, 20, "Stress", "Argument with Alex before a deadline"),
        ],
    )
    add(
        "Social media", "📱", "#7dd3fc", 61, 0, "$",
        [
            (45, 23, "Boredom", "Opened the app in bed and lost an hour"),
            (18, 14, "Routine", "Waiting for a build to finish"),
            (6, 23, "Boredom", ""),
        ],
    )
    add(
        "Sugar", "🍬", "#fcd34d", 31, 2.2, "€",
        [(22, 22, "Craving", "Late-night fridge raid")],
    )
    add(
        "Alcohol", "🍺", "#c4b5fd", 120, 12, "$",
        [
            (90, 20, "Social situation", "Wedding reception"),
            (30, 19, "Celebration", "Promotion drinks with the team"),
        ],
    )
    return smoking


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    theme.apply(app)

    smoking_id = make_db()

    # empty state ---------------------------------------------------------
    empty_dir = Path("/tmp/opencode/clean-slate-empty")
    if empty_dir.exists():
        shutil.rmtree(empty_dir)
    empty_dir.mkdir(parents=True, exist_ok=True)
    empty_db = Database(empty_dir / "empty.db")
    welcome_window = MainWindow(empty_db, remember_geometry=False)
    welcome_window.resize(1240, 850)
    welcome_window.show()
    app.processEvents()
    welcome_window.grab().save(str(OUT / "01-welcome.png"))
    welcome_window.close()

    # populated app -------------------------------------------------------
    db = Database(DB_DIR / "demo.db")
    window = MainWindow(db, remember_geometry=False)
    window.selected_id = smoking_id
    window.refresh(reset_scroll=True)
    window.resize(1240, 850)
    window.show()
    app.processEvents()
    window.grab().save(str(OUT / "02-detail-top.png"))

    window.scroll.verticalScrollBar().setValue(
        window.scroll.verticalScrollBar().maximum()
    )
    app.processEvents()
    window.grab().save(str(OUT / "03-detail-bottom.png"))

    window.resize(1240, 1720)
    app.processEvents()
    window.scroll.verticalScrollBar().setValue(0)
    app.processEvents()
    window.grab().save(str(OUT / "04-detail-tall.png"))
    window.resize(1240, 850)
    app.processEvents()

    # dialogs -------------------------------------------------------------
    habit = db.habit(smoking_id)
    assert habit is not None
    editor = HabitDialog(window, habit=habit)
    editor.show()
    app.processEvents()
    editor.grab().save(str(OUT / "05-habit-dialog.png"))
    editor.close()

    slip = SlipDialog(habit, window)
    slip.show()
    app.processEvents()
    slip.grab().save(str(OUT / "06-slip-dialog.png"))
    slip.close()

    window.close()
    print(f"Screenshots written to {OUT}")


if __name__ == "__main__":
    main()
