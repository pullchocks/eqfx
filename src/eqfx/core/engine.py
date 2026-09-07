from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from eqfx.core.autostart import set_autostart
from eqfx.core.pipewire import (
    FilterChain,
    Sink,
    default_hardware,
    hardware_sinks,
    eqfx_sink,
    move_app_streams_to_eqfx,
    playback_destination,
    set_default_sink,
    user_selected_hardware,
)
from eqfx.core.presets import PRESETS, Band, apply_patches, find_preset
from eqfx.core.store import (
    Settings,
    clear_wanted_output,
    clear_wanted_preset,
    curve_for_device,
    load_settings,
    peek_wanted_output,
    peek_wanted_preset,
    save_settings,
    store_device_curve,
)


class Engine(QObject):
    changed = Signal()
    status = Signal(str)
    devices_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.settings = load_settings()
        self.bands: list[Band] = self.settings.band_objects()
        self.chain = FilterChain()
        self.devices: list[Sink] = []
        self.target: Sink | None = None
        self._poll = QTimer(self)
        self._poll.setInterval(200)
        self._poll.timeout.connect(self.refresh_devices)
        self._apply_timer = QTimer(self)
        self._apply_timer.setSingleShot(True)
        self._apply_timer.setInterval(40)
        self._apply_timer.timeout.connect(self._flush)
        self._live = False

    def start(self) -> None:
        self.refresh_devices()
        if self.settings.autostart:
            set_autostart(True)
        self.engage()
        self._poll.start()

    def shutdown(self, restore: bool = True) -> None:
        self._poll.stop()
        self.persist()
        sink = eqfx_sink()
        if restore and self.settings.restore_default_on_quit and self.settings.previous_default:
            previous = next((d for d in hardware_sinks() if d.name == self.settings.previous_default), None)
            if previous:
                set_default_sink(previous.node_id)
        self.chain.stop()
        self._live = False

    def persist(self) -> None:
        self.settings.set_bands(self.bands)
        if self.target:
            store_device_curve(
                self.settings,
                self.target.name,
                self.settings.preset_id,
                self.bands,
                float(self.settings.output_gain or 0),
            )
        save_settings(self.settings)

    def refresh_devices(self) -> None:
        devices = hardware_sinks()
        snapshot = [(d.node_id, d.name, d.description) for d in devices]
        previous = [(d.node_id, d.name, d.description) for d in self.devices]
        self.devices = devices
        if snapshot != previous:
            self.devices_changed.emit()
        if not self._live:
            return
        wanted = self._resolve_target()
        if wanted and (self.target is None or wanted.name != self.target.name):
            self._switch_target(wanted)
        else:
            self._reclaim_playback()
        if wanted and peek_wanted_output() == wanted.name:
            clear_wanted_output()
        self._apply_wanted_preset()

    def _match(self, name: str) -> Sink | None:
        if not name:
            return None
        return next((d for d in self.devices if d.name == name), None)

    def _resolve_target(self) -> Sink | None:
        if not self.settings.follow_default_output and self.settings.output_device:
            found = self._match(self.settings.output_device)
            if found:
                return found
        requested = self._match(peek_wanted_output())
        if requested:
            return requested
        picked = user_selected_hardware()
        if picked:
            return picked
        playing = self._match(playback_destination())
        if playing:
            return playing
        if self.target and self._match(self.target.name):
            return self._match(self.target.name)
        current = default_hardware()
        if current:
            return current
        if self.settings.previous_default:
            found = self._match(self.settings.previous_default)
            if found:
                return found
        if self.settings.output_device:
            found = self._match(self.settings.output_device)
            if found:
                return found
        return self.devices[0] if self.devices else None

    def _switch_target(self, sink: Sink) -> None:
        if self.target and self.settings.remember_per_device:
            store_device_curve(
                self.settings,
                self.target.name,
                self.settings.preset_id,
                self.bands,
                float(self.settings.output_gain or 0),
            )
        self.target = sink
        self.settings.output_device = sink.name
        if self.settings.remember_per_device:
            preset_id, bands, gain = curve_for_device(self.settings, sink.name)
            self.settings.preset_id = preset_id
            self.bands = bands
            self.settings.output_gain = gain
        self.status.emit(f"Routing through {sink.description}")
        self.changed.emit()
        self._flush()

    def engage(self) -> None:
        target = self._resolve_target()
        if target is None:
            self.status.emit("No playback device found")
            self.changed.emit()
            return
        if self.settings.capture_default:
            current = default_hardware()
            if current:
                self.settings.previous_default = current.name
        if self.settings.remember_per_device:
            preset_id, bands, gain = curve_for_device(self.settings, target.name)
            self.settings.preset_id = preset_id
            self.bands = bands
            self.settings.output_gain = gain
        self.target = target
        self._live = True
        self._flush()
        eq = eqfx_sink()
        if eq and self.settings.capture_default:
            set_default_sink(eq.node_id)
            self.status.emit(f"eqFX is the default output → {target.description}")
        elif eq:
            self.status.emit("eqFX ready. Point apps at eqFX, or enable capture in Settings.")
        else:
            self.status.emit("Could not start the eqFX PipeWire graph")
        self.changed.emit()

    def set_output_device(self, name: str, follow_default: bool) -> None:
        self.settings.follow_default_output = follow_default
        self.settings.output_device = "" if follow_default else name
        wanted = self._resolve_target()
        if wanted:
            self._switch_target(wanted)
        self.persist()

    def _apply_wanted_preset(self) -> None:
        requested = peek_wanted_preset()
        if not requested:
            return
        if any(preset.id == requested for preset in PRESETS):
            self.load_preset(requested)
        clear_wanted_preset()

    def load_preset(self, preset_id: str) -> None:
        preset = find_preset(preset_id)
        self.settings.preset_id = preset.id
        self.bands = apply_patches(preset.patches)
        self.settings.output_gain = preset.output_gain
        self.changed.emit()
        self.status.emit(f"Preset · {preset.name}")
        self.schedule_apply()
        self.persist()

    def set_bypass(self, on: bool) -> None:
        self.settings.bypass = on
        self.changed.emit()
        self.schedule_apply()

    def set_band(self, index: int, **fields) -> None:
        band = self.bands[index]
        for key, value in fields.items():
            setattr(band, key, value)
        if "gain" in fields and abs(float(fields["gain"])) > 0.05:
            band.enabled = True
        self.settings.preset_id = self.settings.preset_id
        self.changed.emit()
        self.schedule_apply()

    def reset_bands(self) -> None:
        self.load_preset("flat")

    def schedule_apply(self) -> None:
        self._apply_timer.start()

    def _reclaim_playback(self) -> None:
        if not self.settings.capture_default:
            return
        eq = eqfx_sink()
        if eq is None:
            return
        if not eq.default:
            set_default_sink(eq.node_id)
            move_app_streams_to_eqfx()

    def _flush(self) -> None:
        if not self._live:
            return
        target_name = self.target.name if self.target else ""
        self.chain.apply(
            self.bands, target_name, self.settings.bypass, float(self.settings.output_gain or 0)
        )
        self._reclaim_playback()
        self.persist()
