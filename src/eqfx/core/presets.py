from __future__ import annotations

import json
import re
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

USER_CATEGORY = "Saved"


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

    @property
    def is_user(self) -> bool:
        return self.id.startswith("user:") or self.category == USER_CATEGORY


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


def bands_to_patches(bands: list[Band]) -> dict:
    """Full band snapshot for user saves."""
    return {
        str(i): {
            "type": band.type,
            "frequency": float(band.frequency),
            "gain": float(band.gain),
            "q": float(band.q),
            "enabled": bool(band.enabled),
        }
        for i, band in enumerate(bands)
    }


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
_USER_CACHE: list[Preset] | None = None


def user_presets_path() -> Path:
    from eqfx.core.store import data_dir

    return data_dir() / "user_presets.json"


def load_user_presets(force: bool = False) -> list[Preset]:
    global _USER_CACHE
    if _USER_CACHE is not None and not force:
        return list(_USER_CACHE)
    path = user_presets_path()
    presets: list[Preset] = []
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = []
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict) or not item.get("id") or not item.get("name"):
                    continue
                pid = str(item["id"])
                if not pid.startswith("user:"):
                    pid = f"user:{pid}"
                presets.append(
                    Preset(
                        id=pid,
                        name=str(item["name"]),
                        category=USER_CATEGORY,
                        description=str(item.get("description") or "Custom save"),
                        patches=item.get("patches") or {},
                        output_gain=float(item.get("output_gain") or 0),
                    )
                )
    presets.sort(key=lambda p: p.name.lower())
    _USER_CACHE = presets
    return list(presets)


def _write_user_presets(presets: list[Preset]) -> None:
    global _USER_CACHE
    path = user_presets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "id": preset.id,
            "name": preset.name,
            "description": preset.description,
            "patches": preset.patches,
            "output_gain": preset.output_gain,
        }
        for preset in presets
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _USER_CACHE = list(presets)


def slugify_user_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return f"user:{slug or 'save'}"


def unique_user_id(name: str, existing: list[Preset], keep_id: str | None = None) -> str:
    base = slugify_user_id(name)
    if keep_id and keep_id.startswith("user:"):
        return keep_id
    taken = {p.id for p in existing}
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def save_user_preset(
    name: str,
    bands: list[Band],
    output_gain: float = 0.0,
    description: str = "",
    replace_id: str | None = None,
) -> Preset:
    name = name.strip() or "Untitled"
    current = load_user_presets(force=True)
    preset_id = None
    if replace_id:
        for preset in current:
            if preset.id == replace_id:
                preset_id = replace_id
                break
    if preset_id is None:
        for preset in current:
            if preset.name.lower() == name.lower():
                preset_id = preset.id
                break
    if preset_id is None:
        preset_id = unique_user_id(name, current)
    saved = Preset(
        id=preset_id,
        name=name,
        category=USER_CATEGORY,
        description=(description or "Custom save").strip() or "Custom save",
        patches=bands_to_patches(bands),
        output_gain=float(output_gain),
    )
    next_list = [p for p in current if p.id != preset_id]
    next_list.append(saved)
    next_list.sort(key=lambda p: p.name.lower())
    _write_user_presets(next_list)
    return saved


def delete_user_preset(preset_id: str) -> bool:
    current = load_user_presets(force=True)
    next_list = [p for p in current if p.id != preset_id]
    if len(next_list) == len(current):
        return False
    _write_user_presets(next_list)
    return True


def rename_user_preset(preset_id: str, name: str) -> Preset | None:
    name = name.strip()
    if not name:
        return None
    current = load_user_presets(force=True)
    for i, preset in enumerate(current):
        if preset.id != preset_id:
            continue
        updated = Preset(
            id=preset.id,
            name=name,
            category=USER_CATEGORY,
            description=preset.description,
            patches=preset.patches,
            output_gain=preset.output_gain,
        )
        current[i] = updated
        current.sort(key=lambda p: p.name.lower())
        _write_user_presets(current)
        return updated
    return None


def find_preset(preset_id: str) -> Preset:
    for preset in load_user_presets():
        if preset.id == preset_id:
            return preset
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
