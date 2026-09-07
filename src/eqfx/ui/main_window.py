from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QPushButton,
    QSlider,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
)

from eqfx.core.engine import Engine
from eqfx.core.presets import CATEGORIES, LABELS, PRESETS, format_db, format_freq
from eqfx.ui.curve import CurveWidget
from eqfx.ui.icons import application_icon, tray_icon
from eqfx.ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, engine: Engine) -> None:
        super().__init__()
        self.engine = engine
        self.selected = 5
        self._force_quit = False
        self._settings: SettingsDialog | None = None
        self._filling = False
        self.setWindowTitle("eqFX")
        self.setWindowIcon(application_icon())
        self.resize(860, 620)
        self._setup_tray()

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(10)
        layout.addWidget(self._presets_pane(), 0)
        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(self._topbar())
        self.curve = CurveWidget()
        wrap = QFrame()
        wrap.setObjectName("panel")
        curve_l = QVBoxLayout(wrap)
        curve_l.setContentsMargins(8, 8, 8, 8)
        curve_l.addWidget(self.curve)
        right.addWidget(wrap, 1)
        right.addWidget(self._sliders())
        right.addWidget(self._inspector())
        layout.addLayout(right, 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        engine.changed.connect(self._sync)
        engine.status.connect(self.status.showMessage)
        engine.devices_changed.connect(self._fill_devices)
        self._sync()
        self._fill_presets()
        self._fill_devices()

        bypass_sc = QAction(self)
        bypass_sc.setShortcut(QKeySequence("B"))
        bypass_sc.triggered.connect(lambda: self.engine.set_bypass(not self.engine.settings.bypass))
        self.addAction(bypass_sc)

    def _topbar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("panel")
        row = QHBoxLayout(bar)
        brand = QLabel("eqFX")
        brand.setObjectName("brand")
        sub = QLabel("LIVE  ·  10 BAND")
        sub.setObjectName("muted")
        self.bypass = QPushButton("Bypass")
        self.bypass.setCheckable(True)
        self.bypass.toggled.connect(self.engine.set_bypass)
        self.device = QComboBox()
        self.device.setMinimumWidth(220)
        self.device.currentIndexChanged.connect(self._pick_device)
        settings = QPushButton("Settings")
        settings.clicked.connect(self._open_settings)
        row.addWidget(brand)
        row.addWidget(sub)
        row.addStretch()
        row.addWidget(QLabel("Output"))
        row.addWidget(self.device)
        row.addWidget(self.bypass)
        row.addWidget(settings)
        return bar

    def _presets_pane(self) -> QWidget:
        pane = QFrame()
        pane.setObjectName("panel")
        pane.setFixedWidth(250)
        layout = QVBoxLayout(pane)
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"Search {len(PRESETS)} presets")
        self.search.textChanged.connect(self._fill_presets)
        self.category = QComboBox()
        for cat in CATEGORIES:
            self.category.addItem(cat)
        self.category.currentTextChanged.connect(self._fill_presets)
        self.preset_list = QListWidget()
        self.preset_list.itemClicked.connect(self._pick_preset)
        layout.addWidget(self.search)
        layout.addWidget(self.category)
        layout.addWidget(self.preset_list, 1)
        return pane

    def _sliders(self) -> QWidget:
        box = QFrame()
        box.setObjectName("panel")
        row = QHBoxLayout(box)
        row.setContentsMargins(10, 10, 10, 8)
        self.sliders: list[QSlider] = []
        self.slider_labels: list[QLabel] = []
        self.gain_labels: list[QLabel] = []
        for i in range(10):
            col = QVBoxLayout()
            gain = QLabel("0.0")
            gain.setObjectName("readout")
            gain.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-120, 120)
            slider.setValue(0)
            slider.setMinimumHeight(120)
            slider.valueChanged.connect(lambda value, idx=i: self._slider_moved(idx, value))
            slider.sliderPressed.connect(lambda idx=i: self._select(idx))
            name = QLabel(str(i + 1))
            name.setObjectName("muted")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            freq = QLabel("")
            freq.setObjectName("muted")
            freq.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col.addWidget(gain)
            col.addWidget(slider, 1, Qt.AlignmentFlag.AlignHCenter)
            col.addWidget(name)
            col.addWidget(freq)
            row.addLayout(col)
            self.sliders.append(slider)
            self.slider_labels.append(freq)
            self.gain_labels.append(gain)
        return box

    def _inspector(self) -> QWidget:
        box = QFrame()
        box.setObjectName("panel")
        row = QHBoxLayout(box)
        self.sel_label = QLabel("Band 6")
        self.type_box = QComboBox()
        for key, label in LABELS.items():
            self.type_box.addItem(label, key)
        self.type_box.currentIndexChanged.connect(self._type_changed)
        self.freq = QDoubleSpinBox()
        self.freq.setRange(20, 20000)
        self.freq.setDecimals(1)
        self.freq.setSuffix(" Hz")
        self.freq.valueChanged.connect(lambda v: self.engine.set_band(self.selected, frequency=v))
        self.q = QDoubleSpinBox()
        self.q.setRange(0.1, 18)
        self.q.setDecimals(2)
        self.q.setSingleStep(0.05)
        self.q.valueChanged.connect(lambda v: self.engine.set_band(self.selected, q=v))
        enable = QPushButton("On")
        enable.clicked.connect(self._toggle_enable)
        self.enable_btn = enable
        reset = QPushButton("Init")
        reset.clicked.connect(self.engine.reset_bands)
        row.addWidget(self.sel_label)
        row.addWidget(self.type_box)
        row.addWidget(QLabel("Freq"))
        row.addWidget(self.freq)
        row.addWidget(QLabel("Q"))
        row.addWidget(self.q)
        row.addWidget(enable)
        row.addStretch()
        row.addWidget(reset)
        return box

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(tray_icon(), self)
        menu = QMenu()
        show = QAction("Show eqFX", self)
        show.triggered.connect(self._show_from_tray)
        bypass = QAction("Toggle bypass", self)
        bypass.triggered.connect(lambda: self.engine.set_bypass(not self.engine.settings.bypass))
        settings = QAction("Settings", self)
        settings.triggered.connect(self._open_settings)
        quit_act = QAction("Quit", self)
        quit_act.triggered.connect(self._quit)
        menu.addAction(show)
        menu.addAction(bypass)
        menu.addAction(settings)
        menu.addSeparator()
        menu.addAction(quit_act)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self._show_from_tray()
            if reason == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
        self.tray.setToolTip("eqFX")
        self.tray.show()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        self._force_quit = True
        self.engine.shutdown()
        QApplication.quit()

    def closeEvent(self, event) -> None:
        if self._force_quit or not self.engine.settings.close_to_tray or not self.tray.isVisible():
            self.engine.shutdown()
            event.accept()
            return
        event.ignore()
        self.hide()
        self.tray.showMessage("eqFX", "Still equalizing in the background.", QSystemTrayIcon.MessageIcon.NoIcon, 1800)

    def _open_settings(self) -> None:
        if self._settings is None:
            self._settings = SettingsDialog(self.engine, self)
        self._settings.show()
        self._settings.raise_()

    def _fill_presets(self) -> None:
        query = self.search.text().strip().lower()
        category = self.category.currentText()
        self.preset_list.clear()
        for preset in PRESETS:
            if category != "All" and preset.category != category:
                continue
            blob = f"{preset.name} {preset.category} {preset.description}".lower()
            if query and query not in blob:
                continue
            item = QListWidgetItem(preset.name)
            item.setToolTip(preset.description)
            item.setData(Qt.ItemDataRole.UserRole, preset.id)
            self.preset_list.addItem(item)
            if preset.id == self.engine.settings.preset_id:
                item.setSelected(True)
                self.preset_list.setCurrentItem(item)

    def _pick_preset(self, item: QListWidgetItem) -> None:
        preset_id = item.data(Qt.ItemDataRole.UserRole)
        if preset_id:
            self.engine.load_preset(preset_id)

    def _fill_devices(self) -> None:
        self._filling = True
        current = self.engine.settings.output_device
        self.device.clear()
        self.device.addItem("Follow system default", "")
        for sink in self.engine.devices:
            self.device.addItem(sink.description, sink.name)
            if sink.name == current and not self.engine.settings.follow_default_output:
                self.device.setCurrentIndex(self.device.count() - 1)
        if self.engine.settings.follow_default_output:
            if self.engine.target:
                self.device.setItemText(0, f"Follow · {self.engine.target.description}")
            self.device.setCurrentIndex(0)
        self._filling = False

    def _pick_device(self) -> None:
        if self._filling:
            return
        name = self.device.currentData()
        follow = name in (None, "")
        self.engine.set_output_device("" if follow else str(name), follow_default=follow)

    def _select(self, index: int) -> None:
        self.selected = index
        self._sync()

    def _slider_moved(self, index: int, value: int) -> None:
        if self._filling:
            return
        self.selected = index
        self.engine.set_band(index, gain=value / 10.0, enabled=True)

    def _type_changed(self) -> None:
        if self._filling:
            return
        kind = self.type_box.currentData()
        if kind:
            self.engine.set_band(self.selected, type=kind, enabled=True)

    def _toggle_enable(self) -> None:
        band = self.engine.bands[self.selected]
        self.engine.set_band(self.selected, enabled=not band.enabled)

    def _sync(self) -> None:
        self._filling = True
        for widget in (*self.sliders, self.freq, self.q, self.type_box, self.bypass, self.device):
            widget.blockSignals(True)
        self.bypass.setChecked(self.engine.settings.bypass)
        self.bypass.setProperty("on", self.engine.settings.bypass)
        self.bypass.style().unpolish(self.bypass)
        self.bypass.style().polish(self.bypass)
        for i, band in enumerate(self.engine.bands):
            self.sliders[i].setValue(int(round(band.gain * 10)))
            self.gain_labels[i].setText(format_db(band.gain) if band.enabled else "off")
            self.slider_labels[i].setText(format_freq(band.frequency))
        band = self.engine.bands[self.selected]
        self.sel_label.setText(f"Band {self.selected + 1}  ·  {LABELS.get(band.type, band.type)}")
        idx = self.type_box.findData(band.type)
        if idx >= 0:
            self.type_box.setCurrentIndex(idx)
        self.freq.setValue(band.frequency)
        self.q.setValue(band.q)
        self.enable_btn.setText("On" if band.enabled else "Off")
        self.curve.set_state(self.engine.bands, self.selected, self.engine.settings.bypass)
        self.tray.setToolTip("eqFX bypassed" if self.engine.settings.bypass else f"eqFX · {self.engine.settings.preset_id}")
        if self.engine.settings.follow_default_output and self.device.count():
            label = (
                f"Follow · {self.engine.target.description}"
                if self.engine.target
                else "Follow system default"
            )
            self.device.setItemText(0, label)
            self.device.setCurrentIndex(0)
        for widget in (*self.sliders, self.freq, self.q, self.type_box, self.bypass, self.device):
            widget.blockSignals(False)
        self._filling = False
