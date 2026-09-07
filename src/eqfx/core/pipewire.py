from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import subprocess
import time

from eqfx.core.presets import Band, PW_LABEL
from eqfx.core.store import filter_conf_path

SINK_NAME = "eqfx.sink"
PLAYBACK_NAME = "eqfx.playback"
SINK_DESC = "eqFX"
LEGACY_SINK_NAMES = {"minieq.sink", SINK_NAME}
PLAYBACK_NAMES = {PLAYBACK_NAME, "minieq.playback"}

ITEM_RE = re.compile(
    r"^(?P<star>\*)?\s*(?P<id>\d+)\.\s+(?P<name>.+?)(?:\s+\[(?P<tag>[^\]]*)\])?\s*$"
)
ENDPOINT_TAIL = re.compile(
    r"\.(?:analog-[^.]+|pro-(?:output|input)-\d+|hdmi-stereo(?:-\d+)?|iec958-stereo)$"
)


def card_key(name: str) -> str:
    return ENDPOINT_TAIL.sub("", name) if name else ""


@dataclass
class Sink:
    node_id: int
    name: str
    description: str
    default: bool = False
    volume: float | None = None

    @property
    def is_eqfx(self) -> bool:
        return (
            self.name.startswith("eqfx.")
            or self.name.startswith("minieq.")
            or self.description in {SINK_DESC, "MiniEQ"}
        )


_SINK_CACHE_TTL = 0.8
_sink_cache: tuple[float, list[Sink]] | None = None


def run(argv: list[str], timeout: float = 2.0) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124, "", "timed out")
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 1, "", str(exc))


def invalidate_sink_cache() -> None:
    global _sink_cache
    _sink_cache = None


def _parse_section(text: str, want: str) -> list[tuple[int, str, bool, str]]:
    rows: list[tuple[int, str, bool, str]] = []
    section = ""
    subsection = ""
    for raw in text.splitlines():
        line = raw.replace("│", " ").replace("├", " ").replace("└", " ").replace("─", " ")
        stripped = line.strip()
        if stripped in {"Audio", "Video", "Settings"}:
            section = stripped
            subsection = ""
            continue
        header = re.match(
            r"^(Devices|Sinks|Sources|Filters|Streams|Default Configured Devices)\s*:?\s*$",
            stripped,
        )
        if header:
            subsection = header.group(1)
            continue
        if section != "Audio" or subsection != want:
            continue
        match = ITEM_RE.match(stripped)
        if not match:
            continue
        tag = match.group("tag") or ""
        rows.append((int(match.group("id")), match.group("name").strip(), bool(match.group("star")), tag))
    return rows


def list_sinks(*, force: bool = False) -> list[Sink]:
    global _sink_cache
    now = time.monotonic()
    if not force and _sink_cache is not None and now - _sink_cache[0] < _SINK_CACHE_TTL:
        return _sink_cache[1]
    named_text = run(["wpctl", "status", "--name"]).stdout
    pretty_text = run(["wpctl", "status"]).stdout
    named = _parse_section(named_text, "Sinks")
    pretty = _parse_section(pretty_text, "Sinks")
    pretty_map = {item[0]: item[1] for item in pretty}
    default_map = {item[0]: item[2] for item in pretty}
    sinks = []
    for node_id, name, default, _tag in named:
        sinks.append(
            Sink(
                node_id=node_id,
                name=name,
                description=pretty_map.get(node_id, name),
                default=default_map.get(node_id, default),
            )
        )
    # Filter-chain graphs show up under Filters, not Sinks.
    for node_id, name, default, _tag in _parse_section(named_text, "Filters"):
        if name not in LEGACY_SINK_NAMES:
            continue
        if any(s.node_id == node_id for s in sinks):
            continue
        sinks.append(
            Sink(
                node_id=node_id,
                name=name,
                description=SINK_DESC,
                default=default,
            )
        )
    _sink_cache = (now, sinks)
    return sinks


def hardware_sinks() -> list[Sink]:
    return [s for s in list_sinks() if not s.is_eqfx]


def select_sink(sinks: list[Sink], name: str) -> Sink | None:
    """Exact Pulse name, else the Analog node on the same card, else any match."""
    if not name:
        return None
    exact = next((sink for sink in sinks if sink.name == name or sink.description == name), None)
    if exact:
        return exact
    key = card_key(name)
    if not key:
        return None
    same = [sink for sink in sinks if card_key(sink.name) == key]
    analog = [
        sink
        for sink in same
        if ".analog-" in sink.name or "mono-fallback" in sink.name or ".mono-" in sink.name
    ]
    if analog:
        return analog[0]
    return same[0] if same else None


def find_sink(name_or_desc: str) -> Sink | None:
    return select_sink(list_sinks(), name_or_desc)


def eqfx_sink() -> Sink | None:
    matches = [sink for sink in list_sinks() if sink.is_eqfx]
    for sink in matches:
        if sink.name == SINK_NAME:
            return sink
    return matches[0] if matches else None


def default_hardware() -> Sink | None:
    sinks = hardware_sinks()
    for sink in sinks:
        if sink.default:
            return sink
    return None


def set_default_sink(node_id: int) -> None:
    run(["wpctl", "set-default", str(node_id)])
    invalidate_sink_cache()


def user_selected_hardware() -> Sink | None:
    """Hardware sink currently starred while eqFX is still in the graph.

    Stream Deck / system output buttons set a speaker as default. That is the
    signal to retarget playback. Ignore the case where eqFX itself is gone
    (graph restart), which also makes a speaker look like the default.
    """
    eq = eqfx_sink()
    if eq is None or eq.default:
        return None
    return default_hardware()


def eqfx_playback_node() -> int | None:
    for node_id, name, _default, _tag in _parse_section(run(["wpctl", "status", "--name"]).stdout, "Filters"):
        if name in PLAYBACK_NAMES:
            return node_id
    return None


def playback_destination() -> str:
    """Name of the hardware sink eqFX is actually playing into right now."""
    sink_by_index: dict[int, str] = {}
    try:
        proc = run(["pactl", "--format=json", "list", "sinks"], timeout=3.0)
        data = json.loads(proc.stdout or "[]")
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                index = item.get("index")
                name = str(item.get("name") or "")
                if index is not None and name:
                    sink_by_index[int(index)] = name
    except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired, TypeError, ValueError):
        sink_by_index = {}
    dest = ""
    for _index, node_name, sink_index in _sink_input_rows():
        if node_name not in PLAYBACK_NAMES:
            continue
        dest = sink_by_index.get(sink_index, "")
        if dest:
            break
    if dest.startswith("eqfx.") or dest.startswith("minieq.") or dest in LEGACY_SINK_NAMES:
        return ""
    return dest


def move_eqfx_playback(sink_name: str) -> bool:
    """Point the live filter at a hardware sink without tearing the graph down."""
    if not sink_name:
        return False
    moved = False
    for index, node_name, _sink_index in _sink_input_rows():
        if node_name not in PLAYBACK_NAMES:
            continue
        proc = run(["pactl", "move-sink-input", index, sink_name], timeout=2.0)
        if proc.returncode == 0:
            moved = True
    node = eqfx_playback_node()
    if node is not None:
        run(
            ["pw-cli", "set-param", str(node), "Props", f'{{ target.object = "{sink_name}" }}'],
            timeout=2.0,
        )
    return moved


def move_app_streams_to_eqfx() -> None:
    """Keep games and players on eqFX after an output switcher yanks them away."""
    for index, node_name in _sink_inputs():
        if node_name.startswith("eqfx.") or node_name.startswith("minieq."):
            continue
        run(["pactl", "move-sink-input", index, SINK_NAME], timeout=2.0)


def _sink_inputs() -> list[tuple[str, str]]:
    return [(index, name) for index, name, _sink in _sink_input_rows()]


def _sink_input_rows() -> list[tuple[str, str, int]]:
    try:
        proc = run(["pactl", "--format=json", "list", "sink-inputs"], timeout=3.0)
        data = json.loads(proc.stdout or "[]")
        if isinstance(data, list):
            rows: list[tuple[str, str, int]] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                index = item.get("index")
                props = item.get("properties") or {}
                name = str(props.get("node.name") or "")
                if index is None:
                    continue
                try:
                    sink_index = int(item.get("sink") or -1)
                except (TypeError, ValueError):
                    sink_index = -1
                rows.append((str(index), name, sink_index))
            return rows
    except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
        pass
    return _parse_sink_inputs(run(["pactl", "list", "sink-inputs"], timeout=3.0).stdout)


def _parse_sink_inputs(text: str) -> list[tuple[str, str, int]]:
    rows: list[tuple[str, str, int]] = []
    index = ""
    name = ""
    sink_index = -1
    for line in text.splitlines():
        header = re.match(r"^Sink Input #(\d+)\s*$", line)
        if header:
            if index:
                rows.append((index, name, sink_index))
            index = header.group(1)
            name = ""
            sink_index = -1
            continue
        sink = re.match(r"^Sink:\s+(\d+)\s*$", line.strip())
        if sink:
            sink_index = int(sink.group(1))
            continue
        match = re.search(r'node\.name\s*=\s*"([^"]+)"', line)
        if match:
            name = match.group(1)
    if index:
        rows.append((index, name, sink_index))
    return rows


def _spa_value(value: float | str) -> str:
    if isinstance(value, str):
        return json.dumps(value)
    if float(value).is_integer():
        return str(int(value)) if abs(value) < 1e-9 or abs(value - int(value)) < 1e-9 and abs(value) < 1e6 else f"{value:.4f}"
    return f"{value:.4f}"


def write_filter_conf(bands: list[Band], target: str) -> Path:
    nodes = []
    links = []
    for i, band in enumerate(bands, start=1):
        kind = PW_LABEL.get(band.type, "bq_peaking")
        freq, q, gain = _effective(band, bypass=False)
        nodes.append(
            "                    {\n"
            "                        type  = builtin\n"
            f'                        name  = eq_band_{i}\n'
            f"                        label = {kind}\n"
            f'                        control = {{ "Freq" = {freq:.4f} "Q" = {q:.4f} "Gain" = {gain:.4f} }}\n'
            "                    }"
        )
        if i < len(bands):
            links.append(
                f'                    {{ output = "eq_band_{i}:Out" input = "eq_band_{i + 1}:In" }}'
            )
    target_line = f'                target.object = "{target}"\n' if target else ""
    text = f"""context.properties = {{
    log.level = 0
}}
context.spa-libs = {{
    audio.convert.* = audioconvert/libspa-audioconvert
    support.*       = support/libspa-support
}}
context.modules = [
    {{ name = libpipewire-module-rt flags = [ ifexists nofail ] }}
    {{ name = libpipewire-module-protocol-native }}
    {{ name = libpipewire-module-client-node }}
    {{ name = libpipewire-module-adapter }}
    {{ name = libpipewire-module-filter-chain
        args = {{
            node.description = "{SINK_DESC}"
            media.name       = "{SINK_DESC}"
            filter.graph = {{
                nodes = [
{chr(10).join(nodes)}
                ]
                links = [
{chr(10).join(links)}
                ]
            }}
            audio.channels = 2
            audio.position = [ FL FR ]
            capture.props = {{
                node.name   = "{SINK_NAME}"
                node.description = "{SINK_DESC}"
                media.class = Audio/Sink
            }}
            playback.props = {{
                node.name   = "{PLAYBACK_NAME}"
                node.passive = true
{target_line}            }}
        }}
    }}
]
"""
    path = filter_conf_path()
    path.write_text(text, encoding="utf-8")
    return path


def _effective(band: Band, bypass: bool) -> tuple[float, float, float]:
    freq = max(20.0, min(20000.0, band.frequency))
    q = max(0.1, min(18.0, band.q))
    gain = band.gain
    silent = bypass or not band.enabled
    if silent:
        if band.type == "highpass":
            return 20.0, 0.71, 0.0
        if band.type == "lowpass":
            return 20000.0, 0.71, 0.0
        if band.type == "notch":
            return 20.0, 0.1, 0.0
        return freq, q, 0.0
    if band.type in {"highpass", "lowpass", "notch"}:
        return freq, q, 0.0
    return freq, q, gain


def set_band_params(node_id: int, bands: list[Band], bypass: bool, output_gain: float) -> None:
    parts = ['"volume"', f"{pow(10.0, output_gain / 20.0):.5f}"]
    params: list[str] = []
    for i, band in enumerate(bands, start=1):
        freq, q, gain = _effective(band, bypass)
        name = f"eq_band_{i}"
        params.extend(
            [
                f'"{name}:Freq"',
                f"{freq:.4f}",
                f'"{name}:Q"',
                f"{q:.4f}",
                f'"{name}:Gain"',
                f"{gain:.4f}",
            ]
        )
    blob = "{ params = [ " + " ".join(params) + " ] " + " ".join(parts) + " }"
    # volume lives next to params on Props
    blob = "{ volume = " + f"{pow(10.0, output_gain / 20.0):.5f}" + " params = [ " + " ".join(params) + " ] }"
    run(["pw-cli", "set-param", str(node_id), "Props", blob], timeout=4.0)


def _kill_orphan_chains() -> None:
    markers = {str(filter_conf_path()), str(Path.home() / ".cache" / "minieq" / "filter-chain.conf")}
    try:
        proc = run(["pgrep", "-af", "pipewire -c"], timeout=2.0)
    except Exception:
        return
    for line in proc.stdout.splitlines():
        if not any(marker in line for marker in markers):
            continue
        pid = line.split(None, 1)[0]
        if pid.isdigit():
            run(["kill", pid], timeout=2.0)


class FilterChain:
    def __init__(self) -> None:
        self.proc: subprocess.Popen[str] | None = None
        self.target = ""
        self.types: list[str] = []

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, bands: list[Band], target: str) -> None:
        self.stop()
        _kill_orphan_chains()
        path = write_filter_conf(bands, target)
        self.proc = subprocess.Popen(
            ["pipewire", "-c", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.target = target
        self.types = [b.type for b in bands]
        self.wait_ready()

    def wait_ready(self, timeout: float = 4.0) -> Sink | None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            sink = eqfx_sink()
            if sink:
                return sink
            time.sleep(0.08)
        return eqfx_sink()

    def stop(self) -> None:
        if self.proc is None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc = None

    def needs_restart(self, bands: list[Band], target: str) -> bool:
        if not self.running:
            return True
        return [b.type for b in bands] != self.types

    def apply(self, bands: list[Band], target: str, bypass: bool, output_gain: float) -> tuple[Sink | None, bool]:
        restarted = self.needs_restart(bands, target)
        if restarted:
            self.start(bands, target)
        elif target and target != self.target:
            write_filter_conf(bands, target)
            move_eqfx_playback(target)
            self.target = target
        sink = eqfx_sink()
        if sink:
            set_band_params(sink.node_id, bands, bypass, output_gain)
        return sink, restarted
