from __future__ import annotations

import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

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
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.bands: list[Band] = []
        self.bypass = False
        self.selected = 5
        self.setMinimumHeight(168)

    def set_state(self, bands: list[Band], selected: int, bypass: bool) -> None:
        self.bands = bands
        self.selected = selected
        self.bypass = bypass
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(C.well))
        pad_l, pad_r, pad_t, pad_b = 36, 10, 10, 22
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
        grad.setColorAt(0, QColor(62, 224, 198, 55))
        grad.setColorAt(1, QColor(62, 224, 198, 0))
        painter.fillPath(fill, grad)
        painter.setPen(QPen(QColor("#6a7388" if self.bypass else C.accent), 2.2))
        painter.drawPath(path)
        for i, band in enumerate(self.bands):
            x = math.log(max(MIN_F, min(MAX_F, band.frequency)) / MIN_F) / math.log(MAX_F / MIN_F) * w
            db = 0.0 if band.type in {"highpass", "lowpass", "notch"} else band.gain
            y = (range_db - db) / (range_db * 2) * h
            r = 7 if i == self.selected else 5.5
            painter.setBrush(QColor(C.accent if i == self.selected and band.enabled else C.panel))
            painter.setPen(QPen(QColor(C.accent_2 if band.enabled else C.mute), 1.4))
            painter.drawEllipse(QPointF(x, y), r, r)
        painter.end()
