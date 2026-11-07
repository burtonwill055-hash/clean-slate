"""Geometry/layout audit for the offscreen UI."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QScrollArea, QWidget

from clean_slate import theme
from clean_slate.app import MainWindow
from clean_slate.db import Database

DB = Path("/tmp/opencode/clean-slate-demo/demo.db")
SHOTS = Path("/tmp/opencode/clean-slate-shots")


def intersect_area(a: QRect, b: QRect) -> int:
    r = a.intersected(b)
    return max(0, r.width()) * max(0, r.height())


def main() -> None:
    app = QApplication([])
    theme.apply(app)
    db = Database(DB)
    window = MainWindow(db, remember_geometry=False)
    window.resize(1240, 850)
    window.show()
    app.processEvents()

    print(f"window: {window.width()}x{window.height()}  dpr={window.devicePixelRatio()}")
    print(f"sidebar: {window.findChild(QWidget, 'sidebar').geometry()}")
    print(f"stack: {window.stack.geometry()}  navigate page={window.stack.currentIndex()}")

    detail = window.detail
    content_h = detail.sizeHint().height()
    print(f"content sizeHint: {detail.sizeHint().width()}x{content_h}, "
          f"actual {detail.width()}x{detail.height()}, scroll viewport "
          f"{window.scroll.viewport().width()}x{window.scroll.viewport().height()}")

    # Key widget geometry, in window coordinates.
    names = ["card", "heroCard", "habitButton", "presetCard"]
    for name in names:
        widgets = detail.findChildren(QWidget, name)
        print(f"{name}: {len(widgets)}")
        for widget in widgets[:6]:
            top_left = widget.mapTo(window, QPoint(0, 0))
            print(f"  {top_left.x()},{top_left.y()} {widget.width()}x{widget.height()}")

    for cls_name in ("HeatmapWidget", "WeeklyChart", "MilestoneRing"):
        matches = [w for w in detail.findChildren(QWidget) if type(w).__name__ == cls_name]
        for match in matches:
            top_left = match.mapTo(window, QPoint(0, 0))
            print(f"{cls_name}: {top_left.x()},{top_left.y()} {match.width()}x{match.height()}")

    # Clipping checks for labels that do not wrap.
    problems = []
    for widget in window.findChildren(QLabel):
        if not widget.isVisible() or widget.wordWrap() or not widget.text():
            continue
        if widget.text().startswith("<"):
            continue
        needed = widget.fontMetrics().horizontalAdvance(widget.text())
        if needed > widget.width() + 2:
            problems.append((widget.text()[:45], needed, widget.width(),
                             widget.objectName()))
    print(f"non-wrapping labels wider than their box: {len(problems)}")
    for item in problems[:20]:
        print("  ", item)

    # Widgets extending beyond the window's right edge.
    outside = []
    for widget in window.findChildren(QWidget):
        if not widget.isVisible() or widget is window:
            continue
        top_left = widget.mapTo(window, QPoint(0, 0))
        if top_left.x() + widget.width() > window.width() + 1:
            outside.append((type(widget).__name__, widget.objectName(),
                            top_left.x(), widget.width()))
    print(f"widgets outside window width: {len(outside)}")
    for item in outside[:10]:
        print("  ", item)

    # Check the heatmap grid is fully inside its widget.
    heatmap = next((w for w in detail.findChildren(QWidget)
                    if type(w).__name__ == "HeatmapWidget"), None)
    if heatmap:
        start_x, top, cell = heatmap._geometry()
        grid_right = start_x + heatmap.WEEKS * cell + (heatmap.WEEKS - 1) * heatmap.GAP
        print(f"heatmap: cell={cell:.2f} start_x={start_x:.1f} grid_right={grid_right:.1f} "
              f"width={heatmap.width()} top={top}")
        days = [d for d in heatmap._cells]
        print(f"heatmap cells: {len(days)} (expected {heatmap.WEEKS * 7})")
        overlaps = 0
        rects = list(heatmap._cells.items())
        for i, (day_a, rect_a) in enumerate(rects[:200]):
            for day_b, rect_b in rects[i + 1: i + 40]:
                if day_a != day_b and intersect_area(rect_a, rect_b):
                    overlaps += 1
        print(f"heatmap overlaps (sampled): {overlaps}")

    # Milestone flow layout rows.
    chips = [w for w in detail.findChildren(QLabel)
             if w.text().endswith("d") and w.height() == 30]
    rows = {}
    for chip in chips:
        pos = chip.mapTo(detail, QPoint(0, 0))
        rows.setdefault(pos.y(), []).append((pos.x(), chip.width(), chip.text()))
    print(f"milestone chips: {len(chips)} across {len(rows)} rows")
    for y, items in sorted(rows.items()):
        right = max(x + w for x, w, _ in items)
        print(f"  row y={y}: {len(items)} chips, right edge={right}, "
              f"texts={[t for _, _, t in items]}")

    window.grab().save(str(SHOTS / "audit.png"))
    print("saved audit.png")
    window.close()


if __name__ == "__main__":
    main()
