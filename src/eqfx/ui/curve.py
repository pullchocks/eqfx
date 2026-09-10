from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from eqfx.core.presets import Band
from eqfx.ui.theme import C

MIN_F = 20.0
MAX_F = 20000.0


def _rbj(kind: str, f0: float, gain: float, q: float, freq: float) -> float:
    a = 10 ** (gain / 40.0)
    w0 = 2 * math.pi * (f0 / 48000.0)
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / (2 * max(q, 0.05))
    if kind == "peaking":
        b0 = 1 + alpha * a
        b1 = -2 * cosw
        b2 = 1 - alpha * a
        a0 = 1 + alpha / a
        a1 = -2 * cosw
        a2 = 1 - alpha / a
    elif kind == "lowshelf":
        two_sqrt_a_alpha = 2 * math.sqrt(a) * alpha
        b0 = a * ((a + 1) - (a - 1) * cosw + two_sqrt_a_alpha)
        b1 = 2 * a * ((a - 1) - (a + 1) * cosw)
        b2 = a * ((a + 1) - (a - 1) * cosw - two_sqrt_a_alpha)
        a0 = (a + 1) + (a - 1) * cosw + two_sqrt_a_alpha
        a1 = -2 * ((a - 1) + (a + 1) * cosw)
        a2 = (a + 1) + (a - 1) * cosw - two_sqrt_a_alpha
    elif kind == "highshelf":
        two_sqrt_a_alpha = 2 * math.sqrt(a) * alpha
        b0 = a * ((a + 1) + (a - 1) * cosw + two_sqrt_a_alpha)
        b1 = -2 * a * ((a - 1) + (a + 1) * cosw)
        b2 = a * ((a + 1) + (a - 1) * cosw - two_sqrt_a_alpha)
        a0 = (a + 1) - (a - 1) * cosw + two_sqrt_a_alpha
        a1 = 2 * ((a - 1) - (a + 1) * cosw)
        a2 = (a + 1) - (a - 1) * cosw - two_sqrt_a_alpha
    elif kind == "highpass":
        b0 = (1 + cosw) / 2
        b1 = -(1 + cosw)
        b2 = (1 + cosw) / 2
        a0 = 1 + alpha
        a1 = -2 * cosw
        a2 = 1 - alpha
    elif kind == "lowpass":
        b0 = (1 - cosw) / 2
        b1 = 1 - cosw
        b2 = (1 - cosw) / 2
        a0 = 1 + alpha
        a1 = -2 * cosw
        a2 = 1 - alpha
    elif kind == "notch":
        b0 = 1
        b1 = -2 * cosw
        b2 = 1
        a0 = 1 + alpha
        a1 = -2 * cosw
        a2 = 1 - alpha
    else:
        return 1.0
    b0 /= a0
    b1 /= a0
    b2 /= a0
    a1 /= a0
    a2 /= a0
    w = 2 * math.pi * (freq / 48000.0)
    cw, sw = math.cos(w), math.sin(w)
    num = (b0 + b1 * cw + b2 * math.cos(2 * w)) ** 2 + (b1 * sw + b2 * math.sin(2 * w)) ** 2
    den = (1 + a1 * cw + a2 * math.cos(2 * w)) ** 2 + (a1 * sw + a2 * math.sin(2 * w)) ** 2
    return math.sqrt(num / max(den, 1e-18))


def curve_db(bands: list[Band], freqs: list[float], bypass: bool = False) -> list[float]:
    out = []
    for freq in freqs:
        mag = 1.0
        if not bypass:
            for band in bands:
                if not band.enabled:
                    continue
                mag *= _rbj(band.type, band.frequency, band.gain, band.q, freq)
        out.append(20 * math.log10(mag + 1e-12))
    return out


class CurveWidget(QWidget):
    band_selected = Signal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.bands: list[Band] = []
        self.bypass = False
        self.selected = 5
        self._spectrum: list[float] = []
        self._spectrum_peaks: list[float] = []
        self._peak_l = 0.0
        self._peak_r = 0.0
        self._monitor_on = True
        self._node_points: list[QPointF] = []
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_state(self, bands: list[Band], selected: int, bypass: bool) -> None:
        self.bands = bands
        self.selected = selected
        self.bypass = bypass
        self.update()

    def set_spectrum(
        self,
        bars: list[float],
        peaks: list[float] | None = None,
        peak_l: float = 0.0,
        peak_r: float = 0.0,
        enabled: bool = True,
    ) -> None:
        self._spectrum = bars
        self._spectrum_peaks = peaks or []
        self._peak_l = peak_l
        self._peak_r = peak_r
        self._monitor_on = enabled
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(C.well))
        pad_l, pad_r, pad_t, pad_b = 36, 28, 10, 22
        w = max(1, self.width() - pad_l - pad_r)
        h = max(1, self.height() - pad_t - pad_b)
        painter.translate(pad_l, pad_t)
        range_db = 18.0
        painter.setPen(QPen(QColor(40, 45, 56), 1))
        for freq, label in ((20, "20"), (100, "100"), (1000, "1k"), (5000, "5k"), (20000, "20k")):
            x = math.log(freq / MIN_F) / math.log(MAX_F / MIN_F) * w
            painter.drawLine(QPointF(x, 0), QPointF(x, h))
            painter.setPen(QColor(C.mute))
            painter.drawText(int(x - 12), h + 16, label)
            painter.setPen(QPen(QColor(40, 45, 56), 1))
        for db in (-12, -6, 0, 6, 12):
            y = (range_db - db) / (range_db * 2) * h
            painter.setPen(QPen(QColor(C.accent) if db == 0 else QColor(40, 45, 56), 1))
            painter.drawLine(QPointF(0, y), QPointF(w, y))

        if self._monitor_on and self._spectrum:
            self._paint_spectrum(painter, w, h)

        freqs = [MIN_F * (MAX_F / MIN_F) ** (i / 255) for i in range(256)]
        dbs = curve_db(self.bands, freqs, self.bypass)
        path = QPainterPath()
        fill = QPainterPath()
        zero = (range_db - 0) / (range_db * 2) * h
        fill.moveTo(0, zero)
        for i, (freq, db) in enumerate(zip(freqs, dbs)):
            x = math.log(freq / MIN_F) / math.log(MAX_F / MIN_F) * w
            y = max(0, min(h, (range_db - db) / (range_db * 2) * h))
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
            fill.lineTo(x, y)
        fill.lineTo(w, zero)
        fill.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(62, 224, 198, 40 if self._spectrum else 55))
        grad.setColorAt(1, QColor(62, 224, 198, 0))
        painter.fillPath(fill, grad)
        painter.setPen(QPen(QColor("#6a7388" if self.bypass else C.accent), 2.2))
        painter.drawPath(path)
        self._node_points = []
        for i, band in enumerate(self.bands):
            x = math.log(max(MIN_F, min(MAX_F, band.frequency)) / MIN_F) / math.log(MAX_F / MIN_F) * w
            db = 0.0 if band.type in {"highpass", "lowpass", "notch"} else band.gain
            y = (range_db - db) / (range_db * 2) * h
            r = 7 if i == self.selected else 5.5
            painter.setBrush(QColor(C.accent if i == self.selected and band.enabled else C.panel))
            painter.setPen(QPen(QColor(C.accent_2 if band.enabled else C.mute), 1.4))
            painter.drawEllipse(QPointF(x, y), r, r)
            self._node_points.append(QPointF(pad_l + x, pad_t + y))

        if self._monitor_on:
            self._paint_meters(painter, w, h)
        painter.end()

    def _hit_band(self, pos) -> int | None:
        best = None
        best_dist = 14.0
        for i, point in enumerate(self._node_points):
            dx = pos.x() - point.x()
            dy = pos.y() - point.y()
            dist = math.hypot(dx, dy)
            if dist <= best_dist:
                best_dist = dist
                best = i
        return best

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            hit = self._hit_band(event.position())
            if hit is not None:
                self.band_selected.emit(hit)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        hit = self._hit_band(event.position())
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if hit is not None else Qt.CursorShape.ArrowCursor
        )
        super().mouseMoveEvent(event)

    def _paint_spectrum(self, painter: QPainter, w: int, h: int) -> None:
        n = len(self._spectrum)
        if n <= 0:
            return
        fill = QPainterPath()
        fill.moveTo(0, h)
        for i, level in enumerate(self._spectrum):
            x = (i + 0.5) / n * w
            y = h - max(0.0, min(1.0, level)) * h * 0.92
            if i == 0:
                fill.lineTo(0, y)
            fill.lineTo(x, y)
        fill.lineTo(w, h - max(0.0, min(1.0, self._spectrum[-1])) * h * 0.92)
        fill.lineTo(w, h)
        fill.closeSubpath()
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor(138, 248, 230, 70))
        grad.setColorAt(0.55, QColor(62, 224, 198, 38))
        grad.setColorAt(1, QColor(62, 224, 198, 6))
        painter.fillPath(fill, grad)
        if self._spectrum_peaks:
            peak_path = QPainterPath()
            for i, level in enumerate(self._spectrum_peaks):
                x = (i + 0.5) / n * w
                y = h - max(0.0, min(1.0, level)) * h * 0.92
                if i == 0:
                    peak_path.moveTo(x, y)
                else:
                    peak_path.lineTo(x, y)
            painter.setPen(QPen(QColor(138, 248, 230, 90), 1.0))
            painter.drawPath(peak_path)

    def _paint_meters(self, painter: QPainter, w: int, h: int) -> None:
        meter_w = 6
        gap = 4
        x0 = w + 10
        for i, peak in enumerate((self._peak_l, self._peak_r)):
            x = x0 + i * (meter_w + gap)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(40, 45, 56))
            painter.drawRoundedRect(x, 0, meter_w, h, 2, 2)
            level = max(0.0, min(1.0, peak))
            bar_h = level * h
            y = h - bar_h
            color = QColor(C.danger if level > 0.92 else C.warn if level > 0.78 else C.accent)
            painter.setBrush(color)
            painter.drawRoundedRect(x, int(y), meter_w, max(2, int(bar_h)), 2, 2)
