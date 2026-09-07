#!/usr/bin/env python3
"""First-run installer for eqFX.

This is not a setuptools script. From the project root:

    python3 setup.py

Installs PySide6 into .venv, writes the app-menu launcher, login autostart
entry, and icon for this checkout.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
LAUNCHER = ROOT / "packaging" / "eqfx"
ICON = Path.home() / ".local/share/icons/hicolor/128x128/apps/eqfx.png"
APP_DESKTOP = Path.home() / ".local/share/applications/eqfx.desktop"
AUTOSTART_DESKTOP = Path.home() / ".config/autostart/eqfx.desktop"
SETTINGS = Path.home() / ".local/share/eqfx/settings.json"
NEEDED = ("pipewire", "wpctl", "pactl")


def _run(command: list[str], **kwargs) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, **kwargs)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"wrote {path}")


def _fill_desktop(name: str, icon: Path) -> str:
    template = (ROOT / "packaging" / name).read_text(encoding="utf-8")
    return template.replace("@ROOT@", str(ROOT)).replace("@ICON@", str(icon))


def _have_module(python: str, name: str) -> bool:
    return (
        subprocess.run(
            [python, "-c", f"import {name}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def _pyside_roots() -> list[Path]:
    return [VENV, ROOT.parent / "popstream" / ".venv"]


def _put_pyside_on_sys_path() -> None:
    for extra in _pyside_roots():
        if not extra.is_dir():
            continue
        sys.path.insert(0, str(extra))
        for pattern in ("lib/python*/site-packages", "lib64/python*/site-packages"):
            for site in extra.glob(pattern):
                sys.path.insert(0, str(site))


def _pyside_ready() -> bool:
    _put_pyside_on_sys_path()
    try:
        import PySide6  # noqa: F401

        return True
    except ImportError:
        return False


def _clear_broken_venv() -> None:
    python = VENV / "bin" / "python"
    if not python.is_file():
        return
    if _have_module(str(python), "pip") or (VENV / "PySide6").is_dir():
        return
    print(f"removing incomplete {VENV}")
    shutil.rmtree(VENV)


def _bootstrap_pip_target() -> None:
    import urllib.request

    VENV.mkdir(parents=True, exist_ok=True)
    get_pip = VENV / "get-pip.py"
    print("+ downloading get-pip.py")
    urllib.request.urlretrieve("https://bootstrap.pypa.io/get-pip.py", get_pip)
    _run([sys.executable, str(get_pip), "--target", str(VENV)])
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(VENV) if not existing else str(VENV) + os.pathsep + existing
    _run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--target",
            str(VENV),
            "-r",
            str(ROOT / "requirements.txt"),
        ],
        env=env,
    )


def check_system() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("eqFX needs Python 3.10+.")
    missing = [name for name in NEEDED if shutil.which(name) is None]
    if missing:
        raise SystemExit(
            "eqFX needs PipeWire on PATH: "
            + ", ".join(missing)
            + ".\nInstall PipeWire / WirePlumber (for wpctl) and the Pulse compat tools (for pactl)."
        )


def install_deps() -> None:
    _clear_broken_venv()
    if _pyside_ready():
        print("PySide6 already available")
        return
    requirements = str(ROOT / "requirements.txt")
    venv_python = VENV / "bin" / "python"
    if venv_python.is_file() and _have_module(str(venv_python), "pip"):
        _run([str(venv_python), "-m", "pip", "install", "-r", requirements])
        return
    try:
        _run([sys.executable, "-m", "venv", str(VENV)])
        _run([str(venv_python), "-m", "pip", "install", "-U", "pip"])
        _run([str(venv_python), "-m", "pip", "install", "-r", requirements])
        return
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("python3 -m venv failed; installing PySide6 with pip --target .venv")
        _clear_broken_venv()
    try:
        _bootstrap_pip_target()
    except Exception as exc:
        raise SystemExit(
            "Need pip or python3-venv so eqFX can install PySide6.\n"
            f"({exc})\n"
            "Install python3-venv / python3-pip, then run python3 setup.py again."
        ) from exc


def write_icon() -> Path:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _put_pyside_on_sys_path()
    sys.path.insert(0, str(ROOT / "src"))
    from PySide6.QtGui import QGuiApplication

    from eqfx.ui.icons import icon_pixmap

    _app = QGuiApplication.instance() or QGuiApplication(["eqfx-setup"])
    ICON.parent.mkdir(parents=True, exist_ok=True)
    pixmap = icon_pixmap(128)
    if not pixmap.save(str(ICON), "PNG"):
        raise SystemExit(f"could not write {ICON}")
    pixmap.save(str(ROOT / "packaging" / "eqfx.png"), "PNG")
    pixmaps = Path.home() / ".local/share/pixmaps/eqfx.png"
    pixmaps.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(str(pixmaps), "PNG")
    for size in (16, 22, 24, 32, 48, 64, 256):
        dest = Path.home() / f".local/share/icons/hicolor/{size}x{size}/apps/eqfx.png"
        dest.parent.mkdir(parents=True, exist_ok=True)
        icon_pixmap(size).save(str(dest), "PNG")
    print(f"wrote {ICON}")
    return ICON


def write_desktop_files(icon: Path, autostart: bool) -> None:
    LAUNCHER.chmod(LAUNCHER.stat().st_mode | 0o111)
    _write(APP_DESKTOP, _fill_desktop("eqfx.desktop", icon))
    if autostart:
        _write(AUTOSTART_DESKTOP, _fill_desktop("eqfx-autostart.desktop", icon))
    elif AUTOSTART_DESKTOP.is_file():
        AUTOSTART_DESKTOP.unlink()
        print(f"removed {AUTOSTART_DESKTOP}")
    update = shutil.which("update-desktop-database")
    if update:
        subprocess.run([update, str(APP_DESKTOP.parent)], check=False)
    cache = shutil.which("gtk-update-icon-cache")
    if cache:
        subprocess.run(
            [cache, "-f", str(Path.home() / ".local/share/icons/hicolor")],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def enable_session_defaults(autostart: bool) -> None:
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    raw: dict = {}
    if SETTINGS.is_file():
        try:
            loaded = json.loads(SETTINGS.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                raw = loaded
        except (OSError, json.JSONDecodeError):
            raw = {}
    raw["autostart"] = autostart
    if autostart:
        raw["start_in_tray"] = True
        raw["close_to_tray"] = True
        raw["capture_default"] = True
        raw["follow_default_output"] = True
    SETTINGS.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {SETTINGS}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    leftover = {
        "build",
        "egg_info",
        "sdist",
        "bdist_wheel",
        "develop",
        "editable_wheel",
    }
    if argv and argv[0] in leftover:
        print(
            "setup.py is the eqFX first-run installer, not setuptools.\n"
            "Run: python3 setup.py\n"
            "The package metadata lives in pyproject.toml.",
            file=sys.stderr,
        )
        return 2

    parser = argparse.ArgumentParser(description="Install eqFX on this Linux machine.")
    parser.add_argument("--no-autostart", action="store_true", help="Skip the login autostart entry.")
    args = parser.parse_args(argv)

    if os.geteuid() == 0:
        print("Do not run setup.py as root.", file=sys.stderr)
        return 1

    print(f"Installing eqFX from {ROOT}")
    check_system()
    install_deps()
    icon = write_icon()
    autostart = not args.no_autostart
    write_desktop_files(icon, autostart=autostart)
    enable_session_defaults(autostart=autostart)

    print()
    print("Done. Open eqFX from the app menu, or:")
    print("  python3 run.py")
    if autostart:
        print("After login it starts in the tray. Quit from the tray to remove the EQ.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
