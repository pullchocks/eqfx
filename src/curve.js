import {
  dbToY,
  freqToX,
  formatDb,
  formatFreq,
  xToFreq,
  yToDb,
  MIN_F,
  MAX_F,
} from "./engine.js";

const GRID_FREQS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000];
const GRID_LABELS = ["20", "50", "100", "200", "500", "1k", "2k", "5k", "10k", "20k"];

export class CurveView {
  constructor(canvas, engine, state) {
    this.canvas = canvas;
    this.engine = engine;
    this.state = state;
    this.ctx2 = canvas.getContext("2d");
    this.dpr = 1;
    this.w = 0;
    this.h = 0;
    this.pad = { l: 48, r: 18, t: 28, b: 36 };
    this.curve = new Float32Array(512);
    this.bandCurve = new Float32Array(512);
    this.preBins = null;
    this.postBins = null;
    this.preSmooth = null;
    this.postSmooth = null;
    this.peakHold = null;
    this.hover = { freq: 1000, db: 0, inside: false };
    this.drag = null;
    this.onChange = null;
    this.onSelect = null;
    this.onHover = null;

    canvas.addEventListener("pointerdown", (e) => this.pointerDown(e));
    canvas.addEventListener("pointermove", (e) => this.pointerMove(e));
    canvas.addEventListener("pointerup", (e) => this.pointerUp(e));
    canvas.addEventListener("pointerleave", () => {
      this.hover.inside = false;
      this.onHover?.(this.hover);
    });
    canvas.addEventListener("wheel", (e) => this.wheel(e), { passive: false });
    canvas.addEventListener("dblclick", (e) => this.dblclick(e));
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.w = Math.max(1, Math.floor(rect.width));
    this.h = Math.max(1, Math.floor(rect.height));
    this.canvas.width = Math.floor(this.w * this.dpr);
    this.canvas.height = Math.floor(this.h * this.dpr);
    this.ctx2.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
  }

  plotW() {
    return Math.max(1, this.w - this.pad.l - this.pad.r);
  }

  plotH() {
    return Math.max(1, this.h - this.pad.t - this.pad.b);
  }

  toLocal(e) {
    const r = this.canvas.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  nodePos(band) {
    const x = this.pad.l + freqToX(band.frequency, this.plotW());
    let y;
    if (band.type === "highpass" || band.type === "lowpass" || band.type === "notch") {
      y = this.pad.t + dbToY(0, this.plotH(), this.state.rangeDb);
    } else {
      y = this.pad.t + dbToY(band.gain, this.plotH(), this.state.rangeDb);
    }
    return { x, y };
  }

  hitTest(x, y) {
    let best = -1;
    let bestD = 16;
    const bands = this.state.bands;
    for (let i = 0; i < bands.length; i++) {
      const p = this.nodePos(bands[i]);
      const d = Math.hypot(p.x - x, p.y - y);
      const extra = i === this.state.selected ? 4 : 0;
      if (d < bestD + extra) {
        bestD = d;
        best = i;
      }
    }
    return best;
  }

  pointerDown(e) {
    this.canvas.setPointerCapture(e.pointerId);
    const { x, y } = this.toLocal(e);
    let idx = this.hitTest(x, y);
    if (idx < 0) {
      idx = this.nearestDisabled(x) ?? this.state.selected;
      const band = this.state.bands[idx];
      band.frequency = xToFreq(x - this.pad.l, this.plotW());
      if (band.type === "peaking" || band.type === "lowshelf" || band.type === "highshelf") {
        band.gain = yToDb(y - this.pad.t, this.plotH(), this.state.rangeDb);
      }
      band.enabled = true;
      this.onSelect?.(idx);
      this.onChange?.();
    } else {
      this.onSelect?.(idx);
    }
    this.drag = {
      index: idx,
      shift: e.shiftKey,
      startY: y,
      startQ: this.state.bands[idx].q,
    };
  }

  nearestDisabled(x) {
    const freq = xToFreq(x - this.pad.l, this.plotW());
    let best = -1;
    let bestD = Infinity;
    this.state.bands.forEach((b, i) => {
      if (b.enabled) return;
      const d = Math.abs(Math.log(b.frequency) - Math.log(freq));
      if (d < bestD) {
        bestD = d;
        best = i;
      }
    });
    return best < 0 ? null : best;
  }

  pointerMove(e) {
    const { x, y } = this.toLocal(e);
    this.hover.inside = true;
    this.hover.freq = xToFreq(x - this.pad.l, this.plotW());
    this.hover.db = yToDb(y - this.pad.t, this.plotH(), this.state.rangeDb);
    this.onHover?.(this.hover);

    if (!this.drag) {
      this.canvas.style.cursor = this.hitTest(x, y) >= 0 ? "grab" : "crosshair";
      return;
    }
    const band = this.state.bands[this.drag.index];
    const fine = e.shiftKey ? 0.15 : 1;
    const fx = xToFreq(x - this.pad.l, this.plotW());
    band.frequency = lerpLog(band.frequency, fx, fine === 1 ? 1 : 0.2);
    if (band.type === "highpass" || band.type === "lowpass" || band.type === "notch") {
      const dy = this.drag.startY - y;
      band.q = clampNum(this.drag.startQ * Math.pow(1.02, dy * (e.shiftKey ? 0.25 : 1)), 0.1, 18);
    } else {
      const db = yToDb(y - this.pad.t, this.plotH(), this.state.rangeDb);
      if (e.shiftKey) band.gain += (db - band.gain) * 0.2;
      else band.gain = db;
      band.gain = clampNum(band.gain, -this.state.rangeDb, this.state.rangeDb);
    }
    this.canvas.style.cursor = "grabbing";
    this.onChange?.();
  }

  pointerUp(e) {
    try {
      this.canvas.releasePointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
    this.drag = null;
    this.onRelease?.();
  }

  wheel(e) {
    e.preventDefault();
    const { x, y } = this.toLocal(e);
    let idx = this.hitTest(x, y);
    if (idx < 0) idx = this.state.selected;
    const band = this.state.bands[idx];
    const dir = e.deltaY > 0 ? -1 : 1;
    band.q = clampNum(band.q * Math.pow(1.08, dir), 0.1, 18);
    this.onSelect?.(idx);
    this.onChange?.();
  }

  dblclick(e) {
    const { x, y } = this.toLocal(e);
    const idx = this.hitTest(x, y);
    if (idx < 0) return;
    const band = this.state.bands[idx];
    if (band.type === "peaking" || band.type === "lowshelf" || band.type === "highshelf") {
      band.gain = 0;
    } else {
      band.enabled = false;
    }
    this.onChange?.();
  }

  draw() {
    if (this.canvas.width === 0) this.resize();
    const ctx = this.ctx2;
    const w = this.w;
    const h = this.h;
    ctx.clearRect(0, 0, w, h);

    this.paintBackdrop(ctx);
    this.paintGrid(ctx);
    this.paintPiano(ctx);
    if (this.state.showAnalyzer) this.paintSpectrum(ctx);
    this.paintCurves(ctx);
    this.paintNodes(ctx);
    this.paintHover(ctx);
  }

  paintBackdrop(ctx) {
    const g = ctx.createLinearGradient(0, 0, 0, this.h);
    g.addColorStop(0, "#10131a");
    g.addColorStop(1, "#090b10");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, this.w, this.h);
  }

  paintGrid(ctx) {
    const pw = this.plotW();
    const ph = this.plotH();
    const x0 = this.pad.l;
    const y0 = this.pad.t;
    const range = this.state.rangeDb;

    ctx.save();
    ctx.translate(x0, y0);

    ctx.strokeStyle = "rgba(255,255,255,0.045)";
    ctx.lineWidth = 1;
    for (let i = 0; i < GRID_FREQS.length; i++) {
      const x = freqToX(GRID_FREQS[i], pw);
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, ph);
      ctx.stroke();
      ctx.fillStyle = "rgba(141,149,168,0.85)";
      ctx.font = "10px 'IBM Plex Mono', monospace";
      ctx.textAlign = "center";
      ctx.fillText(GRID_LABELS[i], x, ph + 22);
    }

    const steps = range <= 12 ? 6 : range <= 18 ? 6 : 6;
    for (let db = -range; db <= range; db += steps) {
      const y = dbToY(db, ph, range);
      ctx.beginPath();
      ctx.strokeStyle = db === 0 ? "rgba(62,224,198,0.22)" : "rgba(255,255,255,0.04)";
      ctx.lineWidth = db === 0 ? 1.2 : 1;
      ctx.moveTo(0, y);
      ctx.lineTo(pw, y);
      ctx.stroke();
      ctx.fillStyle = db === 0 ? "#3ee0c6" : "rgba(141,149,168,0.8)";
      ctx.font = "10px 'IBM Plex Mono', monospace";
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText(`${db > 0 ? "+" : ""}${db}`, -10, y);
    }

    ctx.restore();
  }

  paintPiano(ctx) {
    const pw = this.plotW();
    const y = this.h - 14;
    const h = 10;
    ctx.save();
    for (let midi = 24; midi <= 108; midi++) {
      const f0 = 440 * Math.pow(2, (midi - 69) / 12);
      const f1 = 440 * Math.pow(2, (midi - 68) / 12);
      const x0 = this.pad.l + freqToX(f0, pw);
      const x1 = this.pad.l + freqToX(f1, pw);
      const pc = midi % 12;
      const black = pc === 1 || pc === 3 || pc === 6 || pc === 8 || pc === 10;
      ctx.fillStyle = black ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.1)";
      ctx.fillRect(x0, y - h, Math.max(1, x1 - x0 - 0.4), h);
      if (pc === 0) {
        ctx.fillStyle = "rgba(141,149,168,0.7)";
        ctx.font = "8px 'IBM Plex Mono', monospace";
        ctx.textAlign = "left";
        ctx.fillText(`C${Math.floor(midi / 12) - 1}`, x0 + 2, y - h - 2);
      }
    }
    ctx.restore();
  }

  ensureSpec() {
    const analyser = this.engine.postAnalyser;
    if (!analyser) return false;
    const n = analyser.frequencyBinCount;
    if (!this.postBins || this.postBins.length !== n) {
      this.preBins = new Float32Array(n);
      this.postBins = new Float32Array(n);
      this.preSmooth = new Float32Array(this.plotW());
      this.postSmooth = new Float32Array(this.plotW());
      this.peakHold = new Float32Array(this.plotW());
      this.peakHold.fill(-120);
    }
    return true;
  }

  paintSpectrum(ctx) {
    if (!this.ensureSpec()) return;
    const pre = this.engine.preAnalyser;
    const post = this.engine.postAnalyser;
    post.getFloatFrequencyData(this.postBins);
    if (this.state.showPre) pre.getFloatFrequencyData(this.preBins);

    const pw = this.plotW();
    const ph = this.plotH();
    const nyquist = this.engine.ctx.sampleRate / 2;
    const logMin = Math.log(MIN_F);
    const logMax = Math.log(MAX_F);

    const sample = (bins, x) => {
      const freq = Math.exp(logMin + (x / pw) * (logMax - logMin));
      const bin = (freq / nyquist) * bins.length;
      const i = Math.min(bins.length - 2, Math.max(0, bin));
      const f = i - Math.floor(i);
      const a = bins[Math.floor(i)];
      const b = bins[Math.ceil(i)];
      return a + (b - a) * f;
    };

    for (let x = 0; x < pw; x++) {
      this.postSmooth[x] = sample(this.postBins, x);
      if (this.state.showPre) this.preSmooth[x] = sample(this.preBins, x);
      this.peakHold[x] = Math.max(this.peakHold[x] - 0.35, this.postSmooth[x]);
    }

    const toY = (db) => {
      const n = (db + 90) / 78;
      return ph - clampNum(n, 0, 1) * ph * 0.92;
    };

    ctx.save();
    ctx.translate(this.pad.l, this.pad.t);
    ctx.beginPath();
    ctx.moveTo(0, ph);
    for (let x = 0; x < pw; x++) ctx.lineTo(x, toY(this.postSmooth[x]));
    ctx.lineTo(pw, ph);
    ctx.closePath();
    const fill = ctx.createLinearGradient(0, 0, 0, ph);
    fill.addColorStop(0, "rgba(62,224,198,0.28)");
    fill.addColorStop(1, "rgba(62,224,198,0.02)");
    ctx.fillStyle = fill;
    ctx.fill();

    if (this.state.showPre) {
      ctx.beginPath();
      for (let x = 0; x < pw; x++) {
        const y = toY(this.preSmooth[x]);
        if (x === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = "rgba(150,168,210,0.45)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    ctx.beginPath();
    for (let x = 0; x < pw; x++) {
      const y = toY(this.peakHold[x]);
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = "rgba(138,248,230,0.35)";
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.restore();
  }

  paintCurves(ctx) {
    this.engine.curveDb(this.curve);
    const pw = this.plotW();
    const ph = this.plotH();
    const range = this.state.rangeDb;
    const freqs = this.engine.freqBins;
    const xOf = (i) => freqToX(freqs[i], pw);
    const yOf = (arr, i) => dbToY(arr[i], ph, range);

    ctx.save();
    ctx.translate(this.pad.l, this.pad.t);

    const sel = this.state.selected;
    const selectedBand = this.state.bands[sel];
    if (selectedBand?.enabled || this.drag) {
      this.engine.curveDb(this.bandCurve, { bandIndex: sel });
      ctx.beginPath();
      for (let i = 0; i < freqs.length; i++) {
        const x = xOf(i);
        const y = yOf(this.bandCurve, i);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = "rgba(232,163,90,0.7)";
      ctx.lineWidth = 1.4;
      ctx.stroke();
    }

    ctx.beginPath();
    ctx.moveTo(0, dbToY(0, ph, range));
    for (let i = 0; i < freqs.length; i++) ctx.lineTo(xOf(i), yOf(this.curve, i));
    ctx.lineTo(pw, dbToY(0, ph, range));
    ctx.closePath();
    const g = ctx.createLinearGradient(0, 0, 0, ph);
    g.addColorStop(0, "rgba(62,224,198,0.16)");
    g.addColorStop(0.5, "rgba(62,224,198,0.07)");
    g.addColorStop(1, "rgba(62,224,198,0.0)");
    ctx.fillStyle = g;
    ctx.fill();

    ctx.beginPath();
    for (let i = 0; i < freqs.length; i++) {
      const x = xOf(i);
      const y = yOf(this.curve, i);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = this.state.bypass ? "rgba(141,149,168,0.45)" : "#3ee0c6";
    ctx.lineWidth = 2.2;
    ctx.shadowColor = this.state.bypass ? "transparent" : "rgba(62,224,198,0.45)";
    ctx.shadowBlur = 10;
    ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.restore();
  }

  paintNodes(ctx) {
    this.state.bands.forEach((band, i) => {
      const { x, y } = this.nodePos(band);
      const sel = i === this.state.selected;
      const on = band.enabled;
      ctx.beginPath();
      ctx.arc(x, y, sel ? 8 : 6.5, 0, Math.PI * 2);
      ctx.fillStyle = on ? (sel ? "#3ee0c6" : "#1b3d38") : "#161a22";
      ctx.fill();
      ctx.lineWidth = sel ? 2 : 1.4;
      ctx.strokeStyle = on ? "#8af8e6" : "rgba(141,149,168,0.55)";
      ctx.stroke();
      ctx.fillStyle = sel ? "#06211c" : on ? "#8af8e6" : "#8d95a8";
      ctx.font = "700 9px Outfit, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(String(i + 1), x, y + 0.5);
    });
  }

  paintHover(ctx) {
    if (!this.hover.inside) return;
    const x = this.pad.l + freqToX(this.hover.freq, this.plotW());
    ctx.beginPath();
    ctx.setLineDash([3, 4]);
    ctx.strokeStyle = "rgba(255,255,255,0.12)";
    ctx.moveTo(x, this.pad.t);
    ctx.lineTo(x, this.pad.t + this.plotH());
    ctx.stroke();
    ctx.setLineDash([]);
  }
}

function lerpLog(a, b, t) {
  return Math.exp(Math.log(a) + (Math.log(b) - Math.log(a)) * t);
}

function clampNum(v, a, b) {
  return Math.max(a, Math.min(b, v));
}

export function hoverText(hover) {
  if (!hover.inside) return `${formatFreq(20)}  ·  ${formatDb(0)}`;
  return `${formatFreq(hover.freq)}  ·  ${formatDb(hover.db)}`;
}
