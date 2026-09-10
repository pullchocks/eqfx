from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal

from eqfx.core.autostart import set_autostart
from eqfx.core.monitor import SpectrumMonitor
from eqfx.core.pipewire import (
    FilterChain,
    Sink,
    card_key,
    default_hardware,
    hardware_sinks,
    invalidate_sink_cache,
    eqfx_sink,
    get_sink_mute,
    get_sink_volume,
    move_app_streams_to_eqfx,
    move_eqfx_playback,
    playback_destination,
    select_sink,
    set_default_sink,
    set_sink_mute,
    set_sink_volume,
    user_selected_hardware,
)
from eqfx.core.presets import (
    PRESETS,
    Band,
    apply_patches,
    delete_user_preset,
    find_preset,
    load_user_presets,
    save_user_preset,
)
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
    store_device_volume,
    volume_for_device,
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
        self._poll.setInterval(1500)
        self._poll.timeout.connect(self.refresh_devices)
        self._last_reclaim = 0.0
        self._apply_timer = QTimer(self)
        self._apply_timer.setSingleShot(True)
        self._apply_timer.setInterval(40)
        self._apply_timer.timeout.connect(self._flush)
        self._live = False
        self.monitor = SpectrumMonitor()
        self.monitor_enabled = True

    def start(self) -> None:
        self.refresh_devices()
        if self.settings.autostart:
            set_autostart(True)
        self.engage()
        self._poll.start()

    def shutdown(self, restore: bool = True) -> None:
        self._poll.stop()
        if self.target:
            self._capture_device_volume(self.target.name)
        self.monitor.stop()
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
            self._capture_device_volume(self.target.name)
        save_settings(self.settings)

    def refresh_devices(self) -> None:
        invalidate_sink_cache()
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
            if self.target:
                self._capture_device_volume(self.target.name)
            self._reclaim_playback()
        if wanted:
            requested = peek_wanted_output()
            if requested == wanted.name or (requested and card_key(requested) == card_key(wanted.name)):
                clear_wanted_output()
        self._apply_wanted_preset()

    def _match(self, name: str) -> Sink | None:
        return select_sink(self.devices, name)

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
        fallback_volume: int | None = None
        if self.target and self.target.name != sink.name:
            fallback_volume = get_sink_volume(self.target.name)
            self._capture_device_volume(self.target.name)
        if self.target and self.settings.remember_per_device:
            store_device_curve(
                self.settings,
                self.target.name,
                self.settings.preset_id,
                self.bands,
                float(self.settings.output_gain or 0),
            )
        # Restore the destination volume before audio is moved onto it.
        self._restore_device_volume(sink.name, fallback_volume=fallback_volume)
        self.target = sink
        self.settings.output_device = sink.name
        if self.settings.remember_per_device:
            preset_id, bands, gain = curve_for_device(self.settings, sink.name)
            self.settings.preset_id = preset_id
            self.bands = bands
            self.settings.output_gain = gain
        self.status.emit(f"Routing through {sink.description}")
        self._sync_monitor()
        self.changed.emit()
        self._flush()

    def engage(self) -> None:
        target = self._resolve_target()
        if target is None:
            self.monitor.stop()
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
        self._restore_device_volume(target.name)
        self.target = target
        self._live = True
        self._flush()
        self._sync_monitor()
        eq = eqfx_sink()
        if eq and self.settings.capture_default:
            set_default_sink(eq.node_id)
            self.status.emit(f"eqFX is the default output → {target.description}")
        elif eq:
            self.status.emit("eqFX ready. Point apps at eqFX, or enable capture in Settings.")
        else:
            self.status.emit("Could not start the eqFX PipeWire graph")
        if self.monitor_enabled and not self.monitor.available:
            self.status.emit(self.monitor.error or "Live monitor needs parec")
        self.changed.emit()

    def _capture_device_volume(self, name: str) -> None:
        if not self.settings.remember_device_volume or not name:
            return
        volume = get_sink_volume(name)
        if volume is None:
            return
        store_device_volume(name, volume, get_sink_mute(name))

    def _restore_device_volume(self, name: str, fallback_volume: int | None = None) -> None:
        if not self.settings.remember_device_volume or not name:
            return
        volume, mute = volume_for_device(name)
        if volume is not None:
            set_sink_volume(name, volume)
        elif fallback_volume is not None:
            # First visit to this sink: start from the level we just left, not a stale blast.
            set_sink_volume(name, fallback_volume)
            store_device_volume(name, fallback_volume)
        if mute is not None:
            set_sink_mute(name, mute)

    def set_monitor_enabled(self, on: bool) -> None:
        self.monitor_enabled = bool(on)
        self._sync_monitor()
        self.changed.emit()

    def _sync_monitor(self) -> None:
        if not self.monitor_enabled or not self._live or self.target is None:
            self.monitor.stop()
            return
        # Hardware sink monitor hears post-EQ audio after eqfx.playback.
        source = f"{self.target.name}.monitor"
        self.monitor.start(source)

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
        known = {preset.id for preset in PRESETS} | {preset.id for preset in load_user_presets()}
        if requested in known:
            self.load_preset(requested)
        clear_wanted_preset()

    def load_preset(self, preset_id: str) -> None:
        preset = find_preset(preset_id)
        self.settings.preset_id = preset.id
        self.bands = apply_patches(preset.patches)
        self.settings.output_gain = preset.output_gain
        self.changed.emit()
        label = "Saved" if preset.is_user else "Preset"
        self.status.emit(f"{label} · {preset.name}")
        self.schedule_apply()
        self.persist()

    def save_current_as(self, name: str, replace_id: str | None = None):
        preset = save_user_preset(
            name,
            self.bands,
            float(self.settings.output_gain or 0),
            replace_id=replace_id,
        )
        self.settings.preset_id = preset.id
        self.persist()
        self.status.emit(f"Saved · {preset.name}")
        self.changed.emit()
        return preset

    def delete_saved(self, preset_id: str) -> bool:
        ok = delete_user_preset(preset_id)
        if ok and self.settings.preset_id == preset_id:
            self.settings.preset_id = "flat"
            self.persist()
        if ok:
            self.status.emit("Deleted saved curve")
            self.changed.emit()
        return ok

    def reset_band(self, index: int) -> None:
        from eqfx.core.presets import default_bands

        if index < 0 or index >= len(self.bands):
            return
        blank = default_bands()[index]
        self.bands[index] = blank
        self.changed.emit()
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
        if eq.default:
            if self.target:
                dest = playback_destination()
                if dest != self.target.name:
                    move_eqfx_playback(self.target.name)
            return
        now = time.monotonic()
        if now - self._last_reclaim < 2.0:
            return
        self._last_reclaim = now
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
