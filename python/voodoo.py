import math
import struct
import wave
import random

# =============================================================================
# 1. THE VINTAGE TONE CONFIGURATION
# =============================================================================
CONFIG = {
    'SR': 44100,
    'BPM': 90,               # Slow, heavy blues groove
    'DURATION_BARS': 48,     # Long form (approx 3 mins)
    'DRIVE': 4.0,            # Fuzz Face gain
    'UNIVIBE_SPEED': 4.0,    # Swirling pulse speed (Hz)
    'MASTER_VOL': 0.75
}

# Frequencies for Key of E (Hendrix/Clapton favorite)
# Tuning: Eb Standard (Hendrix style - down half step)
TUNING_OFFSET = -1 
def get_freq(note_index, octave):
    # E is 0. Standard E2 = 82.41 Hz
    base_freq = 82.41 * (2 ** (TUNING_OFFSET/12.0)) 
    semitones = note_index + (12 * octave)
    return base_freq * (2 ** (semitones / 12.0))

# =============================================================================
# 2. VINTAGE DSP ENGINE (The "Anti-Grasshopper" Filter)
# =============================================================================
class VintageAmp:
    def __init__(self):
        self.last = 0.0
        # Univibe LFO state
        self.lfo_phase = 0.0
        
        # Tone Stack State (Low Pass)
        self.lp_state = 0.0
        
        # Delay line for "Universe" reverb
        self.delay_buf = [0.0] * 12000
        self.d_idx = 0

    def process(self, signal, is_lead=True):
        # 1. UNIVIBE SIMULATION (Amplitude + Phase modulation)
        # Creates that underwater/swirling sound
        self.lfo_phase += (CONFIG['UNIVIBE_SPEED'] / CONFIG['SR'])
        lfo = math.sin(self.lfo_phase * 2 * math.pi)
        
        # Modulate amplitude slightly (Tremolo)
        if is_lead:
            signal *= (1.0 + 0.3 * lfo)
        
        # 2. THE "WOMAN TONE" PRE-FILTER
        # Roll off highs BEFORE distortion for creamy sound
        # This kills the "grasshopper" buzz
        cutoff = 0.15 if is_lead else 0.3 
        self.lp_state += cutoff * (signal - self.lp_state)
        signal = self.lp_state

        # 3. FUZZ FACE DISTORTION
        # Asymmetrical clipping (Germaniun transistor simulation)
        gain = CONFIG['DRIVE'] * 1.5 if is_lead else CONFIG['DRIVE'] * 0.8
        driven = signal * gain
        
        # Soft Clip (Tanh) but asymmetrical
        if driven > 0:
            distorted = math.tanh(driven)
        else:
            distorted = math.tanh(driven * 0.8) / 0.8

        # 4. MARSHALL CABINET SIMULATION (Steep Low Pass)
        # 4x12 Speaker emulation - cuts everything above 3.5kHz
        # Simple RC filter implementation
        rc = 1.0 / (2 * math.pi * 3500)
        dt = 1.0 / CONFIG['SR']
        alpha = dt / (rc + dt)
        filtered = self.last + alpha * (distorted - self.last)
        self.last = filtered

        # 5. STADIUM DELAY/REVERB
        # Long tail echo
        d_out = self.delay_buf[self.d_idx]
        self.delay_buf[self.d_idx] = filtered + (d_out * 0.4)
        self.d_idx = (self.d_idx + 1) % len(self.delay_buf)

        return (filtered * 0.7) + (d_out * 0.25)

def vintage_osc(freq, t, type='warm'):
    """Generates a warmer, band-limited waveform"""
    if freq <= 0: return 0.0
    
    # Mix Sine and Triangle for "Flutey" Lead tone (Clapton)
    if type == 'warm':
        sine = math.sin(2 * math.pi * freq * t)
        # Add a little odd harmonic for grit
        tri = (math.asin(math.sin(2 * math.pi * freq * t)) * 2/math.pi)
        return 0.7 * sine + 0.3 * tri
        
    # Square wave with rounded edges for Rhythm (Hendrix Chords)
    else: 
        raw = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
        # Slew limiting happens in the Pre-Filter of the Amp
        return raw * 0.6

# =============================================================================
# 3. THE BLUES COMPOSER (Coherent Structure)
# =============================================================================
class BluesMan:
    def __init__(self):
        self.track_lead = []
        self.track_rhythm = []
        self.samples_per_beat = int((60 / CONFIG['BPM']) * CONFIG['SR'])
        
        # EXPANDED SCALE: 2 Octaves of E Minor Pentatonic + Blues Note
        # This prevents the "Index Error" and allows higher solos
        self.scale = [
            0, 3, 5, 6, 7, 10, 12,     # Octave 1
            15, 17, 18, 19, 22, 24, 27 # Octave 2
        ]

    def render_note(self, freq, duration_beats, track='lead', technique='normal'):
        n_samples = int(duration_beats * self.samples_per_beat)
        samples = []
        
        # Vibrato LFO
        vib_rate = 5.0 # Hz
        vib_depth = 0.0 if track == 'rhythm' else 0.015 # Pitch wobble depth
        
        for i in range(n_samples):
            t = i / CONFIG['SR']
            
            # Apply Vibrato to frequency
            current_freq = freq * (1.0 + vib_depth * math.sin(2*math.pi*vib_rate*t))
            
            osc_type = 'warm' if track == 'lead' else 'grit'
            raw = vintage_osc(current_freq, t, osc_type)
            
            # Envelope (ADSR)
            env = 1.0
            progress = i / n_samples
            
            if technique == 'bend':
                # Simulated bend up sustain
                pass
                
            # Attack/Decay
            if progress < 0.05: env = progress / 0.05
            else: env = math.exp(-(progress-0.05) * 2.0) # Long sustain
            
            samples.append(raw * env)
            
        if track == 'lead': self.track_lead.extend(samples)
        else: self.track_rhythm.extend(samples)

    def generate_blues(self):
        # 12 Bar Blues Progression in E
        # I (E) - 4 bars
        # IV (A) - 2 bars
        # I (E) - 2 bars
        # V (B) - 1 bar, IV (A) - 1 bar
        # I (E) - 1 bar, Turnaround (B) - 1 bar
        
        # Progression map (Root note offsets)
        progression = [0,0,0,0, 5,5, 0,0, 7,5, 0,7] 
        
        # Rhythm: The "Hendrix Chord" (7#9) Pulse
        def play_chord(root_offset, beats):
            # Construct E7#9 shape shifted
            root = get_freq(root_offset, 1) # Low root
            # Render chord as mono mix
            self.render_note(root, beats, 'rhythm')
        
        # Lead: Improvisation
        def play_lick(root_offset):
            # Choose a lick template
            lick_type = random.choice(['slow_bend', 'rapid_fire', 'silence'])
            
            if lick_type == 'slow_bend':
                # Clapton style: Long emotional note
                # Use modulo % to keep index safe
                idx = (random.randint(2, 5) + int(root_offset/2)) % len(self.scale)
                note = self.scale[idx]
                freq = get_freq(note, 3)
                self.render_note(freq, 2.0, 'lead', 'bend')
                self.render_note(0, 2.0, 'lead') # Space
                
            elif lick_type == 'rapid_fire':
                # Hendrix style: Hammer-ons
                start_idx = random.randint(0, 5)
                for _ in range(8):
                    # SAFE INDEX LOGIC:
                    offset = random.randint(0,2)
                    safe_idx = (start_idx + offset) % len(self.scale)
                    
                    note = self.scale[safe_idx]
                    freq = get_freq(note, 3)
                    self.render_note(freq, 0.5, 'lead')
            
            else:
                self.render_note(0, 4.0, 'lead') # Let the rhythm breathe

        # GENERATE SECTIONS
        print("Composing 12-Bar Blues Cycles...")
        total_bars = CONFIG['DURATION_BARS']
        bars_generated = 0
        
        while bars_generated < total_bars:
            cycle_idx = bars_generated % 12
            current_root = progression[cycle_idx]
            
            # Rhythm Track
            play_chord(current_root, 4.0) # 4 beats per bar
            
            # Lead Track
            play_lick(current_root)
            
            bars_generated += 1

# =============================================================================
# 4. RENDERER
# =============================================================================
def main():
    print("IGNITING VOODOO CREAM ENGINE...")
    print(f"Generating {CONFIG['DURATION_BARS']} bars of Psychedelic Blues...")
    print("Applying Univibe & Fuzz Simulation (This may take 30-60s)...")
    
    blues = BluesMan()
    blues.generate_blues()
    
    amp_lead = VintageAmp()
    amp_rhythm = VintageAmp()
    
    final_mix = []
    
    # Pad to equal length
    max_len = max(len(blues.track_lead), len(blues.track_rhythm))
    blues.track_lead += [0.0] * (max_len - len(blues.track_lead))
    blues.track_rhythm += [0.0] * (max_len - len(blues.track_rhythm))
    
    # Mixdown
    for i in range(max_len):
        # Process Lead (Louder, Fuzzier)
        s_lead = amp_lead.process(blues.track_lead[i], is_lead=True)
        
        # Process Rhythm (Cleaner, Thinner)
        s_rhythm = amp_rhythm.process(blues.track_rhythm[i], is_lead=False)
        
        # Sum
        mix = s_lead + (s_rhythm * 0.6)
        
        # Master Limiter
        mix = max(-1.0, min(1.0, mix * CONFIG['MASTER_VOL']))
        final_mix.append(mix)
        
    # Write File
    with wave.open('voodoo_blues_universe.wav', 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(CONFIG['SR'])
        data = struct.pack('<' + ('h'*len(final_mix)), *[int(s * 32767) for s in final_mix])
        f.writeframes(data)
        
    print("DONE. 'voodoo_blues_universe.wav' is ready.")
    print("Turn the volume up.")

if __name__ == "__main__":
    main()