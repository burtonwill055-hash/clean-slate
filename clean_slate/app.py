"""Main window and pages for Clean Slate."""
from __future__ import annotations

import sys
from datetime import date
from typing import Optional

from PyQt6.QtCore import QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .db import Database, Habit, Slip, Stats, fmt_date
from .dialogs import PRESETS, HabitDialog, SlipDialog, confirm
from .theme import MILESTONES
from .widgets import (
    ElidedLabel,
    FlowLayout,
    HabitButton,
    HeatmapWidget,
    MilestoneRing,
    PresetCard,
    SlipRow,
    StatCard,
    Toast,
    TriggerRow,
    WeeklyChart,
    hline,
    label,
)

WEEKDAYS = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"]


def money(currency: str, amount: float) -> str:
    if amount >= 1000:
        return f"{currency}{amount:,.0f}"
    return f"{currency}{amount:,.2f}"


def cost_text(value: float) -> str:
    text = f"{value:,.2f}".rstrip("0").rstrip(".")
    return text or "0"


def legend_item(color: str, text: str) -> QWidget:
    widget = QWidget()
    row = QHBoxLayout(widget)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    dot = QLabel()
    dot.setFixedSize(8, 8)
    dot.setStyleSheet(f"background: {color}; border-radius: 4px;")
    row.addWidget(dot)
    row.addWidget(label(text, "cardSub"))
    return widget


# --------------------------------------------------------------------- welcome
class WelcomePage(QWidget):
    habitRequested = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 32, 28, 32)
        outer.addStretch(1)

        row = QHBoxLayout()
        row.addStretch(1)
        container = QWidget()
        container.setMinimumWidth(624)
        container.setMaximumWidth(820)
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content = QVBoxLayout(container)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)

        logo = QLabel()
        logo.setPixmap(QIcon(theme.icon_path()).pixmap(64, 64))
        logo.setFixedSize(64, 64)
        content.addWidget(logo)
        content.addSpacing(22)

        content.addWidget(label("Break the loop.", size=30, weight=700))
        content.addSpacing(8)
        subtitle = label(
            "Track the habits you want to leave behind. Watch the clean days add up, "
            "learn from the slips, and start again without the shame.",
            "dialogSub", wrap=True,
        )
        subtitle.setMaximumWidth(560)
        content.addWidget(subtitle)
        content.addSpacing(30)

        content.addWidget(label("WHAT DO YOU WANT TO QUIT?", "fieldLabel"))
        content.addSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(12)
        for index, (key, (_emoji, title, description, _color)) in enumerate(PRESETS.items()):
            card = PresetCard(key, PRESETS[key][0], title, description)
            card.clicked.connect(self.habitRequested.emit)
            grid.addWidget(card, index // 3, index % 3)
        for column in range(3):
            grid.setColumnStretch(column, 1)
        content.addLayout(grid)

        content.addSpacing(24)
        note = label(
            "🔒  Everything stays on this device. No accounts, no cloud, no judgment.",
            "cardSub",
        )
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content.addWidget(note)

        row.addWidget(container, 6)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(1)


# ------------------------------------------------------------------ habit detail
class HabitDetail(QWidget):
    slipRequested = pyqtSignal()
    undoRequested = pyqtSignal()
    editRequested = pyqtSignal()
    deleteRequested = pyqtSignal()
    deleteSlipRequested = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._panel: Optional[QWidget] = None

    def set_data(self, habit: Habit, stats: Stats, slips: list[Slip]) -> None:
        if self._panel is not None:
            self._panel.setParent(None)
            self._panel.deleteLater()

        panel = QWidget()
        self._panel = panel
        self._outer.addWidget(panel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 24, 28, 34)
        layout.setSpacing(18)

        today = date.today()
        next_milestone = next((m for m in MILESTONES if m > stats.days_clean), None)

        # ----------------------------------------------------------- header
        header = QHBoxLayout()
        header.setSpacing(14)

        emoji_box = QLabel(habit.emoji)
        emoji_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji_box.setFixedSize(56, 56)
        emoji_font = emoji_box.font()
        emoji_font.setPointSizeF(24)
        emoji_box.setFont(emoji_font)
        emoji_box.setStyleSheet(
            f"background: {theme.hex_to_rgba(habit.color, 0.14)};"
            f"border: 1px solid {theme.hex_to_rgba(habit.color, 0.28)};"
            "border-radius: 16px;"
        )
        header.addWidget(emoji_box)

        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        habit_title = ElidedLabel(habit.name)
        title_font = habit_title.font()
        title_font.setPointSizeF(24)
        title_font.setWeight(QFont.Weight.Bold)
        habit_title.setFont(title_font)
        title_column.addWidget(habit_title)
        title_column.addWidget(label(
            f"Tracking since {fmt_date(habit.quit_date)}", "cardSub"
        ))
        header.addLayout(title_column, 1)

        edit = QPushButton("Edit")
        edit.setProperty("variant", "ghost")
        edit.setCursor(Qt.CursorShape.PointingHandCursor)
        edit.clicked.connect(self.editRequested.emit)
        header.addWidget(edit)

        delete = QPushButton("Delete")
        delete.setProperty("variant", "ghostDanger")
        delete.setCursor(Qt.CursorShape.PointingHandCursor)
        delete.clicked.connect(self.deleteRequested.emit)
        header.addWidget(delete)
        layout.addLayout(header)

        # ------------------------------------------------------------- hero
        hero = QFrame()
        hero.setObjectName("heroCard")
        hero_row = QHBoxLayout(hero)
        hero_row.setContentsMargins(24, 20, 26, 20)
        hero_row.setSpacing(22)

        ring = MilestoneRing()
        ring.set_data(stats.days_clean, next_milestone, habit.color)
        hero_row.addWidget(ring)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(2)
        hero_text.addStretch(1)
        hero_text.addWidget(label("CURRENT STREAK", "fieldLabel"))
        number_row = QHBoxLayout()
        number_row.setSpacing(8)
        number = label(str(stats.days_clean), "heroValue")
        unit = label("day clean" if stats.days_clean == 1 else "days clean", "heroUnit")
        number_row.addWidget(number, 0, Qt.AlignmentFlag.AlignBottom)
        number_row.addWidget(unit, 0, Qt.AlignmentFlag.AlignBottom)
        number_row.addStretch(1)
        hero_text.addLayout(number_row)

        if stats.last_slip is not None:
            days_ago = (today - stats.last_slip.date()).days
            if days_ago == 0:
                relative = "today"
            elif days_ago == 1:
                relative = "yesterday"
            else:
                relative = f"{days_ago} days ago"
            plural = "slip" if stats.total_slips == 1 else "slips"
            sub = f"Last slip {relative} · {stats.total_slips} {plural} logged"
        elif stats.days_clean == 0:
            sub = "Day one starts now. One moment at a time."
        else:
            sub = f"No slips since {fmt_date(habit.quit_date)}"
        sub_label = label(sub, "cardSub")
        sub_label.setToolTip(
            f"Clean since {fmt_date(stats.clean_since)}" if stats.days_clean else ""
        )
        hero_text.addWidget(sub_label)
        hero_text.addStretch(1)
        hero_row.addLayout(hero_text, 1)

        milestone_column = QVBoxLayout()
        milestone_column.setSpacing(6)
        milestone_column.addStretch(1)
        milestone_column.addWidget(label("NEXT MILESTONE", "fieldLabel"),
                                   alignment=Qt.AlignmentFlag.AlignRight)
        if next_milestone is not None:
            milestone_column.addWidget(
                label(f"{next_milestone} days", size=20, weight=700, color=habit.color),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
            progress = QProgressBar()
            progress.setRange(0, next_milestone)
            progress.setValue(min(stats.days_clean, next_milestone))
            progress.setTextVisible(False)
            progress.setFixedHeight(8)
            progress.setFixedWidth(212)
            progress.setStyleSheet(
                "QProgressBar { background: #12151a; border: none; border-radius: 4px; }"
                f"QProgressBar::chunk {{ background: {habit.color}; border-radius: 4px; }}"
            )
            milestone_column.addWidget(progress)
            remaining = next_milestone - stats.days_clean
            milestone_column.addWidget(
                label(
                    f"{remaining} {'day' if remaining == 1 else 'days'} to go",
                    "cardSub",
                ),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
        else:
            milestone_column.addWidget(
                label("Every milestone reached 🏆", size=13, weight=700,
                      color=habit.color),
                alignment=Qt.AlignmentFlag.AlignRight,
            )
        milestone_column.addStretch(1)
        hero_row.addLayout(milestone_column)
        layout.addWidget(hero)

        # ----------------------------------------------------------- actions
        actions = QHBoxLayout()
        actions.setSpacing(10)
        log_button = QPushButton("＋   Log a slip")
        log_button.setProperty("variant", "danger")
        log_button.setCursor(Qt.CursorShape.PointingHandCursor)
        log_button.setMinimumHeight(44)
        log_button.setToolTip("Record a slip — honesty is what makes this work")
        log_button.clicked.connect(self.slipRequested.emit)
        actions.addWidget(log_button)

        undo = QPushButton("Undo last slip")
        undo.setProperty("variant", "ghost")
        undo.setCursor(Qt.CursorShape.PointingHandCursor)
        undo.setMinimumHeight(44)
        undo.setEnabled(bool(slips))
        undo.setToolTip("Remove your most recent entry to restore the streak"
                        if slips else "There are no slips to undo")
        undo.clicked.connect(self.undoRequested.emit)
        actions.addWidget(undo)
        actions.addStretch(1)
        actions.addWidget(label("Honesty beats perfection.", "cardSub"))
        layout.addLayout(actions)

        # ------------------------------------------------------------- stats
        stats_row = QHBoxLayout()
        stats_row.setSpacing(14)

        best = StatCard(
            "Best streak",
            f"{stats.best_streak} days",
            "Your personal record",
        )
        stats_row.addWidget(best)

        total = StatCard(
            "Slips logged",
            str(stats.total_slips),
            f"Since {fmt_date(habit.quit_date)}",
        )
        stats_row.addWidget(total)

        week = StatCard(
            "This week",
            str(stats.slips_this_week),
            "Since Monday",
        )
        stats_row.addWidget(week)

        if habit.daily_cost > 0:
            saved = StatCard(
                "Money saved",
                money(habit.currency, stats.money_saved),
                f"At {habit.currency}{cost_text(habit.daily_cost)}/day avoided",
            )
        else:
            saved = StatCard("Money saved", "—", "Set a daily spend")
        stats_row.addWidget(saved)
        layout.addLayout(stats_row)

        # -------------------------------------------------------- milestones
        milestone_card = QFrame()
        milestone_card.setObjectName("card")
        milestone_layout = QVBoxLayout(milestone_card)
        milestone_layout.setContentsMargins(20, 16, 20, 18)
        milestone_layout.setSpacing(12)

        milestone_header = QHBoxLayout()
        milestone_title = QVBoxLayout()
        milestone_title.setSpacing(1)
        milestone_title.addWidget(label("Milestones", "cardTitle"))
        milestone_title.addWidget(label("Small wins stack up.", "cardSub"))
        milestone_header.addLayout(milestone_title)
        milestone_header.addStretch(1)
        reached = sum(1 for m in MILESTONES if m <= stats.days_clean)
        milestone_header.addWidget(
            label(f"{reached} of {len(MILESTONES)} reached", "cardSub"),
            alignment=Qt.AlignmentFlag.AlignBottom,
        )
        milestone_layout.addLayout(milestone_header)

        flow = FlowLayout(h_spacing=8, v_spacing=8)
        for milestone in MILESTONES:
            achieved = milestone <= stats.days_clean
            is_next = milestone == next_milestone
            text = f"✓ {milestone}d" if achieved else f"{milestone}d"
            chip = QLabel(text)
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip.setFixedHeight(30)
            chip.setToolTip(f"{milestone} days clean")
            if achieved:
                chip.setStyleSheet(
                    f"background: {theme.hex_to_rgba(habit.color, 0.16)};"
                    f"border: 1px solid {theme.hex_to_rgba(habit.color, 0.32)};"
                    f"color: {habit.color}; border-radius: 8px; padding: 0 11px;"
                    "font-size: 11px; font-weight: 700;"
                )
            elif is_next:
                chip.setStyleSheet(
                    f"background: {theme.hex_to_rgba(habit.color, 0.06)};"
                    f"border: 1px solid {theme.hex_to_rgba(habit.color, 0.65)};"
                    f"color: {habit.color}; border-radius: 8px; padding: 0 11px;"
                    "font-size: 11px; font-weight: 700;"
                )
            else:
                chip.setStyleSheet(
                    "background: #15191f; border: 1px solid #242b34;"
                    f"color: {theme.FAINT}; border-radius: 8px; padding: 0 11px;"
                    "font-size: 11px;"
                )
            flow.addWidget(chip)
        milestone_layout.addLayout(flow)
        layout.addWidget(milestone_card)

        # ----------------------------------------------------------- heatmap
        heatmap_card = QFrame()
        heatmap_card.setObjectName("card")
        heatmap_layout = QVBoxLayout(heatmap_card)
        heatmap_layout.setContentsMargins(20, 18, 20, 14)
        heatmap_layout.setSpacing(10)

        heatmap_header = QHBoxLayout()
        heatmap_title = QVBoxLayout()
        heatmap_title.setSpacing(1)
        heatmap_title.addWidget(label("Clean calendar", "cardTitle"))
        heatmap_title.addWidget(label("The last 8 months, one square per day.", "cardSub"))
        heatmap_header.addLayout(heatmap_title)
        heatmap_header.addStretch(1)
        heatmap_header.addWidget(legend_item(habit.color, "Clean"))
        heatmap_header.addSpacing(10)
        heatmap_header.addWidget(legend_item(theme.DANGER, "Slip"))
        heatmap_header.addSpacing(10)
        heatmap_header.addWidget(legend_item("#2a313b", "Before tracking"))
        heatmap_layout.addLayout(heatmap_header)

        heatmap = HeatmapWidget()
        heatmap.set_data(habit.quit_date, stats.slip_dates, habit.color)
        heatmap_layout.addWidget(heatmap)
        layout.addWidget(heatmap_card)

        # ------------------------------------------------------ insights row
        insights = QHBoxLayout()
        insights.setSpacing(18)

        triggers_card = QFrame()
        triggers_card.setObjectName("card")
        triggers_card.setMinimumHeight(250)
        triggers_layout = QVBoxLayout(triggers_card)
        triggers_layout.setContentsMargins(20, 18, 20, 16)
        triggers_layout.setSpacing(10)
        triggers_header = QVBoxLayout()
        triggers_header.setSpacing(1)
        triggers_header.addWidget(label("Triggers", "cardTitle"))
        triggers_header.addWidget(label("What tends to come before a slip.", "cardSub"))
        triggers_layout.addLayout(triggers_header)
        triggers_layout.addSpacing(2)

        if stats.triggers:
            maximum = max(count for _name, count in stats.triggers)
            for name, count in stats.triggers:
                triggers_layout.addWidget(TriggerRow(name, count, maximum, habit.color))
            triggers_layout.addStretch(1)
            peak = max(range(7), key=lambda index: stats.weekday_slips[index])
            if stats.weekday_slips[peak] > 0:
                triggers_layout.addWidget(
                    label(f"Most slips happen on {WEEKDAYS[peak]}.", "cardSub")
                )
        else:
            triggers_layout.addStretch(1)
            empty = label("No slips logged yet.\nThere is nothing to analyze — yet.", "emptyNote")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            triggers_layout.addWidget(empty)
            triggers_layout.addStretch(1)
        insights.addWidget(triggers_card, 1)

        weekly_card = QFrame()
        weekly_card.setObjectName("card")
        weekly_card.setMinimumHeight(250)
        weekly_layout = QVBoxLayout(weekly_card)
        weekly_layout.setContentsMargins(20, 18, 20, 12)
        weekly_layout.setSpacing(6)
        weekly_header = QHBoxLayout()
        weekly_title = QVBoxLayout()
        weekly_title.setSpacing(1)
        weekly_title.addWidget(label("Slips per week", "cardTitle"))
        weekly_title.addWidget(label("Momentum over the last 12 weeks.", "cardSub"))
        weekly_header.addLayout(weekly_title)
        weekly_header.addStretch(1)
        recent_total = sum(stats.weekly_slips)
        weekly_header.addWidget(
            label(f"{recent_total} in 12 weeks", "cardSub"),
            alignment=Qt.AlignmentFlag.AlignBottom,
        )
        weekly_layout.addLayout(weekly_header)

        chart = WeeklyChart()
        chart.set_data(stats.weekly_slips, habit.color)
        weekly_layout.addWidget(chart, 1)
        insights.addWidget(weekly_card, 1)
        layout.addLayout(insights)

        # ---------------------------------------------------------- slip log
        log_card = QFrame()
        log_card.setObjectName("card")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(20, 18, 20, 14)
        log_layout.setSpacing(4)

        log_header = QHBoxLayout()
        log_title = QVBoxLayout()
        log_title.setSpacing(1)
        log_title.addWidget(label("Slip log", "cardTitle"))
        subtitle = ("Every slip, on the record." if slips
                    else "Every slip you log will show up here.")
        log_title.addWidget(label(subtitle, "cardSub"))
        log_header.addLayout(log_title)
        log_header.addStretch(1)
        if slips:
            log_header.addWidget(
                label(f"{len(slips)} total", "cardSub"),
                alignment=Qt.AlignmentFlag.AlignBottom,
            )
        log_layout.addLayout(log_header)
        log_layout.addSpacing(4)

        if slips:
            visible = slips[:10]
            for index, slip in enumerate(visible):
                row = SlipRow(
                    slip.id, slip.at, slip.trigger, slip.note, habit.color
                )
                row.deleteRequested.connect(self.deleteSlipRequested.emit)
                log_layout.addWidget(row)
                if index < len(visible) - 1:
                    log_layout.addWidget(hline())
            if len(slips) > len(visible):
                log_layout.addSpacing(4)
                log_layout.addWidget(label(
                    f"+ {len(slips) - len(visible)} older entries", "cardSub"
                ))
        else:
            empty = label("No slips logged. That's the goal.", "emptyNote")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setContentsMargins(0, 20, 0, 20)
            log_layout.addWidget(empty)

        layout.addWidget(log_card)


# ------------------------------------------------------------------ main window
class MainWindow(QMainWindow):
    def __init__(self, db: Database, remember_geometry: bool = True) -> None:
        super().__init__()
        self.db = db
        self.selected_id: Optional[int] = None
        self._settings = QSettings("CleanSlate", "Clean Slate") if remember_geometry else None
        self._today = date.today()

        self.setWindowTitle("Clean Slate")
        self.setWindowIcon(QIcon(theme.icon_path()))
        self.resize(1240, 850)
        self.setMinimumSize(980, 640)

        root = QWidget()
        self.setCentralWidget(root)
        root_row = QHBoxLayout(root)
        root_row.setContentsMargins(0, 0, 0, 0)
        root_row.setSpacing(0)

        # ------------------------------------------------------- sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(282)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 18, 16, 16)
        sidebar_layout.setSpacing(14)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(QIcon(theme.icon_path()).pixmap(38, 38))
        logo.setFixedSize(38, 38)
        brand.addWidget(logo)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_text.addWidget(label("Clean Slate", "logoTitle"))
        brand_text.addWidget(label("Small steps, clean breaks", "logoSub"))
        brand.addLayout(brand_text)
        brand.addStretch(1)
        sidebar_layout.addLayout(brand)
        sidebar_layout.addWidget(hline())

        sidebar_layout.addWidget(label("YOUR HABITS", "fieldLabel"))
        self.habits_layout = QVBoxLayout()
        self.habits_layout.setContentsMargins(0, 0, 0, 0)
        self.habits_layout.setSpacing(5)
        self.habits_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        habits_container = QWidget()
        habits_container.setLayout(self.habits_layout)
        self.habits_scroll = QScrollArea()
        self.habits_scroll.setWidgetResizable(True)
        self.habits_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.habits_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.habits_scroll.setWidget(habits_container)
        sidebar_layout.addWidget(self.habits_scroll, 1)

        add_button = QPushButton("＋   New habit")
        add_button.setProperty("variant", "add")
        add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_button.setMinimumHeight(42)
        add_button.clicked.connect(self.add_habit)
        sidebar_layout.addWidget(add_button)

        sidebar_layout.addWidget(hline())
        sidebar_layout.addWidget(label(
            "🔒  All data stays on this device", "sidebarFooter"
        ))

        root_row.addWidget(sidebar)

        # ---------------------------------------------------------- content
        self.stack = QStackedWidget()
        self.welcome = WelcomePage()
        self.welcome.habitRequested.connect(self.add_habit)
        self.stack.addWidget(self.welcome)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.detail = HabitDetail()
        self.detail.slipRequested.connect(self.log_slip)
        self.detail.undoRequested.connect(self.undo_last_slip)
        self.detail.editRequested.connect(self.edit_habit)
        self.detail.deleteRequested.connect(self.delete_habit)
        self.detail.deleteSlipRequested.connect(self.delete_slip)
        self.scroll.setWidget(self.detail)
        self.stack.addWidget(self.scroll)
        root_row.addWidget(self.stack, 1)

        self.toast = Toast(self)

        if self._settings is not None:
            geometry = self._settings.value("geometry")
            if geometry is not None:
                self.restoreGeometry(geometry)

        self.refresh()

        self._day_timer = QTimer(self)
        self._day_timer.timeout.connect(self._check_day)
        self._day_timer.start(60_000)

    # ---------------------------------------------------------------- refresh
    def refresh(self, reset_scroll: bool = False) -> None:
        habits = self.db.habits()
        ids = [habit.id for habit in habits]
        if self.selected_id not in ids:
            self.selected_id = ids[0] if ids else None

        self._refresh_sidebar(habits)

        if self.selected_id is None:
            self.stack.setCurrentWidget(self.welcome)
            self.setWindowTitle("Clean Slate")
            return

        habit = self.db.habit(self.selected_id)
        if habit is None:
            self.refresh(reset_scroll)
            return
        stats = self.db.stats(habit.id)
        slips = self.db.slips(habit.id)
        self.detail.set_data(habit, stats, slips)
        self.stack.setCurrentWidget(self.scroll)
        self.setWindowTitle(f"Clean Slate — {habit.name}")

        if reset_scroll:
            QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(0))

    def _refresh_sidebar(self, habits: list[Habit]) -> None:
        while self.habits_layout.count():
            item = self.habits_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        if not habits:
            empty = label("No habits yet.\nAdd one to start.", "emptyNote")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setContentsMargins(0, 24, 0, 0)
            self.habits_layout.addWidget(empty)
            return

        for habit in habits:
            stats = self.db.stats(habit.id)
            button = HabitButton(
                habit.id, habit.emoji, habit.name, habit.color, stats.days_clean
            )
            button.set_selected(habit.id == self.selected_id)
            button.clicked.connect(self.select_habit)
            self.habits_layout.addWidget(button)

    def select_habit(self, habit_id: int) -> None:
        if habit_id == self.selected_id:
            return
        self.selected_id = habit_id
        self.refresh(reset_scroll=True)

    # ---------------------------------------------------------------- actions
    def add_habit(self, preset: Optional[str] = None) -> None:
        dialog = HabitDialog(self, preset=preset)
        if dialog.exec():
            values = dialog.values()
            habit_id = self.db.add_habit(**values)
            self.selected_id = habit_id
            self.refresh(reset_scroll=True)
            self.toast.show_message("Habit created. Day one starts now.")

    def edit_habit(self) -> None:
        if self.selected_id is None:
            return
        habit = self.db.habit(self.selected_id)
        if habit is None:
            return
        dialog = HabitDialog(self, habit=habit)
        if dialog.exec():
            self.db.update_habit(habit.id, **dialog.values())
            self.refresh()
            self.toast.show_message("Habit updated.")

    def delete_habit(self) -> None:
        if self.selected_id is None:
            return
        habit = self.db.habit(self.selected_id)
        if habit is None:
            return
        if confirm(
            self,
            f"Delete “{habit.name}”?",
            "This removes the habit and its entire slip history. It cannot be undone.",
            "Delete habit",
        ):
            self.db.delete_habit(habit.id)
            self.selected_id = None
            self.refresh(reset_scroll=True)
            self.toast.show_message("Habit deleted.")

    def log_slip(self) -> None:
        if self.selected_id is None:
            return
        habit = self.db.habit(self.selected_id)
        if habit is None:
            return
        dialog = SlipDialog(habit, self)
        if dialog.exec():
            values = dialog.values()
            self.db.add_slip(habit.id, **values)
            self.refresh()
            self.toast.show_message("Logged. Honesty beats perfection.")

    def undo_last_slip(self) -> None:
        if self.selected_id is None:
            return
        last = self.db.last_slip(self.selected_id)
        if last is None:
            return
        self.db.delete_slip(last.id)
        self.refresh()
        self.toast.show_message("Last slip removed. Your streak is restored.")

    def delete_slip(self, slip_id: int) -> None:
        if confirm(
            self,
            "Delete this slip entry?",
            "Your streaks and statistics will be recalculated without it.",
            "Delete entry",
        ):
            self.db.delete_slip(slip_id)
            self.refresh()
            self.toast.show_message("Entry deleted.")

    # ----------------------------------------------------------------- window
    def _check_day(self) -> None:
        if date.today() != self._today:
            self._today = date.today()
            self.refresh()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "toast"):
            self.toast.reposition()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._settings is not None:
            self._settings.setValue("geometry", self.saveGeometry())
        self.db.close()
        super().closeEvent(event)

    def center_on_screen(self) -> None:
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.availableGeometry()
            self.move(geometry.center() - self.rect().center())


def main() -> int:
    # Qt derives the X11 WM_CLASS instance name from argv[0]; "python3 -m
    # clean_slate" would otherwise advertise "__main__.py" to the task bar.
    sys.argv[0] = "clean-slate"
    app = QApplication(sys.argv)
    app.setApplicationName("clean-slate")
    app.setApplicationDisplayName("Clean Slate")
    app.setOrganizationName("CleanSlate")
    app.setDesktopFileName("clean-slate")
    app.setWindowIcon(QIcon(theme.icon_path()))
    theme.apply(app)

    db = Database()
    window = MainWindow(db)

    screen = app.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        window.resize(
            min(1240, max(980, available.width() - 100)),
            min(850, max(640, available.height() - 100)),
        )

    window.show()
    window.center_on_screen()
    return app.exec()
