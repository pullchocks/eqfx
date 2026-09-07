const MIN_F = 20;
const MAX_F = 20000;

export function clamp(v, a, b) {
  return Math.max(a, Math.min(b, v));
}

export function lerp(a, b, t) {
  return a + (b - a) * t;
}

function setParam(param, value, ctx) {
  const t = ctx.currentTime;
  param.cancelScheduledValues(t);
  param.setTargetAtTime(value, t, 0.012);
}

function fillBuffer(ctx, seconds, fn) {
  const length = Math.floor(ctx.sampleRate * seconds);
  const buffer = ctx.createBuffer(2, length, ctx.sampleRate);
  const l = buffer.getChannelData(0);
  const r = buffer.getChannelData(1);
  for (let i = 0; i < length; i++) {
    const v = fn(i, ctx.sampleRate);
    l[i] = v;
    r[i] = v * 0.98 + (fn(i + 97, ctx.sampleRate) - v) * 0.04;
  }
  return buffer;
}

function whiteSample() {
  return Math.random() * 2 - 1;
}

function makeWhite(ctx) {
  return fillBuffer(ctx, 2.5, () => whiteSample() * 0.18);
}

function makePink(ctx) {
  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  return fillBuffer(ctx, 2.5, () => {
    const w = whiteSample();
    b0 = 0.99886 * b0 + w * 0.0555179;
    b1 = 0.99332 * b1 + w * 0.0750759;
    b2 = 0.969 * b2 + w * 0.153852;
    b3 = 0.8665 * b3 + w * 0.3104856;
    b4 = 0.55 * b4 + w * 0.5329522;
    b5 = -0.7616 * b5 - w * 0.016898;
    const pink = b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362;
    b6 = w * 0.115926;
    return pink * 0.08;
  });
}

export class EQEngine {
  constructor() {
    this.ctx = null;
    this.filters = [];
    this.visual = [];
    this.inputGain = null;
    this.outputGain = null;
    this.dryGain = null;
    this.wetGain = null;
    this.preAnalyser = null;
    this.postAnalyser = null;
    this.meterL = null;
    this.meterR = null;
    this.splitter = null;
    this.master = null;
    this.freqBins = null;
    this.magA = null;
    this.phaseA = null;
    this.magB = null;
    this.source = null;
    this.mediaStream = null;
    this.mode = "idle";
    this.fileBuffer = null;
    this.fileName = "";
    this.demoBuffer = null;
    this.startedAt = 0;
    this.pausedAt = 0;
    this.playing = false;
    this.loop = true;
    this.bypass = false;
    this.outputDb = 0;
    this.bands = [];
    this.soloIndex = -1;
    this.onEnded = null;
  }

  async ensure() {
    if (this.ctx) {
      if (this.ctx.state === "suspended") await this.ctx.resume();
      return this.ctx;
    }
    const ctx = new AudioContext();
    this.ctx = ctx;

    this.inputGain = ctx.createGain();
    this.dryGain = ctx.createGain();
    this.wetGain = ctx.createGain();
    this.outputGain = ctx.createGain();
    this.master = ctx.createGain();

    this.preAnalyser = ctx.createAnalyser();
    this.postAnalyser = ctx.createAnalyser();
    this.meterL = ctx.createAnalyser();
    this.meterR = ctx.createAnalyser();
    this.splitter = ctx.createChannelSplitter(2);

    for (const a of [this.preAnalyser, this.postAnalyser]) {
      a.fftSize = 8192;
      a.smoothingTimeConstant = 0.72;
      a.minDecibels = -90;
      a.maxDecibels = -12;
    }
    for (const a of [this.meterL, this.meterR]) {
      a.fftSize = 2048;
      a.smoothingTimeConstant = 0;
    }

    this.filters = [];
    this.visual = [];
    let node = this.inputGain;
    this.inputGain.connect(this.preAnalyser);
    this.preAnalyser.connect(this.dryGain);

    for (let i = 0; i < 10; i++) {
      const f = ctx.createBiquadFilter();
      f.type = "peaking";
      f.frequency.value = 1000;
      f.Q.value = 1;
      f.gain.value = 0;
      node.connect(f);
      this.filters.push(f);
      node = f;
      const vis = ctx.createBiquadFilter();
      vis.type = "peaking";
      vis.frequency.value = 1000;
      vis.Q.value = 1;
      vis.gain.value = 0;
      this.visual.push(vis);
    }

    node.connect(this.wetGain);
    this.dryGain.gain.value = 0;
    this.wetGain.gain.value = 1;
    this.dryGain.connect(this.outputGain);
    this.wetGain.connect(this.outputGain);
    this.outputGain.connect(this.postAnalyser);
    this.postAnalyser.connect(this.master);
    this.master.connect(this.splitter);
    this.master.connect(ctx.destination);
    this.splitter.connect(this.meterL, 0);
    this.splitter.connect(this.meterR, 1);

    const n = 512;
    this.freqBins = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const t = i / (n - 1);
      this.freqBins[i] = MIN_F * Math.pow(MAX_F / MIN_F, t);
    }
    this.magA = new Float32Array(n);
    this.phaseA = new Float32Array(n);
    this.magB = new Float32Array(n);

    this.pinkBuffer = makePink(ctx);
    this.whiteBuffer = makeWhite(ctx);

    return ctx;
  }

  applyBands(bands, { snap = false } = {}) {
    this.bands = bands;
    if (!this.ctx) return;
    const ctx = this.ctx;
    if (!this.visual?.length) return;
    for (let i = 0; i < 10; i++) {
      const spec = bands[i];
      const node = this.filters[i];
      const soloed = this.soloIndex >= 0;
      const on = spec.enabled && (!soloed || this.soloIndex === i);
      const freq = clamp(spec.frequency, MIN_F, MAX_F);
      const q = clamp(spec.q, 0.1, 18);
      let type = spec.type;
      let f = freq;
      let qq = q;
      let g = 0;
      if (!on) {
        type = "peaking";
        f = 1000;
        qq = 1;
        g = 0;
      } else if (type === "highpass" || type === "lowpass" || type === "notch") {
        g = 0;
      } else {
        g = spec.gain;
      }
      node.type = type;
      const vis = this.visual[i];
      vis.type = spec.type;
      vis.frequency.value = freq;
      vis.Q.value = q;
      vis.gain.value =
        spec.type === "highpass" || spec.type === "lowpass" || spec.type === "notch" ? 0 : spec.gain;
      if (snap) {
        node.frequency.value = f;
        node.Q.value = qq;
        node.gain.value = g;
      } else {
        setParam(node.frequency, f, ctx);
        setParam(node.Q, qq, ctx);
        setParam(node.gain, g, ctx);
      }
    }
  }

  setOutputDb(db) {
    this.outputDb = db;
    if (!this.outputGain) return;
    setParam(this.outputGain.gain, Math.pow(10, db / 20), this.ctx);
  }

  setBypass(on) {
    this.bypass = on;
    if (!this.ctx) return;
    setParam(this.wetGain.gain, on ? 0 : 1, this.ctx);
    setParam(this.dryGain.gain, on ? 1 : 0, this.ctx);
  }

  setSolo(index) {
    this.soloIndex = index;
    this.applyBands(this.bands);
  }

  curveDb(into, { bandIndex = -1 } = {}) {
    const n = this.freqBins.length;
    if (!into || into.length !== n) into = new Float32Array(n);
    into.fill(0);
    if (!this.ctx || !this.visual?.length) return into;

    const mag = this.magA;
    const phase = this.phaseA;
    const acc = this.magB;
    acc.fill(1);

    const use = (node) => {
      node.getFrequencyResponse(this.freqBins, mag, phase);
      for (let i = 0; i < n; i++) acc[i] *= mag[i];
    };

    if (bandIndex >= 0) {
      acc.fill(1);
      use(this.visual[bandIndex]);
    } else {
      for (let i = 0; i < this.visual.length; i++) {
        const spec = this.bands[i];
        if (spec && spec.enabled) use(this.visual[i]);
      }
    }

    const out = this.outputGain ? this.outputGain.gain.value : 1;
    for (let i = 0; i < n; i++) {
      into[i] = 20 * Math.log10(acc[i] * out + 1e-12);
    }
    return into;
  }

  stopSource() {
    if (this.source) {
      try {
        this.source.onended = null;
        this.source.stop();
      } catch {
        /* already stopped */
      }
      try {
        this.source.disconnect();
      } catch {
        /* ignore */
      }
      this.source = null;
    }
    this.playing = false;
  }

  async stopMic() {
    if (this.mediaStream) {
      for (const t of this.mediaStream.getTracks()) t.stop();
      this.mediaStream = null;
    }
  }

  async playBuffer(buffer, offset = 0, mode = "file") {
    await this.ensure();
    this.stopSource();
    const src = this.ctx.createBufferSource();
    src.buffer = buffer;
    src.loop = true;
    src.connect(this.inputGain);
    const startOffset = clamp(offset, 0, Math.max(0, buffer.duration - 0.01));
    src.start(0, startOffset);
    this.startedAt = this.ctx.currentTime - startOffset;
    this.pausedAt = startOffset;
    this.source = src;
    this.playing = true;
    this.mode = mode;
    src.onended = () => {
      if (this.source === src) {
        this.playing = false;
        this.source = null;
        this.onEnded?.();
      }
    };
  }

  currentTime() {
    const dur = this.activeDuration();
    if (!this.ctx || !dur) return this.pausedAt || 0;
    if (!this.playing) return this.pausedAt;
    const t = this.ctx.currentTime - this.startedAt;
    return ((t % dur) + dur) % dur;
  }

  activeDuration() {
    if (this.mode === "file" && this.fileBuffer) return this.fileBuffer.duration;
    if (this.mode === "demo" && this.demoBuffer) return this.demoBuffer.duration;
    return 0;
  }

  async playFile(offset) {
    if (!this.fileBuffer) return;
    await this.playBuffer(this.fileBuffer, offset ?? this.pausedAt, "file");
  }

  pause() {
    this.pausedAt = this.currentTime();
    this.stopSource();
  }

  async togglePlay() {
    await this.ensure();
    if (this.playing) {
      if (this.mode === "file" || this.mode === "demo") this.pause();
      else this.stopSource();
      return;
    }
    if (this.mode === "file") return this.playFile();
    if (this.mode === "demo") return this.playDemo(this.pausedAt);
    if (this.mode === "pink") return this.playPink();
    if (this.mode === "white") return this.playWhite();
    if (this.mode === "sine") return this.playSine();
    if (this.fileBuffer) return this.playFile();
    return this.playDemo();
  }

  async playPink() {
    await this.ensure();
    await this.playBuffer(this.pinkBuffer, 0, "pink");
  }

  async playWhite() {
    await this.ensure();
    await this.playBuffer(this.whiteBuffer, 0, "white");
  }

  async playSine(freq = 1000) {
    await this.ensure();
    this.stopSource();
    const osc = this.ctx.createOscillator();
    const g = this.ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    g.gain.value = 0.08;
    osc.connect(g);
    g.connect(this.inputGain);
    osc.start();
    this.source = osc;
    this.playing = true;
    this.mode = "sine";
    this.startedAt = this.ctx.currentTime;
  }

  async playMic() {
    await this.ensure();
    this.stopSource();
    await this.stopMic();
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false },
    });
    this.mediaStream = stream;
    const src = this.ctx.createMediaStreamSource(stream);
    src.connect(this.inputGain);
    this.source = src;
    this.playing = true;
    this.mode = "mic";
  }

  async decodeFile(file) {
    await this.ensure();
    const buf = await file.arrayBuffer();
    const audio = await this.ctx.decodeAudioData(buf.slice(0));
    this.fileBuffer = audio;
    this.fileName = file.name;
    this.pausedAt = 0;
    this.mode = "file";
    return audio;
  }

  async playDemo(offset = 0) {
    await this.ensure();
    if (!this.demoBuffer) this.demoBuffer = await renderDemo(this.ctx.sampleRate);
    await this.playBuffer(this.demoBuffer, offset, "demo");
  }

  seek(t) {
    const dur = this.activeDuration();
    if (!dur) return;
    const next = clamp(t, 0, dur);
    if (this.playing) {
      if (this.mode === "file") this.playFile(next);
      else if (this.mode === "demo") this.playDemo(next);
    } else {
      this.pausedAt = next;
    }
  }
}

export function freqToX(freq, width) {
  const t = Math.log(clamp(freq, MIN_F, MAX_F) / MIN_F) / Math.log(MAX_F / MIN_F);
  return t * width;
}

export function xToFreq(x, width) {
  const t = clamp(x / width, 0, 1);
  return MIN_F * Math.pow(MAX_F / MIN_F, t);
}

export function dbToY(db, height, range) {
  const t = (range - db) / (range * 2);
  return clamp(t, 0, 1) * height;
}

export function yToDb(y, height, range) {
  const t = clamp(y / height, 0, 1);
  return range - t * range * 2;
}

export function formatFreq(f) {
  if (f >= 10000) return `${(f / 1000).toFixed(1)} kHz`;
  if (f >= 1000) return `${(f / 1000).toFixed(2)} kHz`;
  if (f >= 100) return `${f.toFixed(0)} Hz`;
  return `${f.toFixed(1)} Hz`;
}

export function formatDb(db) {
  const n = Math.abs(db) < 0.05 ? 0 : db;
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)} dB`;
}

export function formatQ(q) {
  return q.toFixed(2);
}

export function formatTime(s) {
  if (!Number.isFinite(s) || s < 0) s = 0;
  const m = Math.floor(s / 60);
  const sec = s - m * 60;
  return `${m}:${sec.toFixed(1).padStart(4, "0")}`;
}

async function renderDemo(sampleRate) {
  const bpm = 96;
  const beats = 8;
  const duration = (beats * 60) / bpm;
  const ctx = new OfflineAudioContext(2, Math.floor(duration * sampleRate), sampleRate);
  const master = ctx.createGain();
  master.gain.value = 0.9;
  master.connect(ctx.destination);

  const beat = 60 / bpm;
  const noiseBuf = makeWhite(ctx);

  function envGain(t, a, d, v = 1) {
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(v, t + a);
    g.gain.exponentialRampToValueAtTime(0.0008, t + d);
    return g;
  }

  for (let i = 0; i < beats; i++) {
    const t = i * beat + 0.02;
    const osc = ctx.createOscillator();
    const g = envGain(t, 0.004, 0.32, 0.95);
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.setValueAtTime(180, t);
    lp.frequency.exponentialRampToValueAtTime(55, t + 0.18);
    osc.type = "sine";
    osc.frequency.setValueAtTime(150, t);
    osc.frequency.exponentialRampToValueAtTime(42, t + 0.14);
    osc.connect(lp);
    lp.connect(g);
    g.connect(master);
    osc.start(t);
    osc.stop(t + 0.4);
  }

  for (const i of [1, 3, 5, 7]) {
    const t = i * beat + 0.02;
    const noise = ctx.createBufferSource();
    noise.buffer = noiseBuf;
    const bp = ctx.createBiquadFilter();
    bp.type = "bandpass";
    bp.frequency.value = 1800;
    bp.Q.value = 0.7;
    const hp = ctx.createBiquadFilter();
    hp.type = "highpass";
    hp.frequency.value = 600;
    const g = envGain(t, 0.002, 0.22, 0.45);
    noise.connect(hp);
    hp.connect(bp);
    bp.connect(g);
    g.connect(master);
    noise.start(t);
    noise.stop(t + 0.28);

    const body = ctx.createOscillator();
    body.type = "triangle";
    body.frequency.setValueAtTime(220, t);
    body.frequency.exponentialRampToValueAtTime(140, t + 0.12);
    const bg = envGain(t, 0.002, 0.16, 0.22);
    body.connect(bg);
    bg.connect(master);
    body.start(t);
    body.stop(t + 0.2);
  }

  for (let i = 0; i < beats * 2; i++) {
    const t = i * (beat / 2) + 0.02;
    const noise = ctx.createBufferSource();
    noise.buffer = noiseBuf;
    const hp = ctx.createBiquadFilter();
    hp.type = "highpass";
    hp.frequency.value = 7000;
    const g = envGain(t, 0.001, i % 2 === 0 ? 0.07 : 0.04, i % 2 === 0 ? 0.16 : 0.1);
    noise.connect(hp);
    hp.connect(g);
    g.connect(master);
    noise.start(t);
    noise.stop(t + 0.1);
  }

  const notes = [36, 36, 39, 36, 43, 41, 39, 36];
  for (let i = 0; i < notes.length; i++) {
    const t = i * beat + 0.02;
    const freq = 440 * Math.pow(2, (notes[i] - 69) / 12);
    const osc = ctx.createOscillator();
    osc.type = "sawtooth";
    osc.frequency.value = freq;
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.setValueAtTime(420, t);
    lp.frequency.linearRampToValueAtTime(180, t + beat * 0.8);
    lp.Q.value = 1.1;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(0.18, t + 0.03);
    g.gain.linearRampToValueAtTime(0.08, t + beat * 0.7);
    g.gain.linearRampToValueAtTime(0.0001, t + beat);
    osc.connect(lp);
    lp.connect(g);
    g.connect(master);
    osc.start(t);
    osc.stop(t + beat);
  }

  const padNotes = [63, 67, 70, 74];
  for (const midi of padNotes) {
    const osc = ctx.createOscillator();
    osc.type = "sawtooth";
    osc.frequency.value = 440 * Math.pow(2, (midi - 69) / 12);
    const det = ctx.createOscillator();
    det.type = "sawtooth";
    det.frequency.value = osc.frequency.value * 1.006;
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.value = 2200;
    const g = ctx.createGain();
    g.gain.value = 0.035;
    osc.connect(lp);
    det.connect(lp);
    lp.connect(g);
    g.connect(master);
    osc.start(0);
    det.start(0);
    osc.stop(duration);
    det.stop(duration);
  }

  return ctx.startRendering();
}

export { MIN_F, MAX_F };
