"""Reusable custom widgets for Clean Slate."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from PyQt6.QtCore import QPoint, QRect, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .db import fmt_date, fmt_day


# --------------------------------------------------------------------- helpers
def label(
    text: str = "",
    object_name: str | None = None,
    size: int | None = None,
    weight: int | None = None,
    color: str | None = None,
    wrap: bool = False,
) -> QLabel:
    widget = QLabel(text)
    if object_name:
        widget.setObjectName(object_name)
    if wrap:
        widget.setWordWrap(True)
    if size or weight or color:
        font = widget.font()
        if size:
            font.setPointSizeF(size)
        if weight:
            font.setWeight(QFont.Weight(weight))
        widget.setFont(font)
    if color:
        widget.setStyleSheet(f"color: {color};")
    return widget


def hline() -> QFrame:
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {theme.BORDER}; border: none;")
    return line


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class ElidedLabel(QLabel):
    """A one-line label that truncates itself to the space it is given."""

    def __init__(self, text: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setToolTip(text)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        width = max(12, self.width() - 2)
        elided = self.fontMetrics().elidedText(
            self._full_text, Qt.TextElideMode.ElideRight, width
        )
        if elided != self.text():
            super().setText(elided)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(0, super().minimumSizeHint().height())


# ------------------------------------------------------------------ flow layout
class FlowLayout(QLayout):
    """A layout that wraps its children onto new lines (Qt example port)."""

    def __init__(self, parent: Optional[QWidget] = None, margin: int = 0,
                 h_spacing: int = 8, v_spacing: int = 8) -> None:
        super().__init__(parent)
        self._items: list = []
        self._h = h_spacing
        self._v = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item) -> None:  # noqa: N802
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):  # noqa: N802
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        x = rect.x() + margins.left()
        y = rect.y() + margins.top()
        right = rect.right() - margins.right()
        line_height = 0

        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._h
            if next_x - self._h > right and line_height > 0:
                x = rect.x() + margins.left()
                y = y + line_height + self._v
                next_x = x + hint.width() + self._h
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())

        return y + line_height - rect.y() + margins.bottom()


# ------------------------------------------------------------------ habit button
class HabitButton(QFrame):
    clicked = pyqtSignal(int)

    def __init__(self, habit_id: int, emoji: str, name: str, color: str,
                 days: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.habit_id = habit_id
        self.setObjectName("habitButton")
        self.setProperty("selected", False)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(62)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 12, 8)
        row.setSpacing(10)

        emoji_box = QLabel(emoji)
        emoji_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji_box.setFixedSize(36, 36)
        emoji_font = emoji_box.font()
        emoji_font.setPointSizeF(16)
        emoji_box.setFont(emoji_font)
        emoji_box.setStyleSheet(
            f"background: {theme.hex_to_rgba(color, 0.15)};"
            f"border: 1px solid {theme.hex_to_rgba(color, 0.22)};"
            "border-radius: 10px;"
        )
        row.addWidget(emoji_box)

        text = QVBoxLayout()
        text.setSpacing(1)
        text.setContentsMargins(0, 0, 0, 0)
        name_label = label(name, "habitName")
        name_label.setText(QFontMetrics(name_label.font()).elidedText(
            name, Qt.TextElideMode.ElideRight, 130))
        day_text = ("Day one" if days == 0
                    else "1 day clean" if days == 1
                    else f"{days} days clean")
        text.addWidget(name_label)
        text.addWidget(label(day_text, "habitDays"))
        row.addLayout(text, 1)

        dot = QLabel()
        dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background: {color}; border-radius: 3px;")
        row.addWidget(dot)

        for child in self.findChildren(QLabel):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        repolish(self)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.clicked.emit(self.habit_id)
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------- stat card
class StatCard(QFrame):
    def __init__(self, title: str, value: str, hint: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(98)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(3)
        layout.addWidget(label(title.upper(), "fieldLabel"))
        self.value_label = label(value, "cardValue")
        layout.addWidget(self.value_label)
        self.hint_label = label(hint, "cardSub")
        layout.addWidget(self.hint_label)

    def set_value(self, value: str, hint: str) -> None:
        self.value_label.setText(value)
        self.hint_label.setText(hint)


# ----------------------------------------------------------------- milestone ring
class MilestoneRing(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(124, 124)
        self.days = 0
        self.next_milestone: Optional[int] = 1
        self.color = theme.ACCENT

    def set_data(self, days: int, next_milestone: Optional[int], color: str) -> None:
        self.days = days
        self.next_milestone = next_milestone
        self.color = color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pad = 11
        rect = QRectF(self.rect()).adjusted(pad, pad, -pad, -pad)
        pen = QPen(QColor("#252c35"), 9)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        if self.next_milestone:
            progress = min(1.0, self.days / self.next_milestone)
        else:
            progress = 1.0
        if progress > 0:
            pen = QPen(QColor(self.color), 9)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawArc(rect, 90 * 16, -int(progress * 360 * 16))

        painter.setPen(QColor(theme.TEXT))
        number_font = QFont(painter.font())
        number_font.setPointSizeF(20)
        number_font.setWeight(QFont.Weight.Bold)
        painter.setFont(number_font)
        painter.drawText(
            QRectF(0, 40, self.width(), 34),
            Qt.AlignmentFlag.AlignCenter,
            str(self.days),
        )

        small = QFont(painter.font())
        small.setPointSizeF(8)
        small.setWeight(QFont.Weight.DemiBold)
        small.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        painter.setFont(small)
        painter.setPen(QColor(theme.FAINT))
        caption = "DAY" if self.days == 1 else "DAYS"
        painter.drawText(
            QRectF(0, 72, self.width(), 18),
            Qt.AlignmentFlag.AlignCenter,
            caption,
        )


# --------------------------------------------------------------------- heatmap
class HeatmapWidget(QWidget):
    WEEKS = 36
    GAP = 4

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.quit_date = date.today()
        self.slip_dates: set[date] = set()
        self.color = theme.ACCENT
        self.today = date.today()
        self._cells: dict[date, QRect] = {}
        self._hover: Optional[date] = None

    def set_data(self, quit_date: date, slip_dates: set[date], color: str,
                 today: Optional[date] = None) -> None:
        self.quit_date = quit_date
        self.slip_dates = set(slip_dates)
        self.color = color
        self.today = today or date.today()
        self.update()

    def _geometry(self):
        left = 32
        top = 24
        available = max(120, self.width() - left - 6)
        cell = min(18.0, (available - self.GAP * (self.WEEKS - 1)) / self.WEEKS)
        cell = max(6.0, cell)
        grid_width = self.WEEKS * cell + self.GAP * (self.WEEKS - 1)
        start_x = left + max(0.0, (available - grid_width) / 2)
        return start_x, top, cell

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        start_x, top, cell = self._geometry()
        gap = self.GAP
        self._cells = {}

        today = self.today
        monday = today - timedelta(days=today.weekday())
        first_monday = monday - timedelta(weeks=self.WEEKS - 1)

        # weekday hints
        painter.setPen(QColor(theme.FAINT))
        hint_font = QFont(painter.font())
        hint_font.setPointSizeF(8)
        painter.setFont(hint_font)
        for row, text in ((0, "Mon"), (2, "Wed"), (4, "Fri")):
            painter.drawText(
                QRectF(0, top + row * (cell + gap) - 1, 26, cell + 2),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                text,
            )

        # month labels
        last_right = -100.0
        for col in range(self.WEEKS):
            day = first_monday + timedelta(weeks=col)
            if col == 0 or day.month != (day - timedelta(days=7)).month:
                x = start_x + col * (cell + gap)
                text = day.strftime("%b")
                width = QFontMetrics(hint_font).horizontalAdvance(text)
                if x > last_right + 6:
                    painter.setPen(QColor(theme.FAINT))
                    painter.drawText(QRectF(x, 1, width + 4, 16),
                                     Qt.AlignmentFlag.AlignLeft, text)
                    last_right = x + width

        for col in range(self.WEEKS):
            for row in range(7):
                day = first_monday + timedelta(weeks=col, days=row)
                x = start_x + col * (cell + gap)
                y = top + row * (cell + gap)
                rect = QRectF(x, y, cell, cell)
                self._cells[day] = QRect(round(x), round(y), round(cell), round(cell))

                if day > today:
                    continue

                if day < self.quit_date:
                    fill = QColor("#15191f")
                    border = QColor("#1d222a")
                elif day in self.slip_dates:
                    fill = QColor(theme.DANGER)
                    border = QColor(theme.DANGER).lighter(115)
                else:
                    fill = QColor(self.color)
                    if day != today:
                        fill.setAlpha(220)
                    border = fill.lighter(112)

                painter.setPen(QPen(border, 1))
                painter.setBrush(fill)
                painter.drawRoundedRect(rect, 3.5, 3.5)

                if day == today or day == self._hover:
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.setPen(QPen(QColor(theme.TEXT), 1.4))
                    painter.drawRoundedRect(rect.adjusted(0.7, 0.7, -0.7, -0.7), 3.5, 3.5)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position().toPoint()
        hovered: Optional[date] = None
        for day, rect in self._cells.items():
            if rect.contains(pos):
                hovered = day
                break
        if hovered != self._hover:
            self._hover = hovered
            self.update()

        if hovered is None:
            QToolTip.hideText()
            return

        if hovered > self.today:
            status = "Upcoming"
        elif hovered < self.quit_date:
            status = "Before tracking started"
        elif hovered in self.slip_dates:
            status = "Slip logged"
        elif hovered == self.today:
            status = "Today · clean so far"
        else:
            status = "Clean"

        QToolTip.showText(
            event.globalPosition().toPoint(),
            f"{hovered.strftime('%a, %b %-d')} · {status}",
            self,
        )

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = None
        self.update()
        super().leaveEvent(event)


# ------------------------------------------------------------------ weekly chart
class WeeklyChart(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.values: list[int] = [0] * 12
        self.color = theme.ACCENT
        self.today = date.today()
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_data(self, values: list[int], color: str, today: Optional[date] = None) -> None:
        self.values = values or [0] * 12
        self.color = color
        self.today = today or date.today()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width()
        height = self.height()
        left, right, top, bottom = 4, 4, 20, 24
        plot_w = max(10, width - left - right)
        plot_h = max(10, height - top - bottom)
        baseline = top + plot_h

        values = self.values[-12:]
        scale_max = max(3, max(values) if values else 0)
        slot = plot_w / max(1, len(values))
        bar_w = min(22.0, slot * 0.52)

        painter.setPen(QPen(QColor("#222831"), 1, Qt.PenStyle.DashLine))
        painter.drawLine(left, top, width - right, top)
        painter.drawLine(left, baseline, width - right, baseline)

        label_font = QFont(painter.font())
        label_font.setPointSizeF(8)
        value_font = QFont(painter.font())
        value_font.setPointSizeF(8)
        value_font.setWeight(QFont.Weight.DemiBold)

        monday = self.today - timedelta(days=self.today.weekday())
        first_monday = monday - timedelta(weeks=len(values) - 1)

        for index, value in enumerate(values):
            center = left + slot * index + slot / 2
            bar_h = (value / scale_max) * (plot_h - 4) if value else 3
            rect = QRectF(center - bar_w / 2, baseline - bar_h, bar_w, bar_h)
            color = QColor(self.color if value else "#252c35")
            if value:
                color.setAlpha(230)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(rect, 4, 4)

            if value:
                painter.setFont(value_font)
                painter.setPen(QColor(theme.TEXT))
                painter.drawText(
                    QRectF(center - 14, baseline - bar_h - 16, 28, 14),
                    Qt.AlignmentFlag.AlignCenter,
                    str(value),
                )

            if index % 3 == 0:
                week = first_monday + timedelta(weeks=index)
                painter.setFont(label_font)
                painter.setPen(QColor(theme.FAINT))
                painter.drawText(
                    QRectF(center - 30, baseline + 5, 60, 16),
                    Qt.AlignmentFlag.AlignCenter,
                    fmt_day(week),
                )


# ------------------------------------------------------------------ trigger row
class TriggerRow(QWidget):
    def __init__(self, name: str, count: int, maximum: int, color: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        name_label = label(name, "muted")
        name_label.setFixedWidth(112)
        metrics = QFontMetrics(name_label.font())
        name_label.setText(metrics.elidedText(name, Qt.TextElideMode.ElideRight, 108))
        name_label.setToolTip(name)
        row.addWidget(name_label)

        bar = QProgressBar()
        bar.setRange(0, max(1, maximum))
        bar.setValue(count)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setStyleSheet(
            "QProgressBar { background: #12151a; border: none; border-radius: 4px; }"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}"
        )
        row.addWidget(bar, 1)

        count_label = label(str(count), "muted")
        count_label.setFixedWidth(18)
        count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(count_label)


# -------------------------------------------------------------------- slip row
class SlipRow(QWidget):
    deleteRequested = pyqtSignal(int)

    def __init__(self, slip_id: int, at: datetime, trigger: str, note: str,
                 color: str, today: Optional[date] = None,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        today = today or date.today()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 8, 0, 8)
        row.setSpacing(12)

        day = at.date()
        if day == today:
            day_text = "Today"
        elif day == today - timedelta(days=1):
            day_text = "Yesterday"
        else:
            day_text = fmt_date(day)

        when = QVBoxLayout()
        when.setSpacing(0)
        when.setContentsMargins(0, 0, 0, 0)
        when.addWidget(label(day_text, "habitName"))
        when.addWidget(label(at.strftime("%H:%M"), "cardSub"))
        block = QWidget()
        block.setLayout(when)
        block.setFixedWidth(100)
        row.addWidget(block)

        if trigger.strip():
            pill = QLabel(trigger.strip())
            metrics = QFontMetrics(pill.font())
            pill.setText(metrics.elidedText(trigger.strip(), Qt.TextElideMode.ElideRight, 120))
            pill.setToolTip(trigger.strip())
            pill.setStyleSheet(
                f"background: {theme.hex_to_rgba(color, 0.13)};"
                f"color: {color}; border: 1px solid {theme.hex_to_rgba(color, 0.22)};"
                "border-radius: 8px; padding: 3px 9px; font-size: 10px; font-weight: 700;"
            )
            pill.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            row.addWidget(pill)
        else:
            row.addWidget(label("no trigger noted", "faint"))

        if note.strip():
            note_label = label(note.strip(), "muted")
            metrics = QFontMetrics(note_label.font())
            note_label.setText(metrics.elidedText(note.strip(), Qt.TextElideMode.ElideRight, 360))
            note_label.setToolTip(note.strip())
            note_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            row.addWidget(note_label, 1)
        else:
            row.addStretch(1)

        remove = QPushButton("✕")
        remove.setObjectName("iconButton")
        remove.setToolTip("Delete this entry")
        remove.setCursor(Qt.CursorShape.PointingHandCursor)
        remove.setFixedSize(26, 26)
        remove.clicked.connect(lambda: self.deleteRequested.emit(slip_id))
        row.addWidget(remove)


# ------------------------------------------------------------------- preset card
class PresetCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, key: str, emoji: str, title: str, description: str,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.key = key
        self.setObjectName("presetCard")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(92)
        self.setMinimumWidth(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 14, 16, 14)
        row.setSpacing(13)

        emoji_box = QLabel(emoji)
        emoji_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji_box.setFixedSize(44, 44)
        emoji_font = emoji_box.font()
        emoji_font.setPointSizeF(20)
        emoji_box.setFont(emoji_font)
        emoji_box.setStyleSheet(
            "background: #1d232b; border: 1px solid #2a323d; border-radius: 12px;"
        )
        row.addWidget(emoji_box)

        text = QVBoxLayout()
        text.setSpacing(2)
        text.setContentsMargins(0, 0, 0, 0)
        text.addWidget(label(title, "habitName", size=13, weight=700))
        text.addWidget(label(description, "cardSub", wrap=True))
        row.addLayout(text, 1)

        for child in self.findChildren(QLabel):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.clicked.emit(self.key)
        super().mouseReleaseEvent(event)


# ----------------------------------------------------------------------- toast
class Toast(QLabel):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, error: bool = False) -> None:
        self.setObjectName("errorToast" if error else "toast")
        repolish(self)
        self.setText(text)
        self.adjustSize()
        self.reposition()
        self.raise_()
        self.show()
        self._timer.start(3400)

    def reposition(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        x = (parent.width() - self.width()) // 2
        y = parent.height() - self.height() - 26
        self.move(max(12, x), max(12, y))
