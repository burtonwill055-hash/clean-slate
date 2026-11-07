"""Habit editor, slip logger and small confirmation dialogs."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QDate, QDateTime, QTime, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .db import Habit
from .widgets import label


PRESETS: dict[str, tuple[str, str, str, str]] = {
    "smoking": ("🚬", "Smoking", "Cigarettes, vaping, nicotine", "#6ee7a8"),
    "social": ("📱", "Social media", "Doomscrolling and endless feeds", "#7dd3fc"),
    "sugar": ("🍬", "Sugar", "Sweets, soda and snacks", "#fcd34d"),
    "alcohol": ("🍺", "Alcohol", "Drinking and nights out", "#c4b5fd"),
    "gambling": ("🎲", "Gambling", "Bets, loot boxes and casino apps", "#fca5a5"),
    "custom": ("🌱", "Something else", "Name your own habit", "#a3e635"),
}

COLOR_NAMES = {
    "#6ee7a8": "Mint",
    "#7dd3fc": "Sky",
    "#c4b5fd": "Lilac",
    "#fcd34d": "Amber",
    "#f9a8d4": "Pink",
    "#93c5fd": "Blue",
    "#fca5a5": "Coral",
    "#a3e635": "Lime",
}


def confirm(parent: QWidget, title: str, text: str, ok_text: str = "Delete",
            destructive: bool = True) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(title)
    box.setInformativeText(text)
    box.setIcon(
        QMessageBox.Icon.Warning if destructive else QMessageBox.Icon.Question
    )
    ok = box.addButton(ok_text, QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    if destructive:
        ok.setStyleSheet(
            "QPushButton { background: #2a181c; border: 1px solid #512930;"
            " color: #ff9a9a; font-weight: 700; padding: 8px 16px; border-radius: 9px; }"
            "QPushButton:hover { background: #382025; }"
        )
    box.exec()
    return box.clickedButton() is ok


class HabitDialog(QDialog):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        habit: Optional[Habit] = None,
        preset: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self.habit = habit
        self.setWindowTitle("Edit habit" if habit else "New habit")
        self.setModal(True)
        self.setMinimumWidth(620)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 22)
        root.setSpacing(16)

        title = "Edit habit" if habit else "New habit"
        root.addWidget(label(title, "dialogTitle"))
        root.addWidget(label(
            "Track what you're quitting. You can change any of this later.",
            "dialogSub",
        ))

        # name ------------------------------------------------------------
        root.addWidget(label("NAME", "fieldLabel"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Smoking, Sugar, Social media")
        self.name_edit.setMaxLength(60)
        root.addWidget(self.name_edit)

        # emoji + color ---------------------------------------------------
        row = QHBoxLayout()
        row.setSpacing(24)

        emoji_column = QVBoxLayout()
        emoji_column.setSpacing(8)
        emoji_column.addWidget(label("ICON", "fieldLabel"))
        emoji_row = QHBoxLayout()
        emoji_row.setSpacing(6)
        self.emoji_edit = QLineEdit()
        self.emoji_edit.setFixedWidth(52)
        self.emoji_edit.setMaxLength(4)
        self.emoji_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji_font = self.emoji_edit.font()
        emoji_font.setPointSizeF(15)
        self.emoji_edit.setFont(emoji_font)
        emoji_row.addWidget(self.emoji_edit)
        for emoji in theme.EMOJIS[:7]:
            button = QPushButton(emoji)
            button.setFixedSize(30, 30)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(
                "QPushButton { background: #15191f; border: 1px solid #2a313b;"
                " border-radius: 8px; padding: 0; font-size: 16px; }"
                "QPushButton:hover { border-color: #4a5868; }"
            )
            button.setToolTip(f"Use {emoji}")
            button.clicked.connect(
                lambda _checked=False, value=emoji: self.emoji_edit.setText(value)
            )
            emoji_row.addWidget(button)
        emoji_row.addStretch(1)
        emoji_column.addLayout(emoji_row)
        row.addLayout(emoji_column, 1)

        color_column = QVBoxLayout()
        color_column.setSpacing(8)
        color_column.addWidget(label("COLOR", "fieldLabel"))
        swatch_row = QHBoxLayout()
        swatch_row.setSpacing(7)
        self._color_group = QButtonGroup(self)
        self._color_group.setExclusive(True)
        self._selected_color = theme.HABIT_COLORS[0]
        for index, color in enumerate(theme.HABIT_COLORS):
            swatch = QPushButton()
            swatch.setCheckable(True)
            swatch.setFixedSize(24, 24)
            swatch.setCursor(Qt.CursorShape.PointingHandCursor)
            color_name = COLOR_NAMES.get(color, color)
            swatch.setToolTip(color_name)
            swatch.setAccessibleName(f"{color_name} accent")
            swatch.setStyleSheet(
                f"QPushButton {{ background: {color}; border: 2px solid transparent;"
                " border-radius: 8px; }\n"
                "QPushButton:hover { border-color: #8d98a8; }\n"
                "QPushButton:checked { border-color: #e9eef5; }"
            )
            swatch.clicked.connect(
                lambda _checked=False, value=color: self._set_color(value)
            )
            self._color_group.addButton(swatch, index)
            swatch_row.addWidget(swatch)
            if index == 0:
                swatch.setChecked(True)
        swatch_row.addStretch(1)
        color_column.addLayout(swatch_row)
        row.addLayout(color_column)

        root.addLayout(row)

        # date + cost -----------------------------------------------------
        meta_row = QHBoxLayout()
        meta_row.setSpacing(18)

        date_column = QVBoxLayout()
        date_column.setSpacing(8)
        date_column.addWidget(label("TRACKING SINCE", "fieldLabel"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("MMM d, yyyy")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMaximumDate(QDate.currentDate())
        self.date_edit.setMinimumDate(QDate(2000, 1, 1))
        date_column.addWidget(self.date_edit)
        meta_row.addLayout(date_column, 1)

        cost_column = QVBoxLayout()
        cost_column.setSpacing(8)
        cost_column.addWidget(label("DAILY SPEND AVOIDED (OPTIONAL)", "fieldLabel"))
        cost_row = QHBoxLayout()
        cost_row.setSpacing(8)
        self.currency_edit = QLineEdit("$")
        self.currency_edit.setFixedWidth(44)
        self.currency_edit.setMaxLength(4)
        self.currency_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cost_row.addWidget(self.currency_edit)
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setDecimals(2)
        self.cost_spin.setRange(0, 100000)
        self.cost_spin.setSingleStep(1)
        self.cost_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.cost_spin.setSpecialValueText("0.00")
        cost_row.addWidget(self.cost_spin, 1)
        cost_column.addLayout(cost_row)
        meta_row.addLayout(cost_column, 1)

        root.addLayout(meta_row)

        self.error_label = label("", "errorLabel")
        self.error_label.hide()
        root.addWidget(self.error_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setProperty("variant", "ghost")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        save = QPushButton("Save changes" if habit else "Create habit")
        save.setProperty("variant", "primary")
        save.setDefault(True)
        save.clicked.connect(self._submit)
        buttons.addWidget(save)
        root.addLayout(buttons)

        if habit:
            self._load(habit)
        elif preset and preset in PRESETS:
            emoji, name, _description, color = PRESETS[preset]
            if preset != "custom":
                self.name_edit.setText(name)
            self.emoji_edit.setText(emoji)
            self._set_color(color)

    # ------------------------------------------------------------------ internals
    def _set_color(self, color: str) -> None:
        self._selected_color = color
        for index, palette_color in enumerate(theme.HABIT_COLORS):
            button = self._color_group.button(index)
            if button is not None:
                button.setChecked(palette_color == color)

    def _load(self, habit: Habit) -> None:
        self.name_edit.setText(habit.name)
        self.emoji_edit.setText(habit.emoji)
        self._set_color(habit.color if habit.color in theme.HABIT_COLORS else theme.HABIT_COLORS[0])
        self.date_edit.setDate(QDate(habit.quit_date.year, habit.quit_date.month, habit.quit_date.day))
        self.currency_edit.setText(habit.currency)
        self.cost_spin.setValue(habit.daily_cost)

    def _submit(self) -> None:
        if not self.name_edit.text().strip():
            self.error_label.setText("Give your habit a name so you can tell it apart.")
            self.error_label.show()
            self.name_edit.setFocus()
            return
        self.error_label.hide()
        self.accept()

    def values(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "emoji": self.emoji_edit.text().strip() or "🌱",
            "color": self._selected_color,
            "quit_date": self.date_edit.date().toPyDate(),
            "daily_cost": float(self.cost_spin.value()),
            "currency": self.currency_edit.text().strip() or "$",
        }


class SlipDialog(QDialog):
    def __init__(self, habit: Habit, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Log a slip")
        self.setModal(True)
        self.setMinimumWidth(480)

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 22)
        root.setSpacing(14)

        root.addWidget(label("Log a slip", "dialogTitle"))
        root.addWidget(label(
            "No judgment — recording the moment is how you spot the pattern.",
            "dialogSub", wrap=True,
        ))

        habit_row = QHBoxLayout()
        habit_row.setSpacing(9)
        emoji = QLabel(habit.emoji)
        emoji.setFixedSize(30, 30)
        emoji.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji_font = emoji.font()
        emoji_font.setPointSizeF(15)
        emoji.setFont(emoji_font)
        emoji.setStyleSheet(
            f"background: {theme.hex_to_rgba(habit.color, 0.14)};"
            f"border: 1px solid {theme.hex_to_rgba(habit.color, 0.24)};"
            "border-radius: 9px;"
        )
        habit_row.addWidget(emoji)
        habit_row.addWidget(label(habit.name, "habitName", size=13, weight=700))
        habit_row.addStretch(1)
        root.addLayout(habit_row)

        root.addWidget(label("WHEN", "fieldLabel"))
        self.when_edit = QDateTimeEdit()
        self.when_edit.setCalendarPopup(True)
        self.when_edit.setDisplayFormat("MMM d, yyyy  ·  HH:mm")
        now = QDateTime.currentDateTime()
        self.when_edit.setDateTime(now)
        self.when_edit.setMaximumDateTime(now)
        self.when_edit.setMinimumDateTime(
            QDateTime(QDate(habit.quit_date.year, habit.quit_date.month, habit.quit_date.day),
                      QTime(0, 0))
        )
        self.when_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        root.addWidget(self.when_edit)

        root.addWidget(label("TRIGGER", "fieldLabel"))
        self.trigger_combo = QComboBox()
        self.trigger_combo.setEditable(True)
        self.trigger_combo.addItems([
            "Stress", "Boredom", "Craving", "Social situation", "Routine",
            "Feeling down", "Tired", "Celebration", "Alcohol",
        ])
        self.trigger_combo.setCurrentIndex(-1)
        self.trigger_combo.lineEdit().setPlaceholderText(
            "Pick one or type your own (optional)"
        )
        root.addWidget(self.trigger_combo)

        root.addWidget(label("NOTE", "fieldLabel"))
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("What happened right before? (optional)")
        self.note_edit.setMaxLength(240)
        root.addWidget(self.note_edit)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setProperty("variant", "ghost")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        log = QPushButton("Log slip")
        log.setProperty("variant", "danger")
        log.setDefault(True)
        log.clicked.connect(self.accept)
        buttons.addWidget(log)
        root.addLayout(buttons)

    def values(self) -> dict:
        return {
            "at": self.when_edit.dateTime().toPyDateTime().replace(second=0, microsecond=0),
            "trigger": self.trigger_combo.currentText().strip(),
            "note": self.note_edit.text().strip(),
        }
