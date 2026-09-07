from __future__ import annotations

from pathlib import Path

AUTOSTART_PATH = Path.home() / ".config" / "autostart" / "eqfx.desktop"
LEGACY_AUTOSTART_PATH = Path.home() / ".config" / "autostart" / "minieq.desktop"


def launcher_path() -> Path:
    return Path(__file__).resolve().parents[3] / "packaging" / "eqfx"


def desktop_body(exec_path: str, hidden: bool = False) -> str:
    return f"""[Desktop Entry]
Type=Application
Version=1.0
Name=eqFX
Comment=System-wide 10-band equalizer
Exec={exec_path} --tray
Path={Path(exec_path).resolve().parent.parent}
Icon=eqfx
Terminal=false
Categories=AudioVideo;Audio;
StartupNotify=false
StartupWMClass=eqfx
X-GNOME-Autostart-enabled={"false" if hidden else "true"}
X-GNOME-Autostart-Delay=2
Hidden={"true" if hidden else "false"}
"""


def autostart_enabled() -> bool:
    if not AUTOSTART_PATH.is_file():
        return False
    text = AUTOSTART_PATH.read_text(encoding="utf-8")
    return "Hidden=true" not in text and "X-GNOME-Autostart-enabled=false" not in text


def _remove_legacy_autostart() -> None:
    if LEGACY_AUTOSTART_PATH.is_file():
        LEGACY_AUTOSTART_PATH.unlink()


def set_autostart(enabled: bool) -> None:
    AUTOSTART_PATH.parent.mkdir(parents=True, exist_ok=True)
    exec_path = str(launcher_path())
    _remove_legacy_autostart()
    if enabled:
        AUTOSTART_PATH.write_text(desktop_body(exec_path, hidden=False), encoding="utf-8")
        AUTOSTART_PATH.chmod(0o644)
        return
    if AUTOSTART_PATH.is_file():
        AUTOSTART_PATH.unlink()
