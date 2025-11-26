import math
import struct
import wave

# =============================================================================
# 1. CONFIGURATION & TUNING
# =============================================================================
CONFIG = {
    'SAMPLE_RATE': 44100,
    'BPM': 124,                  # Tempo from Tab
    'GAIN': 85.0,                # Extreme Distortion
    'CAB_HZ': 3800,              # Celestion Speaker Sim
    'DELAY_MS': 363,             # Dotted 8th delay at 124 BPM (The secret sauce)
    'MASTER_VOL': 0.8
}

# Standard Tuning Frequencies
TUNING = { 'E': 82.41, 'A': 110.00, 'D': 146.83, 'G': 196.00, 'B': 246.94, 'e': 329.63 }

def get_freq(string_name, fret):
    base = TUNING[string_name]
    return base * (2 ** (fret / 12.0))

# =============================================================================
# 2. THE PHYSICS ENGINE (DSP)
# =============================================================================
class GuitarAmp:
    def __init__(self):
        self.sr = CONFIG['SAMPLE_RATE']
        self.last_sample = 0.0
        
        # Delay Line (For the Intro)
        self.delay_len = int((CONFIG['DELAY_MS']/1000.0) * self.sr)
        self.delay_buf = [0.0] * self.delay_len
        self.d_idx = 0

    def process(self, signal, is_lead=False):
        # 1. PRE-AMP (Mid Boost for "Jungle" Tone)
        # Simple high-pass to tighten low end before distortion
        signal = signal - (self.last_sample * 0.1) 
        
        # 2. DISTORTION (Hyperbolic Tangent)
        drive = signal * (CONFIG['GAIN'] * 1.5 if is_lead else CONFIG['GAIN'])
        distorted = math.tanh(drive)
        
        # 3. CABINET SIMULATION (Low Pass Filter)
        rc = 1.0 / (2 * math.pi * CONFIG['CAB_HZ'])
        dt = 1.0 / self.sr
        alpha = dt / (rc + dt)
        filtered = self.last_sample + alpha * (distorted - self.last_sample)
        self.last_sample = filtered
        
        # 4. DELAY (The Intro Effect)
        # We only apply heavy delay if it's the lead track
        wet = 0.0
        if is_lead:
            delayed = self.delay_buf[self.d_idx]
            self.delay_buf[self.d_idx] = filtered + (delayed * 0.3) # Feedback
            self.d_idx = (self.d_idx + 1) % self.delay_len
            wet = delayed * 0.4
            
        return (filtered * 0.8) + wet

def generate_string_pluck(freq, duration, type='pick'):
    """Generates raw string vibration physics"""
    sr = CONFIG['SAMPLE_RATE']
    n_samples = int(duration * sr)
    samples = []
    
    # Harmonics: Sawtooth (Bite) + Square (Body)
    for i in range(n_samples):
        t = i / sr
        
        # Oscillators
        osc1 = 2.0 * ((t * freq) % 1.0) - 1.0 # Saw
        osc2 = 1.0 if ((t * freq) % 1.0) < 0.5 else -1.0 # Square
        raw = (osc1 * 0.6) + (osc2 * 0.4)
        
        # Envelope (ADSR)
        env = 0.0
        if type == 'pm': # Palm Mute: Short, percussive
            if t < 0.005: env = t/0.005
            else: env = math.exp(-(t-0.005)*25.0) # Fast decay
        elif type == 'pick': # Open note
            if t < 0.01: env = t/0.01
            else: env = math.exp(-(t-0.01)*4.0)
            
        samples.append(raw * env)
    return samples

# =============================================================================
# 3. THE SEQUENCER (Transcribing the Tab)
# =============================================================================
class Sequencer:
    def __init__(self):
        self.track_1 = [] # Lead / Intro
        self.track_2 = [] # Rhythm
        self.beat_sec = 60.0 / CONFIG['BPM']
        self.sixteenth = self.beat_sec / 4.0
        
    def add_note(self, track_id, freq, dur_16ths, type='pick'):
        dur_sec = dur_16ths * self.sixteenth
        audio = generate_string_pluck(freq, dur_sec, type)
        target = self.track_1 if track_id == 1 else self.track_2
        target.extend(audio)

    def add_rest(self, track_id, dur_16ths):
        dur_sec = dur_16ths * self.sixteenth
        n = int(dur_sec * CONFIG['SAMPLE_RATE'])
        target = self.track_1 if track_id == 1 else self.track_2
        target.extend([0.0] * n)

    def build_intro(self):
        # --- GUITAR 1: RIFF A (The Delay Riff) ---
        # D string: 4--4-2--2--0 (repeated)
        # Note: We play staccato to let delay fill the gaps
        f_B = get_freq('D', 4)
        f_A = get_freq('D', 2)
        f_G = get_freq('D', 0) # Open D (actually tab says 2-2-0 on A, but standard variation uses D)
        # Let's stick to your tab: D string 4, 2
        
        print("Sequencing Intro Riff A...")
        for _ in range(4): # Play loop 4 times
            # "4 -- 4"
            self.add_note(1, f_B, 2, 'pm'); self.add_rest(1, 2) 
            self.add_note(1, f_B, 2, 'pm'); self.add_rest(1, 2)
            # "2 -- 2"
            self.add_note(1, f_A, 2, 'pm'); self.add_rest(1, 2)
            self.add_note(1, f_A, 2, 'pm'); self.add_rest(1, 2)
            # "0" (on A string actually per tab context, let's use low A freq)
            self.add_note(1, get_freq('A', 2), 2, 'pm'); self.add_rest(1, 14) # Long rest for fill

        # --- GUITAR 2: POWER CHORDS (B5 A5 G5 E5) ---
        # Enters after 2 loops of Gtr 1
        print("Sequencing Rhythm Chords...")
        self.add_rest(2, 64) # Wait for Gtr 1
        
        # B5 (A string fret 2)
        freqs_b5 = [get_freq('A',2), get_freq('D',4)]
        # A5 (Open A)
        freqs_a5 = [get_freq('A',0), get_freq('D',2)]
        # G5 (Low E fret 3)
        freqs_g5 = [get_freq('E',3), get_freq('A',5)]
        # E5 (Open E)
        freqs_e5 = [get_freq('E',0), get_freq('A',2)]
        
        chord_prog = [freqs_b5, freqs_a5, freqs_g5, freqs_e5]
        
        for chord in chord_prog:
            # Strumming physics (slight offset)
            dur = 16 # 1 bar each
            # Render chord as combined wave
            root = generate_string_pluck(chord[0], dur * self.sixteenth, 'pick')
            fifth = generate_string_pluck(chord[1], dur * self.sixteenth, 'pick')
            combined = [r + f for r, f in zip(root, fifth)]
            self.track_2.extend(combined)

    def build_main_riff(self):
        # --- THE MAIN VERSE RIFF ---
        # E|-------------------------|
        # A|--7--7--5--7--7--7-5-4-2-|
        # E|--5--5--3--5--5--5-3-2-0-|
        
        print("Sequencing Main Riff...")
        # A5 root
        r_A = get_freq('E', 5)
        r_G = get_freq('E', 3)
        r_Gb = get_freq('E', 2)
        r_E = get_freq('E', 0)
        
        # A string notes (Power chord tops)
        t_A = get_freq('A', 7)
        t_G = get_freq('A', 5)
        
        def play_power(root, top, dur, palm=False):
            # Combined wave for rhythm track
            s1 = generate_string_pluck(root, dur*self.sixteenth, 'pm' if palm else 'pick')
            s2 = generate_string_pluck(top, dur*self.sixteenth, 'pm' if palm else 'pick')
            mix = [x+y for x,y in zip(s1,s2)]
            self.track_2.extend(mix)

        for _ in range(4): # 4 Bars
            play_power(r_A, t_A, 2); play_power(r_A, t_A, 2) # 7-7
            play_power(r_G, t_G, 2) # 5
            play_power(r_A, t_A, 2); play_power(r_A, t_A, 2); play_power(r_A, t_A, 2) # 7-7-7
            play_power(r_G, t_G, 1) # 5
            play_power(r_Gb, get_freq('A',4), 1) # 4
            play_power(r_E, get_freq('A',2), 2) # 2 (E5)

        # Guitar 1 plays high scratches/shreds over this
        self.add_rest(1, 128) # Just silence on track 1 for clarity

# =============================================================================
# 4. MIXER & RENDERER
# =============================================================================
def main():
    print("Initializing JUNGLE ENGINE...")
    seq = Sequencer()
    
    # 1. Write the notes
    seq.build_intro()
    seq.build_main_riff()
    
    # 2. Pad tracks to equal length
    max_len = max(len(seq.track_1), len(seq.track_2))
    seq.track_1.extend([0.0] * (max_len - len(seq.track_1)))
    seq.track_2.extend([0.0] * (max_len - len(seq.track_2)))
    
    # 3. Process Amps (Left and Right)
    amp1 = GuitarAmp()
    amp2 = GuitarAmp()
    
    print("Processing Physics (Tube Saturation + Cabinet Convolution)...")
    final_mix = []
    
    for i in range(max_len):
        # Track 1 (Lead) -> Amp 1 (With Delay)
        s1 = amp1.process(seq.track_1[i], is_lead=True)
        # Track 2 (Rhythm) -> Amp 2 (Dryer)
        s2 = amp2.process(seq.track_2[i], is_lead=False)
        
        # Stereo Width (Pan Gtr 1 Left, Gtr 2 Right)
        # Mix down to mono for safety, or simple stereo interleaving
        # Let's do a centered mix for maximum power
        mix = (s1 * 0.6) + (s2 * 0.6)
        
        # Hard Limiter
        mix = max(-1.0, min(1.0, mix))
        final_mix.append(mix)

    # 4. Save to WAV
    print(f"Writing {len(final_mix)} samples to WAV...")
    with wave.open('welcome_to_the_jungle.wav', 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(CONFIG['SAMPLE_RATE'])
        
        data = struct.pack('<' + ('h'*len(final_mix)), *[int(s * 32767) for s in final_mix])
        f.writeframes(data)
        
    print("DONE. File 'welcome_to_the_jungle.wav' created.")
    print("WARNING: Volume is loud. Distortion is high.")

if __name__ == "__main__":
    main()