"""Colors, typography and the global stylesheet for Clean Slate."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QFont

ASSETS = Path(__file__).resolve().parent / "assets"

# ---------------------------------------------------------------- palette
BG = "#0f1115"
SIDEBAR = "#13161b"
CARD = "#181c22"
CARD_ALT = "#1d222a"
BORDER = "#262c36"
BORDER_SOFT = "#20252d"
TEXT = "#e9eef5"
MUTED = "#8d98a8"
FAINT = "#5c6675"
ACCENT = "#6ee7a8"
ACCENT_DARK = "#0b2a1c"
DANGER = "#ff7a7a"
DANGER_SOFT = "#ff9a9a"
DANGER_BG = "#2a181c"
WARN = "#f6c177"

HABIT_COLORS = [
    "#6ee7a8",  # mint
    "#7dd3fc",  # sky
    "#c4b5fd",  # lilac
    "#fcd34d",  # amber
    "#f9a8d4",  # pink
    "#93c5fd",  # blue
    "#fca5a5",  # coral
    "#a3e635",  # lime
]

EMOJIS = ["🚬", "📱", "🍬", "🍺", "🎮", "☕", "🛒", "💸", "🍔", "🎲", "🖥️", "🌱"]

# Milestones (days) used for badges and the progress ring.
MILESTONES = [1, 3, 7, 14, 21, 30, 45, 60, 90, 120, 180, 270, 365, 500, 730]


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """#rrggbb -> rgba(r, g, b, a) for Qt stylesheets."""
    value = hex_color.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


_QSS = """
* { outline: none; }

QWidget {
    color: @@text@@;
    font-family: "Cantarell", "DejaVu Sans";
}

QMainWindow, QDialog { background: @@bg@@; }

#sidebar { background: @@sidebar@@; border-right: 1px solid @@border@@; }
#logoTitle { font-size: 17px; font-weight: 700; }
#logoSub { color: @@muted@@; font-size: 11px; }
#sectionLabel { color: @@faint@@; font-size: 10px; font-weight: 700; }
#sidebarFooter { color: @@faint@@; font-size: 10px; }
#muted { color: @@muted@@; }
#faint { color: @@faint@@; }
#fieldLabel { color: @@muted@@; font-size: 10px; font-weight: 700; }
#cardTitle { font-size: 14px; font-weight: 700; }
#cardSub { color: @@muted@@; font-size: 11px; }
#cardValue { font-size: 22px; font-weight: 700; }
#heroValue { font-size: 46px; font-weight: 700; }
#heroUnit { color: @@muted@@; font-size: 15px; }
#dialogTitle { font-size: 20px; font-weight: 700; }
#dialogSub { color: @@muted@@; font-size: 12px; }
#errorLabel { color: @@danger@@; font-size: 11px; }
#emptyNote { color: @@muted@@; font-size: 12px; }
#linkLabel { color: @@muted@@; font-size: 11px; }

QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2c333d; border-radius: 4px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: #39424f; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: #2c333d; border-radius: 4px; min-width: 32px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

#card {
    background: @@card@@;
    border: 1px solid @@border@@;
    border-radius: 16px;
}
#heroCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 #1a2028, stop:1 #161a20);
    border: 1px solid #2a323d;
    border-radius: 18px;
}
#presetCard {
    background: @@card@@;
    border: 1px solid @@border@@;
    border-radius: 14px;
}
#presetCard:hover { background: #1e242c; border-color: #3a4655; }
#habitButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 12px;
}
#habitButton:hover { background: #1a1f26; }
#habitButton[selected="true"] {
    background: #1e252e;
    border: 1px solid #2f3a46;
}
#habitName { font-size: 13px; font-weight: 700; }
#habitDays { color: @@muted@@; font-size: 11px; }
#habitDot { border-radius: 3px; }

QPushButton {
    background: @@card@@;
    border: 1px solid @@border@@;
    border-radius: 9px;
    padding: 8px 14px;
    color: @@text@@;
}
QPushButton:hover { background: #222932; border-color: #333c48; }
QPushButton:pressed { background: #262f39; }
QPushButton:disabled { color: @@faint@@; border-color: @@borderSoft@@; }

QPushButton[variant="primary"] {
    background: @@accent@@; color: #071e13; border: 1px solid @@accent@@;
    font-weight: 700; padding: 10px 18px;
}
QPushButton[variant="primary"]:hover { background: #8bf0bb; border-color: #8bf0bb; }
QPushButton[variant="primary"]:pressed { background: #5cd99a; }

QPushButton[variant="danger"] {
    background: @@dangerBg@@; border: 1px solid #512930;
    color: @@dangerSoft@@; font-weight: 700; padding: 11px 20px;
}
QPushButton[variant="danger"]:hover { background: #382025; border-color: #713941; }

QPushButton[variant="ghost"] {
    background: transparent; border: 1px solid @@border@@; color: @@muted@@;
}
QPushButton[variant="ghost"]:hover { background: @@cardAlt@@; color: @@text@@; }
QPushButton[variant="ghostDanger"] {
    background: transparent; border: 1px solid @@border@@; color: @@dangerSoft@@;
}
QPushButton[variant="ghostDanger"]:hover { background: @@dangerBg@@; border-color: #512930; }

QPushButton[variant="add"] {
    background: transparent; border: 1px dashed #333d48; color: @@muted@@;
    border-radius: 12px; padding: 11px 14px; text-align: left; font-weight: 600;
}
QPushButton[variant="add"]:hover { border-color: @@accent@@; color: @@accent@@; background: #16201b; }

QPushButton#iconButton {
    background: transparent; border: none; color: @@faint@@;
    font-size: 13px; padding: 3px 7px; border-radius: 7px;
}
QPushButton#iconButton:hover { background: @@dangerBg@@; color: @@dangerSoft@@; }

QLineEdit, QComboBox, QDateEdit, QDateTimeEdit, QDoubleSpinBox {
    background: #12151a;
    border: 1px solid #2a313b;
    border-radius: 9px;
    padding: 8px 10px;
    min-height: 19px;
    selection-background-color: #2d6a4f;
    selection-color: #eafff4;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDateTimeEdit:focus,
QDoubleSpinBox:focus { border-color: @@accent@@; }
QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled,
QDateTimeEdit:disabled, QDoubleSpinBox:disabled { color: @@faint@@; }
QComboBox { padding-right: 26px; }
QComboBox::drop-down, QDateEdit::drop-down, QDateTimeEdit::drop-down {
    border: none; width: 24px;
}
QComboBox::down-arrow, QDateEdit::down-arrow, QDateTimeEdit::down-arrow {
    image: url(@@chevron@@); width: 10px; height: 10px;
}
QComboBox QAbstractItemView {
    background: #161a20; border: 1px solid @@border@@; border-radius: 8px;
    padding: 4px; outline: 0; selection-background-color: #253039;
}
QAbstractItemView::item { padding: 6px; min-height: 22px; }
QCalendarWidget QWidget { alternate-background-color: #161a20; background: #161a20; }
QCalendarWidget QWidget#qt_calendar_navigationbar { background: #1b2028; }
QCalendarWidget QToolButton {
    background: transparent; border: none; color: @@text@@; padding: 4px 8px;
}
QCalendarWidget QToolButton:hover { background: #262d37; border-radius: 6px; }
QCalendarWidget QAbstractItemView:enabled {
    background: #161a20; color: @@text@@;
    selection-background-color: @@accent@@; selection-color: #071e13;
}
QCalendarWidget QSpinBox { background: #12151a; border: 1px solid #2a313b; }

QProgressBar { background: #12151a; border: none; border-radius: 4px; }
QProgressBar::chunk { border-radius: 4px; }

QMenu {
    background: #1a1f26; border: 1px solid @@border@@; border-radius: 10px;
    padding: 5px;
}
QMenu::item { padding: 7px 18px; border-radius: 6px; }
QMenu::item:selected { background: #262f39; }
QMenu::separator { height: 1px; background: @@border@@; margin: 4px 6px; }

QToolTip {
    background: #20262f; color: @@text@@; border: 1px solid #333c48;
    border-radius: 6px; padding: 5px 8px;
}

QMessageBox { background: @@bg@@; }
QMessageBox QLabel { color: @@text@@; }

#toast {
    background: #1b2621; border: 1px solid #2e5140; border-radius: 10px;
    color: #c9f7dd; padding: 10px 18px; font-size: 12px; font-weight: 600;
}
#errorToast {
    background: #2a1b1e; border: 1px solid #593039; border-radius: 10px;
    color: #ffc3c3; padding: 10px 18px; font-size: 12px; font-weight: 600;
}
"""


def stylesheet() -> str:
    qss = _QSS
    tokens = {
        "@@bg@@": BG,
        "@@sidebar@@": SIDEBAR,
        "@@card@@": CARD,
        "@@cardAlt@@": CARD_ALT,
        "@@border@@": BORDER,
        "@@borderSoft@@": BORDER_SOFT,
        "@@text@@": TEXT,
        "@@muted@@": MUTED,
        "@@faint@@": FAINT,
        "@@accent@@": ACCENT,
        "@@danger@@": DANGER,
        "@@dangerSoft@@": DANGER_SOFT,
        "@@dangerBg@@": DANGER_BG,
        "@@chevron@@": str(ASSETS / "chevron.svg"),
    }
    for key, value in tokens.items():
        qss = qss.replace(key, value)
    return qss


def icon_path() -> str:
    return str(ASSETS / "icon.svg")


def base_font() -> QFont:
    font = QFont("Cantarell", 10)
    return font


def apply(app) -> None:
    """Apply the app font and stylesheet in one place."""
    app.setFont(base_font())
    app.setStyleSheet(stylesheet())
