# eqFX

System-wide 10-band parametric EQ for PipeWire. Games, browsers, and music players all go through the same curve.

eqFX is playback only. It does not touch your microphone.

It is a Linux app. It is not tied to Pop!_OS. Any distro with PipeWire (Ubuntu, Fedora, Arch, Debian, Omarchy, and the rest) should work. It will not run on Windows, macOS, or a PulseAudio-only machine.

## Requirements

Install these on the host first. `setup.py` installs PySide6 into `.venv`; it does **not** install Python for you.

- Linux with PipeWire (not PulseAudio-only)
- **Python 3.10+** (`python3 --version`), from your distro packages
- `wpctl` (WirePlumber) and `pactl` (PipeWire-pulse)
- [PySide6](https://pypi.org/project/PySide6/) 6.5+ (pulled into `.venv` by setup)

## Install

From the project root:

```bash
python3 setup.py
```

That is the first-run installer (not setuptools; package metadata is in `pyproject.toml`). It:

- checks for Python 3.10+, PipeWire, `wpctl`, and `pactl`
- installs PySide6 into `.venv`
- writes the app-menu launcher and icon for **this checkout**
- enables login autostart (tray)

Then open **eqFX** from the app menu. After login it starts hidden in the tray. Look for the tray icon (Hyprland/Omarchy: top bar), or launch again to raise the window. Closing the window keeps the EQ running; quit from the tray to remove it from the PipeWire graph.

Skip autostart if you only want the menu entry:

```bash
python3 setup.py --no-autostart
```

## Run

```bash
python3 run.py
```

Stay in the tray (EQ keeps running with no window):

```bash
python3 run.py --tray
```

If PySide6 is not in `.venv`, eqFX also looks at `../popstream/.venv`.

## What it does

eqFX starts a PipeWire filter-chain sink named **eqFX**. With **Make eqFX the default playback device** on (the default):

```
apps  →  eqFX  →  Wave 3 / speakers / HDMI / …
```

Band gain, frequency, and Q update live. Changing a filter type rebuilds the graph.

### Microphone

Leave Discord, Steam, and system **input** on the real mic (for example the Elgato Wave 3). Do not set the microphone to eqFX.

### Output switchers

Stream Deck keys, `pactl set-default-sink`, and the system sound picker still choose the **hardware**. eqFX stays the default for apps and follows whichever speaker or headset you last selected.

Keep **Follow output-switcher buttons** on for that. Pin a device in the Output menu only if you want eqFX glued to one sink.

The Output menu shows `Follow ·` plus the active device. Pulse/PipeWire will still report **eqFX** as the default sink; that is intentional.

## Presets

67 factory curves in four banks, plus **All**:

| Bank | Count | For |
| --- | ---: | --- |
| **Music** | 20 | listening (Harman, bass, night loudness, genre) |
| **Communication** | 14 | Discord, in-game VOIP, raid calls, quiet talkers |
| **Games** | 20 | FPS footsteps, Valorant/CS, CoD/Apex, BR, sims |
| **Hybrid** | 13 | game + team voice, music + Discord, stream monitor |

**Game + Team Voice** or **FPS Competitive** if you want footsteps and squad chat at the same time. Each output device can remember its own curve.

## Settings

**Session**

- **Start eqFX when I log in**: `~/.config/autostart/eqfx.desktop`
- **Start in the background**: tray only
- **Close window to tray**: the EQ keeps running after you close the window

**Devices**

- Follow output-switcher buttons, or pin Wave 3 / Leviathan / HDMI / …
- Make eqFX the default playback device
- Restore the previous default when eqFX quits
- Remember a separate EQ for each output device

## PopStream

PopStream Audio actions know about eqFX:

- **Set Output** still targets the Wave 3 or speakers, not the virtual sink
- **EQ Preset** loads a factory curve on the current output

eqFX watches drop files under `~/.local/share/eqfx/`:

| File | Contents |
| --- | --- |
| `wanted-output` | PipeWire sink name to route to |
| `wanted-preset` | factory preset id |

## Shortcuts

| Key | Action |
| --- | --- |
| B | Bypass |

## Files

| Path | Role |
| --- | --- |
| `~/.local/share/eqfx/settings.json` | session, devices, per-output curves |
| `~/.cache/eqfx/filter-chain.conf` | live PipeWire graph |
| `packaging/eqfx` | GUI launcher |
