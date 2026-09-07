from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from eqfx.ui.theme import C


def icon_pixmap(size: int = 128) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    box = QRectF(size * 0.08, size * 0.08, size * 0.84, size * 0.84)
    painter.setPen(QPen(QColor(C.muted), max(1.5, size / 28)))
    painter.setBrush(QColor(C.bg))
    painter.drawRoundedRect(box, size * 0.16, size * 0.16)
    path = QPainterPath()
    path.moveTo(box.left() + box.width() * 0.12, box.center().y() + box.height() * 0.12)
    path.cubicTo(
        box.left() + box.width() * 0.28, box.top() + box.height() * 0.18,
        box.left() + box.width() * 0.42, box.bottom() - box.height() * 0.22,
        box.center().x(), box.center().y() - box.height() * 0.04,
    )
    path.cubicTo(
        box.center().x() + box.width() * 0.16, box.top() + box.height() * 0.16,
        box.right() - box.width() * 0.16, box.center().y() + box.height() * 0.08,
        box.right() - box.width() * 0.1, box.center().y() + box.height() * 0.02,
    )
    painter.setPen(QPen(QColor(C.accent), max(2, size / 16)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)
    painter.end()
    return pm


def application_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 22, 24, 32, 48, 64, 128):
        icon.addPixmap(icon_pixmap(size))
    return icon


def tray_icon() -> QIcon:
    return application_icon()
