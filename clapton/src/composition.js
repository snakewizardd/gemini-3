/* ════════════════════════════════════════════════════════════════════════════
   FILAMENT — the score, as code.
   An original 12/8 blues-rock ballad, A minor, dotted-quarter = 72.
   Form: Intro · Verse I · Chorus I · Verse II · Chorus II (break) · Solo (D Dorian)
         · Final Chorus · Outro (+ final chord).
   Everything here is deterministic: performance humanization uses a fixed-seed
   PRNG (SEED below). No Math.random anywhere.

   Motifs (r = reference tonic of the motif's register):
     X  "the sigh"  — (r-2) bent up a whole step into r, held; then the turn
                      r+3 · r · r-2, then the fall to r-5 (slide) with late vibrato.
                      The fall is withheld in the intro and in the last bars, and is
                      finally completed down to the tonic in the very last note.
     Y  "the answer"— consequent that walks down to r-12 (resolves) or stops on r-5 (half cadence).
     Z  "the lift"  — chorus antecedent reaching up: r+3 (blue curl) · (r+5 bent to r+7) · r+10 …
   Articulation carries phrase function:
     • microtonal curls (+25…+35 c) only on blue thirds (C in A minor, F in D Dorian, G over E7♯9)
     • whole-step bends on phrase goals, bend-release-rebend "cries" only at cadential pressure
     • vibrato only on phrase-final sustains, onset delayed, depth grows across the form
     • hammer/pull-offs inside turns; slides into falls
   ════════════════════════════════════════════════════════════════════════════ */
(function (global) {
'use strict';

const SEED = 0x0C1A9707;
const BPM = 72, BEAT = 60 / BPM, PULSE = BEAT / 3, PRE = 1.2, NBARS = 64;
const OPEN = [64, 59, 55, 50, 45, 40];          // e B G D A E  (string 0 = high e)
const hz = m => 440 * Math.pow(2, (m - 69) / 12);
function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const rnd = mulberry32(SEED);
const jit = s => (rnd() * 2 - 1) * s;

// ─── Time map (12 pulses per bar; rubato only where it means something) ──────
const pulseDur = [], pulseStart = [];
for (let b = 0; b < NBARS; b++) for (let p = 0; p < 12; p++) {
  let f = 1;
  if (b === 51 && p >= 6) f = 1.15;                 // the held climax bend breathes
  if (b === 62) f = 1 + 0.42 * (p + 0.5) / 12;      // closing ritardando
  pulseDur.push(PULSE * f);
}
{ let acc = PRE; for (let i = 0; i < pulseDur.length; i++) { pulseStart.push(acc); acc += pulseDur[i]; } pulseStart.push(acc); pulseDur.push(PULSE); }
function T(bar, pulse) {
  const gp = bar * 12 + pulse, i = Math.max(0, Math.min(pulseDur.length - 1, Math.floor(gp)));
  return pulseStart[i] + (gp - i) * pulseDur[i];
}
const D = (bar, p, d) => T(bar, p + d) - T(bar, p);

// ─── Form ─────────────────────────────────────────────────────────────────────
const SECTIONS = [
  { id: 'intro',   name: 'Intro',        bar0: 0,  bar1: 4,  key: 'A minor' },
  { id: 'verse1',  name: 'Verse I',      bar0: 4,  bar1: 12, key: 'A minor' },
  { id: 'chorus1', name: 'Chorus I',     bar0: 12, bar1: 20, key: 'A minor' },
  { id: 'verse2',  name: 'Verse II',     bar0: 20, bar1: 28, key: 'A minor' },
  { id: 'chorus2', name: 'Chorus II',    bar0: 28, bar1: 36, key: 'A minor' },
  { id: 'solo',    name: 'Solo',         bar0: 36, bar1: 52, key: 'D Dorian' },
  { id: 'final',   name: 'Final Chorus', bar0: 52, bar1: 60, key: 'A minor' },
  { id: 'outro',   name: 'Outro',        bar0: 60, bar1: 64, key: 'A minor' }
];
const sectionOf = bar => SECTIONS.find(s => bar >= s.bar0 && bar < s.bar1) || SECTIONS[SECTIONS.length - 1];

const CH = {
  Am7: [45, 52, 55, 60, 64], Am9: [45, 57, 60, 64, 71], Em7: [40, 47, 52, 55, 62, 64],
  Dm9: [50, 53, 60, 64, 69], Dm7: [50, 57, 60, 65], Fmaj7: [41, 53, 57, 60, 64], G6: [43, 50, 55, 59, 64],
  Esus4: [40, 47, 52, 57, 59, 64], E7: [40, 47, 50, 56, 59, 64], E7s9: [40, 52, 56, 62, 67],
  'Am7/G': [43, 52, 57, 60, 64], A7s9: [45, 55, 61, 67, 72],
  sDm7: [50, 57, 60, 65, 69], G9: [43, 53, 59, 62, 69], Bbmaj7: [46, 53, 57, 62], Cadd9: [48, 52, 55, 62, 64],
  Gm7: [43, 53, 58, 62], A7sus4: [45, 52, 57, 62, 64], A7: [45, 52, 55, 61, 64]
};
const ROOT = { Am7: 33, Am9: 33, Em7: 28, Dm9: 38, Dm7: 38, Fmaj7: 29, G6: 31, Esus4: 28, E7: 28, E7s9: 28, 'Am7/G': 31, A7s9: 33,
  sDm7: 38, G9: 31, Bbmaj7: 34, Cadd9: 36, Gm7: 31, A7sus4: 33, A7: 33 };
const PRESSURE = { Am7: 0.08, Am9: 0.06, Em7: 0.3, Dm9: 0.34, Dm7: 0.34, Fmaj7: 0.3, G6: 0.4, Esus4: 0.55, E7: 0.66, E7s9: 0.88,
  'Am7/G': 0.22, A7s9: 0.82, sDm7: 0.14, G9: 0.3, Bbmaj7: 0.55, Cadd9: 0.36, Gm7: 0.42, A7sus4: 0.6, A7: 0.72 };
const DISPLAY = { sDm7: 'Dm7', E7s9: 'E7♯9', A7s9: 'A7♯9', Cadd9: 'C(add9)' };
const VERSE = ['Am7', 'Em7', 'Dm9', 'Am7', 'Fmaj7', 'Dm7', ['Esus4', 'E7'], 'Am7'];
const CHORUS = ['Fmaj7', 'G6', 'Am7', 'Am7/G', 'Dm9', 'Fmaj7', ['Esus4', 'E7'], 'E7s9'];
const PROG = [
  'Am9', 'Am9', 'Fmaj7', ['Esus4', 'E7'],
  ...VERSE, ...CHORUS, ...VERSE, ...CHORUS.slice(0, 7), 'A7s9',
  'sDm7', 'G9', 'sDm7', 'G9', 'Bbmaj7', 'Cadd9', 'sDm7', 'sDm7',
  'Gm7', 'Cadd9', 'Bbmaj7', ['A7sus4', 'A7'], 'sDm7', 'G9', 'Bbmaj7', 'E7s9',
  ...CHORUS,
  'Am9', 'Fmaj7', ['Esus4', 'E7'], 'Am9'
];
const chordAt = (bar, p = 0) => { const c = PROG[bar]; return Array.isArray(c) ? (p < 6 ? c[0] : c[1]) : c; };
const TENSION = [
  0.06, 0.08, 0.12, 0.18,
  0.2, 0.22, 0.25, 0.24, 0.28, 0.3, 0.36, 0.3,
  0.4, 0.43, 0.45, 0.44, 0.5, 0.5, 0.56, 0.6,
  0.32, 0.33, 0.36, 0.35, 0.38, 0.4, 0.46, 0.42,
  0.5, 0.52, 0.55, 0.54, 0.6, 0.6, 0.66, 0.72,
  0.5, 0.5, 0.54, 0.55, 0.6, 0.62, 0.56, 0.6, 0.68, 0.7, 0.76, 0.8, 0.82, 0.88, 0.96, 1.0,
  0.8, 0.74, 0.7, 0.66, 0.62, 0.58, 0.56, 0.55,
  0.35, 0.25, 0.16, 0.08
];

// ═══ LEAD — written phrase by phrase ═══════════════════════════════════════════
const LEAD = [];
let PHRASE = 0, MOTIF = '', ROLE = '', POS = 5;
const phrase = (motif, role, pos) => { PHRASE++; MOTIF = motif; ROLE = role; if (pos != null) POS = pos; };
function L(bar, p, midi, dur, o = {}) { LEAD.push({ bar, p, midi, dur, o, phrase: PHRASE, motif: MOTIF, role: ROLE, pos: POS }); }
const bendTo = (to, at = 0.25, dur = 0.9, c = 'ease') => ({ to, at, dur, c });
const VIB = (at, d, r = 5.3, m = 'up', k = 0.3) => ({ at, d, r, m, k });

// X — the sigh / turn / fall.  opt: s (start pulse), v, fall (hold pulses | 0 = withheld), turnUp, curl, bendDur, vib
function X(bar, r, opt = {}) {
  const s = opt.s ?? 2, v = opt.v ?? 0.6, bd = opt.bendDur ?? 0.9, vd = opt.vib ?? 0.24;
  L(bar, s, r - 2, 3.6, { v, bend: [bendTo(2, 0.25, bd)], vib: VIB(0.55, vd * 1.1, 5.0, 'sym', 0.35) });
  if (opt.sighOnly) return;
  if (opt.turnUp) {
    L(bar, s + 4, r + 3, 1, { v: v * 1.02, curl: opt.curl ? 30 : 0 });
    L(bar, s + 5, r + 5, 1, { v: v * 0.9, art: 'ham' });
    L(bar, s + 6, r + 7, 1, { v: v * 1.05 });
    if (opt.fall === 0) return;
    L(bar, s + 7, r + 3, opt.fall ?? 8, { v: v * 0.95, art: 'slide', slide: 0.16, vib: VIB(0.6, vd * 1.3, 5.2) });
  } else {
    L(bar, s + 4, r + 3, 1, { v: v * 1.04, curl: opt.curl ? 30 : 0 });
    L(bar, s + 5, r, 1, { v: v * 0.9, art: 'pull' });
    L(bar, s + 6, r - 2, 1, { v: v * 0.95 });
    if (opt.fall === 0) return;
    L(bar, s + 7, r - 5, opt.fall ?? 9, { v: v * 0.9, art: 'slide', slide: 0.14, vib: VIB(0.6, vd * 1.3, 5.2) });
  }
}
// Y — the answer. opt.half → stops on r-5 (half cadence); else resolves to r-12.
function Y(bar, r, opt = {}) {
  const v = opt.v ?? 0.55, vd = opt.vib ?? 0.24;
  L(bar, 0, r - 7, 1, { v });
  L(bar, 1, r - 5, 2, { v: v * 0.9, art: 'ham' });
  L(bar, 3, r - 2, 2, { v: v * 1.05 });
  L(bar, 5, r - 5, 1, { v: v * 0.85, art: 'pull' });
  L(bar, 6, r - 9, 2, { v, curl: 28 });
  if (opt.half) {
    L(bar, 8, r - 7, 1, { v: v * 0.9, art: 'ham' });
    L(bar, 9, r - 5, opt.hold ?? 6, { v: v * 0.95, art: 'slide', slide: 0.1, vib: VIB(0.5, vd * 1.4, 5.1) });
  } else {
    L(bar, 8, r - 12, opt.hold ?? 6, { v: v * 0.95, vib: VIB(0.45, vd * 1.2, 5.0) });
  }
}
// Z — the lift (chorus antecedent)
function Z(bar, r, opt = {}) {
  const v = opt.v ?? 0.7, vd = opt.vib ?? 0.3;
  L(bar, 0, r + 3, 2, { v, curl: 30 });
  L(bar, 2, r + 5, 4, { v: v * 1.05, bend: [bendTo(2, 0.2, 0.8)], vib: VIB(0.45, vd, 5.2, 'sym') });
  L(bar, 6, r + 10, 1, { v: v * 1.08 });
  L(bar, 7, r + 7, 1, { v: v * 0.9, art: 'pull' });
  L(bar, 8, r + 5, 1, { v: v * 0.95 });
  L(bar, 9, r + 3, opt.hold ?? 6, { v: v * 0.95, curl: 26, vib: VIB(0.6, vd * 1.1, 5.3) });
}
// cry — bend, release, re-bend (only at cadential pressure)
function cry(bar, p, m, to, dur, v, vd = 0.3) {
  L(bar, p, m, dur, { v, bend: [bendTo(to, 0.2, 0.7), bendTo(0, 2.2, 0.6, 'smooth'), bendTo(to, 3.1, 0.8)], vib: VIB(1.2, vd, 5.4, 'sym') });
}

// ── INTRO (0–3): the sigh alone, unanswered. A question in the dark.
phrase('X', 'call', 5);
X(0, 69, { s: 6, v: 0.42, sighOnly: true, bendDur: 1.3 });
phrase('X', 'call');
X(2, 69, { s: 2, v: 0.5, fall: 0 });                         // sigh + turn, fall withheld
phrase('lead-in', 'bridge');
L(3, 6, 71, 2, { v: 0.45 });
L(3, 8, 68, 6, { v: 0.5, vib: VIB(0.6, 0.18, 4.8) });          // G♯ leading tone into the verse

// ── VERSE I (4–11): clean, restrained, space between phrases
phrase('X', 'call', 5);   X(4, 69, { v: 0.55 });
phrase('Y', 'answer');    Y(6, 69, { v: 0.5, half: true, hold: 8 });
phrase('pickup', 'bridge'); L(7, 9, 57, 1, { v: 0.4 }); L(7, 10, 60, 1, { v: 0.42, art: 'ham' }); L(7, 11, 62, 1, { v: 0.45, art: 'ham' });
phrase('X', 'call');      X(8, 69, { v: 0.6, turnUp: true, fall: 7 });
phrase('Y', 'answer');    L(9, 8, 69, 1, { v: 0.45 }); L(9, 9, 72, 2, { v: 0.5, curl: 30 }); L(9, 11, 74, 1, { v: 0.5, art: 'ham' });
phrase('cry', 'cadence'); cry(10, 0, 71, 1, 6, 0.58, 0.22);
L(10, 6, 68, 6, { v: 0.55, vib: VIB(0.5, 0.22, 5.1) });
phrase('resolve', 'cadence'); L(11, 0, 69, 5, { v: 0.5, art: 'ham', vib: VIB(0.5, 0.2, 5.0) });
L(11, 9, 64, 1, { v: 0.45 }); L(11, 10, 67, 1, { v: 0.5 }); L(11, 11, 71, 1, { v: 0.5, art: 'ham' });

// ── CHORUS I (12–19)
phrase('Z', 'call', 8);   Z(12, 69, { v: 0.68, hold: 5 });
phrase('Z-answer', 'answer'); L(13, 6, 74, 1, { v: 0.6 }); L(13, 7, 71, 1, { v: 0.55, art: 'pull' }); L(13, 8, 67, 4, { v: 0.58, vib: VIB(0.5, 0.26, 5.2) });
phrase('X', 'call', 5);   X(14, 69, { v: 0.64, curl: true });
phrase('pickup', 'bridge'); L(15, 8, 72, 1, { v: 0.55 }); L(15, 9, 74, 1, { v: 0.58, art: 'ham' }); L(15, 10, 76, 2, { v: 0.62 });
phrase('Z', 'call', 12);
L(16, 0, 79, 5, { v: 0.74, bend: [bendTo(2, 0.25, 0.9)], vib: VIB(0.5, 0.32, 5.3, 'sym') });
L(16, 6, 79, 1, { v: 0.7 }); L(16, 7, 76, 1, { v: 0.6, art: 'pull' }); L(16, 8, 74, 1, { v: 0.62 }); L(16, 9, 72, 3, { v: 0.62, curl: 30 });
phrase('Y', 'answer', 5); L(17, 0, 69, 5, { v: 0.6, vib: VIB(0.5, 0.26, 5.1) });
L(17, 9, 72, 1, { v: 0.52 }); L(17, 10, 69, 1, { v: 0.48, art: 'pull' }); L(17, 11, 67, 1, { v: 0.5 });
phrase('cry', 'cadence', 7); cry(18, 0, 74, 2, 6, 0.7, 0.3);
L(18, 6, 68, 3, { v: 0.6 }); L(18, 9, 71, 3, { v: 0.55, vib: VIB(0.4, 0.2, 5.2) });
phrase('sharp9', 'cadence', 3);
L(19, 0, 67, 2, { v: 0.66, curl: 32 }); L(19, 2, 64, 1, { v: 0.55, art: 'pull' }); L(19, 3, 62, 1, { v: 0.55 });
L(19, 4, 64, 11, { v: 0.58, art: 'ham', vib: VIB(0.7, 0.3, 5.0) });

// ── VERSE II (20–27): the motif displaced by half a bar; ornament grows
phrase('X', 'call', 5);   X(20, 69, { s: 6, v: 0.6, curl: true, fall: 9 });
phrase('pickup', 'bridge'); L(21, 10, 67, 1, { v: 0.5 }); L(21, 11, 69, 1, { v: 0.52, art: 'ham' });
phrase('Y', 'answer');
L(22, 0, 65, 3, { v: 0.6, ds: 69 }); L(22, 3, 64, 1, { v: 0.52 }); L(22, 4, 62, 2, { v: 0.5, art: 'pull' });
L(22, 6, 60, 2, { v: 0.55, curl: 30 }); L(22, 8, 64, 8, { v: 0.56, art: 'slide', slide: 0.12, vib: VIB(0.55, 0.32, 5.1) });
phrase('turn-inv', 'answer', 8); L(23, 6, 76, 2, { v: 0.55 }); L(23, 8, 74, 1, { v: 0.5, art: 'pull' }); L(23, 9, 72, 3, { v: 0.56, curl: 30 });
phrase('X', 'call', 5);   X(24, 69, { v: 0.66, turnUp: true, curl: true, bendDur: 1.3, fall: 7 });
phrase('Y', 'answer');    L(25, 6, 69, 2, { v: 0.52 }); L(25, 8, 72, 1, { v: 0.56, curl: 30 }); L(25, 9, 74, 3, { v: 0.6, art: 'ham', vib: VIB(0.4, 0.22, 5.2) });
phrase('cry', 'cadence', 7); cry(26, 0, 74, 2, 6, 0.68, 0.3);
L(26, 6, 71, 1, { v: 0.6 }); L(26, 7, 68, 1, { v: 0.55, art: 'pull' }); L(26, 8, 64, 4, { v: 0.56, vib: VIB(0.45, 0.28, 5.1) });
phrase('resolve', 'cadence', 5); L(27, 3, 69, 3, { v: 0.52, vib: VIB(0.4, 0.2, 5.0) });
L(27, 10, 69, 1, { v: 0.55 }); L(27, 11, 71, 1, { v: 0.56, art: 'ham' });

// ── CHORUS II (28–35) — hotter, and it breaks open on A7♯9
phrase('Z', 'call', 8);   Z(28, 69, { v: 0.74, hold: 5, vib: 0.34 });
phrase('Z-answer', 'answer'); L(29, 6, 74, 1, { v: 0.64, ds: 71 }); L(29, 7, 71, 1, { v: 0.58, art: 'pull' }); L(29, 8, 67, 4, { v: 0.62, vib: VIB(0.45, 0.3, 5.3) });
phrase('X', 'call', 5);   X(30, 69, { v: 0.7, curl: true, vib: 0.3 });
phrase('pickup', 'bridge'); L(31, 8, 72, 1, { v: 0.6 }); L(31, 9, 74, 1, { v: 0.62, art: 'ham' }); L(31, 10, 76, 2, { v: 0.66 });
phrase('Z', 'call', 12);
L(32, 0, 79, 5, { v: 0.8, bend: [bendTo(2, 0.25, 0.8)], vib: VIB(0.45, 0.38, 5.4, 'sym') });
L(32, 6, 81, 1, { v: 0.76 }); L(32, 7, 79, 1, { v: 0.66, art: 'pull' }); L(32, 8, 76, 1, { v: 0.66 }); L(32, 9, 74, 1, { v: 0.64, art: 'pull' }); L(32, 10, 72, 2, { v: 0.66, curl: 32 });
phrase('Y', 'answer', 5); L(33, 0, 69, 5, { v: 0.64, vib: VIB(0.45, 0.3, 5.2) });
L(33, 9, 72, 1, { v: 0.58 }); L(33, 10, 74, 1, { v: 0.6, art: 'ham' }); L(33, 11, 76, 1, { v: 0.62 });
phrase('cry', 'cadence', 7); cry(34, 0, 74, 2, 6, 0.78, 0.36);
L(34, 6, 76, 1, { v: 0.68 }); L(34, 7, 74, 1, { v: 0.6, art: 'pull' }); L(34, 8, 71, 1, { v: 0.62 }); L(34, 9, 68, 3, { v: 0.64, vib: VIB(0.3, 0.26, 5.4) });
phrase('X', 'call', 15);                                      // the sigh an octave up, alone in the break
L(35, 2, 79, 4, { v: 0.78, bend: [bendTo(2, 0.35, 1.1), bendTo(0, 3.6, 0.9, 'smooth')], vib: VIB(0.6, 0.3, 5.2, 'sym') });
L(35, 7, 76, 1, { v: 0.6, art: 'pull' });
L(35, 8, 73, 3.4, { v: 0.66, curl: 0, vib: VIB(0.35, 0.28, 5.5) });  // C♯ — the ear turns toward D

// ── SOLO (36–51), D Dorian. Woman-tone at first, opening to full bite at the peak.
phrase('X', 'call', 10);  X(36, 74, { v: 0.64, curl: true, fall: 8, vib: 0.28 });
phrase('response', 'answer', 10);
L(37, 6, 65, 1, { v: 0.52 }); L(37, 7, 67, 1, { v: 0.5, art: 'ham' }); L(37, 8, 69, 1, { v: 0.55 }); L(37, 9, 71, 3, { v: 0.6, vib: VIB(0.35, 0.3, 5.4) });
phrase('X', 'call', 10);
L(38, 0, 72, 2.6, { v: 0.62, bend: [bendTo(2, 0.2, 0.6)] });
L(38, 3, 72, 3, { v: 0.7, bend: [bendTo(2, 0.25, 0.9)], vib: VIB(0.4, 0.34, 5.5, 'sym') });
L(38, 6, 77, 1, { v: 0.72, curl: 32 }); L(38, 7, 76, 1, { v: 0.6, art: 'pull' }); L(38, 8, 74, 1, { v: 0.6, art: 'pull' });
L(38, 9, 72, 1, { v: 0.64 }); L(38, 10, 69, 5, { v: 0.62, vib: VIB(0.45, 0.32, 5.3) });
phrase('response', 'answer', 10);
L(39, 5, 67, 1, { v: 0.55 }); L(39, 6, 69, 1, { v: 0.55, art: 'ham' }); L(39, 7, 71, 1, { v: 0.58, art: 'ham' }); L(39, 8, 74, 4, { v: 0.64, vib: VIB(0.4, 0.3, 5.4) });
phrase('call-high', 'call', 13);
L(40, 0, 77, 2, { v: 0.72 });
L(40, 2, 79, 5.6, { v: 0.78, bend: [bendTo(2, 0.25, 0.8), bendTo(0, 5.3, 0.3, 'smooth')], vib: VIB(0.5, 0.4, 5.5, 'sym') });
L(40, 8, 77, 1, { v: 0.66 }); L(40, 9, 74, 5, { v: 0.64, art: 'pull', vib: VIB(0.5, 0.3, 5.3) });
phrase('turn-seq', 'answer', 12);
L(41, 3, 79, 1, { v: 0.66 }); L(41, 4, 76, 1, { v: 0.56, art: 'pull' }); L(41, 5, 74, 1, { v: 0.6 });
L(41, 6, 76, 1, { v: 0.64 }); L(41, 7, 72, 1, { v: 0.55, art: 'pull' }); L(41, 8, 69, 1, { v: 0.58 });
L(41, 9, 72, 1, { v: 0.62 }); L(41, 10, 69, 1, { v: 0.54, art: 'pull' }); L(41, 11, 67, 1, { v: 0.56 });
phrase('rest', 'resolve', 10); L(42, 0, 69, 5, { v: 0.6, art: 'slide', slide: 0.08, vib: VIB(0.4, 0.34, 5.3) });
phrase('ascent', 'bridge', 12);
L(43, 6, 74, 1, { v: 0.62 }); L(43, 7, 77, 1, { v: 0.62, art: 'ham' }); L(43, 8, 79, 1, { v: 0.66, art: 'ham' }); L(43, 9, 81, 3, { v: 0.74, vib: VIB(0.3, 0.3, 5.6) });
phrase('cry', 'call', 15);
L(44, 0, 79, 5.4, { v: 0.8, bend: [bendTo(2, 0.2, 0.6), bendTo(0, 2.0, 0.5, 'smooth'), bendTo(2, 3.0, 0.7)], vib: VIB(0.9, 0.36, 5.6, 'sym') });
L(44, 6, 77, 1, { v: 0.72 }); L(44, 7, 74, 1, { v: 0.62, art: 'pull' });
L(44, 8, 77, 4, { v: 0.76, bend: [bendTo(2, 0.25, 0.8)], vib: VIB(0.4, 0.4, 5.7, 'sym') });
phrase('response', 'answer', 10);
L(45, 3, 76, 1, { v: 0.62 }); L(45, 4, 74, 1, { v: 0.55, art: 'pull' }); L(45, 5, 72, 1, { v: 0.6 });
L(45, 6, 69, 2, { v: 0.6 }); L(45, 8, 72, 4, { v: 0.7, bend: [bendTo(2, 0.25, 0.8)], vib: VIB(0.4, 0.38, 5.6, 'sym') });
phrase('call-high', 'call', 17);
L(46, 0, 81, 2, { v: 0.82, vib: VIB(0.25, 0.3, 5.8) }); L(46, 2, 79, 1, { v: 0.7 }); L(46, 3, 77, 1, { v: 0.7 });
L(46, 4, 79, 1, { v: 0.72, art: 'ham' }); L(46, 5, 81, 1, { v: 0.76 });
L(46, 6, 81, 6, { v: 0.84, bend: [bendTo(1, 0.2, 0.6)], vib: VIB(0.5, 0.42, 5.8, 'sym') });
phrase('question', 'call', 12);
L(47, 0, 74, 1, { v: 0.7 }); L(47, 1, 76, 2, { v: 0.66, art: 'ham' }); L(47, 3, 79, 2, { v: 0.74 });
L(47, 6, 72, 6, { v: 0.8, bend: [bendTo(1, 0.3, 0.8)], vib: VIB(0.6, 0.3, 5.8, 'sym') });   // C→C♯ on A7
phrase('X', 'call', 10);  X(48, 74, { v: 0.84, curl: true, fall: 2, vib: 0.4 });
L(48, 10, 72, 1, { v: 0.7 }); L(48, 11, 74, 1, { v: 0.74, art: 'ham' });
phrase('turn-seq-up', 'bridge', 15);                           // the turn, sequenced upward
L(49, 0, 77, 1, { v: 0.76 }); L(49, 1, 74, 1, { v: 0.62, art: 'pull' }); L(49, 2, 72, 1, { v: 0.66 });
L(49, 3, 79, 1, { v: 0.8 }); L(49, 4, 77, 1, { v: 0.66, art: 'pull' }); L(49, 5, 74, 1, { v: 0.7 });
L(49, 6, 81, 1, { v: 0.86 }); L(49, 7, 79, 1, { v: 0.7, art: 'pull' }); L(49, 8, 77, 1, { v: 0.74 });
L(49, 9, 84, 1, { v: 0.92 }); L(49, 10, 81, 1, { v: 0.76, art: 'pull' }); L(49, 11, 79, 1, { v: 0.8 });
phrase('summit', 'climax', 19);
L(50, 0, 86, 9, { v: 1.0, vib: VIB(0.7, 0.62, 5.9, 'up', 0.5) });                  // D6 — the highest note of the work
L(50, 9, 84, 1, { v: 0.78, art: 'pull' }); L(50, 10, 81, 1, { v: 0.76, art: 'pull' }); L(50, 11, 79, 1, { v: 0.8 });
phrase('X', 'climax', 15);                                     // the sigh, completed in the silence: G → G♯ → A
L(51, 2, 79, 15.4, { v: 0.96, T: 14, bend: [bendTo(1, 0.3, 1.4), bendTo(2, 4.6, 1.8), bendTo(0, 14.0, 1.2, 'smooth')], vib: VIB(2.4, 0.44, 5.4, 'sym', 0.9) });

// ── FINAL CHORUS (52–59): the motifs in the high octave, then descending home
phrase('release', 'resolve', 15);
L(52, 6, 76, 1, { v: 0.74 }); L(52, 7, 74, 1, { v: 0.62, art: 'pull' }); L(52, 8, 72, 4, { v: 0.7, curl: 30, vib: VIB(0.5, 0.36, 5.4) });
phrase('Z-answer', 'answer', 12);
L(53, 3, 71, 1, { v: 0.64 }); L(53, 4, 74, 2, { v: 0.66, art: 'ham' });
L(53, 6, 79, 6, { v: 0.76, bend: [bendTo(2, 0.25, 0.9)], vib: VIB(0.5, 0.36, 5.4, 'sym') });
phrase('X', 'call', 17);  X(54, 81, { v: 0.8, curl: true, fall: 10, vib: 0.36 });
phrase('pickup', 'bridge', 12); L(55, 8, 72, 1, { v: 0.62 }); L(55, 9, 74, 1, { v: 0.64, art: 'ham' }); L(55, 10, 76, 2, { v: 0.68 });
phrase('Z', 'call', 12);
L(56, 0, 79, 5, { v: 0.78, bend: [bendTo(2, 0.25, 0.9)], vib: VIB(0.5, 0.36, 5.3, 'sym') });
L(56, 6, 79, 1, { v: 0.7 }); L(56, 7, 76, 1, { v: 0.6, art: 'pull' }); L(56, 8, 74, 1, { v: 0.62 }); L(56, 9, 72, 3, { v: 0.62, curl: 30 });
phrase('Y', 'answer', 5); L(57, 0, 69, 5, { v: 0.6, vib: VIB(0.5, 0.28, 5.1) });
L(57, 9, 72, 1, { v: 0.52 }); L(57, 10, 69, 1, { v: 0.48, art: 'pull' }); L(57, 11, 67, 1, { v: 0.5 });
phrase('cry', 'cadence', 7); cry(58, 0, 74, 2, 6, 0.68, 0.3);
L(58, 6, 68, 6, { v: 0.6, vib: VIB(0.5, 0.26, 5.1) });
phrase('sharp9', 'cadence', 3);
L(59, 0, 67, 2, { v: 0.6, curl: 32 }); L(59, 2, 64, 1, { v: 0.5, art: 'pull' }); L(59, 3, 62, 1, { v: 0.5 });
L(59, 4, 64, 8, { v: 0.52, art: 'ham', vib: VIB(0.7, 0.24, 4.9) });

// ── OUTRO (60–63): clean again. The fall is withheld once more … then completed.
phrase('X', 'call', 5);   X(60, 69, { s: 2, v: 0.46, fall: 0, bendDur: 1.2, vib: 0.2 });
phrase('Y', 'answer');
L(61, 0, 62, 1, { v: 0.42 }); L(61, 1, 64, 2, { v: 0.4, art: 'ham' }); L(61, 3, 67, 2, { v: 0.44 }); L(61, 5, 64, 1, { v: 0.38, art: 'pull' });
L(61, 6, 60, 6, { v: 0.44, curl: 26, vib: VIB(0.6, 0.18, 4.8) });
phrase('X-fall', 'resolve', 5);
L(62, 6, 59, 2, { v: 0.4 }); L(62, 8, 56, 4, { v: 0.42, vib: VIB(0.5, 0.14, 4.6) });
L(63, 0, 57, 14, { v: 0.5, vib: VIB(1.1, 0.2, 4.6, 'up', 0.8), ring: true, T: 7 });   // the motif's fall, at last, to the tonic

// ═══ ACCOMPANIMENT ═══════════════════════════════════════════════════════════
const RHY = [], BASS = [], DRUM = [], ORGAN = [], PARAM = [];
const leadOnsets = new Set(LEAD.map(n => n.bar * 12 + Math.round(n.p)));
const leadNear = (bar, p) => leadOnsets.has(bar * 12 + p);

function strum(bar, p, name, vel, dir = 'D', o = {}) { RHY.push({ bar, p, name, vel, dir, kind: o.kind || 'strum', ring: o.ring, idx: o.idx }); }
function arpBar(bar, pattern, vel, o = {}) {
  for (const [p, idx, a] of pattern) {
    const name = chordAt(bar, p);
    let v = vel * (a ?? 1);
    if (o.respond && p !== 0 && leadNear(bar, p)) { if (idx >= 3) continue; v *= 0.55; }   // make room for the lead
    RHY.push({ bar, p, name, vel: v, dir: 'D', kind: 'arp', idx });
  }
}
function strumBar(bar, pattern, vel, o = {}) {
  for (const [p, dir, a] of pattern) {
    const name = chordAt(bar, p);
    let v = vel * a;
    if (o.respond && p !== 0 && leadNear(bar, p) && dir !== 'X') v *= 0.6;
    RHY.push({ bar, p, name, vel: v, dir: dir === 'X' ? 'D' : dir, kind: dir === 'X' ? 'mute' : 'strum' });
  }
}
const ARP_VERSE = [[0, 0, 1], [2, 2, 0.7], [3, 3, 0.85], [5, 4, 0.6], [6, 1, 0.9], [8, 3, 0.65], [9, 2, 0.8], [11, 4, 0.55]];
const ARP_SPARSE = [[0, 0, 1], [3, 2, 0.7], [6, 3, 0.75], [9, 4, 0.6]];
const STRUM_CHORUS = [[0, 'D', 1], [3, 'D', 0.55], [5, 'U', 0.38], [6, 'D', 0.85], [8, 'X', 0.35], [9, 'D', 0.6], [11, 'U', 0.42]];
const STRUM_SOLO_A = [[0, 'D', 0.9], [6, 'D', 0.6], [9, 'U', 0.35]];
const STRUM_SOLO_B = [[0, 'D', 0.95], [3, 'U', 0.4], [5, 'D', 0.5], [6, 'D', 0.85], [8, 'X', 0.35], [9, 'D', 0.6], [11, 'D', 0.72]];

function bassNote(bar, p, midi, dur, vel) { BASS.push({ bar, p, midi, dur, vel }); }
function nextRoot(bar) { return ROOT[chordAt(Math.min(NBARS - 1, bar + 1), 0)]; }
function bassBar(bar, style, vel) {
  const r0 = ROOT[chordAt(bar, 0)], r6 = ROOT[chordAt(bar, 6)], nr = nextRoot(bar);
  const appr = nr - 1 >= 28 ? nr - 1 : nr + 2;
  if (style === 'verse') { bassNote(bar, 0, r0, 5, vel); bassNote(bar, 5, r0 + 7, 1, vel * 0.6); bassNote(bar, 6, r6, 3, vel * 0.9); bassNote(bar, 9, r6 + 7, 2, vel * 0.7); bassNote(bar, 11, appr, 1, vel * 0.65); }
  else if (style === 'chorus') { bassNote(bar, 0, r0, 3, vel); bassNote(bar, 3, r0 + 7, 2, vel * 0.7); bassNote(bar, 5, r0 + 12, 1, vel * 0.55); bassNote(bar, 6, r6, 2, vel * 0.9); bassNote(bar, 8, r6 + 7, 1, vel * 0.6); bassNote(bar, 9, r6 + 12, 2, vel * 0.7); bassNote(bar, 11, appr, 1, vel * 0.7); }
  else if (style === 'soloA') { bassNote(bar, 0, r0, 6, vel); bassNote(bar, 6, r6, 3, vel * 0.85); bassNote(bar, 9, r6 + 7, 2, vel * 0.7); bassNote(bar, 11, appr, 1, vel * 0.7); }
  else if (style === 'soloB') { for (const [p, iv, a] of [[0, 0, 1], [2, 12, 0.5], [3, 7, 0.75], [5, 0, 0.6], [6, 0, 0.9], [8, 12, 0.5], [9, 7, 0.75], [11, 0, 0.7]]) bassNote(bar, p, (p < 6 ? r0 : r6) + iv, p === 11 ? 1 : 2, vel * a); }
  else if (style === 'hold') { bassNote(bar, 0, r0, 11, vel); }
  else if (style === 'outro') { bassNote(bar, 0, r0, 6, vel); bassNote(bar, 6, r6, 6, vel * 0.8); }
}
const hit = (bar, p, type, v, extra) => DRUM.push(Object.assign({ bar, p, type, v }, extra || {}));
function drumBar(bar, style, lvl = 1) {
  for (let p = 0; p < 12; p++) {
    const beat = p % 3 === 0, acc = beat ? (p % 6 === 0 ? 1 : 0.8) : 0.55;
    switch (style) {
      case 'verse1':
        hit(bar, p, 'hat', 0.5 * acc * lvl);
        if (p === 3 || p === 9) hit(bar, p, 'rim', 0.55 * lvl);
        if (p === 0) hit(bar, p, 'kick', 0.6 * lvl); if (p === 7) hit(bar, p, 'kick', 0.35 * lvl);
        break;
      case 'verse2':
        hit(bar, p, 'hat', 0.55 * acc * lvl);
        if (p === 3 || p === 9) hit(bar, p, 'snare', 0.5 * lvl); if (p === 8 || p === 11) hit(bar, p, 'snare', 0.1 * lvl);
        if (p === 0) hit(bar, p, 'kick', 0.7 * lvl); if (p === 7 || p === 8) hit(bar, p, 'kick', 0.4 * lvl);
        break;
      case 'chorus':
        hit(bar, p, 'ride', 0.6 * acc * lvl);
        if (p === 3 || p === 9) hit(bar, p, 'snare', 0.82 * lvl); if (p === 11) hit(bar, p, 'snare', 0.14 * lvl);
        if (p === 0 || p === 6) hit(bar, p, 'kick', 0.85 * lvl); if (p === 5 || p === 8) hit(bar, p, 'kick', 0.45 * lvl);
        break;
      case 'soloA':
        hit(bar, p, 'ride', 0.55 * acc * lvl);
        if (p === 3 || p === 9) hit(bar, p, 'snare', 0.76 * lvl); if (p === 5 || p === 11) hit(bar, p, 'snare', 0.12 * lvl);
        if (p === 0 || p === 7) hit(bar, p, 'kick', 0.8 * lvl);
        break;
      case 'soloB':
        hit(bar, p, 'ride', 0.62 * acc * lvl); if (p === 11) hit(bar, p, 'hat', 0.4 * lvl, { open: true });
        if (p === 3 || p === 9) hit(bar, p, 'snare', 0.88 * lvl); if (p === 2 || p === 5 || p === 8 || p === 11) hit(bar, p, 'snare', 0.16 * lvl);
        if (p === 0 || p === 2 || p === 6 || p === 8) hit(bar, p, 'kick', (p % 6 === 0 ? 0.9 : 0.55) * lvl);
        break;
      case 'outro':
        if (beat) hit(bar, p, 'ride', 0.45 * acc * lvl);
        if (p === 6) hit(bar, p, 'snare', 0.5 * lvl); if (p === 0) hit(bar, p, 'kick', 0.6 * lvl);
        break;
    }
  }
}
function fill(bar, from, kind, lvl = 1) {
  for (let p = from; p < 12; p++) {
    const k = p - from;
    if (kind === 'snare') hit(bar, p, 'snare', (0.35 + 0.08 * k) * lvl);
    else hit(bar, p, 'tom', (0.55 + 0.06 * k) * lvl, { f: [196, 165, 131, 110, 98, 82][k % 6] });
    if (p === 11) hit(bar, p, 'kick', 0.7 * lvl);
  }
}
const organPad = (bar, p, name, dur, v, att, rel) => {
  const ms = CH[name].filter(m => m >= 50).map(m => (m < 55 ? m + 12 : m)).filter((m, i, a) => a.indexOf(m) === i);
  ORGAN.push({ bar, p, midis: ms, dur, v, att, rel });
};
const organBar = (bar, v, att = 0.25) => {
  const c = PROG[bar];
  if (Array.isArray(c)) { organPad(bar, 0, c[0], 6, v, att, 0.3); organPad(bar, 6, c[1], 6, v, att, 0.4); }
  else organPad(bar, 0, c, 12, v, att, 0.4);
};
const param = (bar, p, name, v, tc = 0.4) => PARAM.push({ bar, p, name, v, tc });

// Intro
strum(0, 0, 'Am9', 0.5, 'D', { kind: 'roll', ring: true });
arpBar(1, ARP_SPARSE, 0.42, { respond: true }); arpBar(2, ARP_SPARSE, 0.46, { respond: true }); arpBar(3, ARP_SPARSE, 0.48, { respond: true });
bassNote(2, 0, 29, 11, 0.45); bassNote(3, 0, 28, 5, 0.5); bassNote(3, 6, 28, 5, 0.5);
hit(3, 0, 'swell', 0.8, { dur: D(3, 0, 12) });
// Verses
for (let b = 4; b < 12; b++) { arpBar(b, ARP_VERSE, 0.46, { respond: true }); bassBar(b, 'verse', 0.55); drumBar(b, 'verse1', 0.72); }
for (let b = 20; b < 28; b++) { arpBar(b, ARP_VERSE, 0.5, { respond: true }); bassBar(b, 'verse', 0.62); drumBar(b, 'verse2', 0.8); organBar(b, 0.22, 0.6); }
fill(11, 9, 'tom', 0.7); fill(27, 9, 'snare', 0.9);
// Choruses
for (const c0 of [12, 28, 52]) {
  const lift = c0 === 52 ? 1.08 : c0 === 28 ? 1.04 : 1;
  for (let b = c0; b < c0 + 8; b++) {
    if (c0 === 28 && b === 35) continue;
    strumBar(b, STRUM_CHORUS, 0.62 * lift, { respond: true }); bassBar(b, 'chorus', 0.72 * lift); drumBar(b, 'chorus', 0.92 * lift); organBar(b, 0.34 * lift);
  }
  hit(c0, 0, 'crash', 0.8 * lift);
}
fill(19, 9, 'snare', 0.9); fill(59, 9, 'tom', 0.85);
// The break (bar 35): one A7♯9 stab, then only the lead
strum(35, 0, 'A7s9', 0.85, 'D'); strum(35, 2, 'A7s9', 0.3, 'D', { kind: 'mute' });
bassNote(35, 0, 33, 1.5, 0.8); hit(35, 0, 'kick', 0.9); hit(35, 0, 'crash', 0.7, { dec: 1.6 });
// Solo
for (let b = 36; b < 44; b++) { strumBar(b, STRUM_SOLO_A, 0.55, { respond: true }); bassBar(b, 'soloA', 0.72); drumBar(b, 'soloA', 0.9); organBar(b, 0.4, 0.5); }
for (let b = 44; b < 51; b++) { strumBar(b, STRUM_SOLO_B, 0.6, { respond: true }); bassBar(b, 'soloB', 0.76); drumBar(b, 'soloB', 0.95 + (b - 44) * 0.012); organBar(b, 0.48, 0.2); }
hit(36, 0, 'crash', 0.75); hit(44, 0, 'crash', 0.8); fill(43, 6, 'tom', 0.8); fill(49, 6, 'snare', 1.0); hit(50, 0, 'crash', 0.95);
// Bar 51: stop-time. One hit, then silence around the bend.
strum(51, 0, 'E7s9', 0.95, 'D'); strum(51, 2, 'E7s9', 0.35, 'D', { kind: 'mute' });
bassNote(51, 0, 28, 1.5, 0.9); hit(51, 0, 'kick', 1.0); hit(51, 0, 'crash', 0.9, { dec: 2.2 });
// Outro + ending
arpBar(60, ARP_VERSE, 0.46, { respond: true }); arpBar(61, ARP_SPARSE, 0.42, { respond: true });
arpBar(62, [[0, 0, 1], [3, 2, 0.7], [6, 0, 0.9], [8, 3, 0.6], [10, 4, 0.55]], 0.4, { respond: true });
bassBar(60, 'outro', 0.6); bassBar(61, 'outro', 0.55); bassNote(62, 0, 28, 5, 0.52); bassNote(62, 6, 28, 5, 0.48);
drumBar(60, 'outro', 0.8); drumBar(61, 'outro', 0.7);
hit(62, 0, 'ride', 0.35); hit(62, 6, 'ride', 0.3); hit(62, 0, 'kick', 0.5);
for (let p = 6; p < 12; p++) hit(62, p, 'tom', 0.22 + 0.05 * (p - 6), { f: [98, 110, 98, 87, 82, 73][p - 6] });
organBar(60, 0.26, 0.8); organPad(61, 0, 'Fmaj7', 12, 0.2, 0.8, 1.2);
// The last chord: rolled, ringing, then damped by hand.
strum(63, 0, 'Am9', 0.62, 'D', { kind: 'roll', ring: true }); bassNote(63, 0, 33, 13, 0.62);
hit(63, 0, 'kick', 0.7); hit(63, 0, 'crash', 0.55, { dec: 3.4 });
const FINAL_T = T(63, 0), DAMP_T = FINAL_T + 4.4, END = Math.ceil((DAMP_T + 2.4) * 60) / 60;

// Tone automation — the amp's own arc: clean → warm → woman-tone → full bite → cooling.
const tone = (bar, s) => { for (const k in s) param(bar, 0, k, s[k], s.tc || 0.5); };
tone(0,  { leadDrive: 1.5, leadPost: 0.9, neck: 1, middle: 0, tone: 4200, toneQ: 0.8, echoFb: 0.26, leadEcho: 0.13, leadRev: 0.3, rhythmOut: 0.38, organOut: 0, organRate: 0.8, drums: 0.42, bassOut: 0.54, stackMid: 2, leadOut: 0.74 });
tone(12, { leadDrive: 2.4, leadPost: 0.72, neck: 0.8, middle: 0.35, tone: 4800, rhythmOut: 0.52, organOut: 0.4, drums: 0.56, bassOut: 0.6, leadOut: 0.7 });
tone(20, { leadDrive: 1.8, leadPost: 0.84, neck: 1, middle: 0.1, tone: 4400, rhythmOut: 0.42, organOut: 0.22, drums: 0.46, bassOut: 0.56, leadOut: 0.74 });
tone(28, { leadDrive: 2.8, leadPost: 0.66, neck: 0.8, middle: 0.4, tone: 5000, rhythmOut: 0.54, organOut: 0.45, drums: 0.58, bassOut: 0.6, leadOut: 0.72 });
tone(36, { leadOut: 0.58, leadDrive: 7, leadPost: 0.3, neck: 1, middle: 0, tone: 1450, toneQ: 2.2, stackMid: 4, echoFb: 0.3, leadEcho: 0.16, rhythmOut: 0.48, organOut: 0.42 });
tone(40, { tone: 2100, toneQ: 1.8, leadDrive: 8 });
tone(44, { tone: 2900, toneQ: 1.4, leadDrive: 9.5, leadPost: 0.26, middle: 0.5, neck: 0.8, organRate: 5.8, organOut: 0.55, drums: 0.62 });
tone(48, { tone: 3800, toneQ: 1.1, leadDrive: 11, leadPost: 0.22, middle: 0.8, neck: 0.6, echoFb: 0.34 });
tone(50, { tone: 5400, toneQ: 0.9, leadDrive: 13, leadPost: 0.19, echoFb: 0.4, leadEcho: 0.2, organOut: 0.62, tc: 0.25 });
param(51, 0.5, 'organOut', 0, 0.06); param(51, 0, 'drums', 0.62);
tone(52, { leadOut: 0.7, leadDrive: 4.5, leadPost: 0.4, neck: 0.8, middle: 0.5, tone: 4600, toneQ: 0.8, stackMid: 2.5, echoFb: 0.3, leadEcho: 0.15, organOut: 0.5, organRate: 0.8, drums: 0.6, tc: 0.15 });
tone(60, { leadDrive: 1.5, leadPost: 0.9, neck: 1, middle: 0, tone: 3500, organOut: 0.28, rhythmOut: 0.4, drums: 0.42, leadOut: 0.74, tc: 1.2 });
param(62, 0, 'organOut', 0, 2.0);

// ═══ PERFORMANCE: score → String Engine commands + note events ════════════════
const cmds = { lead: [], rhythm: [], bass: [] }, native = [], events = [];
const secLay = { intro: 0.02, verse1: 0.022, chorus1: 0.016, verse2: 0.02, chorus2: 0.014, solo: 0.008, final: 0.012, outro: 0.024 };
LEAD.sort((a, b) => (a.bar * 12 + a.p) - (b.bar * 12 + b.p));

// string/fret assignment (for the image: where along which string the note lives)
let prevStr = 1;
function place(n, prev) {
  let best = null, bestC = 1e9;
  for (let s = 0; s < 6; s++) {
    const f = n.midi - OPEN[s]; if (f < 0 || f > 22) continue;
    let c = Math.abs(f - (n.pos + 1.5));
    if (prev && n.o.art && s === prev.str && Math.abs(f - prev.fret) <= 5) c -= 6;
    if (f === 0) c += 2;
    if (n.o.bend && s >= 4) c += 4;                                   // bends live on the top strings
    if (c < bestC) { bestC = c; best = { str: s, fret: f }; }
  }
  return best || { str: prevStr, fret: Math.max(0, n.midi - OPEN[prevStr]) };
}

let voice = 0, prevNote = null;
for (let i = 0; i < LEAD.length; i++) {
  const n = LEAD[i], o = n.o, sec = sectionOf(n.bar), next = LEAD[i + 1];
  const legato = o.art === 'ham' || o.art === 'pull' || o.art === 'slide';
  const lay = secLay[sec.id] + jit(legato ? 0.003 : 0.007);
  const t = T(n.bar, n.p) + lay;
  let tEnd = T(n.bar, n.p + n.dur) + lay;
  const nextT = next ? T(next.bar, next.p) + secLay[sectionOf(next.bar).id] : Infinity;
  const nextLegato = next && (next.o.art === 'ham' || next.o.art === 'pull' || next.o.art === 'slide');
  if (!o.ring && tEnd > nextT - 0.004) tEnd = nextT - 0.004;
  if (o.ring) tEnd = Math.min(tEnd, DAMP_T);
  const pl = place(n, legato ? prevNote : null); prevStr = pl.str;
  if (!legato || !prevNote) voice = (voice + 1) % 4;
  const v = voice, vel = Math.max(0.05, Math.min(1, o.v ?? 0.6));
  const solo = sec.id === 'solo', f0 = hz(n.midi);
  const bright = Math.min(1, 0.4 + 0.5 * vel + (solo ? 0.08 : 0));
  const T60 = o.T ?? Math.max(solo ? 5.5 : sec.id === 'final' ? 4.8 : 3.4, Math.min(16, (tEnd - t) * (solo ? 2.6 : 2.0)));
  const ev = { id: events.length, inst: 'lead', midi: n.midi, str: pl.str, fret: pl.fret, t, dur: tEnd - t, vel, art: o.art || 'pick',
    section: sec.id, phrase: n.phrase, motif: n.motif, role: n.role, bends: [], vib: null, ds: o.ds || null };
  if (legato && prevNote) {
    if (o.art === 'slide') cmds.lead.push({ t, type: 'bend', v, f: f0, d: o.slide ?? 0.1, c: 'lin' });
    else cmds.lead.push({ t, type: 'legato', v, f: f0, d: 0.005, a: (o.art === 'pull' ? 0.17 : 0.1) * (0.4 + 0.6 * vel), b: 0.85, T: T60 });
  } else {
    cmds.lead.push({ t, type: 'pluck', v, f: hz(n.midi + (o.pre || 0)), a: 0.3 + 0.7 * vel, b: bright, p: 0.1 + rnd() * 0.06,
      s: solo ? 0.2 : 0.27, T: T60, n: 0.18 + 0.28 * vel, k: 0.45 + 0.9 * vel * vel });
  }
  // bends (whole/half-step goals, cries) and microtonal curls on blue thirds
  let stages = (o.bend || []).slice();
  if (o.curl) stages = [{ to: o.curl / 100, at: 0.22, dur: 0.5, c: 'ease' }, { to: 0, at: Math.min(n.dur * 0.6, 2.4), dur: 0.9, c: 'smooth' }];
  let from = (o.pre || 0) * 100;
  for (const s of stages) {
    const t0 = T(n.bar, n.p + s.at) + lay, t1 = t0 + D(n.bar, n.p + s.at, s.dur);
    if (t0 >= tEnd) break;
    cmds.lead.push({ t: t0, type: 'bend', v, f: hz(n.midi + s.to), d: t1 - t0, c: s.c });
    ev.bends.push({ t0, t1, from, to: s.to * 100, c: s.c }); from = s.to * 100;
  }
  // bent note followed by a legato note on the same string: the finger releases first
  if (o.vib && tEnd - t > o.vib.at + 0.08) {
    const vt = t + o.vib.at;
    cmds.lead.push({ t: vt, type: 'vib', v, d: o.vib.d, r: o.vib.r, m: o.vib.m, k: o.vib.k });
    cmds.lead.push({ t: tEnd - 0.02, type: 'vib', v, d: 0, k: 0.05 });
    ev.vib = { t: vt, t1: tEnd, d: o.vib.d, r: o.vib.r, m: o.vib.m, k: o.vib.k };
  }
  if (o.ds) {
    // double-stop: the partner string sounds on the next voice; if a legato note
    // follows, it continues on the partner string and the upper string is lifted.
    const v2 = (v + 1) % 4;
    cmds.lead.push({ t: t + 0.004, type: 'pluck', v: v2, f: hz(o.ds), a: 0.26 + 0.6 * vel, b: bright, p: 0.12, s: 0.27, T: T60, n: 0.3, k: 0.5 * vel });
    if (!nextLegato) cmds.lead.push({ t: tEnd, type: 'damp', v: v2, T: 0.15 });
    cmds.lead.push({ t: tEnd, type: 'damp', v, T: 0.16 });
    voice = v2;
  } else if (!nextLegato || o.ring) cmds.lead.push({ t: tEnd, type: 'damp', v, T: o.ring ? 0.35 : 0.16 });
  events.push(ev); prevNote = { ...ev };
}

// Rhythm guitar: one worklet voice per string slot.
RHY.sort((a, b) => (a.bar * 12 + a.p) - (b.bar * 12 + b.p));
for (const r of RHY) {
  const ms = CH[r.name], t0 = T(r.bar, r.p) + jit(0.004), vel = r.vel;
  if (r.kind === 'arp') {
    const idx = Math.min(r.idx, ms.length - 1), m = ms[idx];
    if (r.p === 0) for (let k = 0; k < 6; k++) if (k !== idx) cmds.rhythm.push({ t: t0 - 0.003, type: 'damp', v: k, T: 0.25 });
    cmds.rhythm.push({ t: t0, type: 'pluck', v: idx, f: hz(m), a: 0.35 + 0.55 * vel, b: 0.35 + 0.3 * vel, p: 0.2, s: 0.34, T: 3.2, n: 0.2, k: 0.25 });
    events.push({ id: events.length, inst: 'rhythm', midi: m, str: idx, t: t0, dur: 1.2, vel, chord: r.name, section: sectionOf(r.bar).id, kind: 'arp' });
    continue;
  }
  const order = r.dir === 'U' ? ms.map((m, i) => i).reverse() : ms.map((m, i) => i);
  const spread = r.kind === 'roll' ? 0.085 : r.dir === 'U' ? 0.009 : 0.013;
  for (let k = ms.length; k < 6; k++) cmds.rhythm.push({ t: t0 - 0.002, type: 'damp', v: k, T: 0.1 });
  order.forEach((i, j) => {
    const tt = t0 + j * spread, m = ms[i];
    if (r.kind === 'mute') cmds.rhythm.push({ t: tt, type: 'pluck', v: i, f: hz(m), a: 0.22 + 0.3 * vel, b: 0.3, p: 0.15, s: 0.4, T: 0.045, n: 0.7, k: 0.5 });
    else cmds.rhythm.push({ t: tt, type: 'pluck', v: i, f: hz(m), a: (0.3 + 0.55 * vel) * (r.dir === 'U' ? 0.8 : 1), b: 0.35 + 0.35 * vel, p: 0.14, s: 0.32, T: r.ring ? 6 : 2.6, n: 0.3, k: 0.35 });
  });
  events.push({ id: events.length, inst: 'rhythm', midi: ms[0], midis: ms, t: t0, dur: 0.6, vel, chord: r.name, section: sectionOf(r.bar).id, kind: r.kind, dir: r.dir });
}
for (let k = 0; k < 6; k++) cmds.rhythm.push({ t: DAMP_T, type: 'damp', v: k, T: 0.3 });

// Bass
let bv = 0;
BASS.sort((a, b) => (a.bar * 12 + a.p) - (b.bar * 12 + b.p));
for (const b of BASS) {
  const t0 = T(b.bar, b.p) + 0.004 + jit(0.004), t1 = T(b.bar, b.p + b.dur) - 0.01;
  bv = 1 - bv;
  cmds.bass.push({ t: t0, type: 'pluck', v: bv, f: hz(b.midi), a: 0.5 + 0.45 * b.vel, b: 0.22 + 0.2 * b.vel, p: 0.24, s: 0.45, T: 2.4, n: 0.12, k: 0.1 });
  cmds.bass.push({ t: Math.min(t1, b.bar === 63 ? DAMP_T : t1), type: 'damp', v: bv, T: 0.12 });
  events.push({ id: events.length, inst: 'bass', midi: b.midi, t: t0, dur: t1 - t0, vel: b.vel, section: sectionOf(b.bar).id });
}
// Drums, organ, automation → native commands
for (const d of DRUM) {
  const t0 = T(d.bar, d.p) + (d.type === 'swell' ? 0 : jit(0.003));
  native.push(Object.assign({ t: t0 }, d, { bar: undefined, p: undefined }));
  if (d.type !== 'swell') events.push({ id: events.length, inst: 'drum', type: d.type, t: t0, vel: d.v, section: sectionOf(d.bar).id });
}
for (const o of ORGAN) {
  const t0 = T(o.bar, o.p), dur = D(o.bar, o.p, o.dur);
  native.push({ t: t0, type: 'organ', dur, midis: o.midis, v: o.v * 0.5, att: o.att, rel: o.rel });
  events.push({ id: events.length, inst: 'organ', midis: o.midis, t: t0, dur, vel: o.v, section: sectionOf(o.bar).id });
}
for (const p of PARAM) native.push({ t: Math.max(0, T(p.bar, p.p) - 0.05), type: 'param', name: p.name, v: p.v, tc: p.tc });
native.sort((a, b) => a.t - b.t);
for (const k in cmds) cmds[k].sort((a, b) => a.t - b.t);
events.sort((a, b) => a.t - b.t || a.id - b.id);
events.forEach((e, i) => { e.id = i; });

const bars = [];
for (let b = 0; b < NBARS; b++) {
  const c0 = chordAt(b, 0), c6 = chordAt(b, 6);
  bars.push({ i: b, t0: T(b, 0), t1: b === NBARS - 1 ? END : T(b + 1, 0), section: sectionOf(b).id, chords: c0 === c6 ? [DISPLAY[c0] || c0] : [DISPLAY[c0] || c0, DISPLAY[c6] || c6],
    tension: TENSION[b], pressure: [PRESSURE[c0], PRESSURE[c6]], roots: [ROOT[c0] % 12, ROOT[c6] % 12] });
}
const sections = SECTIONS.map(s => ({ ...s, t0: T(s.bar0, 0), t1: s.bar1 >= NBARS ? END : T(s.bar1, 0) }));

global.FilamentScore = {
  meta: { title: 'FILAMENT', subtitle: 'a blues in A minor (solo in D Dorian)', bpm: BPM, meter: '12/8', seed: SEED, pre: PRE,
    finalChord: FINAL_T, damp: DAMP_T, duration: END, sampleRate: 48000, fps: 60, frames: Math.round(END * 60) },
  sections, bars, events, cmds, native, T
};
})(typeof window !== 'undefined' ? window : globalThis);
