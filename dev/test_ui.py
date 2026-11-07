"""End-to-end UI smoke test (offscreen, no real data touched)."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox

from clean_slate import theme
from clean_slate.app import MainWindow
from clean_slate.db import Database


def check(name: str, condition: bool) -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}")
    if not condition:
        raise SystemExit(1)


def visible_dialog(name: str):
    for widget in QApplication.topLevelWidgets():
        if type(widget).__name__ == name and widget.isVisible():
            return widget
    return None


def main() -> None:
    app = QApplication([])
    theme.apply(app)

    tmp = tempfile.TemporaryDirectory()
    db = Database(Path(tmp.name) / "ui.db")
    window = MainWindow(db, remember_geometry=False)
    window.resize(1240, 850)
    window.show()
    app.processEvents()

    check("empty state shows welcome", window.stack.currentWidget() is window.welcome)

    # Create a habit through the welcome preset flow.
    def fill_smoking():
        dialog = visible_dialog("HabitDialog")
        assert dialog is not None
        check("preset prefills name", dialog.name_edit.text() == "Smoking")
        dialog._submit()

    QTimer.singleShot(120, fill_smoking)
    window.welcome.habitRequested.emit("smoking")

    habits = db.habits()
    check("habit created", len(habits) == 1 and habits[0].name == "Smoking")
    check("detail page shown", window.stack.currentWidget() is window.scroll)
    check("window title follows habit", "Smoking" in window.windowTitle())

    habit_id = habits[0].id

    # Log a slip.
    def fill_slip():
        dialog = visible_dialog("SlipDialog")
        assert dialog is not None
        dialog.trigger_combo.setEditText("Stress")
        dialog.note_edit.setText("smoke test")
        dialog.accept()

    QTimer.singleShot(120, fill_slip)
    window.log_slip()
    slips = db.slips(habit_id)
    check("slip logged", len(slips) == 1 and slips[0].trigger == "Stress")
    check("toast shown", window.toast.isVisible() and "Logged" in window.toast.text())

    # Undo it.
    window.undo_last_slip()
    check("undo removes slip", db.slips(habit_id) == [])

    # Edit the habit.
    def rename():
        dialog = visible_dialog("HabitDialog")
        assert dialog is not None
        dialog.name_edit.setText("Cigarettes")
        dialog.cost_spin.setValue(9.25)
        dialog._submit()

    QTimer.singleShot(120, rename)
    window.edit_habit()
    edited = db.habit(habit_id)
    check("habit edited", edited is not None and edited.name == "Cigarettes"
          and edited.daily_cost == 9.25)
    check("sidebar rebuilt", "Cigarettes" in window.windowTitle())

    # Switch pages when two habits exist.
    second_id = db.add_habit("Sugar", "🍬", "#fcd34d", date.today())
    window.refresh()
    window.select_habit(second_id)
    check("habit switch works", "Sugar" in window.windowTitle())

    # Delete the second habit through the confirm dialog.
    def confirm_delete():
        box = visible_dialog("QMessageBox")
        assert box is not None
        for button in box.buttons():
            if box.buttonRole(button) == QMessageBox.ButtonRole.AcceptRole:
                button.click()
                return

    QTimer.singleShot(120, confirm_delete)
    window.delete_habit()
    check("habit deleted", len(db.habits()) == 1)

    # Delete the last habit -> welcome page.
    window.select_habit(habit_id)
    QTimer.singleShot(120, confirm_delete)
    window.delete_habit()
    check("last habit delete returns to welcome",
          db.habits() == [] and window.stack.currentWidget() is window.welcome)

    window.close()
    tmp.cleanup()
    print("\nAll UI smoke checks passed.")


if __name__ == "__main__":
    main()
