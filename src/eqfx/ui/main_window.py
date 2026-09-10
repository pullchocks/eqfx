from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStatusBar,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from eqfx.core.engine import Engine
from eqfx.core.presets import CATEGORIES, LABELS, PRESETS, format_db, format_freq, load_user_presets
from eqfx.ui.curve import CurveWidget
from eqfx.ui.icons import application_icon, tray_icon
from eqfx.ui.settings_dialog import SettingsDialog


class BandColumn(QFrame):
    clicked = Signal(int)

    def __init__(self, index: int, parent=None) -> None:
        super().__init__(parent)
        self.index = index
        self.setObjectName("bandCol")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
        super().mousePressEvent(event)


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
        self.setMinimumSize(720, 520)
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
        self.curve.setMinimumHeight(160)
        self.curve.band_selected.connect(self._select)
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
        self._spectrum_timer = QTimer(self)
        self._spectrum_timer.setInterval(50)
        self._spectrum_timer.timeout.connect(self._tick_spectrum)
        self._spectrum_timer.start()
        self._sync()
        self._fill_presets()
        self._fill_saved(switch_tab=True)
        self._fill_devices()

        bypass_sc = QAction(self)
        bypass_sc.setShortcut(QKeySequence("B"))
        bypass_sc.triggered.connect(lambda: self.engine.set_bypass(not self.engine.settings.bypass))
        self.addAction(bypass_sc)
        prev_band = QAction(self)
        prev_band.setShortcut(QKeySequence("["))
        prev_band.setToolTip("Previous band")
        prev_band.triggered.connect(lambda: self._select((self.selected - 1) % 10))
        self.addAction(prev_band)
        next_band = QAction(self)
        next_band.setShortcut(QKeySequence("]"))
        next_band.setToolTip("Next band")
        next_band.triggered.connect(lambda: self._select((self.selected + 1) % 10))
        self.addAction(next_band)

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
        self.monitor_btn = QPushButton("Monitor")
        self.monitor_btn.setCheckable(True)
        self.monitor_btn.setChecked(True)
        self.monitor_btn.setToolTip("Live post-EQ spectrum from the current output device")
        self.monitor_btn.toggled.connect(self.engine.set_monitor_enabled)
        self.device = QComboBox()
        self.device.setMinimumWidth(180)
        self.device.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.device.currentIndexChanged.connect(self._pick_device)
        settings = QPushButton("Settings")
        settings.clicked.connect(self._open_settings)
        row.addWidget(brand)
        row.addWidget(sub)
        row.addStretch()
        row.addWidget(QLabel("Output"))
        row.addWidget(self.device)
        row.addWidget(self.monitor_btn)
        row.addWidget(self.bypass)
        row.addWidget(settings)
        return bar

    def _presets_pane(self) -> QWidget:
        pane = QFrame()
        pane.setObjectName("panel")
        pane.setMinimumWidth(220)
        pane.setMaximumWidth(300)
        pane.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.preset_tabs = QTabWidget()
        self.preset_tabs.addTab(self._factory_tab(), "Factory")
        self.preset_tabs.addTab(self._saved_tab(), "Saved")
        layout.addWidget(self.preset_tabs, 1)
        return pane

    def _factory_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
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
        return page

    def _saved_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)
        self.saved_search = QLineEdit()
        self.saved_search.setPlaceholderText("Search saved")
        self.saved_search.textChanged.connect(self._fill_saved)
        self.saved_list = QListWidget()
        self.saved_list.itemClicked.connect(self._pick_saved)
        self.save_name = QLineEdit()
        self.save_name.setPlaceholderText("Name for current curve")
        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        save_btn = QPushButton("Save")
        save_btn.setToolTip("Save the current EQ curve under this name")
        save_btn.setObjectName("accent")
        save_btn.clicked.connect(self._save_current)
        update_btn = QPushButton("Update")
        update_btn.setToolTip("Overwrite the selected saved curve with the current EQ")
        update_btn.clicked.connect(self._update_selected_save)
        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("danger")
        delete_btn.setToolTip("Delete the selected saved curve")
        delete_btn.clicked.connect(self._delete_selected_save)
        buttons.addWidget(save_btn, 1)
        buttons.addWidget(update_btn)
        buttons.addWidget(delete_btn)
        hint = QLabel("Your curves stay separate from factory presets.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(self.saved_search)
        layout.addWidget(self.saved_list, 1)
        layout.addWidget(self.save_name)
        layout.addLayout(buttons)
        layout.addWidget(hint)
        return page

    def _sliders(self) -> QWidget:
        box = QFrame()
        box.setObjectName("panel")
        row = QHBoxLayout(box)
        row.setContentsMargins(8, 8, 8, 8)
        row.setSpacing(4)
        self.sliders: list[QSlider] = []
        self.slider_labels: list[QLabel] = []
        self.gain_labels: list[QLabel] = []
        self.band_cols: list[BandColumn] = []
        for i in range(10):
            col = BandColumn(i)
            col.clicked.connect(self._select)
            layout = QVBoxLayout(col)
            layout.setContentsMargins(4, 6, 4, 6)
            layout.setSpacing(4)
            gain = QLabel("0.0")
            gain.setObjectName("readout")
            gain.setAlignment(Qt.AlignmentFlag.AlignCenter)
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-120, 120)
            slider.setValue(0)
            slider.setMinimumHeight(100)
            slider.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            slider.valueChanged.connect(lambda value, idx=i: self._slider_moved(idx, value))
            slider.sliderPressed.connect(lambda idx=i: self._select(idx))
            name = QLabel(f"B{i + 1}")
            name.setObjectName("muted")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            freq = QLabel("")
            freq.setObjectName("muted")
            freq.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(gain)
            layout.addWidget(slider, 0, Qt.AlignmentFlag.AlignHCenter)
            layout.addWidget(name)
            layout.addWidget(freq)
            row.addWidget(col, 1)
            self.band_cols.append(col)
            self.sliders.append(slider)
            self.slider_labels.append(freq)
            self.gain_labels.append(gain)
        return box

    def _inspector(self) -> QWidget:
        box = QFrame()
        box.setObjectName("panel")
        row = QHBoxLayout(box)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(8)

        pick_label = QLabel("Band")
        pick_label.setObjectName("bandPick")
        self.band_box = QComboBox()
        self.band_box.setMinimumWidth(150)
        self.band_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        for i in range(10):
            self.band_box.addItem(f"Band {i + 1}", i)
        self.band_box.currentIndexChanged.connect(self._band_box_changed)
        prev = QPushButton("‹")
        prev.setObjectName("bandStep")
        prev.setToolTip("Previous band ([)")
        prev.clicked.connect(lambda: self._select((self.selected - 1) % 10))
        nxt = QPushButton("›")
        nxt.setObjectName("bandStep")
        nxt.setToolTip("Next band (])")
        nxt.clicked.connect(lambda: self._select((self.selected + 1) % 10))

        self.type_box = QComboBox()
        self.type_box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        for key, label in LABELS.items():
            self.type_box.addItem(label, key)
        self.type_box.currentIndexChanged.connect(self._type_changed)

        self.freq = QDoubleSpinBox()
        self.freq.setRange(20, 20000)
        self.freq.setDecimals(1)
        self.freq.setSuffix(" Hz")
        self.freq.setMinimumWidth(96)
        self.freq.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.freq.valueChanged.connect(lambda v: self.engine.set_band(self.selected, frequency=v))

        self.q = QDoubleSpinBox()
        self.q.setRange(0.1, 18)
        self.q.setDecimals(2)
        self.q.setSingleStep(0.05)
        self.q.setMinimumWidth(72)
        self.q.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.q.valueChanged.connect(lambda v: self.engine.set_band(self.selected, q=v))

        self.gain = QDoubleSpinBox()
        self.gain.setRange(-12.0, 12.0)
        self.gain.setDecimals(1)
        self.gain.setSingleStep(0.1)
        self.gain.setSuffix(" dB")
        self.gain.setMinimumWidth(88)
        self.gain.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.gain.valueChanged.connect(self._gain_spin_changed)

        self.enable_btn = QPushButton("On")
        self.enable_btn.setCheckable(True)
        self.enable_btn.setToolTip("Enable or disable this band")
        self.enable_btn.toggled.connect(self._enable_toggled)
        reset = QPushButton("Reset band")
        reset.setToolTip("Reset only the selected band")
        reset.clicked.connect(lambda: self.engine.reset_band(self.selected))

        row.addWidget(pick_label)
        row.addWidget(prev)
        row.addWidget(self.band_box)
        row.addWidget(nxt)
        row.addSpacing(8)
        row.addWidget(QLabel("Type"))
        row.addWidget(self.type_box)
        row.addWidget(QLabel("Freq"))
        row.addWidget(self.freq)
        row.addWidget(QLabel("Q"))
        row.addWidget(self.q)
        row.addWidget(QLabel("Gain"))
        row.addWidget(self.gain)
        row.addWidget(self.enable_btn)
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

    def _fill_saved(self, switch_tab: bool = False) -> None:
        query = self.saved_search.text().strip().lower()
        self.saved_list.clear()
        for preset in load_user_presets(force=True):
            blob = f"{preset.name} {preset.description}".lower()
            if query and query not in blob:
                continue
            item = QListWidgetItem(preset.name)
            item.setToolTip(preset.description)
            item.setData(Qt.ItemDataRole.UserRole, preset.id)
            self.saved_list.addItem(item)
            if preset.id == self.engine.settings.preset_id:
                item.setSelected(True)
                self.saved_list.setCurrentItem(item)
                if not self.save_name.text().strip():
                    self.save_name.setText(preset.name)
                if switch_tab:
                    self.preset_tabs.setCurrentIndex(1)

    def _pick_preset(self, item: QListWidgetItem) -> None:
        preset_id = item.data(Qt.ItemDataRole.UserRole)
        if preset_id:
            self.engine.load_preset(preset_id)
            self.saved_list.clearSelection()

    def _pick_saved(self, item: QListWidgetItem) -> None:
        preset_id = item.data(Qt.ItemDataRole.UserRole)
        if not preset_id:
            return
        self.engine.load_preset(preset_id)
        self.save_name.setText(item.text())
        self.preset_list.clearSelection()

    def _save_current(self) -> None:
        name = self.save_name.text().strip()
        if not name:
            self.status.showMessage("Enter a name for this save")
            self.save_name.setFocus()
            return
        preset = self.engine.save_current_as(name)
        self.save_name.setText(preset.name)
        self._fill_saved()
        self.preset_tabs.setCurrentIndex(1)

    def _update_selected_save(self) -> None:
        item = self.saved_list.currentItem()
        if item is None:
            self.status.showMessage("Select a saved curve to update")
            return
        preset_id = item.data(Qt.ItemDataRole.UserRole)
        name = self.save_name.text().strip() or item.text()
        preset = self.engine.save_current_as(name, replace_id=str(preset_id))
        self.save_name.setText(preset.name)
        self._fill_saved()

    def _delete_selected_save(self) -> None:
        item = self.saved_list.currentItem()
        if item is None:
            self.status.showMessage("Select a saved curve to delete")
            return
        preset_id = str(item.data(Qt.ItemDataRole.UserRole) or "")
        name = item.text()
        answer = QMessageBox.question(
            self,
            "Delete save",
            f'Delete "{name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.engine.delete_saved(preset_id):
            self._fill_saved()
            self._fill_presets()

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
        self.selected = max(0, min(9, int(index)))
        self._sync()

    def _band_box_changed(self) -> None:
        if self._filling:
            return
        data = self.band_box.currentData()
        if data is not None:
            self._select(int(data))

    def _slider_moved(self, index: int, value: int) -> None:
        if self._filling:
            return
        self.selected = index
        self.engine.set_band(index, gain=value / 10.0, enabled=True)

    def _gain_spin_changed(self, value: float) -> None:
        if self._filling:
            return
        self.engine.set_band(self.selected, gain=float(value), enabled=True)

    def _type_changed(self) -> None:
        if self._filling:
            return
        kind = self.type_box.currentData()
        if kind:
            self.engine.set_band(self.selected, type=kind, enabled=True)

    def _enable_toggled(self, on: bool) -> None:
        if self._filling:
            return
        self.engine.set_band(self.selected, enabled=bool(on))

    def _sync(self) -> None:
        self._filling = True
        for widget in (
            *self.sliders,
            self.freq,
            self.q,
            self.gain,
            self.type_box,
            self.band_box,
            self.bypass,
            self.monitor_btn,
            self.enable_btn,
            self.device,
        ):
            widget.blockSignals(True)
        self.bypass.setChecked(self.engine.settings.bypass)
        self.bypass.setProperty("on", self.engine.settings.bypass)
        self.bypass.style().unpolish(self.bypass)
        self.bypass.style().polish(self.bypass)
        self.monitor_btn.setChecked(self.engine.monitor_enabled)
        self.monitor_btn.setProperty("on", self.engine.monitor_enabled)
        self.monitor_btn.style().unpolish(self.monitor_btn)
        self.monitor_btn.style().polish(self.monitor_btn)
        for i, band in enumerate(self.engine.bands):
            self.sliders[i].setValue(int(round(band.gain * 10)))
            self.gain_labels[i].setText(format_db(band.gain) if band.enabled else "off")
            self.slider_labels[i].setText(format_freq(band.frequency))
            self.band_box.setItemText(
                i, f"Band {i + 1}  ·  {format_freq(band.frequency)}  ·  {LABELS.get(band.type, band.type)}"
            )
            selected = i == self.selected
            self.band_cols[i].setProperty("selected", selected)
            self.band_cols[i].style().unpolish(self.band_cols[i])
            self.band_cols[i].style().polish(self.band_cols[i])
        band = self.engine.bands[self.selected]
        self.band_box.setCurrentIndex(self.selected)
        idx = self.type_box.findData(band.type)
        if idx >= 0:
            self.type_box.setCurrentIndex(idx)
        self.freq.setValue(band.frequency)
        self.q.setValue(band.q)
        self.gain.setValue(band.gain)
        self.enable_btn.setChecked(band.enabled)
        self.enable_btn.setText("On" if band.enabled else "Off")
        self.enable_btn.setProperty("on", band.enabled)
        self.enable_btn.style().unpolish(self.enable_btn)
        self.enable_btn.style().polish(self.enable_btn)
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
        for widget in (
            *self.sliders,
            self.freq,
            self.q,
            self.gain,
            self.type_box,
            self.band_box,
            self.bypass,
            self.monitor_btn,
            self.enable_btn,
            self.device,
        ):
            widget.blockSignals(False)
        self._filling = False

    def _tick_spectrum(self) -> None:
        enabled = self.engine.monitor_enabled
        if not enabled:
            self.curve.set_spectrum([], [], 0.0, 0.0, enabled=False)
            return
        bars, peaks, peak_l, peak_r = self.engine.monitor.snapshot()
        self.curve.set_spectrum(bars, peaks, peak_l, peak_r, enabled=True)
