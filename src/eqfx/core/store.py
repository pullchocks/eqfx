from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from eqfx.core.presets import Band, apply_patches, default_bands, find_preset


def data_dir() -> Path:
    path = Path.home() / ".local" / "share" / "eqfx"
    legacy = Path.home() / ".local" / "share" / "MiniEQ"
    if not path.exists() and legacy.is_dir():
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            legacy.rename(path)
        except OSError:
            path.mkdir(parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)
    return path


def settings_path() -> Path:
    return data_dir() / "settings.json"


def runtime_dir() -> Path:
    path = Path.home() / ".cache" / "eqfx"
    legacy = Path.home() / ".cache" / "minieq"
    if not path.exists() and legacy.is_dir():
        try:
            legacy.rename(path)
        except OSError:
            path.mkdir(parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)
    return path


def filter_conf_path() -> Path:
    return runtime_dir() / "filter-chain.conf"


def wanted_output_path() -> Path:
    """Stream Deck / other switchers drop the hardware sink name here."""
    return data_dir() / "wanted-output"


def peek_wanted_output() -> str:
    path = wanted_output_path()
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def write_wanted_output(name: str) -> None:
    path = wanted_output_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(name.strip(), encoding="utf-8")


def clear_wanted_output() -> None:
    path = wanted_output_path()
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def wanted_preset_path() -> Path:
    """Stream Deck EQ keys drop a factory preset id here."""
    return data_dir() / "wanted-preset"


def peek_wanted_preset() -> str:
    path = wanted_preset_path()
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def write_wanted_preset(preset_id: str) -> None:
    path = wanted_preset_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(preset_id.strip(), encoding="utf-8")


def clear_wanted_preset() -> None:
    path = wanted_preset_path()
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


@dataclass
class Settings:
    autostart: bool = False
    start_in_tray: bool = False
    close_to_tray: bool = True
    capture_default: bool = True
    restore_default_on_quit: bool = True
    follow_default_output: bool = True
    output_device: str = ""
    remember_per_device: bool = True
    preset_id: str = "flat"
    bypass: bool = False
    output_gain: float = 0.0
    bands: list[dict] = field(default_factory=list)
    device_curves: dict[str, dict] = field(default_factory=dict)
    previous_default: str = ""

    def band_objects(self) -> list[Band]:
        if not self.bands:
            return default_bands()
        out = default_bands()
        for i, raw in enumerate(self.bands[:10]):
            out[i] = Band(
                type=str(raw.get("type") or out[i].type),
                frequency=float(raw.get("frequency") or out[i].frequency),
                gain=float(raw.get("gain") or 0.0) if "gain" in raw else out[i].gain,
                q=float(raw.get("q") or out[i].q),
                enabled=bool(raw.get("enabled", out[i].enabled)),
            )
        return out

    def set_bands(self, bands: list[Band]) -> None:
        self.bands = [asdict(b) for b in bands]


def load_settings() -> Settings:
    path = settings_path()
    if not path.is_file():
        return Settings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()
    known = Settings()
    for key in known.__dataclass_fields__:
        if key in raw:
            setattr(known, key, raw[key])
    return known


def save_settings(settings: Settings) -> None:
    payload = asdict(settings)
    settings_path().write_text(json.dumps(payload, indent=2), encoding="utf-8")


def curve_for_device(settings: Settings, device_name: str) -> tuple[str, list[Band], float]:
    if settings.remember_per_device and device_name and device_name in settings.device_curves:
        stored = settings.device_curves[device_name]
        preset_id = str(stored.get("preset_id") or "flat")
        bands_raw = stored.get("bands") or []
        tmp = Settings(bands=bands_raw, preset_id=preset_id)
        if "output_gain" in stored:
            gain = float(stored.get("output_gain") or 0)
        else:
            gain = find_preset(preset_id).output_gain
        return preset_id, tmp.band_objects(), gain
    preset = find_preset(settings.preset_id)
    return preset.id, apply_patches(preset.patches), float(preset.output_gain)


def store_device_curve(
    settings: Settings, device_name: str, preset_id: str, bands: list[Band], output_gain: float = 0.0
) -> None:
    if not device_name:
        return
    settings.device_curves[device_name] = {
        "preset_id": preset_id,
        "bands": [asdict(b) for b in bands],
        "output_gain": float(output_gain),
    }
