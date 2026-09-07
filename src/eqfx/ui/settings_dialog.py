from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from eqfx.core.autostart import set_autostart
from eqfx.core.engine import Engine


class SettingsDialog(QDialog):
    def __init__(self, engine: Engine, parent=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle("eqFX Settings")
        self.setModal(False)
        self.setMinimumWidth(460)
        self.setMinimumHeight(420)
        outer = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._session_page(), "Session")
        tabs.addTab(self._devices_page(), "Devices")
        outer.addWidget(tabs, 1)
        row = QHBoxLayout()
        row.addStretch()
        close = QPushButton("Close")
        close.clicked.connect(self.close)
        row.addWidget(close)
        outer.addLayout(row)
        engine.devices_changed.connect(self._fill_devices)
        engine.changed.connect(self._sync)
        self._sync()
        self._fill_devices()

    def _session_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        hint = QLabel(
            "eqFX sits in the PipeWire graph so games, browsers, and players "
            "all hear the same curve. Closing the window keeps it running in the tray."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        self.autostart = QCheckBox("Start eqFX when I log in")
        self.autostart.toggled.connect(self._toggle_autostart)
        self.start_tray = QCheckBox("Start in the background (tray only)")
        self.start_tray.toggled.connect(self._toggle_start_tray)
        self.close_tray = QCheckBox("Close window to tray instead of quitting")
        self.close_tray.toggled.connect(self._toggle_close_tray)
        layout.addRow(hint)
        layout.addRow(self.autostart)
        layout.addRow(self.start_tray)
        layout.addRow(self.close_tray)
        layout.addRow(QLabel(""))
        return page

    def _devices_page(self) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        hint = QLabel(
            "Games and music play into eqFX. eqFX then sends the equalized "
            "signal to the speakers or headset you pick. Leave Follow on if you "
            "switch outputs with Stream Deck or system buttons — those still "
            "choose the hardware, and eqFX stays in the path."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        self.follow = QCheckBox("Follow output-switcher buttons (Wave 3, speakers, …)")
        self.follow.toggled.connect(self._toggle_follow)
        self.device = QComboBox()
        self.device.currentIndexChanged.connect(self._pick_device)
        self.capture = QCheckBox("Make eqFX the default playback device")
        self.capture.toggled.connect(self._toggle_capture)
        self.restore = QCheckBox("Restore the previous default when eqFX quits")
        self.restore.toggled.connect(self._toggle_restore)
        self.remember = QCheckBox("Remember a separate EQ for each output device")
        self.remember.toggled.connect(self._toggle_remember)
        refresh = QPushButton("Refresh devices")
        refresh.clicked.connect(self.engine.refresh_devices)
        layout.addRow(hint)
        layout.addRow(self.follow)
        layout.addRow("Output device", self.device)
        layout.addRow("", refresh)
        layout.addRow(self.capture)
        layout.addRow(self.restore)
        layout.addRow(self.remember)
        return page

    def _sync(self) -> None:
        s = self.engine.settings
        widgets = [
            self.autostart,
            self.start_tray,
            self.close_tray,
            self.follow,
            self.capture,
            self.restore,
            self.remember,
            self.device,
        ]
        for widget in widgets:
            widget.blockSignals(True)
        self.autostart.setChecked(s.autostart)
        self.start_tray.setChecked(s.start_in_tray)
        self.close_tray.setChecked(s.close_to_tray)
        self.follow.setChecked(s.follow_default_output)
        self.capture.setChecked(s.capture_default)
        self.restore.setChecked(s.restore_default_on_quit)
        self.remember.setChecked(s.remember_per_device)
        self.device.setEnabled(not s.follow_default_output)
        for widget in widgets:
            widget.blockSignals(False)

    def _fill_devices(self) -> None:
        self.device.blockSignals(True)
        current = self.engine.settings.output_device
        self.device.clear()
        for sink in self.engine.devices:
            self.device.addItem(sink.description, sink.name)
            if sink.name == current:
                self.device.setCurrentIndex(self.device.count() - 1)
        if self.device.currentIndex() < 0 and self.device.count():
            self.device.setCurrentIndex(0)
        self.device.blockSignals(False)

    def _toggle_autostart(self, on: bool) -> None:
        self.engine.settings.autostart = on
        set_autostart(on)
        self.engine.persist()

    def _toggle_start_tray(self, on: bool) -> None:
        self.engine.settings.start_in_tray = on
        self.engine.persist()

    def _toggle_close_tray(self, on: bool) -> None:
        self.engine.settings.close_to_tray = on
        self.engine.persist()

    def _toggle_follow(self, on: bool) -> None:
        name = self.device.currentData() or ""
        self.engine.set_output_device(name, follow_default=on)
        self.device.setEnabled(not on)

    def _pick_device(self) -> None:
        if self.engine.settings.follow_default_output:
            return
        name = self.device.currentData() or ""
        if name:
            self.engine.set_output_device(name, follow_default=False)

    def _toggle_capture(self, on: bool) -> None:
        self.engine.settings.capture_default = on
        self.engine.persist()
        self.engine.engage()

    def _toggle_restore(self, on: bool) -> None:
        self.engine.settings.restore_default_on_quit = on
        self.engine.persist()

    def _toggle_remember(self, on: bool) -> None:
        self.engine.settings.remember_per_device = on
        self.engine.persist()
