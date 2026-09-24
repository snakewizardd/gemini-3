/* ════════════════════════════════════════════════════════════════════════════
   FILAMENT — String Engine (extended)
   Copy-and-extend of the Karplus–Strong AudioWorklet in opus/hendrix.html.
   Extensions for this work:
     • seeded PRNG (mulberry32) instead of Math.random → bit-reproducible renders
     • T60-based loop gain per note, smoothed damping (no clicks on mutes)
     • triangle+noise pick excitation, pick-click transient scaled by velocity
     • shaped glides: 'lin' (slides), 'ease' (finger bends), 'smooth' (releases)
     • vibrato with upward-only ('up', fretted finger vibrato) or symmetric ('sym',
       vibrato on a held bend) modes, phase reset at onset so visuals can mirror it
     • pickup-position comb (neck / middle Strat response)
     • events accepted up-front (processorOptions, offline) or streamed (port, live)
   Works with any BaseAudioContext (AudioContext or OfflineAudioContext).
   ════════════════════════════════════════════════════════════════════════════ */
(function (global) {
'use strict';

const WORKLET_SRC = `
const SR = sampleRate, TAU = 6.283185307179586, LN2_12 = Math.LN2 / 12, LN1000 = Math.log(0.001);
function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const ease = (c, u) => c === 'lin' ? u : c === 'smooth' ? u * u * (3 - 2 * u) : 1 - Math.pow(1 - u, 2.2);
class Voice {
  constructor(len) {
    this.m = len - 1; this.buf = new Float32Array(len); this.exc = new Float32Array(len);
    this.w = 0; this.lnP = Math.log(SR / 110); this.S = 0.35; this.g = 0; this.gT = 0; this.prev = 0;
    this.eL = 0; this.eI = 0;
    this.gA = 0; this.gB = 0; this.gN = 0; this.gI = 0; this.gC = 'ease';
    this.vd = 0; this.vdT = 0; this.vr = 5.5; this.ph = 0; this.vk = 0.0004; this.vm = 1;
    this.cA = 0; this.cI = 0; this.cN = 0; this.cz = 0;
  }
}
class FilamentString extends AudioWorkletProcessor {
  constructor(opt) {
    super();
    const o = (opt && opt.processorOptions) || {};
    let len = 1; while (len < SR / 20) len <<= 1;
    this.maxP = len - 8; this.V = [];
    const nv = o.voices || 6; for (let i = 0; i < nv; i++) this.V.push(new Voice(len));
    this.rnd = mulberry32(o.seed || 1);
    this.pu = o.pickup || 0; this.puMix = o.pickupMix || 0; this.outGain = o.gain || 0.5;
    this.q = (o.events || []).slice().sort((a, b) => a.t - b.t); this.qi = 0;
    this.port.onmessage = e => {
      const a = e.data; if (!a || !a.length) return;
      const rest = this.q.slice(this.qi); for (let i = 0; i < a.length; i++) rest.push(a[i]);
      rest.sort((x, y) => x.t - y.t); this.q = rest; this.qi = 0;
    };
  }
  lnPer(f) { return Math.log(Math.min(this.maxP, Math.max(4, SR / f))); }
  gFor(v, T) {
    // loop gain so the FUNDAMENTAL decays by 60 dB in T seconds: compensate the two-point loss filter
    const P = Math.exp(v.lnP), f = SR / P, w = TAU / P, S = v.S;
    const H = Math.sqrt((1 - S + S * Math.cos(w)) ** 2 + (S * Math.sin(w)) ** 2);
    return Math.min(0.99999, Math.exp(LN1000 / Math.max(1, f * T)) / H);
  }
  excite(v, amp, bright, pp, noiseMix) {
    // Plucked-string initial shape: triangle (apex at pick position) blended with
    // pick-position-combed noise, then a brightness low-pass (soft neck pick vs hard attack).
    const L = Math.max(8, Math.min(this.maxP, Math.round(Math.exp(v.lnP))));
    const e = v.exc, z = this.tmp || (this.tmp = new Float32Array(e.length)), R = this.rnd;
    const apex = Math.max(1, Math.min(L - 2, Math.round(L * pp)));
    let lp = 0, triMean = 0;
    for (let i = 0; i < L; i++) { lp += 0.5 * ((R() * 2 - 1) - lp); z[i] = lp; triMean += i <= apex ? i / apex : (L - i) / (L - apex); }
    triMean /= L;
    const a = 0.12 + 0.86 * bright; let f = 0;
    for (let i = 0; i < L; i++) {
      const tri = (i <= apex ? i / apex : (L - i) / (L - apex)) - triMean;
      const comb = z[i] - (i >= apex ? z[i - apex] : 0);
      const x = (1 - noiseMix) * tri * 1.4 + noiseMix * comb * 1.1;
      f += a * (x - f); e[i] = f * amp;
    }
    v.eL = L; v.eI = 0;
  }
  glide(v, f, sec, curve) {
    v.gA = v.lnP; v.gB = this.lnPer(f); v.gN = Math.max(1, Math.round(sec * SR)); v.gI = 0; v.gC = curve || 'ease';
  }
  handle(ev) {
    const v = this.V[ev.v]; if (!v) return;
    switch (ev.type) {
      case 'pluck': {
        for (let i = 0; i <= v.m; i++) v.buf[i] *= 0.25;         // pick meets a ringing string
        v.lnP = this.lnPer(ev.f); v.gN = 0; v.vd = 0; v.vdT = 0; v.S = ev.s ?? 0.3;
        v.g = v.gT = this.gFor(v, ev.T ?? 3);
        this.excite(v, ev.a, ev.b ?? 0.7, ev.p ?? 0.13, ev.n ?? 0.35);
        v.cA = (ev.k ?? 0) * ev.a; v.cN = Math.round(SR * 0.0016); v.cI = 0; v.cz = 0;
        break;
      }
      case 'legato':
        this.glide(v, ev.f, ev.d ?? 0.004, 'lin');
        if (ev.a > 0) this.excite(v, ev.a, ev.b ?? 0.9, 0.5, 0.6);
        if (ev.T) v.gT = this.gFor(v, ev.T);
        break;
      case 'bend': this.glide(v, ev.f, ev.d, ev.c); break;
      case 'damp': v.gT = this.gFor(v, ev.T ?? 0.08); break;
      case 'vib':
        if (v.vd < 1e-3 && ev.d > 0) v.ph = 0;
        v.vdT = ev.d; v.vr = ev.r ?? 5.5; v.vm = ev.m === 'sym' ? 0 : 1;
        v.vk = 1 - Math.exp(-1 / (Math.max(0.005, ev.k ?? 0.25) * SR));
        break;
    }
  }
  process(inputs, outputs) {
    const out = outputs[0][0]; if (!out) return true;
    const n = out.length, V = this.V, R = this.rnd;
    for (let i = 0; i < n; i++) {
      const t = currentTime + i / SR;
      while (this.qi < this.q.length && this.q[this.qi].t <= t) this.handle(this.q[this.qi++]);
      let s = 0;
      for (let k = 0; k < V.length; k++) {
        const v = V[k];
        if (v.gI < v.gN) { v.gI++; v.lnP = v.gA + (v.gB - v.gA) * ease(v.gC, v.gI / v.gN); }
        v.g += (v.gT - v.g) * 0.0015;
        let lp = v.lnP;
        if (v.vdT > 0 || v.vd > 1e-4) {
          v.vd += (v.vdT - v.vd) * v.vk;
          v.ph += TAU * v.vr / SR; if (v.ph > TAU) v.ph -= TAU;
          const osc = v.vm ? (0.5 - 0.5 * Math.cos(v.ph)) : 0.5 * Math.sin(v.ph);
          lp -= v.vd * osc * LN2_12;
        }
        let P = Math.exp(lp) - v.S;
        if (P > this.maxP) P = this.maxP; else if (P < 3) P = 3;
        const rp = v.w - P, ip = Math.floor(rp), fr = rp - ip, m = v.m, b = v.buf;
        const xm = b[(ip - 1) & m], x0 = b[ip & m], x1 = b[(ip + 1) & m], x2 = b[(ip + 2) & m];
        const c1 = 0.5 * (x1 - xm), c2 = xm - 2.5 * x0 + 2 * x1 - 0.5 * x2, c3 = 0.5 * (x2 - xm) + 1.5 * (x0 - x1);
        const d = ((c3 * fr + c2) * fr + c1) * fr + x0;
        let y = v.g * ((1 - v.S) * d + v.S * v.prev); v.prev = d;
        if (v.eI < v.eL) y += v.exc[v.eI++];
        if (y > 1) y = 1 + 0.5 * Math.tanh(y - 1); else if (y < -1) y = -1 - 0.5 * Math.tanh(-y - 1);
        if (y < 1e-20 && y > -1e-20) y = 0;
        b[v.w] = y; v.w = (v.w + 1) & m;
        let o = y;
        if (this.puMix > 0) { const D = Math.max(1, Math.round(P * this.pu)); o = y - this.puMix * b[(v.w - 1 - D) & m]; }
        if (v.cI < v.cN) { const u = v.cI++ / v.cN; v.cz += 0.55 * ((R() * 2 - 1) - v.cz); o += v.cA * v.cz * (1 - u) * (1 - u); }
        s += o;
      }
      out[i] = s * this.outGain;
    }
    return true;
  }
}
registerProcessor('filament-string', FilamentString);

// Deterministic hall: pre-delay → 4 Schroeder all-pass diffusers → 8-line FDN
// (Householder feedback, per-line one-pole damping, T60-derived gains) → stereo taps.
class FilamentVerb extends AudioWorkletProcessor {
  constructor(opt) {
    super();
    const o = (opt && opt.processorOptions) || {};
    const k = SR / 48000, size = o.size || 1.6, rt = o.rt60 || 2.8;
    this.damp = o.damp ?? 0.32; this.gain = o.gain ?? 0.3;
    this.pre = new Float32Array(4096); this.preN = Math.max(1, Math.round((o.predelay ?? 0.018) * SR)); this.pw = 0;
    this.ap = [229, 173, 611, 447].map(n => ({ b: new Float32Array(Math.round(n * k)), i: 0 }));
    const L = [1557, 1617, 1491, 1422, 1277, 1356, 1188, 1116].map(n => Math.round(n * k * size));
    this.lines = L.map(n => ({ b: new Float32Array(n), i: 0, g: Math.pow(10, -3 * n / (SR * rt)), lp: 0 }));
  }
  process(inputs, outputs) {
    const inp = inputs[0], out = outputs[0], oL = out[0], oR = out[1] || out[0];
    const n = oL.length, a = inp && inp[0], b = inp && inp[1], lines = this.lines, ap = this.ap, d = this.damp;
    const y = this.y || (this.y = new Float64Array(8));
    for (let i = 0; i < n; i++) {
      let x = (a ? a[i] : 0) + (b ? b[i] : (a ? a[i] : 0));
      x *= 0.5;
      const pr = this.pre; pr[this.pw] = x; x = pr[(this.pw - this.preN + 4096) & 4095]; this.pw = (this.pw + 1) & 4095;
      for (let j = 0; j < 4; j++) { const A = ap[j], z = A.b[A.i]; const v = x + 0.7 * z; A.b[A.i] = v; x = z - 0.7 * v; A.i = (A.i + 1) % A.b.length; }
      let sum = 0;
      for (let j = 0; j < 8; j++) { const Ln = lines[j]; let s = Ln.b[Ln.i]; Ln.lp = s + d * (Ln.lp - s); s = Ln.lp * Ln.g; y[j] = s; sum += s; }
      sum *= 0.25;
      for (let j = 0; j < 8; j++) {
        const Ln = lines[j]; let v = y[j] - sum + (j & 1 ? -x : x) * 0.35;
        if (v < 1e-20 && v > -1e-20) v = 0;
        Ln.b[Ln.i] = v; Ln.i = (Ln.i + 1) % Ln.b.length;
      }
      oL[i] = (y[0] - y[2] + y[4] - y[6]) * this.gain;
      oR[i] = (y[1] - y[3] + y[5] - y[7]) * this.gain;
    }
    return true;
  }
}
registerProcessor('filament-verb', FilamentVerb);

// Deterministic summing bus. Web Audio sums a node's fan-in in hash-set order, so three or
// more simultaneous non-zero sources can round differently from run to run. Every
// multi-source mix in FILAMENT goes through here: one source (or two) per input, summed
// in fixed index order.
class FilamentMix extends AudioWorkletProcessor {
  process(inputs, outputs) {
    const out = outputs[0];
    for (let c = 0; c < out.length; c++) out[c].fill(0);
    for (let k = 0; k < inputs.length; k++) {
      const inp = inputs[k]; if (!inp || !inp.length) continue;
      for (let c = 0; c < out.length; c++) {
        const s = inp[Math.min(c, inp.length - 1)], o = out[c];
        for (let i = 0; i < o.length; i++) o[i] += s[i];
      }
    }
    return true;
  }
}
registerProcessor('filament-mix', FilamentMix);
`;

function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

async function loadWorklet(ctx) {
  if (!ctx.audioWorklet) throw new Error('AudioWorklet unsupported (requires a secure context / modern browser).');
  try {
    await ctx.audioWorklet.addModule('data:text/javascript;charset=utf-8,' + encodeURIComponent(WORKLET_SRC));
  } catch (err) {
    const url = URL.createObjectURL(new Blob([WORKLET_SRC], { type: 'text/javascript' }));
    try { await ctx.audioWorklet.addModule(url); } finally { URL.revokeObjectURL(url); }
  }
}

// Tube stage: asymmetric tanh with a bias → even harmonics, soft knee (12AX7-ish preamp).
function tubeCurve(bias) {
  const n = 8192, c = new Float32Array(n), off = Math.tanh(bias);
  let peak = 0;
  for (let i = 0; i < n; i++) {
    const x = i * 2 / (n - 1) - 1;
    const y = Math.tanh(x * 1.0 + bias) - off;
    c[i] = y; peak = Math.max(peak, Math.abs(y));
  }
  for (let i = 0; i < n; i++) c[i] /= peak;
  return c;
}
function softCurve(k) {
  const n = 4096, c = new Float32Array(n), d = Math.tanh(k);
  for (let i = 0; i < n; i++) { const x = i * 2 / (n - 1) - 1; c[i] = Math.tanh(k * x) / d; }
  return c;
}
/* Build the full FILAMENT signal graph on a BaseAudioContext.
   opts.stems (offline): route master L/R → destination ch0/1 and dry lead → ch2. */
async function build(ctx, opts = {}) {
  const seed = opts.seed >>> 0 || 1;
  const rnd = mulberry32(seed ^ 0x9e3779b9);
  await loadWorklet(ctx);
  const N = {};
  const biq = (type, f, Q = 0.7, g = 0) => { const b = ctx.createBiquadFilter(); b.type = type; b.frequency.value = f; b.Q.value = Q; b.gain.value = g; return b; };
  const gain = v => { const g = ctx.createGain(); g.gain.value = v; return g; };
  const shaper = (c, os = '4x') => { const s = ctx.createWaveShaper(); s.curve = c; s.oversample = os; return s; };
  const pan = p => { const s = ctx.createStereoPanner(); s.pan.value = p; return s; };
  const chain = (...ns) => { for (let i = 0; i < ns.length - 1; i++) ns[i].connect(ns[i + 1]); return ns[ns.length - 1]; };
  const ev = opts.events || { lead: [], rhythm: [], bass: [] };
  const mk = (name, voices, s, extra) => new AudioWorkletNode(ctx, 'filament-string', {
    numberOfInputs: 0, numberOfOutputs: 1, outputChannelCount: [1],
    processorOptions: Object.assign({ voices, seed: (seed * 31 + s) >>> 0, events: ev[name] || [] }, extra)
  });
  N.lead = mk('lead', 4, 11, { pickup: 0.22, pickupMix: 0.35, gain: 0.55 });
  N.rhythm = mk('rhythm', 6, 23, { pickup: 0.16, pickupMix: 0.25, gain: 0.32 });
  N.bass = mk('bass', 2, 37, { pickup: 0.2, pickupMix: 0.3, gain: 0.7 });

  const mix = (nIn, outCh) => new AudioWorkletNode(ctx, 'filament-mix', { numberOfInputs: nIn, numberOfOutputs: 1, outputChannelCount: [outCh] });
  const BUS = { lead: 0, rhythm: 1, bass: 2, orgL: 3, orgR: 4, drums: 5, echo: 6, rev: 7 };
  const SEND = { lead: 0, rhythm: 1, organ: 2, drums: 3, echo: 4 };

  // Master bus (fixed-order deterministic sum)
  N.bus = mix(8, 2);
  // bus tilt: trim sub rumble, open the top a little (the 'mastering EQ' lives in the engine)
  N.busLo = biq('lowshelf', 70, 0.7, -2.5); N.busHi = biq('highshelf', 3600, 0.7, 3.5); N.busBox = biq('peaking', 380, 0.9, -2);
  N.glue = ctx.createDynamicsCompressor();
  N.glue.threshold.value = -20; N.glue.knee.value = 10; N.glue.ratio.value = 2.2; N.glue.attack.value = 0.02; N.glue.release.value = 0.3;
  N.master = gain(opts.masterGain ?? 0.9);
  chain(N.bus, N.busLo, N.busBox, N.busHi, N.glue, N.master);

  // Space: plate-ish hall + tape echo (shared sends)
  N.rev = new AudioWorkletNode(ctx, 'filament-verb', {
    numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [2], channelCount: 2, channelCountMode: 'explicit',
    processorOptions: { rt60: 2.9, size: 1.6, damp: 0.34, predelay: 0.018, gain: 0.32 }
  });
  N.revIn = mix(5, 2); N.revHP = biq('highpass', 180); N.revOut = gain(0.9);
  chain(N.revIn, N.revHP, N.rev, N.revOut); N.revOut.connect(N.bus, 0, BUS.rev);
  N.echo = ctx.createDelay(2); N.echo.delayTime.value = opts.echoTime ?? 0.5556;
  N.echoIn = gain(1); N.echoLP = biq('lowpass', 2600); N.echoHP = biq('highpass', 300);
  N.echoSat = shaper(softCurve(1.3), '2x'); N.echoFb = gain(0.3); N.echoOut = gain(0.55); N.echoPan = pan(-0.3);
  chain(N.echoIn, N.echo, N.echoLP, N.echoHP, N.echoSat); N.echoSat.connect(N.echoFb); N.echoFb.connect(N.echo);
  chain(N.echoSat, N.echoOut, N.echoPan); N.echoPan.connect(N.bus, 0, BUS.echo); N.echoOut.connect(N.revIn, 0, SEND.echo);
  N.wow = ctx.createOscillator(); N.wow.frequency.value = 0.31; N.wowD = gain(0.0018); chain(N.wow, N.wowD, N.echo.delayTime); N.wow.start(0);

  // LEAD: Strat → pickup blend (neck/middle) → tone knob → tube preamp → tone stack → power tube → cab
  N.leadHP = biq('highpass', 85);
  N.neck = gain(1); N.neckLP = biq('lowpass', 3300, 0.9); N.neckBody = biq('peaking', 260, 1.0, 1.2);
  N.middle = gain(0); N.midPk = biq('peaking', 3900, 1.4, 4); N.midLP = biq('lowpass', 6500, 0.7);
  N.pickSum = gain(1);
  N.leadHP.connect(N.neck); chain(N.neck, N.neckLP, N.neckBody, N.pickSum);
  N.leadHP.connect(N.middle); chain(N.middle, N.midPk, N.midLP, N.pickSum);
  N.tone = biq('lowpass', 5200, 0.9);
  N.drive = gain(1.6); N.tube = shaper(tubeCurve(0.28)); N.post = gain(0.8);
  N.stackLo = biq('lowshelf', 180, 0.7, 1.5); N.stackMid = biq('peaking', 750, 0.8, 2.5); N.stackHi = biq('highshelf', 3200, 0.7, -1.5);
  N.power = shaper(softCurve(1.6)); N.powerIn = gain(0.9);
  N.cabHP = biq('highpass', 95); N.cabRes = biq('peaking', 115, 1.1, 3); N.cabPres = biq('peaking', 2700, 0.9, 4); N.cabNotch = biq('peaking', 4600, 2.5, -4); N.cabLP = biq('lowpass', 6800, 0.75);
  N.leadOut = gain(0.62); N.leadPan = pan(0.1);
  chain(N.lead, N.leadHP);
  chain(N.pickSum, N.tone, N.drive, N.tube, N.post, N.stackLo, N.stackMid, N.stackHi, N.powerIn, N.power, N.cabHP, N.cabRes, N.cabPres, N.cabNotch, N.cabLP, N.leadOut, N.leadPan); N.leadPan.connect(N.bus, 0, BUS.lead);
  N.leadRev = gain(0.28); N.leadEcho = gain(0.16);
  N.leadOut.connect(N.leadRev); N.leadRev.connect(N.revIn, 0, SEND.lead);
  N.leadOut.connect(N.leadEcho); N.leadEcho.connect(N.echoIn);

  // RHYTHM: clean Strat (middle/bridge-ish), light tube warmth, left of centre
  N.rhHP = biq('highpass', 140); N.rhLP = biq('lowpass', 7200, 0.7); N.rhDrive = gain(1.1); N.rhTube = shaper(tubeCurve(0.18));
  N.rhCab = biq('peaking', 3000, 0.8, 3.5); N.rhBox = biq('peaking', 420, 1.0, -2.5); N.rhOut = gain(0.5); N.rhPan = pan(-0.34);
  chain(N.rhythm, N.rhHP, N.rhBox, N.rhLP, N.rhDrive, N.rhTube, N.rhCab, N.rhOut, N.rhPan); N.rhPan.connect(N.bus, 0, BUS.rhythm);
  N.rhRev = gain(0.3); N.rhOut.connect(N.rhRev); N.rhRev.connect(N.revIn, 0, SEND.rhythm);

  // BASS: fingered string, round and centred
  N.bsLP = biq('lowpass', 1800, 0.8); N.bsLow = biq('highpass', 36, 0.7); N.bsDrive = gain(1.3); N.bsSh = shaper(softCurve(1.2), '2x'); N.bsOut = gain(0.62);
  chain(N.bass, N.bsLP, N.bsLow, N.bsDrive, N.bsSh, N.bsOut); N.bsOut.connect(N.bus, 0, BUS.bass);

  // ORGAN (tonewheel drawbars, additive) → Leslie-style tremolo + slight stereo spread
  N.orgIn = mix(16, 1); N.orgSlot = 0; N.orgLP = biq('lowpass', 3200, 0.6);
  N.orgTrem = gain(1); N.orgLFO = ctx.createOscillator(); N.orgLFO.frequency.value = 0.8; N.orgLFOd = gain(0.12);
  chain(N.orgLFO, N.orgLFOd, N.orgTrem.gain); N.orgLFO.start(0);
  N.orgOut = gain(0.0); N.orgL = pan(-0.55); N.orgR = pan(0.55); N.orgDel = ctx.createDelay(0.05); N.orgDel.delayTime.value = 0.011;
  chain(N.orgIn, N.orgLP, N.orgTrem, N.orgOut); N.orgOut.connect(N.orgL); N.orgOut.connect(N.orgDel); N.orgDel.connect(N.orgR);
  N.orgL.connect(N.bus, 0, BUS.orgL); N.orgR.connect(N.bus, 0, BUS.orgR); N.orgRev = gain(0.4); N.orgOut.connect(N.orgRev); N.orgRev.connect(N.revIn, 0, SEND.organ);

  // DRUMS (synthesized; seeded noise)
  N.drumMix = mix(16, 1); N.drumSlot = 0;
  N.drums = gain(0.55); N.drumRev = gain(0.16); N.drumMix.connect(N.drums);
  N.drums.connect(N.bus, 0, BUS.drums); N.drums.connect(N.drumRev); N.drumRev.connect(N.revIn, 0, SEND.drums);
  N.noise = ctx.createBuffer(1, ctx.sampleRate * 3, ctx.sampleRate);
  { const d = N.noise.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = rnd() * 2 - 1; }

  // Outputs
  if (opts.stems) {
    N.merge = ctx.createChannelMerger(3);
    N.split = ctx.createChannelSplitter(2);
    N.master.connect(N.split); N.split.connect(N.merge, 0, 0); N.split.connect(N.merge, 1, 1);
    N.leadDry = gain(1); N.lead.connect(N.leadDry); N.leadDry.connect(N.merge, 0, 2);
    N.merge.connect(ctx.destination);
  } else {
    N.safety = ctx.createDynamicsCompressor();
    N.safety.threshold.value = -3; N.safety.knee.value = 0; N.safety.ratio.value = 20; N.safety.attack.value = 0.002; N.safety.release.value = 0.12;
    chain(N.master, N.safety, ctx.destination);
  }

  const noiseSrc = (t, dur) => { const s = ctx.createBufferSource(); s.buffer = N.noise; s.start(t, (t * 7.31) % 2.2, dur); return s; };
  // each drum hit sums its (at most two) components in its own gain, then takes a mixer slot
  const hitBus = () => { const g = ctx.createGain(); g.connect(N.drumMix, 0, N.drumSlot); N.drumSlot = (N.drumSlot + 1) % 16; return g; };
  const env = (node, t, peak, dec, dest, att = 0.001) => {
    const g = ctx.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(peak, t + att);
    g.gain.exponentialRampToValueAtTime(0.0005, t + att + dec); g.gain.setValueAtTime(0, t + att + dec + 0.01);
    node.connect(g); g.connect(dest); return g;
  };
  const Drum = {
    kick(t, v) {
      const h = hitBus();
      const o = ctx.createOscillator(); o.frequency.setValueAtTime(120, t); o.frequency.exponentialRampToValueAtTime(54, t + 0.07);
      env(o, t, v * 0.72, 0.3, h); o.start(t); o.stop(t + 0.5);
      const n = noiseSrc(t, 0.02), lp = biq('lowpass', 3200); n.connect(lp); env(lp, t, v * 0.3, 0.014, h);
    },
    snare(t, v) {
      const h = hitBus();
      const n = noiseSrc(t, 0.3), bp = biq('bandpass', 2600, 0.6); n.connect(bp); env(bp, t, v * 0.55, 0.2, h);
      const o = ctx.createOscillator(); o.type = 'triangle'; o.frequency.setValueAtTime(205, t); o.frequency.exponentialRampToValueAtTime(165, t + 0.08);
      env(o, t, v * 0.42, 0.11, h); o.start(t); o.stop(t + 0.15);
    },
    rim(t, v) {
      const h = hitBus();
      const o = ctx.createOscillator(); o.type = 'square'; o.frequency.value = 1650; const bp = biq('bandpass', 1700, 6); o.connect(bp);
      env(bp, t, v * 0.32, 0.035, h); o.start(t); o.stop(t + 0.06);
      const n = noiseSrc(t, 0.02), hp = biq('highpass', 3000); n.connect(hp); env(hp, t, v * 0.12, 0.015, h);
    },
    hat(t, v, open) {
      const h = hitBus();
      const dec = open ? 0.35 : 0.05, n = noiseSrc(t, dec + 0.05), hp = biq('highpass', 7800), pk = biq('peaking', 10500, 1.2, 4);
      n.connect(hp); hp.connect(pk); env(pk, t, v * 0.3, dec, h);
    },
    ride(t, v) {
      const h = hitBus();
      const n = noiseSrc(t, 0.9), hp = biq('highpass', 5200), bp = biq('peaking', 7200, 2, 6); n.connect(hp); hp.connect(bp); env(bp, t, v * 0.17, 0.75, h);
      const o = ctx.createOscillator(); o.type = 'sine'; o.frequency.value = 3920; env(o, t, v * 0.02, 0.4, h); o.start(t); o.stop(t + 0.5);
    },
    tom(t, f, v) {
      const h = hitBus();
      const o = ctx.createOscillator(); o.frequency.setValueAtTime(f * 1.5, t); o.frequency.exponentialRampToValueAtTime(f, t + 0.12);
      env(o, t, v * 0.7, 0.45, h); o.start(t); o.stop(t + 0.55);
      const n = noiseSrc(t, 0.05), bp = biq('bandpass', f * 4, 1); n.connect(bp); env(bp, t, v * 0.15, 0.04, h);
    },
    crash(t, v, dec = 2.4) {
      const h = hitBus();
      const n = noiseSrc(t, dec + 0.2), hp = biq('highpass', 3600), pk = biq('peaking', 6000, 0.8, 3); n.connect(hp); hp.connect(pk); env(pk, t, v * 0.3, dec, h);
    },
    swell(t, dur, v) {
      const n = noiseSrc(t, dur + 0.1), hp = biq('highpass', 4200), g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(v * 0.18, t + dur); g.gain.linearRampToValueAtTime(0, t + dur + 0.08);
      n.connect(hp); hp.connect(g); g.connect(hitBus());
    }
  };
  // Tonewheel drawbars 16' 8' 5?' 4' 2?' 2' as ONE PeriodicWave per note (fundamental = 16' footage)
  const DRAWBARS = [[1, 0.55], [2, 0.8], [3, 0.35], [4, 0.5], [6, 0.2], [8, 0.12]];
  const re = new Float32Array(9), im = new Float32Array(9);
  for (const [h, a] of DRAWBARS) im[h] = a * 0.09;
  N.orgWave = ctx.createPeriodicWave(re, im, { disableNormalization: true });
  function organ(t, dur, midis, v, att = 0.25, rel = 0.6) {
    for (const m of midis) {
      const f = 440 * Math.pow(2, (m - 69) / 12) * 0.5, hold = Math.max(att, dur);
      const g = ctx.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(v, t + att);
      g.gain.setValueAtTime(v, t + hold); g.gain.linearRampToValueAtTime(0, t + hold + rel);
      g.connect(N.orgIn, 0, N.orgSlot); N.orgSlot = (N.orgSlot + 1) % 16;
      const o = ctx.createOscillator(); o.setPeriodicWave(N.orgWave); o.frequency.value = f;
      o.connect(g); o.start(t); o.stop(t + hold + rel + 0.05);
    }
  }
  const PARAMS = {
    leadDrive: N.drive.gain, leadPost: N.post.gain, neck: N.neck.gain, middle: N.middle.gain, tone: N.tone.frequency,
    toneQ: N.tone.Q, echoFb: N.echoFb.gain, leadEcho: N.leadEcho.gain, leadRev: N.leadRev.gain, leadOut: N.leadOut.gain,
    rhythmOut: N.rhOut.gain, rhythmDrive: N.rhDrive.gain, organOut: N.orgOut.gain, organRate: N.orgLFO.frequency,
    drums: N.drums.gain, bassOut: N.bsOut.gain, stackMid: N.stackMid.gain, master: N.master.gain
  };

  // Schedule native-node commands (drums, organ, automation). `off` = context time of song t=0.
  function scheduleNative(cmds, off) {
    for (const c of cmds) {
      const t = c.t + off; if (t < ctx.currentTime) continue;
      switch (c.type) {
        case 'kick': Drum.kick(t, c.v); break;
        case 'snare': Drum.snare(t, c.v); break;
        case 'rim': Drum.rim(t, c.v); break;
        case 'hat': Drum.hat(t, c.v, c.open); break;
        case 'ride': Drum.ride(t, c.v); break;
        case 'tom': Drum.tom(t, c.f, c.v); break;
        case 'crash': Drum.crash(t, c.v, c.dec); break;
        case 'swell': Drum.swell(t, c.dur, c.v); break;
        case 'organ': organ(t, c.dur, c.midis, c.v, c.att, c.rel); break;
        case 'param': {
          const p = PARAMS[c.name]; if (!p) break;
          if (c.tc) p.setTargetAtTime(c.v, t, c.tc); else p.setValueAtTime(c.v, t);
          break;
        }
      }
    }
  }
  // Stream string events to worklets (live mode). Offline events were passed in processorOptions.
  function postStrings(byInst, off) {
    for (const k of ['lead', 'rhythm', 'bass']) {
      const a = byInst[k]; if (!a || !a.length) continue;
      N[k].port.postMessage(a.map(e => Object.assign({}, e, { t: e.t + off })));
    }
  }
  return { N, scheduleNative, postStrings, PARAMS };
}

global.FilamentEngine = { build, WORKLET_SRC, mulberry32 };
})(typeof window !== 'undefined' ? window : globalThis);
