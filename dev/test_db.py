"""Quick sanity checks for the storage and streak math."""
from __future__ import annotations

import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clean_slate.db import Database, default_db_path

TODAY = date(2026, 11, 6)


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        raise SystemExit(1)


with tempfile.TemporaryDirectory() as tmp:
    db = Database(Path(tmp) / "test.db")
    quit_day = TODAY - timedelta(days=10)

    habit_id = db.add_habit(
        "Smoking", "🚬", "#6ee7a8", quit_day, daily_cost=6.0, currency="$"
    )
    habit = db.habit(habit_id)
    check("habit round-trips", habit is not None and habit.name == "Smoking")

    stats = db.stats(habit_id, today=TODAY)
    check("fresh streak counts from quit date", stats.days_clean == 10, str(stats.days_clean))
    check("no slips initially", stats.total_slips == 0)
    check("money saved", abs(stats.money_saved - 60.0) < 0.001, str(stats.money_saved))

    # A slip 4 days ago: current streak should be 3 full days.
    slip_at = datetime.combine(TODAY - timedelta(days=4), datetime.min.time()).replace(hour=21)
    db.add_slip(habit_id, slip_at, "Stress", "rough day")
    stats = db.stats(habit_id, today=TODAY)
    check("streak resets after slip", stats.days_clean == 3, str(stats.days_clean))
    check("best streak remembers before slip", stats.best_streak == 6, str(stats.best_streak))
    check("slip counted", stats.total_slips == 1)
    check("trigger recorded", stats.triggers == [("Stress", 1)], str(stats.triggers))
    check("last slip", stats.last_slip is not None and stats.last_slip.date() == slip_at.date())
    check("money follows current streak", abs(stats.money_saved - 18.0) < 0.001)

    # A slip today zeroes the streak.
    db.add_slip(habit_id, datetime.combine(TODAY, datetime.min.time()).replace(hour=9))
    stats = db.stats(habit_id, today=TODAY)
    check("slip today zeroes streak", stats.days_clean == 0, str(stats.days_clean))
    check("slips this week", stats.slips_this_week == 2, str(stats.slips_this_week))
    check("weekly buckets", len(stats.weekly_slips) == 12 and stats.weekly_slips[-1] == 2)
    check("weekday buckets", len(stats.weekday_slips) == 7 and sum(stats.weekday_slips) == 2)
    check("noted slip without trigger", ("Not noted", 1) in stats.triggers)

    # Undo works through the same path the UI uses.
    last = db.last_slip(habit_id)
    db.delete_slip(last.id)
    stats = db.stats(habit_id, today=TODAY)
    check("undo restores streak", stats.days_clean == 3, str(stats.days_clean))

    # Editing and cascade delete.
    db.update_habit(habit_id, "Cigarettes", "🚭", "#7dd3fc", quit_day, 7.5, "€")
    updated = db.habit(habit_id)
    check("habit edits persist",
          updated is not None and updated.name == "Cigarettes"
          and updated.currency == "€" and updated.daily_cost == 7.5)
    db.delete_habit(habit_id)
    check("habit delete cascades", db.habits() == [] and db.slips(habit_id) == [])

    print("\nDefault DB path:", default_db_path())

print("\nAll storage checks passed.")
