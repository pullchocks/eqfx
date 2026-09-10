from __future__ import annotations

import math
import shutil
import struct
import subprocess
import threading
import time
from array import array


RATE = 48000
CHANNELS = 2
FFT_N = 1024
BARS = 96
MIN_F = 20.0
MAX_F = 20000.0


def _fft(re: list[float], im: list[float]) -> None:
    """In-place radix-2 Cooley–Tukey FFT."""
    n = len(re)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            re[i], re[j] = re[j], re[i]
            im[i], im[j] = im[j], im[i]
    length = 2
    while length <= n:
        half = length // 2
        ang = -2.0 * math.pi / length
        wlen_re = math.cos(ang)
        wlen_im = math.sin(ang)
        for i in range(0, n, length):
            wr, wi = 1.0, 0.0
            for k in range(half):
                u_re = re[i + k]
                u_im = im[i + k]
                v_re = re[i + k + half] * wr - im[i + k + half] * wi
                v_im = re[i + k + half] * wi + im[i + k + half] * wr
                re[i + k] = u_re + v_re
                im[i + k] = u_im + v_im
                re[i + k + half] = u_re - v_re
                im[i + k + half] = u_im - v_im
                nwr = wr * wlen_re - wi * wlen_im
                wi = wr * wlen_im + wi * wlen_re
                wr = nwr
        length <<= 1


def _hann(n: int) -> list[float]:
    if n <= 1:
        return [1.0]
    return [0.5 - 0.5 * math.cos(2.0 * math.pi * i / (n - 1)) for i in range(n)]


def _bar_edges() -> list[tuple[float, float]]:
    edges = [MIN_F * (MAX_F / MIN_F) ** (i / BARS) for i in range(BARS + 1)]
    return list(zip(edges, edges[1:]))


class SpectrumMonitor:
    """Live post-EQ spectrum via Pulse/PipeWire monitor source (`parec`)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._wanted = ""
        self._active = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._proc: subprocess.Popen[bytes] | None = None
        self._bars = [0.0] * BARS
        self._peaks = [0.0] * BARS
        self._peak_l = 0.0
        self._peak_r = 0.0
        self._available = bool(shutil.which("parec"))
        self._error = "" if self._available else "parec not found (install pulseaudio-utils / pipewire-pulse)"
        self._window = _hann(FFT_N)
        self._edges = _bar_edges()
        self._bin_hz = RATE / FFT_N

    @property
    def available(self) -> bool:
        return self._available

    @property
    def error(self) -> str:
        with self._lock:
            return self._error

    def start(self, source: str) -> None:
        source = (source or "").strip()
        with self._lock:
            self._wanted = source
            self._active = True
            self._error = "" if self._available else self._error
        if not source:
            return
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="eqfx-spectrum", daemon=True)
            self._thread.start()

    def set_source(self, source: str) -> None:
        source = (source or "").strip()
        with self._lock:
            if source == self._wanted:
                return
            self._wanted = source
            self._bars = [0.0] * BARS
            self._peaks = [0.0] * BARS
            self._peak_l = 0.0
            self._peak_r = 0.0
        self._kill_proc()

    def stop(self) -> None:
        with self._lock:
            self._active = False
            self._wanted = ""
            self._bars = [0.0] * BARS
            self._peaks = [0.0] * BARS
            self._peak_l = 0.0
            self._peak_r = 0.0
        self._stop.set()
        self._kill_proc()

    def snapshot(self) -> tuple[list[float], list[float], float, float]:
        with self._lock:
            return list(self._bars), list(self._peaks), self._peak_l, self._peak_r

    def _kill_proc(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=0.4)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                if not self._active:
                    break
                source = self._wanted
            if not self._available:
                time.sleep(0.5)
                continue
            if not source:
                time.sleep(0.2)
                self._decay_idle()
                continue
            args = [
                "parec",
                "--raw",
                f"--format=s16le",
                f"--rate={RATE}",
                f"--channels={CHANNELS}",
                "--latency-msec=50",
                f"--device={source}",
            ]
            try:
                self._proc = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=0,
                )
            except OSError as exc:
                with self._lock:
                    self._error = str(exc)
                time.sleep(0.5)
                continue
            assert self._proc.stdout is not None
            frame_bytes = FFT_N * CHANNELS * 2
            buf = bytearray()
            while not self._stop.is_set():
                with self._lock:
                    if not self._active or self._wanted != source:
                        break
                chunk = self._proc.stdout.read(frame_bytes - len(buf) or frame_bytes)
                if not chunk:
                    break
                buf.extend(chunk)
                while len(buf) >= frame_bytes:
                    block = bytes(buf[:frame_bytes])
                    del buf[:frame_bytes]
                    self._process(block)
            self._kill_proc()
            time.sleep(0.05)
        with self._lock:
            self._thread = None

    def _decay_idle(self) -> None:
        with self._lock:
            self._bars = [v * 0.85 for v in self._bars]
            self._peaks = [max(0.0, v - 1.2) for v in self._peaks]
            self._peak_l *= 0.85
            self._peak_r *= 0.85

    def _process(self, block: bytes) -> None:
        count = len(block) // 2
        samples = struct.unpack("<" + "h" * count, block)
        mono = array("f")
        peak_l = 0.0
        peak_r = 0.0
        for i in range(0, count, 2):
            left = samples[i] / 32768.0
            right = samples[i + 1] / 32768.0
            peak_l = max(peak_l, abs(left))
            peak_r = max(peak_r, abs(right))
            mono.append(0.5 * (left + right))
        re = [mono[i] * self._window[i] for i in range(FFT_N)]
        im = [0.0] * FFT_N
        _fft(re, im)
        half = FFT_N // 2
        mags = [0.0] * half
        scale = 2.0 / FFT_N
        for i in range(half):
            mags[i] = math.sqrt(re[i] * re[i] + im[i] * im[i]) * scale
        bars = [0.0] * BARS
        for bi, (lo, hi) in enumerate(self._edges):
            i0 = max(1, int(lo / self._bin_hz))
            i1 = min(half - 1, max(i0 + 1, int(hi / self._bin_hz)))
            peak = 0.0
            for i in range(i0, i1 + 1):
                peak = max(peak, mags[i])
            # Map amplitude to 0..1 with gentle log feel.
            db = 20.0 * math.log10(peak + 1e-9)
            bars[bi] = max(0.0, min(1.0, (db + 72.0) / 72.0))
        with self._lock:
            smoothed = []
            peaks = []
            for i, value in enumerate(bars):
                prev = self._bars[i]
                next_v = value if value >= prev else prev * 0.72 + value * 0.28
                smoothed.append(next_v)
                hold = max(self._peaks[i] - 0.018, next_v)
                peaks.append(hold)
            self._bars = smoothed
            self._peaks = peaks
            self._peak_l = max(peak_l, self._peak_l * 0.82)
            self._peak_r = max(peak_r, self._peak_r * 0.82)
            self._error = ""
