import {
  EQEngine,
  clamp,
  formatDb,
  formatFreq,
  formatQ,
  formatTime,
} from "./engine.js";
import {
  CATEGORIES,
  FILTER_TYPES,
  PRESETS,
  TYPE_LABELS,
  clonePresetBands,
  defaultBands,
  findPreset,
} from "./presets.js";
import { CurveView, hoverText } from "./curve.js";

const state = {
  bands: defaultBands(),
  selected: 5,
  bypass: false,
  rangeDb: 18,
  showAnalyzer: true,
  showPre: true,
  presetId: "flat",
  presetDirty: false,
  slot: "A",
  slotA: null,
  slotB: null,
  category: "All",
  search: "",
  solo: -1,
};

const engine = new EQEngine();
const els = {};

function $(id) {
  return document.getElementById(id);
}

function snapshot() {
  return {
    bands: state.bands.map((b) => ({ ...b })),
    outputGain: engine.outputDb,
    presetId: state.presetId,
  };
}

function restore(snap) {
  state.bands = snap.bands.map((b) => ({ ...b }));
  state.presetId = snap.presetId;
  engine.setOutputDb(snap.outputGain);
  $("out-gain").value = String(snap.outputGain);
  $("out-gain-val").textContent = formatDb(snap.outputGain);
  applyEngine({ snap: true });
  markDirty(false);
  syncPresetHeader();
  renderBands();
  renderInspector();
}

function applyEngine(opts) {
  engine.applyBands(state.bands, opts);
  engine.setSolo(state.solo);
}

function markDirty(dirty = true) {
  state.presetDirty = dirty;
  $("preset-dirty").hidden = !dirty;
}

function syncPresetHeader() {
  const p = findPreset(state.presetId);
  $("preset-name").textContent = p.name;
  $("preset-category").textContent = p.category;
}

function loadPreset(id, { dirty = false } = {}) {
  const p = findPreset(id);
  state.presetId = p.id;
  state.bands = clonePresetBands(p);
  state.solo = -1;
  engine.setOutputDb(p.outputGain || 0);
  $("out-gain").value = String(p.outputGain || 0);
  $("out-gain-val").textContent = formatDb(p.outputGain || 0);
  applyEngine({ snap: true });
  markDirty(dirty);
  syncPresetHeader();
  renderBands();
  renderInspector();
  renderPresets();
}

function syncKnobReadouts() {
  const band = state.bands[state.selected];
  const knobs = document.querySelectorAll("#knobs .knob");
  if (knobs.length !== 3) return;
  knobs[0].querySelector(".knob-value").textContent = formatFreq(band.frequency);
  knobs[1].querySelector(".knob-value").textContent = formatDb(band.gain);
  knobs[2].querySelector(".knob-value").textContent = formatQ(band.q);
}

function changed({ rebuild = false } = {}) {
  applyEngine();
  markDirty(true);
  renderBands();
  if (rebuild) renderInspector();
  else syncKnobReadouts();
}

function toast(msg) {
  const el = $("toast");
  el.textContent = msg;
  el.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => {
    el.hidden = true;
  }, 2200);
}

function renderPresets() {
  const q = state.search.trim().toLowerCase();
  const list = $("preset-list");
  list.innerHTML = "";
  const items = PRESETS.filter((p) => {
    if (state.category !== "All" && p.category !== state.category) return false;
    if (!q) return true;
    return `${p.name} ${p.category} ${p.description}`.toLowerCase().includes(q);
  });
  for (const p of items) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "preset-item" + (p.id === state.presetId ? " is-on" : "");
    btn.innerHTML = `<span class="dot"></span><span><span class="name">${escapeHtml(
      p.name
    )}</span><div class="desc">${escapeHtml(p.description)}</div></span>`;
    btn.addEventListener("click", async () => {
      await engine.ensure();
      loadPreset(p.id);
      document.querySelector(".sidebar").classList.remove("is-open");
    });
    list.appendChild(btn);
  }
}

function renderCats() {
  const wrap = $("preset-cats");
  wrap.innerHTML = "";
  for (const c of CATEGORIES) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "cat" + (c === state.category ? " is-on" : "");
    b.textContent = c;
    b.addEventListener("click", () => {
      state.category = c;
      renderCats();
      renderPresets();
    });
    wrap.appendChild(b);
  }
}

function renderBands() {
  const strip = $("band-strip");
  strip.innerHTML = "";
  state.bands.forEach((band, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className =
      "band-chip" +
      (i === state.selected ? " is-on" : "") +
      (!band.enabled ? " is-off" : "") +
      (state.solo === i ? " is-solo" : "");
    const type = FILTER_TYPES.find((t) => t.id === band.type)?.label || band.type;
    b.innerHTML = `<span class="band-idx"><span>${i + 1}</span><span>${type}</span></span>
      <span class="freq">${formatFreq(band.frequency)}</span>
      <span class="gain">${band.type === "highpass" || band.type === "lowpass" || band.type === "notch" ? "Q " + formatQ(band.q) : formatDb(band.gain)}</span>`;
    b.addEventListener("click", () => selectBand(i));
    strip.appendChild(b);
  });
}

function selectBand(i) {
  state.selected = i;
  renderBands();
  renderInspector();
}

function renderInspector() {
  const band = state.bands[state.selected];
  $("sel-name").textContent = `Band ${state.selected + 1}`;
  $("sel-type").textContent = TYPE_LABELS[band.type];
  $("btn-enable").classList.toggle("is-on", band.enabled);
  $("btn-enable").textContent = band.enabled ? "On" : "Off";
  $("btn-solo").classList.toggle("is-on", state.solo === state.selected);

  const types = $("type-row");
  types.innerHTML = "";
  for (const t of FILTER_TYPES) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = t.label;
    btn.className = t.id === band.type ? "is-on" : "";
    btn.addEventListener("click", () => {
      band.type = t.id;
      if (t.id === "highpass" || t.id === "lowpass" || t.id === "notch") band.gain = 0;
      band.enabled = true;
      changed({ rebuild: true });
    });
    types.appendChild(btn);
  }

  const knobs = $("knobs");
  knobs.innerHTML = "";
  knobs.appendChild(
    makeKnob({
      label: "Freq",
      value: band.frequency,
      min: 20,
      max: 20000,
      log: true,
      format: formatFreq,
      onInput: (v) => {
        band.frequency = v;
        changed();
      },
    })
  );
  const gainDisabled = band.type === "highpass" || band.type === "lowpass" || band.type === "notch";
  knobs.appendChild(
    makeKnob({
      label: "Gain",
      value: band.gain,
      min: -18,
      max: 18,
      format: formatDb,
      disabled: gainDisabled,
      onInput: (v) => {
        band.gain = v;
        band.enabled = true;
        changed();
      },
    })
  );
  knobs.appendChild(
    makeKnob({
      label: "Q",
      value: band.q,
      min: 0.1,
      max: 18,
      log: true,
      format: formatQ,
      onInput: (v) => {
        band.q = v;
        changed();
      },
    })
  );
}

function makeKnob({ label, value, min, max, log = false, format, onInput, disabled = false }) {
  const root = document.createElement("div");
  root.className = "knob";
  root.innerHTML = `<div class="knob-dial"><canvas width="124" height="124"></canvas></div>
    <div class="knob-value"></div>
    <div class="knob-label">${label}</div>`;
  const canvas = root.querySelector("canvas");
  const valEl = root.querySelector(".knob-value");
  let v = value;

  const toT = (x) => {
    if (log) return Math.log(x / min) / Math.log(max / min);
    return (x - min) / (max - min);
  };
  const fromT = (t) => {
    t = clamp(t, 0, 1);
    if (log) return min * Math.pow(max / min, t);
    return min + (max - min) * t;
  };

  const paint = () => {
    const ctx = canvas.getContext("2d");
    const s = 62;
    ctx.setTransform(2, 0, 0, 2, 0, 0);
    ctx.clearRect(0, 0, s, s);
    const c = 31;
    const r = 24;
    ctx.beginPath();
    ctx.arc(c, c, r + 4, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(255,255,255,0.06)";
    ctx.lineWidth = 3;
    ctx.stroke();
    const a0 = Math.PI * 0.75;
    const a1 = Math.PI * 2.25;
    ctx.beginPath();
    ctx.arc(c, c, r + 4, a0, a1);
    ctx.strokeStyle = "#222733";
    ctx.lineWidth = 3;
    ctx.stroke();
    const t = toT(v);
    ctx.beginPath();
    ctx.arc(c, c, r + 4, a0, a0 + (a1 - a0) * t);
    ctx.strokeStyle = disabled ? "#3a4150" : "#3ee0c6";
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.stroke();
    const ang = a0 + (a1 - a0) * t;
    ctx.beginPath();
    ctx.arc(c, c, r, 0, Math.PI * 2);
    const g = ctx.createRadialGradient(c - 4, c - 6, 4, c, c, r);
    g.addColorStop(0, "#2a3140");
    g.addColorStop(1, "#12151c");
    ctx.fillStyle = g;
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.08)";
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(c + Math.cos(ang) * 6, c + Math.sin(ang) * 6);
    ctx.lineTo(c + Math.cos(ang) * (r - 5), c + Math.sin(ang) * (r - 5));
    ctx.strokeStyle = disabled ? "#6a7388" : "#eef1f6";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.stroke();
    valEl.textContent = format(v);
  };

  paint();
  if (disabled) {
    root.style.opacity = "0.4";
    root.style.pointerEvents = "none";
    return root;
  }

  let dragging = false;
  let lastY = 0;
  root.addEventListener("pointerdown", (e) => {
    dragging = true;
    lastY = e.clientY;
    root.setPointerCapture(e.pointerId);
  });
  root.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const dy = lastY - e.clientY;
    lastY = e.clientY;
    const scale = e.shiftKey ? 0.0015 : 0.006;
    v = fromT(toT(v) + dy * scale);
    onInput(v);
    paint();
  });
  root.addEventListener("pointerup", () => {
    dragging = false;
  });
  root.addEventListener("wheel", (e) => {
    e.preventDefault();
    const dir = e.deltaY > 0 ? -1 : 1;
    v = fromT(toT(v) + dir * 0.03);
    onInput(v);
    paint();
  });
  return root;
}

function drawMeters(canvas) {
  const ctx = canvas.getContext("2d");
  const dpr = Math.min(devicePixelRatio || 1, 2);
  const w = 64;
  const h = canvas.parentElement.clientHeight - 22;
  if (h <= 0) return;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.height = `${h}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = "#08090d";
  ctx.fillRect(0, 0, w, h);

  const peaks = [engine._peakL || -60, engine._peakR || -60];
  const rms = [engine._rmsL || -60, engine._rmsR || -60];
  const labels = ["+6", "0", "-6", "-12", "-24", "-48"];
  ctx.fillStyle = "#5c6478";
  ctx.font = "8px 'IBM Plex Mono', monospace";
  ctx.textAlign = "center";
  labels.forEach((lb, i) => {
    ctx.fillText(lb, w / 2, 12 + i * ((h - 20) / (labels.length - 1)));
  });

  const meter = (x, peak, rmsv) => {
    const top = 8;
    const bot = h - 8;
    const hh = bot - top;
    const dbTo = (db) => bot - clamp((db + 60) / 66, 0, 1) * hh;
    const yPeak = dbTo(peak);
    const yRms = dbTo(rmsv);
    ctx.fillStyle = "#161a22";
    ctx.fillRect(x, top, 10, hh);
    const g = ctx.createLinearGradient(0, bot, 0, top);
    g.addColorStop(0, "#3ee0c6");
    g.addColorStop(0.7, "#e8a35a");
    g.addColorStop(1, "#e15b5b");
    ctx.fillStyle = g;
    ctx.fillRect(x, yRms, 10, bot - yRms);
    ctx.fillStyle = peak > -0.2 ? "#ff4d4d" : "#eef1f6";
    ctx.fillRect(x, yPeak, 10, 2);
  };
  meter(12, peaks[0], rms[0]);
  meter(42, peaks[1], rms[1]);
}

function readMeters() {
  if (!engine.meterL) return;
  const tmp = readMeters._buf || (readMeters._buf = new Float32Array(2048));
  const channel = (analyser, keyP, keyR) => {
    analyser.getFloatTimeDomainData(tmp);
    let peak = 0;
    let sum = 0;
    for (let i = 0; i < tmp.length; i++) {
      const a = Math.abs(tmp[i]);
      if (a > peak) peak = a;
      sum += tmp[i] * tmp[i];
    }
    const pDb = 20 * Math.log10(peak + 1e-12);
    const rDb = 20 * Math.log10(Math.sqrt(sum / tmp.length) + 1e-12);
    engine[keyP] = Math.max(pDb, (engine[keyP] ?? -60) - 0.7);
    engine[keyR] = rDb * 0.35 + (engine[keyR] ?? rDb) * 0.65;
  };
  channel(engine.meterL, "_peakL", "_rmsL");
  channel(engine.meterR, "_peakR", "_rmsR");
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function updateTransport() {
  const playing = engine.playing;
  $("btn-play").textContent = playing ? "Pause" : "Play";
  $("btn-play").classList.toggle("is-on", playing);
  const dur = engine.activeDuration();
  const t = engine.currentTime();
  $("time-now").textContent = formatTime(t);
  $("time-end").textContent = formatTime(dur);
  if (!$("seek")._dragging) {
    $("seek").value = dur ? String(Math.round((t / dur) * 1000)) : "0";
  }
  const names = {
    idle: "No source · load a file, use Demo Mix, or noise",
    file: engine.fileName || "Audio file",
    demo: "Demo Mix — drums, bass, pad",
    pink: "Pink noise",
    white: "White noise",
    sine: "1 kHz sine",
    mic: "Microphone input",
  };
  $("track-name").textContent = names[engine.mode] || names.idle;
  for (const id of ["btn-demo", "btn-pink", "btn-white", "btn-sine", "btn-mic"]) {
    $(id).classList.toggle("is-on", false);
  }
  const map = { demo: "btn-demo", pink: "btn-pink", white: "btn-white", sine: "btn-sine", mic: "btn-mic" };
  if (map[engine.mode]) $(map[engine.mode]).classList.add("is-on");
}

async function boot() {
  els.canvas = $("eq-canvas");
  const curve = new CurveView(els.canvas, engine, state);
  curve.onChange = () => changed();
  curve.onRelease = () => renderInspector();
  curve.onSelect = (i) => selectBand(i);
  curve.onHover = (h) => {
    $("hover-readout").textContent = hoverText(h);
  };

  await engine.ensure().catch(() => {});
  state.slotA = snapshot();
  state.slotB = snapshot();
  loadPreset("flat");

  renderCats();
  renderPresets();
  $("preset-search").placeholder = `Search ${PRESETS.length} factory presets`;
  renderBands();
  renderInspector();

  $("preset-search").addEventListener("input", (e) => {
    state.search = e.target.value;
    renderPresets();
  });
  $("preset-open").addEventListener("click", () => {
    const side = document.querySelector(".sidebar");
    side.classList.toggle("is-open");
    $("preset-search").focus();
  });
  document.addEventListener("click", (e) => {
    const side = document.querySelector(".sidebar");
    if (!side.classList.contains("is-open")) return;
    if (e.target.closest(".sidebar") || e.target.closest("#preset-open")) return;
    side.classList.remove("is-open");
  });
  $("btn-init").addEventListener("click", () => loadPreset("flat"));

  $("btn-a").addEventListener("click", () => {
    if (state.slot === "A") return;
    state.slotB = snapshot();
    state.slot = "A";
    restore(state.slotA);
    $("btn-a").classList.add("is-on");
    $("btn-b").classList.remove("is-on");
  });
  $("btn-b").addEventListener("click", () => {
    if (state.slot === "B") return;
    state.slotA = snapshot();
    if (!state.slotB) state.slotB = snapshot();
    state.slot = "B";
    restore(state.slotB);
    $("btn-b").classList.add("is-on");
    $("btn-a").classList.remove("is-on");
  });
  $("btn-copy-ab").addEventListener("click", () => {
    const snap = snapshot();
    if (state.slot === "A") {
      state.slotB = snap;
      toast("Copied A → B");
    } else {
      state.slotA = snap;
      toast("Copied B → A");
    }
  });

  $("btn-bypass").addEventListener("click", () => {
    state.bypass = !state.bypass;
    engine.setBypass(state.bypass);
    $("btn-bypass").classList.toggle("is-on", state.bypass);
    $("btn-bypass").setAttribute("aria-pressed", String(state.bypass));
  });

  $("out-gain").addEventListener("input", (e) => {
    const v = Number(e.target.value);
    engine.setOutputDb(v);
    $("out-gain-val").textContent = formatDb(v);
    markDirty(true);
  });

  $("toggle-analyzer").addEventListener("change", (e) => {
    state.showAnalyzer = e.target.checked;
  });
  $("toggle-pre").addEventListener("change", (e) => {
    state.showPre = e.target.checked;
  });
  document.querySelectorAll(".seg button").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.rangeDb = Number(btn.dataset.range);
      document.querySelectorAll(".seg button").forEach((b) => b.classList.toggle("is-on", b === btn));
    });
  });

  $("btn-enable").addEventListener("click", () => {
    const band = state.bands[state.selected];
    band.enabled = !band.enabled;
    changed({ rebuild: true });
  });
  $("btn-solo").addEventListener("click", () => {
    state.solo = state.solo === state.selected ? -1 : state.selected;
    changed({ rebuild: true });
  });
  $("btn-reset-band").addEventListener("click", () => {
    const d = defaultBands()[state.selected];
    Object.assign(state.bands[state.selected], d);
    changed({ rebuild: true });
  });

  $("btn-load").addEventListener("click", () => $("file-input").click());
  $("file-input").addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (file) await openFile(file);
  });
  $("btn-play").addEventListener("click", async () => {
    await engine.togglePlay();
    updateTransport();
  });
  $("btn-stop").addEventListener("click", async () => {
    engine.pause();
    engine.pausedAt = 0;
    engine.stopSource();
    await engine.stopMic();
    engine.mode = engine.fileBuffer ? "file" : "idle";
    updateTransport();
  });
  $("seek").addEventListener("pointerdown", () => {
    $("seek")._dragging = true;
  });
  window.addEventListener("pointerup", () => {
    $("seek")._dragging = false;
  });
  $("seek").addEventListener("input", (e) => {
    const dur = engine.activeDuration();
    if (!dur) return;
    engine.seek((Number(e.target.value) / 1000) * dur);
  });

  $("btn-demo").addEventListener("click", async () => {
    toast("Rendering demo mix…");
    await engine.playDemo();
    updateTransport();
  });
  $("btn-pink").addEventListener("click", () => engine.playPink().then(updateTransport));
  $("btn-white").addEventListener("click", () => engine.playWhite().then(updateTransport));
  $("btn-sine").addEventListener("click", () => engine.playSine().then(updateTransport));
  $("btn-mic").addEventListener("click", async () => {
    try {
      await engine.playMic();
      updateTransport();
    } catch {
      toast("Microphone permission denied");
    }
  });

  window.addEventListener("dragover", (e) => {
    e.preventDefault();
    document.querySelector(".app").classList.add("is-drag");
  });
  window.addEventListener("dragleave", () => {
    document.querySelector(".app").classList.remove("is-drag");
  });
  window.addEventListener("drop", async (e) => {
    e.preventDefault();
    document.querySelector(".app").classList.remove("is-drag");
    const file = [...e.dataTransfer.files].find((f) => f.type.startsWith("audio") || /\.(wav|mp3|flac|ogg|m4a|aiff)$/i.test(f.name));
    if (file) await openFile(file);
  });

  window.addEventListener("keydown", async (e) => {
    if (e.target.matches("input, textarea")) return;
    if (e.code === "Space") {
      e.preventDefault();
      await engine.togglePlay();
      updateTransport();
    } else if (e.key === "b" || e.key === "B") {
      $("btn-bypass").click();
    } else if (e.key >= "1" && e.key <= "9") {
      selectBand(Number(e.key) - 1);
    } else if (e.key === "0") {
      selectBand(9);
    } else if (e.key === "a" || e.key === "A") {
      $("btn-a").click();
    }
  });

  window.addEventListener("pointerdown", () => {
    engine.ensure();
  }, { once: true });
  window.addEventListener("resize", () => curve.resize());
  curve.resize();

  engine.onEnded = () => updateTransport();

  const loop = () => {
    readMeters();
    drawMeters($("meter-canvas"));
    curve.draw();
    updateTransport();
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}

async function openFile(file) {
  try {
    await engine.decodeFile(file);
    await engine.playFile(0);
    updateTransport();
  } catch (err) {
    toast("Could not decode that audio file");
    console.error(err);
  }
}

boot();
