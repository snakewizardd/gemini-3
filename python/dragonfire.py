import math
import random
import struct
import wave

# =============================================================================
# 1. THE HYPER-CONFIG
# =============================================================================
CONFIG = {
    'SR': 44100,
    'BPM': 190,              # Blistering Speed
    'GAIN': 150.0,           # Absurd Gain
    'MASTER': 0.7,
    'SCALES': {
        # The "Yngwie" Scale (Harmonic Minor)
        'harmonic_minor': [0, 2, 3, 5, 7, 8, 11, 12],
        # The "Marty" Scale (Phrygian Dominant)
        'phrygian_dom':   [0, 1, 4, 5, 7, 8, 10, 12],
        # The "Dimebag" Chromatic passing tones
        'chromatic':      [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    }
}

# =============================================================================
# 2. DSP PHYSICS ( The "Tone" )
# =============================================================================
class ShredDSP:
    def __init__(self):
        self.delay_buf = [0.0] * int(0.4 * CONFIG['SR']) # 400ms buffer
        self.d_idx = 0
        self.last_sample = 0.0

    def process(self, raw_signal):
        # 1. PRE-DISTORTION EQ (Tighten bass)
        # High-pass filter at 300Hz to remove mud
        hpf = raw_signal - (self.last_sample * 0.85)
        self.last_sample = hpf

        # 2. GAIN STAGING
        # Boost
        boosted = hpf * CONFIG['GAIN']
        
        # 3. WAVE SHAPING (The Distortion)
        # Asymmetrical Soft Clipping (Tube-like)
        if boosted > 0:
            distorted = math.tanh(boosted) 
        else:
            # Diode clipping symmetry simulation
            distorted = math.tanh(boosted * 1.2) / 1.2

        # 4. CABINET SIMULATION (Low Pass @ 4kHz)
        # Simple IIR Filter
        cab_out = distorted * 0.2 + self.last_sample * 0.8
        self.last_sample = cab_out

        # 5. STEREO DELAY (Ping Pong Simulation - Mono downmix for WAV)
        delayed = self.delay_buf[self.d_idx]
        # Write feedback
        self.delay_buf[self.d_idx] = cab_out + (delayed * 0.4)
        self.d_idx = (self.d_idx + 1) % len(self.delay_buf)

        # Mix Dry + Wet
        return (cab_out * 0.7) + (delayed * 0.3)

def osc(freq, t, type='saw'):
    """High-aliasing oscillators for raw metal texture"""
    if freq <= 0: return 0.0
    phase = (t * freq) % 1.0
    
    if type == 'saw':
        return 2.0 * phase - 1.0
    elif type == 'square':
        return 1.0 if phase < 0.5 else -1.0
    elif type == 'sine':
        return math.sin(2 * math.pi * t * freq)
    return 0.0

# =============================================================================
# 3. THE VIRTUOSO AI ( The "High IQ" Composer )
# =============================================================================
class Virtuoso:
    def __init__(self):
        self.root = 146.83 # D3
        self.current_scale = 'harmonic_minor'
        self.samples = []
        self.beat_len = 60.0 / CONFIG['BPM']
        self.t = 0.0

    def get_freq(self, note_index, octave_offset=0):
        scale = CONFIG['SCALES'][self.current_scale]
        octave = note_index // len(scale) + octave_offset
        degree = note_index % len(scale)
        semitones = scale[degree] + (12 * octave)
        return self.root * (2 ** (semitones / 12.0))

    def render_note(self, freq, duration, technique='pick'):
        n_samples = int(duration * CONFIG['SR'])
        local_samples = []
        
        # Pinch Harmonic probability
        is_pinch = random.random() > 0.9 and technique == 'pick'
        if is_pinch: freq *= 2.0 # Artificial octave

        for i in range(n_samples):
            time_now = self.t + (i / CONFIG['SR'])
            
            # Oscillator Mix
            # Sawtooth (Bridge Pickup) + Sine (Neck resonance)
            val = osc(freq, time_now, 'saw') * 0.8 + osc(freq, time_now, 'sine') * 0.2
            
            # Envelope Physics
            env = 1.0
            rel_t = i / n_samples
            
            if technique == 'palm_mute':
                env = math.exp(-rel_t * 20.0) # Fast decay
            elif technique == 'sweep':
                env = math.exp(-rel_t * 5.0)  # Fluid
            elif technique == 'tap':
                # Attack spike then sustain
                if rel_t < 0.1: env = rel_t * 10
                else: env = math.exp(-(rel_t-0.1) * 2.0)
            else: # Sustain
                if rel_t < 0.01: env = rel_t * 100
                else: env = math.exp(-(rel_t-0.01) * 3.0)

            local_samples.append(val * env)
        
        self.t += duration
        self.samples.extend(local_samples)

    # --- TECHNIQUES ---

    def sweep_arpeggio(self):
        """Generates a Neo-Classical Sweep (Root-3-5-Octave)"""
        base = random.randint(0, 5)
        pattern = [0, 2, 4, 7, 4, 2] # Up and down
        speed = self.beat_len / 4 # 16th notes
        
        for p in pattern:
            f = self.get_freq(base + p, octave_offset=1)
            self.render_note(f, speed, 'sweep')

    def tapping_run(self):
        """Van Halen style tapping (Root - Tap Octave - Pull Off)"""
        base = random.randint(5, 12)
        speed = self.beat_len / 6 # Sextuplets
        
        for _ in range(4):
            # Tap high note
            self.render_note(self.get_freq(base + 7, 1), speed, 'tap')
            # Pull to base
            self.render_note(self.get_freq(base, 0), speed, 'pick')
            # Pull to lower
            self.render_note(self.get_freq(base - 2, 0), speed, 'pick')

    def shred_scale(self):
        """Linear alternate picking run"""
        start = random.randint(0, 10)
        length = 16
        direction = 1 if random.random() > 0.5 else -1
        speed = self.beat_len / 4 # 16th notes
        
        for i in range(length):
            idx = start + (i * direction)
            # Switch scale mid-run for "High IQ" jazz feel
            if i > 8: self.current_scale = 'phrygian_dom'
            
            f = self.get_freq(idx, 1)
            self.render_note(f, speed, 'palm_mute' if i % 2 == 0 else 'pick')

    def dive_bomb(self):
        """Simulate Whammy Bar Dive"""
        n_samples = int(self.beat_len * 4 * CONFIG['SR'])
        start_f = self.get_freq(12, 0)
        
        for i in range(n_samples):
            prog = i / n_samples
            # Logarithmic pitch drop
            curr_f = start_f * (0.5 ** (prog * 2)) # Drop 2 octaves
            val = osc(curr_f, self.t + (i/CONFIG['SR']), 'saw')
            self.samples.append(val)
        self.t += (self.beat_len * 4)

    # --- COMPOSER LOGIC ---
    def compose(self):
        # Intro Scream
        self.render_note(self.get_freq(12, 1), self.beat_len * 2, 'pick')
        
        bars = 16
        for _ in range(bars):
            # Decision Tree (Markov Chain-ish)
            choice = random.random()
            
            if choice < 0.3:
                self.sweep_arpeggio()
            elif choice < 0.6:
                self.shred_scale()
            elif choice < 0.9:
                self.tapping_run()
            else:
                # Occasional squeal
                self.render_note(self.get_freq(random.randint(10,15), 1), self.beat_len, 'pick')

        # Finish with a dive bomb
        self.dive_bomb()

# =============================================================================
# 4. MAIN EXECUTION
# =============================================================================
if __name__ == "__main__":
    print(f"IGNITING DRAGONFIRE ENGINE @ {CONFIG['BPM']} BPM...")
    
    # 1. Compose
    v = Virtuoso()
    v.compose()
    
    # 2. Process DSP
    dsp = ShredDSP()
    final_audio = []
    
    print(f"Processing {len(v.samples)} samples through Tube Simulation...")
    
    for s in v.samples:
        processed = dsp.process(s)
        # Limiter to prevent wrap-around clipping
        processed = max(-1.0, min(1.0, processed * CONFIG['MASTER']))
        final_audio.append(processed)
        
    # 3. Write
    print("Writing 'high_iq_solo.wav'...")
    with wave.open('high_iq_solo.wav', 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(CONFIG['SR'])
        # Convert float to int16
        data = struct.pack('<' + ('h'*len(final_audio)), *[int(s * 32767) for s in final_audio])
        f.writeframes(data)
        
    print("DONE. Prepare your ears.")