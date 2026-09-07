from __future__ import annotations

import json
from dataclasses import dataclass, replace
from importlib import resources
from pathlib import Path

from eqfx.core import data as data_pkg

LABELS = {
    "highpass": "HP",
    "lowshelf": "LS",
    "peaking": "Peak",
    "notch": "Notch",
    "highshelf": "HS",
    "lowpass": "LP",
}

PW_LABEL = {
    "highpass": "bq_highpass",
    "lowshelf": "bq_lowshelf",
    "peaking": "bq_peaking",
    "notch": "bq_notch",
    "highshelf": "bq_highshelf",
    "lowpass": "bq_lowpass",
}

CATEGORIES = [
    "All",
    "Music",
    "Communication",
    "Games",
    "Hybrid",
]


@dataclass
class Band:
    type: str
    frequency: float
    gain: float
    q: float
    enabled: bool = True


@dataclass
class Preset:
    id: str
    name: str
    category: str
    description: str
    patches: dict
    output_gain: float = 0.0


def default_bands() -> list[Band]:
    return [
        Band("highpass", 20, 0, 0.71, False),
        Band("lowshelf", 80, 0, 0.85, False),
        Band("peaking", 160, 0, 1.1, False),
        Band("peaking", 350, 0, 1.05, False),
        Band("peaking", 700, 0, 1.0, False),
        Band("peaking", 1500, 0, 1.0, False),
        Band("peaking", 3000, 0, 1.1, False),
        Band("peaking", 5500, 0, 1.15, False),
        Band("highshelf", 10000, 0, 0.85, False),
        Band("lowpass", 20000, 0, 0.71, False),
    ]


def apply_patches(patches: dict | None) -> list[Band]:
    bands = default_bands()
    if not patches:
        return bands
    for key, patch in patches.items():
        i = int(key)
        if i < 0 or i >= len(bands):
            continue
        current = bands[i]
        enabled = patch.get("enabled")
        bands[i] = replace(
            current,
            type=str(patch.get("type") or current.type),
            frequency=float(patch.get("frequency", current.frequency)),
            gain=float(patch.get("gain", current.gain)),
            q=float(patch.get("q", current.q)),
            enabled=current.enabled if enabled is None else bool(enabled),
        )
        if enabled is None and patch:
            bands[i].enabled = True
    return bands


def load_factory() -> list[Preset]:
    try:
        ref = resources.files(data_pkg).joinpath("presets.json")
        raw = json.loads(ref.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        fallback = Path(__file__).resolve().parent.parent / "data" / "presets.json"
        raw = json.loads(fallback.read_text(encoding="utf-8"))
    presets = []
    for item in raw:
        presets.append(
            Preset(
                id=item["id"],
                name=item["name"],
                category=item["category"],
                description=item["description"],
                patches=item.get("patches") or {},
                output_gain=float(item.get("output_gain") or 0),
            )
        )
    return presets


PRESETS = load_factory()


def find_preset(preset_id: str) -> Preset:
    for preset in PRESETS:
        if preset.id == preset_id:
            return preset
    return PRESETS[0]


def format_freq(value: float) -> str:
    if value >= 10000:
        return f"{value / 1000:.1f} kHz"
    if value >= 1000:
        return f"{value / 1000:.2f} kHz"
    if value >= 100:
        return f"{value:.0f} Hz"
    return f"{value:.1f} Hz"


def format_db(value: float) -> str:
    if abs(value) < 0.05:
        value = 0.0
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f} dB"
