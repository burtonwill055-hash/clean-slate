"""SQLite storage and streak math for Clean Slate."""
from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_date(value: date) -> str:
    return f"{_MONTHS[value.month - 1]} {value.day}, {value.year}"


def fmt_day(value: date) -> str:
    return f"{_MONTHS[value.month - 1]} {value.day}"


@dataclass(frozen=True)
class Habit:
    id: int
    name: str
    emoji: str
    color: str
    quit_date: date
    daily_cost: float = 0.0
    currency: str = "$"
    created_at: str = ""


@dataclass(frozen=True)
class Slip:
    id: int
    habit_id: int
    at: datetime
    trigger: str = ""
    note: str = ""


@dataclass
class Stats:
    days_clean: int = 0
    best_streak: int = 0
    total_slips: int = 0
    slips_this_week: int = 0
    money_saved: float = 0.0
    total_days_tracked: int = 0
    last_slip: Optional[datetime] = None
    clean_since: date = field(default_factory=date.today)
    slip_dates: set[date] = field(default_factory=set)
    triggers: list[tuple[str, int]] = field(default_factory=list)
    weekly_slips: list[int] = field(default_factory=list)
    weekday_slips: list[int] = field(default_factory=list)


def default_db_path() -> Path:
    from PyQt6.QtCore import QStandardPaths

    base = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.GenericDataLocation
    )
    return Path(base or str(Path.home() / ".local" / "share")) / "clean-slate" / "clean-slate.db"


class Database:
    def __init__(self, path: Optional[Path | str] = None) -> None:
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS habits (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                emoji       TEXT NOT NULL DEFAULT '🌱',
                color       TEXT NOT NULL DEFAULT '#6ee7a8',
                quit_date   TEXT NOT NULL,
                daily_cost  REAL NOT NULL DEFAULT 0,
                currency    TEXT NOT NULL DEFAULT '$',
                created_at  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS slips (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id    INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
                at          TEXT NOT NULL,
                trigger     TEXT NOT NULL DEFAULT '',
                note        TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_slips_habit ON slips(habit_id, at);
            """
        )
        self.conn.commit()

    # ------------------------------------------------------------ habits
    def habits(self) -> list[Habit]:
        rows = self.conn.execute("SELECT * FROM habits ORDER BY id").fetchall()
        return [self._habit(row) for row in rows]

    def habit(self, habit_id: int) -> Optional[Habit]:
        row = self.conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
        return self._habit(row) if row else None

    def add_habit(
        self,
        name: str,
        emoji: str,
        color: str,
        quit_date: date,
        daily_cost: float = 0.0,
        currency: str = "$",
    ) -> int:
        cursor = self.conn.execute(
            """INSERT INTO habits (name, emoji, color, quit_date, daily_cost, currency, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                name.strip(),
                emoji.strip() or "🌱",
                color,
                quit_date.isoformat(),
                max(0.0, float(daily_cost)),
                (currency.strip() or "$")[:4],
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def update_habit(
        self,
        habit_id: int,
        name: str,
        emoji: str,
        color: str,
        quit_date: date,
        daily_cost: float,
        currency: str,
    ) -> None:
        self.conn.execute(
            """UPDATE habits SET name = ?, emoji = ?, color = ?, quit_date = ?,
                                 daily_cost = ?, currency = ?
               WHERE id = ?""",
            (
                name.strip(),
                emoji.strip() or "🌱",
                color,
                quit_date.isoformat(),
                max(0.0, float(daily_cost)),
                (currency.strip() or "$")[:4],
                habit_id,
            ),
        )
        self.conn.commit()

    def delete_habit(self, habit_id: int) -> None:
        self.conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
        self.conn.commit()

    # ------------------------------------------------------------- slips
    def slips(self, habit_id: int, limit: Optional[int] = None) -> list[Slip]:
        sql = "SELECT * FROM slips WHERE habit_id = ? ORDER BY at DESC, id DESC"
        params: list = [habit_id]
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [self._slip(row) for row in rows]

    def add_slip(
        self,
        habit_id: int,
        at: datetime,
        trigger: str = "",
        note: str = "",
    ) -> int:
        cursor = self.conn.execute(
            "INSERT INTO slips (habit_id, at, trigger, note) VALUES (?, ?, ?, ?)",
            (
                habit_id,
                at.replace(microsecond=0).isoformat(timespec="seconds"),
                trigger.strip(),
                note.strip(),
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def delete_slip(self, slip_id: int) -> None:
        self.conn.execute("DELETE FROM slips WHERE id = ?", (slip_id,))
        self.conn.commit()

    def last_slip(self, habit_id: int) -> Optional[Slip]:
        slips = self.slips(habit_id, limit=1)
        return slips[0] if slips else None

    # ------------------------------------------------------------- stats
    def stats(self, habit_id: int, today: Optional[date] = None) -> Stats:
        habit = self.habit(habit_id)
        if habit is None:
            return Stats()
        today = today or date.today()
        all_slips = self.slips(habit_id)

        slip_dates = sorted({s.at.date() for s in all_slips if s.at.date() >= habit.quit_date})
        cursor = habit.quit_date
        best = 0
        for slip_date in slip_dates:
            best = max(best, max(0, (slip_date - cursor).days))
            cursor = slip_date + timedelta(days=1)

        clean_since = cursor if slip_dates else habit.quit_date
        days_clean = max(0, (today - clean_since).days)
        best = max(best, days_clean)

        monday = today - timedelta(days=today.weekday())
        slips_this_week = sum(
            1 for s in all_slips if monday <= s.at.date() <= today
        )

        weekly: list[int] = []
        for weeks_ago in range(11, -1, -1):
            start = monday - timedelta(weeks=weeks_ago)
            end = start + timedelta(days=6)
            weekly.append(sum(1 for s in all_slips if start <= s.at.date() <= end))

        weekday = [0] * 7
        for slip in all_slips:
            weekday[slip.at.weekday()] += 1

        trigger_counter = Counter(
            (s.trigger.strip() or "Not noted") for s in all_slips
        )

        last = all_slips[0].at if all_slips else None
        daily_cost = habit.daily_cost
        return Stats(
            days_clean=days_clean,
            best_streak=best,
            total_slips=len(all_slips),
            slips_this_week=slips_this_week,
            money_saved=round(days_clean * daily_cost, 2),
            total_days_tracked=max(1, (today - habit.quit_date).days + 1),
            last_slip=last,
            clean_since=clean_since,
            slip_dates=set(slip_dates),
            triggers=trigger_counter.most_common(5),
            weekly_slips=weekly,
            weekday_slips=weekday,
        )

    # ------------------------------------------------------------ helpers
    @staticmethod
    def _habit(row: sqlite3.Row) -> Habit:
        return Habit(
            id=row["id"],
            name=row["name"],
            emoji=row["emoji"],
            color=row["color"],
            quit_date=date.fromisoformat(row["quit_date"]),
            daily_cost=float(row["daily_cost"]),
            currency=row["currency"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _slip(row: sqlite3.Row) -> Slip:
        return Slip(
            id=row["id"],
            habit_id=row["habit_id"],
            at=datetime.fromisoformat(row["at"]),
            trigger=row["trigger"],
            note=row["note"],
        )

    def close(self) -> None:
        self.conn.close()
