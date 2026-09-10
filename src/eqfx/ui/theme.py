from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class C:
    bg = "#07080b"
    panel = "#11141b"
    panel_alt = "#171b24"
    well = "#0a0c10"
    accent = "#3ee0c6"
    accent_2 = "#8af8e6"
    accent_dim = "#163833"
    text = "#eef1f6"
    muted = "#8d95a8"
    mute = "#5c6478"
    danger = "#e15b5b"
    warn = "#e8a35a"
    border = "#2a3140"
    input = "#0c0e13"
    on_accent = "#06211c"


def stylesheet() -> str:
    return f"""
QWidget {{
    background: {C.bg};
    color: {C.text};
    font-family: "Inter", "Segoe UI", "Ubuntu", sans-serif;
    font-size: 13px;
}}
QMainWindow, QDialog {{
    background: {C.bg};
}}
QLabel {{
    background: transparent;
}}
QLabel#brand {{
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 2px;
}}
QLabel#hint, QLabel#muted {{
    color: {C.muted};
}}
QLabel#readout {{
    font-family: "IBM Plex Mono", "JetBrains Mono", monospace;
    font-size: 11px;
    color: {C.accent_2};
}}
QFrame#panel, QWidget#panel {{
    background: {C.panel};
    border: 1px solid {C.border};
    border-radius: 12px;
}}
QPushButton {{
    background: {C.panel};
    color: {C.muted};
    border: 1px solid {C.border};
    border-radius: 8px;
    padding: 6px 12px;
    font-weight: 600;
    letter-spacing: 0.6px;
}}
QPushButton:hover {{
    color: {C.text};
    border-color: {C.accent};
}}
QPushButton#accent, QPushButton:checked, QPushButton[on="true"] {{
    background: {C.accent};
    color: {C.on_accent};
    border-color: {C.accent};
}}
QPushButton#danger {{
    color: {C.danger};
}}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
    background: {C.input};
    color: {C.text};
    border: 1px solid {C.border};
    border-radius: 8px;
    padding: 4px 8px;
    min-height: 28px;
}}
QComboBox:focus, QLineEdit:focus {{
    border-color: {C.accent};
}}
QListWidget {{
    background: {C.well};
    border: 1px solid {C.border};
    border-radius: 8px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px;
    border-radius: 6px;
}}
QListWidget::item:selected {{
    background: {C.accent_dim};
    color: {C.accent_2};
}}
QCheckBox {{
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {C.border};
    background: {C.input};
}}
QCheckBox::indicator:checked {{
    background: {C.accent};
    border-color: {C.accent};
}}
QFrame#bandCol {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
}}
QFrame#bandCol[selected="true"] {{
    background: {C.accent_dim};
    border: 1px solid {C.accent};
}}
QLabel#bandPick {{
    font-weight: 600;
    color: {C.accent_2};
}}
QPushButton#bandStep {{
    min-width: 32px;
    max-width: 32px;
    padding: 6px 0;
}}
QSlider::groove:vertical {{
    background: {C.well};
    width: 8px;
    border-radius: 4px;
}}
QSlider::handle:vertical {{
    background: {C.accent};
    height: 14px;
    margin: 0 -5px;
    border-radius: 7px;
}}
QSlider::add-page:vertical {{
    background: {C.accent};
    border-radius: 4px;
}}
QSlider::sub-page:vertical {{
    background: {C.well};
}}
QSlider::groove:horizontal {{
    background: {C.well};
    height: 6px;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {C.accent};
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QTabWidget::pane {{
    border: 1px solid {C.border};
    border-radius: 10px;
    background: {C.panel};
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {C.muted};
    padding: 8px 14px;
    margin-right: 2px;
}}
QTabBar::tab:selected {{
    color: {C.accent_2};
    border-bottom: 2px solid {C.accent};
}}
QStatusBar {{
    color: {C.muted};
    background: {C.bg};
}}
QMenu {{
    background: {C.panel};
    border: 1px solid {C.border};
    padding: 6px;
}}
QMenu::item:selected {{
    background: {C.accent_dim};
    color: {C.accent_2};
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {C.border};
    border-radius: 4px;
    min-height: 24px;
}}
"""


def apply_app_theme(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(C.bg))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(C.text))
    palette.setColor(QPalette.ColorRole.Base, QColor(C.input))
    palette.setColor(QPalette.ColorRole.Text, QColor(C.text))
    palette.setColor(QPalette.ColorRole.Button, QColor(C.panel))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(C.text))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(C.accent))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(C.on_accent))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet())
