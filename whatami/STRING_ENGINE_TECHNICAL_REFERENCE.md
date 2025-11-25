# STRING ENGINE TECHNICAL REFERENCE
## Universal Musical Programming Framework

**Version 1.0 | Comprehensive Whiteboard Reference**

---

# PART I: ARCHITECTURE OVERVIEW

## The Three Pillars

Every music program in this system rests on three integrated subsystems:

```
┌─────────────────────────────────────────────────────────────────┐
│                      STRING ENGINE                               │
├───────────────────┬───────────────────┬─────────────────────────┤
│   1. AUDIO        │   2. SEQUENCER    │   3. VISUAL             │
│   ENGINE          │   ENGINE          │   ENGINE                │
├───────────────────┼───────────────────┼─────────────────────────┤
│ • Sound synthesis │ • Beat tracking   │ • Canvas rendering      │
│ • Effects chain   │ • Tab/note data   │ • Note visualization    │
│ • Tone shaping    │ • Lookahead sched │ • Hit feedback          │
└───────────────────┴───────────────────┴─────────────────────────┘
```

---

# PART II: THE CONFIGURATION BLOCK

## Essential Configuration

Every program begins with a CONFIG object that establishes the musical foundation:

```javascript
const CONFIG = {
    BPM: 120,                                          // Tempo
    STRINGS: [64, 59, 55, 50, 45, 40],                // MIDI notes
    BASE_FREQS: [329.63, 246.94, 196.00, 146.83, 110.00, 82.41],  // Hz
    STRING_NAMES: ['e', 'B', 'G', 'D', 'A', 'E']      // Labels
};
```

### Standard Guitar Tuning Reference

| String | Name | MIDI | Frequency (Hz) |
|--------|------|------|----------------|
| 0      | e    | 64   | 329.63        |
| 1      | B    | 59   | 246.94        |
| 2      | G    | 55   | 196.00        |
| 3      | D    | 50   | 146.83        |
| 4      | A    | 45   | 110.00        |
| 5      | E    | 40   | 82.41         |

### Alternate Tunings

**Drop D:**
```javascript
BASE_FREQS: [329.63, 246.94, 196.00, 146.83, 110.00, 73.42]  // Low string = D
STRING_NAMES: ['e', 'B', 'G', 'D', 'A', 'D']
```

**Open G (Slide/Blues):**
```javascript
BASE_FREQS: [293.66, 246.94, 196.00, 146.83, 110.00, 73.42]  // D-B-G-D-G-D
```

---

# PART III: THE AUDIO ENGINE

## Core Architecture Pattern

```javascript
const AudioEngine = {
    ctx: null,           // Web Audio Context
    master: null,        // Master gain node
    reverb: null,        // Convolver node
    reverbGain: null,    // Wet/dry control
    isPlaying: false,    // Playback state
    
    init: async () => { ... },
    playString: (stringIdx, fret, time, duration) => { ... },
    createImpulse: async (duration, decay) => { ... },
    setReverb: (val) => { ... }
};
```

## Initialization Pattern

```javascript
init: async () => {
    const AC = window.AudioContext || window.webkitAudioContext;
    AudioEngine.ctx = new AC();
    
    // Master output
    AudioEngine.master = AudioEngine.ctx.createGain();
    AudioEngine.master.gain.value = 0.5;
    
    // Effects chain...
    AudioEngine.master.connect(AudioEngine.ctx.destination);
}
```

---

## TONE RECIPES

### 1. Clean Acoustic / Nylon Guitar

**Character:** Warm, round, woody
**Use for:** Classical, Fingerstyle, Folk, Latin

```javascript
playString: (stringIdx, fret, time, duration = 1.2) => {
    const freq = CONFIG.BASE_FREQS[stringIdx] * Math.pow(2, fret / 12);
    
    // OSCILLATOR MIX: Sine dominant + Triangle harmonics
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    const osc3 = ctx.createOscillator();
    
    osc1.type = 'triangle';  // Body
    osc2.type = 'sine';      // 2nd harmonic
    osc3.type = 'sine';      // 3rd harmonic
    
    osc1.frequency.value = freq;
    osc2.frequency.value = freq * 2;
    osc3.frequency.value = freq * 3;
    
    // MIX RATIOS
    const g1 = ctx.createGain(); g1.gain.value = 0.5;  // Fundamental
    const g2 = ctx.createGain(); g2.gain.value = 0.3;  // 2nd
    const g3 = ctx.createGain(); g3.gain.value = 0.2;  // 3rd
    
    // FILTER: Warm lowpass with decay
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(3000, time);
    filter.frequency.exponentialRampToValueAtTime(800, time + 0.2);
    filter.Q.value = 1;
    
    // ENVELOPE: Fast attack, natural decay
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0, time);
    amp.gain.linearRampToValueAtTime(0.45, time + 0.008);   // 8ms attack
    amp.gain.exponentialRampToValueAtTime(0.2, time + 0.15);
    amp.gain.exponentialRampToValueAtTime(0.001, time + duration);
}
```

### 2. High Gain / Metal

**Character:** Aggressive, saturated, tight
**Use for:** Metal, Hard Rock, Djent

```javascript
// DISTORTION CURVE
makeDistortionCurve: (amount) => {
    const k = amount;  // 0 = clean, 400+ = extreme
    const n = 44100;
    const curve = new Float32Array(n);
    for (let i = 0; i < n; i++) {
        let x = i * 2 / n - 1;
        curve[i] = Math.tanh(k * x);  // Soft clipping
    }
    return curve;
}

// METAL TONE
playString: (stringIdx, fret, time, duration = 0.4) => {
    const freq = CONFIG.BASE_FREQS[stringIdx] * Math.pow(2, fret / 12);
    
    // OSCILLATOR MIX: Sawtooth + Square (aggressive harmonics)
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    
    osc1.type = 'sawtooth';
    osc2.type = 'square';
    osc2.detune.value = 5;  // Slight detune for thickness
    
    osc1.frequency.value = freq;
    osc2.frequency.value = freq;
    
    // FILTER: Tight lowpass (simulate cab)
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 3500;
    filter.Q.value = 1;
    
    // SHORT ENVELOPE (tight, punchy)
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0, time);
    amp.gain.linearRampToValueAtTime(0.5, time + 0.005);
    amp.gain.exponentialRampToValueAtTime(0.001, time + duration);
    
    // Route through distortion
    amp.connect(AudioEngine.drive);
}
```

### 3. Blues / Rock Lead (Sustaining)

**Character:** Singing, sustaining, expressive
**Use for:** Blues solos, Santana-style, Classic rock

```javascript
playString: (stringIdx, fret, time, duration = 2.5, bend = null) => {
    const baseFreq = CONFIG.BASE_FREQS[stringIdx];
    const freq = baseFreq * Math.pow(2, fret / 12);
    
    // OSCILLATORS: Sawtooth + Square with slight detuning
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    
    osc1.type = 'sawtooth';
    osc2.type = 'square';
    osc2.detune.value = 5;
    
    // VIBRATO (adds life to sustains)
    const vib = ctx.createOscillator();
    const vibGain = ctx.createGain();
    vib.frequency.value = 5.5;  // ~5.5 Hz human vibrato
    vibGain.gain.value = 8;     // Subtle pitch deviation
    vib.connect(vibGain);
    vibGain.connect(osc1.frequency);
    vibGain.connect(osc2.frequency);
    vib.start(time + 0.3);  // Delay vibrato onset
    
    // BEND LOGIC
    if (bend === 'full') {
        const targetFreq = freq * Math.pow(2, 2/12);  // Whole step
        osc1.frequency.setValueAtTime(freq, time);
        osc1.frequency.linearRampToValueAtTime(targetFreq, time + 0.2);
    }
    
    // SUSTAINING ENVELOPE
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0, time);
    amp.gain.linearRampToValueAtTime(0.5, time + 0.01);
    amp.gain.exponentialRampToValueAtTime(0.3, time + 0.2);  // Sustain level
    amp.gain.exponentialRampToValueAtTime(0.001, time + duration);
}
```

### 4. Ska / Reggae (Choppy)

**Character:** Bright, staccato, rhythmic
**Use for:** Ska, Reggae, Funk rhythm

```javascript
playString: (stringIdx, fret, time, duration = 0.15) => {
    // KEY: Very short duration creates the "chop"
    
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    
    osc1.type = 'triangle';   // Body
    osc2.type = 'sawtooth';   // Bite
    
    // BRIGHT FILTER
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 5000;  // Let highs through
    
    // STACCATO ENVELOPE
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0, time);
    amp.gain.linearRampToValueAtTime(0.5, time + 0.01);
    amp.gain.exponentialRampToValueAtTime(0.001, time + duration);  // Quick cutoff
}
```

---

## EFFECTS CHAIN PATTERNS

### Reverb (Convolver-based)

```javascript
createImpulse: async (duration, decay) => {
    const rate = AudioEngine.ctx.sampleRate;
    const length = rate * duration;
    const impulse = AudioEngine.ctx.createBuffer(2, length, rate);
    const L = impulse.getChannelData(0);
    const R = impulse.getChannelData(1);
    
    for (let i = 0; i < length; i++) {
        // Exponential decay envelope on noise
        L[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, decay);
        R[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, decay);
    }
    return impulse;
}

// USAGE GUIDE:
// createImpulse(2.5, 2.5) → Hall (long, natural)
// createImpulse(1.0, 4.0) → Room (short, tight)
// createImpulse(1.5, 4.0) → Spring (twangy, with chirp mod)
```

### Spring Reverb (with chirp)

```javascript
// Simulates spring tank character
for (let i = 0; i < length; i++) {
    const chirp = Math.sin(i * 0.1) * 0.5;  // Metallic resonance
    L[i] = ((Math.random() * 2 - 1) + chirp) * Math.pow(1 - i / length, decay);
    R[i] = ((Math.random() * 2 - 1) - chirp) * Math.pow(1 - i / length, decay);
}
```

### Slapback Delay

```javascript
AudioEngine.delay = AudioEngine.ctx.createDelay(1.0);
AudioEngine.delay.delayTime.value = 0.18;  // 180ms slapback

AudioEngine.delayGain = AudioEngine.ctx.createGain();
AudioEngine.delayGain.gain.value = 0.15;  // Mix level

// Routing
AudioEngine.master.connect(AudioEngine.delay);
AudioEngine.delay.connect(AudioEngine.delayGain);
AudioEngine.delayGain.connect(AudioEngine.ctx.destination);
```

### EQ Shaping

```javascript
// Body resonance (warm up low-mids)
AudioEngine.body = AudioEngine.ctx.createBiquadFilter();
AudioEngine.body.type = 'peaking';
AudioEngine.body.frequency.value = 250;
AudioEngine.body.gain.value = 4;
AudioEngine.body.Q.value = 2;

// Presence (add clarity)
AudioEngine.eq = AudioEngine.ctx.createBiquadFilter();
AudioEngine.eq.type = 'peaking';
AudioEngine.eq.frequency.value = 2500;
AudioEngine.eq.gain.value = 3;
AudioEngine.eq.Q.value = 1;
```

---

## PERCUSSION SYNTHESIS

### Kick Drum

```javascript
playKick: (time) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    // PITCH SWEEP: High → Low creates "punch"
    osc.frequency.setValueAtTime(180, time);
    osc.frequency.exponentialRampToValueAtTime(50, time + 0.1);
    
    // ENVELOPE
    gain.gain.setValueAtTime(1.0, time);
    gain.gain.exponentialRampToValueAtTime(0.001, time + 0.3);
    
    osc.connect(gain);
    gain.connect(AudioEngine.drumBus);
    
    osc.start(time);
    osc.stop(time + 0.3);
}
```

### Snare / Clap

```javascript
playSnare: (time) => {
    // NOISE COMPONENT
    const bufSize = ctx.sampleRate * 0.1;
    const buffer = ctx.createBuffer(1, bufSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufSize; i++) data[i] = Math.random() * 2 - 1;
    
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;
    
    // HIGHPASS for "crack"
    const filter = ctx.createBiquadFilter();
    filter.type = 'highpass';
    filter.frequency.value = 2000;
    
    const env = ctx.createGain();
    env.gain.setValueAtTime(0.6, time);
    env.gain.exponentialRampToValueAtTime(0.001, time + 0.1);
    
    noise.connect(filter);
    filter.connect(env);
    env.connect(AudioEngine.drumBus);
    noise.start(time);
    
    // BODY (optional for "snare" vs "clap")
    const osc = ctx.createOscillator();
    osc.frequency.setValueAtTime(250, time);
    osc.frequency.exponentialRampToValueAtTime(150, time + 0.1);
    // ... envelope and routing
}
```

### Hi-Hat

```javascript
playHat: (time) => {
    const bufSize = ctx.sampleRate * 0.05;  // Very short
    const buffer = ctx.createBuffer(1, bufSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufSize; i++) data[i] = Math.random() * 2 - 1;
    
    const noise = ctx.createBufferSource();
    noise.buffer = buffer;
    
    // HIGH FREQUENCY FILTER (sizzle)
    const filter = ctx.createBiquadFilter();
    filter.type = 'highpass';
    filter.frequency.value = 10000;
    
    const env = ctx.createGain();
    env.gain.setValueAtTime(0.3, time);
    env.gain.exponentialRampToValueAtTime(0.001, time + 0.03);  // Very fast decay
    
    noise.connect(filter);
    filter.connect(env);
    noise.start(time);
}
```

### Dead Note / Chug (Palm Mute Simulation)

```javascript
playChug: (time) => {
    const noise = ctx.createBufferSource();
    const noiseBuffer = ctx.createBuffer(1, 4410, ctx.sampleRate);
    const data = noiseBuffer.getChannelData(0);
    for (let i = 0; i < 4410; i++) data[i] = Math.random() * 2 - 1;
    noise.buffer = noiseBuffer;
    
    // BANDPASS creates "chunk" character
    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = 150;
    filter.Q.value = 5;
    
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0, time);
    amp.gain.linearRampToValueAtTime(0.6, time + 0.005);
    amp.gain.exponentialRampToValueAtTime(0.001, time + 0.08);
    
    noise.connect(filter);
    filter.connect(amp);
    amp.connect(AudioEngine.preGain);  // Route through distortion
    noise.start(time);
}
```

### 808 Bass

```javascript
playBass: (freq, time, duration) => {
    // SINE for sub
    const osc = ctx.createOscillator();
    osc.type = 'sine';
    osc.frequency.value = freq;
    
    // SQUARE for texture (quiet)
    const osc2 = ctx.createOscillator();
    osc2.type = 'square';
    osc2.frequency.value = freq;
    
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0, time);
    amp.gain.linearRampToValueAtTime(0.8, time + 0.01);
    amp.gain.setValueAtTime(0.8, time + duration - 0.05);
    amp.gain.linearRampToValueAtTime(0, time + duration);
    
    // Lowpass on square
    const filter = ctx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = 400;
    
    osc.connect(amp);
    osc2.connect(filter);
    filter.connect(ctx.createGain()).gain.value = 0.2;
    // ... routing
}
```

---

# PART IV: THE SEQUENCER ENGINE

## Duration Constants

```javascript
const X = 0.125;   // 32nd note
const S = 0.25;    // 16th note
const T = 0.167;   // Triplet eighth
const E = 0.5;     // 8th note
const Q = 1.0;     // Quarter note
const H = 2.0;     // Half note
const W = 4.0;     // Whole note
```

## Note Data Structure

```javascript
const TAB = [];

function addNote(beat, string, fret, type = 'pluck', target = null) {
    TAB.push({ beat, string, fret, type, target });
}

// WITH SECTIONS (for visual display)
function addNote(beat, string, fret) {
    TAB.push({ beat, string, fret, section: currentSection });
}
```

### Extended Note Types

```javascript
// Standard note
{ beat: 0, string: 0, fret: 5 }

// Slide
{ beat: 0, string: 0, fret: 5, type: 'slide', target: 7 }

// Bend
{ beat: 0, string: 0, fret: 5, bend: 'full' }      // Whole step
{ beat: 0, string: 0, fret: 5, bend: 'half' }      // Half step
{ beat: 0, string: 0, fret: 5, bend: 'release' }   // Release from bend

// Palm mute
{ beat: 0, string: 0, fret: 5, technique: 'pm' }

// Dead note
{ beat: 0, string: 0, fret: 0, type: 'x' }

// Tremolo
{ beat: 0, string: 0, fret: 5, technique: 'trem' }

// Vibrato
{ beat: 0, string: 0, fret: 5, technique: 'vib' }
```

## The Scheduler

```javascript
let currentBeat = -1.0;   // Start with lead-in
let startTime = 0;
let nextNoteIdx = 0;

function scheduler() {
    if (!AudioEngine.isPlaying) return;
    
    const currentTime = AudioEngine.ctx.currentTime;
    const elapsed = currentTime - startTime;
    currentBeat = elapsed * (CONFIG.BPM / 60);
    
    // LOOP LOGIC
    if (currentBeat >= LOOP_LENGTH) {
        startTime = currentTime;
        currentBeat = 0;
        nextNoteIdx = 0;
    }
    
    // LOOKAHEAD SCHEDULING (0.1 beats ahead)
    while (nextNoteIdx < TAB.length) {
        const note = TAB[nextNoteIdx];
        
        if (note.beat <= currentBeat + 0.1) {
            // Convert beat to absolute time
            const playTime = startTime + (note.beat * (60 / CONFIG.BPM));
            
            // Dispatch to audio engine
            if (note.type === 'x') {
                AudioEngine.playDeadNote(playTime);
            } else if (note.type === 'slide') {
                AudioEngine.playString(note.string, note.fret, playTime, 1.5, note.target);
            } else {
                AudioEngine.playString(note.string, note.fret, playTime, 1.5);
            }
            
            // Trigger visual feedback
            triggerVisual(note);
            
            nextNoteIdx++;
        } else {
            break;
        }
    }
    
    requestAnimationFrame(scheduler);
}
```

---

# PART V: COMPOSITION PATTERNS

## Chord Helper Functions

### Rasgueado (Rapid Strum)

```javascript
function rasgueado(beat, chord, speed = 0.02) {
    chord.forEach((note, i) => {
        addNote(beat + i * speed, note[0], note[1]);
    });
}

// Usage
const Am = [[5,0], [4,0], [3,2], [2,2], [1,1], [0,0]];
rasgueado(b, Am);
```

### Tremolo Pattern

```javascript
function tremolo(beat, string, fret, duration, speed = 0.08) {
    let t = beat;
    while (t < beat + duration) {
        addNote(t, string, fret);
        t += speed;
    }
}

// Usage: Bass note + tremolo melody
addNote(b, 4, 0);                           // Bass A
tremolo(b + 0.05, 0, 12, Q * 1.5, 0.06);    // High E tremolo
```

### Chord Strum

```javascript
function addChord(beat, notes) {
    notes.forEach(n => addNote(beat, n[0], n[1]));
}

// Usage
const Em7 = [[0,0], [1,3], [2,0], [3,0], [4,2], [5,0]];
addChord(b, Em7);
```

### Arpeggio

```javascript
function arpeggio(beat, chord, speed = 0.125) {
    chord.forEach((note, i) => {
        addNote(beat + i * speed, note[0], note[1]);
    });
}
```

### Power Chord (Drop D)

```javascript
function addPowerChord(beat, rootFret, technique = null) {
    TAB.push({ beat, type: 'power', fret: rootFret, technique });
}

// In playback:
playPowerChord: (rootFret, time, duration = 0.3, technique = null) => {
    AudioEngine.playString(5, rootFret, time, duration, technique);
    AudioEngine.playString(4, rootFret, time + 0.005, duration, technique);
    AudioEngine.playString(3, rootFret + 2, time + 0.01, duration, technique);  // 5th
}
```

---

## Common Chord Voicings

### Open Position

```javascript
const Am    = [[5,0], [4,0], [3,2], [2,2], [1,1], [0,0]];
const E7    = [[5,0], [4,2], [3,0], [2,1], [1,0], [0,0]];
const F     = [[5,1], [4,3], [3,3], [2,2], [1,1], [0,1]];
const G     = [[5,3], [4,2], [3,0], [2,0], [1,0], [0,3]];
const Dm    = [[4,0], [3,0], [2,2], [1,3], [0,1]];
const C     = [[4,3], [3,2], [2,0], [1,1], [0,0]];
const Em    = [[5,0], [4,2], [3,2], [2,0], [1,0], [0,0]];
```

### Flamenco Voicings

```javascript
const E7b9  = [[5,0], [4,2], [3,0], [2,1], [1,0], [0,1]];  // "The" flamenco chord
const Fmaj7 = [[5,1], [4,3], [3,2], [2,2], [1,1], [0,0]];
const Am9   = [[5,0], [4,0], [3,2], [2,0], [1,1], [0,0]];
```

### Acoustic Open Voicings (Wonderwall style)

```javascript
const Em7    = [[5,0], [4,2], [3,0], [2,0], [1,3], [0,3]];
const G      = [[5,3], [4,2], [3,0], [2,0], [1,3], [0,3]];
const Dsus4  = [[3,0], [2,2], [1,3], [0,3]];
const A7sus4 = [[4,0], [3,2], [2,0], [1,3], [0,0]];
const Cadd9  = [[4,3], [3,2], [2,0], [1,3], [0,3]];
```

---

## Scale Patterns

### E Phrygian Dominant (Spanish)
**Intervals:** E F G# A B C D

```javascript
const phryDom = [0, 1, 4, 5, 7, 8, 10, 12];  // Frets from E root

// Ascending run on low E string
phryDom.forEach(fret => {
    addNote(b, 5, fret); b += S;
});
```

### E Harmonic Minor
**Intervals:** E F# G A B C D#

```javascript
const harmMinor = [0, 2, 3, 5, 7, 8, 11, 12];

harmMinor.forEach((fret, i) => {
    addNote(b, 3, fret); b += S;
});
```

### Pentatonic Box (Position 1, Minor)

```javascript
// A Minor Pentatonic, 5th position
const pentatonic = [
    [0, 5], [0, 8],           // High E: A, C
    [1, 5], [1, 8],           // B: E, G
    [2, 5], [2, 7],           // G: C, D
    [3, 5], [3, 7],           // D: G, A
    [4, 5], [4, 7],           // A: D, E
    [5, 5], [5, 8]            // Low E: A, C
];
```

---

## Rhythmic Patterns

### Gallop (Thrash Metal)

```javascript
for (let rep = 0; rep < 4; rep++) {
    addNote(b, 5, 0, 'pm'); b += S;   // Palm muted
    addNote(b, 5, 0, 'pm'); b += S;
    addNote(b, 5, 0, 'pm'); b += E;
}
```

### Ska Upstroke

```javascript
// Off-beat emphasis
b += E;  // Skip downbeat
addChord(b, chord); b += E;  // Staccato chord
b += E;  // Rest
addChord(b, chord); b += E;
```

### Fingerpicking Pattern

```javascript
// Travis picking style
function travisPattern(beat, chord) {
    addNote(beat + 0.0, 5, chord[5][1]);     // Bass
    addNote(beat + 0.25, 2, chord[2][1]);    // Treble
    addNote(beat + 0.5, 4, chord[4][1]);     // Alt bass
    addNote(beat + 0.75, 1, chord[1][1]);    // Treble
    addNote(beat + 1.0, 5, chord[5][1]);     // Bass
    addNote(beat + 1.25, 0, chord[0][1]);    // High
    addNote(beat + 1.5, 4, chord[4][1]);     // Alt bass
    addNote(beat + 1.75, 2, chord[2][1]);    // Treble
}
```

### 12-Beat Compás (Flamenco)

```javascript
// Traditional Soleá rhythm
for (let cycle = 0; cycle < 2; cycle++) {
    // Beat 1-2-3
    rasgueado(b, Am); b += Q;
    addNote(b, 4, 0); addNote(b, 0, 0); b += E;
    addNote(b, 3, 2); b += E;
    rasgueado(b, Am); b += Q;
    
    // Beat 4-5-6
    rasgueado(b, G); b += Q;
    addNote(b, 5, 3); addNote(b, 0, 3); b += E;
    addNote(b, 4, 2); b += E;
    rasgueado(b, G); b += Q;
    
    // Beat 7-8
    rasgueado(b, F); b += Q;
    addNote(b, 5, 1); addNote(b, 0, 1); b += E;
    addNote(b, 4, 3); b += E;
    
    // Beat 9-10 (ACCENT)
    rasgueado(b, E7); b += E;
    rasgueado(b, E7); b += S;
    rasgueado(b, E7); b += S;
    rasgueado(b, E7); b += Q;
    
    // Beat 11-12 (resolution)
    addNote(b, 5, 0); addNote(b, 4, 2); addNote(b, 3, 2); b += E;
    addNote(b, 2, 1); b += E;
    addNote(b, 1, 0); b += E;
    addNote(b, 0, 0); b += E;
}
```

### Djent Syncopation

```javascript
const breakdownRhythm = [1,0,0,1,0,1,1,0, 1,0,0,1,0,0,1,1];

breakdownRhythm.forEach(hit => {
    if (hit) {
        addPowerChord(b, 0, 'pm');
    } else {
        addChug(b);
    }
    b += S;
});
```

---

# PART VI: THE VISUAL ENGINE

## Core Structure

```javascript
const cvs = document.getElementById('canvas');
const ctx = cvs.getContext('2d');
let w, h;
const activeNotes = [];

function resize() {
    w = cvs.width = window.innerWidth;
    h = cvs.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();

function triggerVisual(note) {
    activeNotes.push({
        ...note,
        x: w * 0.2,    // Hit line position
        life: 1.0,
        born: Date.now()
    });
}
```

## Draw Loop Pattern

```javascript
function draw() {
    // Clear (with optional trail effect)
    ctx.fillStyle = 'rgba(5, 5, 5, 0.15)';  // Trail
    ctx.fillRect(0, 0, w, h);
    // OR: ctx.clearRect(0, 0, w, h);       // No trail
    
    const STAFF_Y = h / 2;
    const SPACING = 30;
    const HIT_X = w * 0.2;
    const pixelsPerBeat = 150;
    
    // DRAW STRING LINES
    ctx.lineWidth = 1;
    ctx.strokeStyle = '#333';
    ctx.font = "14px monospace";
    ctx.fillStyle = '#888';
    
    CONFIG.STRING_NAMES.forEach((name, i) => {
        const y = STAFF_Y + (i * SPACING) - (2.5 * SPACING);
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
        ctx.fillText(name, 10, y + 5);
    });
    
    // DRAW HIT LINE
    ctx.beginPath();
    ctx.moveTo(HIT_X, STAFF_Y - 100);
    ctx.lineTo(HIT_X, STAFF_Y + 100);
    ctx.strokeStyle = '#ff2200';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // DRAW INCOMING NOTES
    TAB.forEach(note => {
        let dist = note.beat - currentBeat;
        if (dist < -2) dist += LOOP_LENGTH;  // Wrap for loop
        
        const x = HIT_X + (dist * pixelsPerBeat);
        
        if (x > 0 && x < w) {
            const y = STAFF_Y + (note.string * SPACING) - (2.5 * SPACING);
            
            // Circle background
            ctx.beginPath();
            ctx.arc(x, y, 10, 0, Math.PI * 2);
            ctx.fillStyle = '#1a1a1a';
            ctx.fill();
            ctx.strokeStyle = '#ff2200';
            ctx.lineWidth = 1.5;
            ctx.stroke();
            
            // Fret number
            ctx.fillStyle = '#fff';
            ctx.fillText(note.fret, x - 4, y + 4);
        }
    });
    
    // DRAW HIT ANIMATIONS (ripples)
    for (let i = activeNotes.length - 1; i >= 0; i--) {
        const n = activeNotes[i];
        const y = STAFF_Y + (n.string * SPACING) - (2.5 * SPACING);
        
        const radius = 12 + ((1 - n.life) * 50);  // Expanding
        ctx.beginPath();
        ctx.arc(HIT_X, y, radius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255, 34, 0, ${n.life})`;  // Fading
        ctx.lineWidth = 2;
        ctx.stroke();
        
        n.life -= 0.05;  // Decay rate
        if (n.life <= 0) activeNotes.splice(i, 1);
    }
    
    requestAnimationFrame(draw);
}
```

---

# PART VII: USER INTERACTION

## Standard Input Pattern

```javascript
document.addEventListener('keydown', (e) => {
    if (e.code === 'Space') {
        e.preventDefault();
        togglePlay();
    }
});

document.addEventListener('click', () => {
    if (!AudioEngine.ctx) {
        AudioEngine.init();
        togglePlay();
    }
});

// Interactive parameter control
document.addEventListener('mousemove', (e) => {
    if (!AudioEngine.ctx) return;
    
    const y = e.clientY / window.innerHeight;
    
    // Map Y axis to effect (examples):
    AudioEngine.setReverb(y * 0.5);           // Reverb wet
    AudioEngine.setDistortion(1 - y);          // Drive amount
    AudioEngine.filter.frequency.setTargetAtTime(
        200 + ((1-y) * 19800),                 // Filter sweep
        AudioEngine.ctx.currentTime, 
        0.1
    );
});
```

## Play/Pause Toggle

```javascript
function togglePlay() {
    if (AudioEngine.isPlaying) {
        AudioEngine.isPlaying = false;
        document.getElementById('overlay').classList.remove('hidden');
    } else {
        AudioEngine.isPlaying = true;
        document.getElementById('overlay').classList.add('hidden');
        
        // Seamless resume
        startTime = AudioEngine.ctx.currentTime - (currentBeat * (60 / CONFIG.BPM));
        scheduler();
    }
}
```

---

# PART VIII: COMPLETE TEMPLATE

## Minimal Working Example

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>String Engine Template</title>
<style>
    body { margin: 0; background: #111; overflow: hidden; color: #fff; font-family: monospace; }
    #canvas { display: block; position: absolute; top: 0; left: 0; width: 100%; height: 100%; }
    #overlay { position: absolute; top: 0; left: 0; width: 100%; height: 100%;
               display: flex; flex-direction: column; justify-content: center; align-items: center;
               background: rgba(0,0,0,0.95); z-index: 10; transition: opacity 0.5s; }
    .hidden { opacity: 0; pointer-events: none; }
</style>
</head>
<body>

<div id="overlay">
    <h1>TITLE</h1>
    <p>[ CLICK TO PLAY ]</p>
</div>
<canvas id="canvas"></canvas>

<script>
// ═══════════════════════════════════════════════════════════════
// CONFIG
// ═══════════════════════════════════════════════════════════════
const CONFIG = {
    BPM: 120,
    BASE_FREQS: [329.63, 246.94, 196.00, 146.83, 110.00, 82.41],
    STRING_NAMES: ['e', 'B', 'G', 'D', 'A', 'E']
};

// ═══════════════════════════════════════════════════════════════
// AUDIO ENGINE
// ═══════════════════════════════════════════════════════════════
const AudioEngine = {
    ctx: null,
    master: null,
    isPlaying: false,

    init: async () => {
        AudioEngine.ctx = new (window.AudioContext || window.webkitAudioContext)();
        AudioEngine.master = AudioEngine.ctx.createGain();
        AudioEngine.master.gain.value = 0.5;
        AudioEngine.master.connect(AudioEngine.ctx.destination);
    },

    playString: (stringIdx, fret, time, duration = 1.0) => {
        if (!AudioEngine.ctx) return;
        const freq = CONFIG.BASE_FREQS[stringIdx] * Math.pow(2, fret / 12);
        
        const osc = AudioEngine.ctx.createOscillator();
        osc.type = 'triangle';
        osc.frequency.value = freq;
        
        const amp = AudioEngine.ctx.createGain();
        amp.gain.setValueAtTime(0, time);
        amp.gain.linearRampToValueAtTime(0.4, time + 0.01);
        amp.gain.exponentialRampToValueAtTime(0.001, time + duration);
        
        osc.connect(amp);
        amp.connect(AudioEngine.master);
        osc.start(time);
        osc.stop(time + duration);
    }
};

// ═══════════════════════════════════════════════════════════════
// TAB DATA
// ═══════════════════════════════════════════════════════════════
const TAB = [];
function addNote(beat, string, fret) { TAB.push({ beat, string, fret }); }

const S = 0.25, E = 0.5, Q = 1.0, H = 2.0;
let b = 0;

// ═══════════════════════════════════════════════════════════════
// COMPOSE YOUR MUSIC HERE
// ═══════════════════════════════════════════════════════════════
addNote(b, 5, 0); b += Q;
addNote(b, 4, 2); b += Q;
addNote(b, 3, 2); b += Q;
addNote(b, 2, 0); b += Q;

const LOOP_LENGTH = b + 1;

// ═══════════════════════════════════════════════════════════════
// SEQUENCER
// ═══════════════════════════════════════════════════════════════
let currentBeat = 0, startTime = 0, nextNoteIdx = 0;

function scheduler() {
    if (!AudioEngine.isPlaying) return;
    const currentTime = AudioEngine.ctx.currentTime;
    currentBeat = (currentTime - startTime) * (CONFIG.BPM / 60);
    
    if (currentBeat >= LOOP_LENGTH) {
        startTime = currentTime;
        currentBeat = 0;
        nextNoteIdx = 0;
    }
    
    while (nextNoteIdx < TAB.length && TAB[nextNoteIdx].beat <= currentBeat + 0.1) {
        const note = TAB[nextNoteIdx];
        const playTime = startTime + (note.beat * (60 / CONFIG.BPM));
        AudioEngine.playString(note.string, note.fret, playTime);
        triggerVisual(note);
        nextNoteIdx++;
    }
    
    requestAnimationFrame(scheduler);
}

// ═══════════════════════════════════════════════════════════════
// VISUAL ENGINE
// ═══════════════════════════════════════════════════════════════
const cvs = document.getElementById('canvas');
const ctx = cvs.getContext('2d');
let w, h;
const activeNotes = [];

function resize() { w = cvs.width = innerWidth; h = cvs.height = innerHeight; }
window.addEventListener('resize', resize);
resize();

function triggerVisual(note) { activeNotes.push({ ...note, life: 1.0 }); }

function draw() {
    ctx.clearRect(0, 0, w, h);
    const STAFF_Y = h / 2, SPACING = 30, HIT_X = w * 0.2;
    
    // Strings
    ctx.strokeStyle = '#333'; ctx.lineWidth = 1;
    CONFIG.STRING_NAMES.forEach((name, i) => {
        const y = STAFF_Y + (i - 2.5) * SPACING;
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
        ctx.fillStyle = '#666'; ctx.fillText(name, 10, y + 5);
    });
    
    // Hit line
    ctx.strokeStyle = '#f00'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(HIT_X, STAFF_Y - 90); ctx.lineTo(HIT_X, STAFF_Y + 90); ctx.stroke();
    
    // Notes
    const pixelsPerBeat = 150;
    TAB.forEach(note => {
        let dist = note.beat - currentBeat;
        if (dist < -2) dist += LOOP_LENGTH;
        const x = HIT_X + dist * pixelsPerBeat;
        if (x > 0 && x < w) {
            const y = STAFF_Y + (note.string - 2.5) * SPACING;
            ctx.beginPath(); ctx.arc(x, y, 10, 0, Math.PI * 2);
            ctx.fillStyle = '#222'; ctx.fill();
            ctx.strokeStyle = '#f00'; ctx.stroke();
            ctx.fillStyle = '#fff'; ctx.fillText(note.fret, x - 4, y + 4);
        }
    });
    
    // Ripples
    for (let i = activeNotes.length - 1; i >= 0; i--) {
        const n = activeNotes[i];
        const y = STAFF_Y + (n.string - 2.5) * SPACING;
        ctx.beginPath(); ctx.arc(HIT_X, y, 12 + (1 - n.life) * 40, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255, 0, 0, ${n.life})`; ctx.stroke();
        n.life -= 0.05;
        if (n.life <= 0) activeNotes.splice(i, 1);
    }
    
    requestAnimationFrame(draw);
}

// ═══════════════════════════════════════════════════════════════
// CONTROLS
// ═══════════════════════════════════════════════════════════════
document.addEventListener('click', () => {
    if (!AudioEngine.ctx) { AudioEngine.init(); togglePlay(); }
});

document.addEventListener('keydown', e => { if (e.code === 'Space') { e.preventDefault(); togglePlay(); } });

function togglePlay() {
    if (AudioEngine.isPlaying) {
        AudioEngine.isPlaying = false;
        document.getElementById('overlay').classList.remove('hidden');
    } else {
        AudioEngine.isPlaying = true;
        document.getElementById('overlay').classList.add('hidden');
        startTime = AudioEngine.ctx.currentTime - (currentBeat * (60 / CONFIG.BPM));
        scheduler();
    }
}

draw();
</script>
</body>
</html>
```

---

# PART IX: GENRE QUICK REFERENCE

| Genre | BPM | Oscillators | Filter | Attack | Decay | Effects | Rhythm Pattern |
|-------|-----|-------------|--------|--------|-------|---------|----------------|
| Flamenco | 80-120 | Triangle + Sine harmonics | LPF 800→3000 | 8ms | 1.2s | Hall reverb | 12-beat compás |
| Metal | 160-220 | Saw + Square | LPF 3500 | 5ms | 0.3s | Short room + drive | Gallop, chugs |
| Blues | 60-100 | Saw + Square detuned | LPF 3000 | 10ms | 2.5s | Spring reverb | Shuffle, bends |
| Jazz | 100-180 | Triangle + Sine | LPF 2000 | 8ms | 1.5s | Room reverb | Chromatic runs |
| Acoustic | 80-140 | Triangle + Sine 2nd+3rd | LPF 3000→800 | 8ms | 1.0s | Hall reverb | Fingerpicking |
| Ska/Reggae | 85-95 | Triangle + Saw | HPF 200, LPF 5000 | 10ms | 0.15s | Spring | Upstroke chops |
| Classical | 60-120 | Sine + Triangle | LPF 2500 | 15ms | 2.0s | Large hall | Tremolo, arpeggios |
| K-Pop | 120-140 | Square + Sine | LPF sweep | 5ms | 0.5s | Bright reverb | Sidechain pump |

---

# PART X: TROUBLESHOOTING

## Common Issues

**No Sound**
- Check `AudioEngine.ctx` is initialized
- Verify user interaction triggered init (browser requirement)
- Check master gain value

**Clicking/Popping**
- Ensure envelope doesn't start at non-zero
- Add 1-5ms attack ramp
- Check oscillator stop time matches envelope end

**Notes Out of Sync**
- Verify lookahead timing (0.1 beat typical)
- Check `startTime` calculation
- Ensure `LOOP_LENGTH` matches composition

**Harsh/Digital Sound**
- Add lowpass filter
- Reduce high harmonic content
- Add subtle reverb
- Check oscillator mix ratios

**Memory Issues**
- Oscillators and nodes are garbage collected after stop
- Don't create new AudioContext on each play
- Clear activeNotes array properly

---

# APPENDIX: FREQUENCY REFERENCE

## Note Frequencies (A4 = 440 Hz)

| Note | Hz | Note | Hz | Note | Hz |
|------|-----|------|-----|------|-----|
| C2 | 65.41 | C3 | 130.81 | C4 | 261.63 |
| D2 | 73.42 | D3 | 146.83 | D4 | 293.66 |
| E2 | 82.41 | E3 | 164.81 | E4 | 329.63 |
| F2 | 87.31 | F3 | 174.61 | F4 | 349.23 |
| G2 | 98.00 | G3 | 196.00 | G4 | 392.00 |
| A2 | 110.00 | A3 | 220.00 | A4 | 440.00 |
| B2 | 123.47 | B3 | 246.94 | B4 | 493.88 |

## Fret-to-Frequency Formula

```javascript
frequency = baseFrequency * Math.pow(2, fret / 12);
```

---

**END OF REFERENCE DOCUMENT**

*This document synthesizes patterns from 31+ production music programs spanning flamenco, metal, classical, blues, jazz, ska, K-pop, and folk genres.*
