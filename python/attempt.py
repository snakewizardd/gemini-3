import math
import random
import struct
import wave
import sys

# =============================================================================
# 1. PHYSICS CONFIGURATION (Reference: STRING_ENGINE_TECHNICAL_REFERENCE.md)
# =============================================================================
CONFIG = {
    'SAMPLE_RATE': 44100,
    'BPM': 170,                  # Fast Metal Tempo
    'DISTORTION_GAIN': 50.0,     # "High Gain" (Input Multiplier)
    'CAB_CUTOFF': 4000,          # 4kHz Cabinet Lowpass
    'DELAY_TIME': 0.35,          # 350ms Delay
    'DELAY_FEEDBACK': 0.4,       # Echo trails
    'MASTER_VOL': 0.6
}

# Standard Tuning Frequencies (Reference Part II)
STRINGS = {
    'E2': 82.41, 'A2': 110.00, 'D3': 146.83, 
    'G3': 196.00, 'B3': 246.94, 'E4': 329.63
}

# =============================================================================
# 2. RAW DSP ENGINE (Digital Signal Processing)
# =============================================================================
class AudioPhysics:
    def __init__(self):
        self.sr = CONFIG['SAMPLE_RATE']
        self.dt = 1.0 / self.sr
        
        # Filter State (Previous output for IIR filter)
        self.last_sample = 0.0
        
        # Delay Line (Circular Buffer)
        self.delay_len = int(CONFIG['DELAY_TIME'] * self.sr)
        self.delay_buffer = [0.0] * self.delay_len
        self.delay_idx = 0
        
        # Filter Coefficient (RC Lowpass formula)
        rc = 1.0 / (2 * math.pi * CONFIG['CAB_CUTOFF'])
        self.alpha = self.dt / (rc + self.dt)

    def generate_oscillator(self, freq, t, shape='saw'):
        """Simulates string vibration physics."""
        # Sawtooth: Rich even/odd harmonics (The "Buzz")
        if shape == 'saw':
            period = 1.0 / freq
            phase = (t % period) / period
            return 2.0 * (phase - 0.5)
        
        # Square: Hollow, woody harmonics (Reference: Part III Metal Tone)
        elif shape == 'square':
            period = 1.0 / freq
            phase = (t % period) / period
            return 1.0 if phase < 0.5 else -1.0
        
        # Triangle: Soft body
        elif shape == 'tri':
            period = 1.0 / freq
            phase = (t % period) / period
            return 4.0 * abs(phase - 0.5) - 1.0

    def process_signal(self, raw_signal):
        """The Amplifier Chain: Drive -> Clip -> Cab -> Delay."""
        
        # 1. HIGH GAIN PRE-AMP
        driven = raw_signal * CONFIG['DISTORTION_GAIN']
        
        # 2. TUBE SATURATION (Hyperbolic Tangent)
        # This creates the "Physics" of a tube amp limiting
        distorted = math.tanh(driven)
        
        # 3. CABINET SIMULATION (Low Pass Filter)
        # Removes the harsh digital edges
        filtered = self.last_sample + self.alpha * (distorted - self.last_sample)
        self.last_sample = filtered
        
        # 4. STADIUM DELAY
        delayed = self.delay_buffer[self.delay_idx]
        output = filtered + (delayed * 0.3) # Mix wet
        
        # Write back to delay buffer with feedback
        self.delay_buffer[self.delay_idx] = filtered + (delayed * CONFIG['DELAY_FEEDBACK'])
        self.delay_idx = (self.delay_idx + 1) % self.delay_len
        
        return output * CONFIG['MASTER_VOL']

# =============================================================================
# 3. PROCEDURAL COMPOSER (The "Endless" Logic)
# =============================================================================
class ShredComposer:
    def __init__(self):
        # Reference Part V: Scale Patterns
        # A Harmonic Minor: A B C D E F G#
        self.scale_intervals = [0, 2, 3, 5, 7, 8, 11, 12]
        self.root_freq = 110.00 # A2
        
    def get_freq(self, degree, octave_shift=0):
        """Calculates frequency based on scale degree."""
        octave = degree // len(self.scale_intervals)
        idx = degree % len(self.scale_intervals)
        semitones = self.scale_intervals[idx] + (12 * (octave + octave_shift))
        return self.root_freq * (2 ** (semitones / 12.0))

    def generate_riff(self):
        """Generates a low-end chug pattern (Palm Mute logic)."""
        pattern = []
        # Djent-style syncopation
        rhythm = random.choice([
            [1, 1, 0, 1, 0, 0, 1, 0], # Gallopish
            [1, 0, 0, 1, 1, 0, 1, 1], # Syncopated
            [1, 1, 1, 1, 0, 1, 1, 0]  # Driving
        ])
        
        for hit in rhythm:
            if hit == 1:
                # Low A Power Chord
                pattern.append({'freq': 110.00, 'dur': 0.15, 'type': 'pm'})
            else:
                # Dead note / Silence
                pattern.append({'freq': 0, 'dur': 0.15, 'type': 'rest'})
        return pattern

    def generate_solo(self):
        """Generates a high-speed scalar run (Sweep/Shred logic)."""
        pattern = []
        start_degree = random.randint(0, 7)
        length = random.randint(8, 16)
        
        # Ascending or Descending run
        direction = 1 if random.random() > 0.5 else -1
        
        for i in range(length):
            degree = start_degree + (i * direction)
            # High octave for solos
            freq = self.get_freq(degree, octave_shift=1) 
            pattern.append({'freq': freq, 'dur': 0.08, 'type': 'shred'}) # Fast!
            
        # End on a long sustained note (Bend simulation)
        final_degree = start_degree + (length * direction)
        pattern.append({'freq': self.get_freq(final_degree, octave_shift=1), 'dur': 1.0, 'type': 'sustain'})
        return pattern

# =============================================================================
# 4. MAIN GENERATION LOOP
# =============================================================================
def main():
    print(f"Initializing GUITAR UNIVERSE ENGINE...")
    print(f"BPM: {CONFIG['BPM']} | Gain: {CONFIG['DISTORTION_GAIN']}x")
    print("Generating 60 seconds of procedural audio (this uses raw math, please wait)...")

    physics = AudioPhysics()
    composer = ShredComposer()
    
    samples = []
    total_seconds = 60
    samples_to_gen = total_seconds * CONFIG['SAMPLE_RATE']
    
    current_sample_count = 0
    
    # Progress Bar Helper
    def update_progress(progress):
        barLength = 20
        status = ""
        if progress >= 1:
            progress = 1
            status = "Done\r\n"
        block = int(round(barLength*progress))
        text = "\rProgress: [{0}] {1}%".format( "#"*block + "-"*(barLength-block), int(progress*100))
        sys.stdout.write(text)
        sys.stdout.flush()

    # THE ENDLESS LOOP
    while current_sample_count < samples_to_gen:
        # Decide: Riff or Solo?
        if random.random() > 0.6:
            phrase = composer.generate_solo()
        else:
            phrase = composer.generate_riff()
            
        for note in phrase:
            freq = note['freq']
            dur = note['dur']
            note_type = note['type']
            
            # Convert duration to samples
            num_samples = int(dur * CONFIG['SAMPLE_RATE'])
            
            # Envelope State
            envelope = 0.0
            
            for i in range(num_samples):
                t = i / CONFIG['SAMPLE_RATE']
                
                # 1. ENVELOPE SHAPING (Physics of the pluck)
                if note_type == 'pm': # Palm Mute: Fast decay
                    # Attack 5ms, Decay fast
                    if t < 0.005: envelope = t / 0.005
                    else: envelope = math.exp(-(t-0.005) * 15.0)
                elif note_type == 'sustain': # Solo sustain
                    if t < 0.02: envelope = t / 0.02
                    else: envelope = 1.0 * math.exp(-(t-0.02) * 1.5)
                elif note_type == 'rest':
                    envelope = 0.0
                else: # Shred note
                    if t < 0.005: envelope = t / 0.005
                    else: envelope = math.exp(-(t-0.005) * 5.0)

                # 2. OSCILLATOR MIX (Reference Part III)
                if freq > 0:
                    # Mix Sawtooth (Bite) and Square (Body)
                    raw = (physics.generate_oscillator(freq, current_sample_count * physics.dt, 'saw') * 0.7 +
                           physics.generate_oscillator(freq, current_sample_count * physics.dt, 'square') * 0.3)
                else:
                    raw = 0.0

                # 3. APPLY ENVELOPE
                signal = raw * envelope

                # 4. PROCESS THROUGH AMP SIMULATOR
                final_output = physics.process_signal(signal)
                
                samples.append(final_output)
                current_sample_count += 1
                
                if current_sample_count >= samples_to_gen:
                    break
            
            update_progress(current_sample_count / samples_to_gen)
            if current_sample_count >= samples_to_gen:
                break

    # =========================================================================
    # 5. WRITE TO WAV
    # =========================================================================
    print("\nEncoding WAV file...")
    output_file = 'guitar_universe.wav'
    
    with wave.open(output_file, 'w') as wav_file:
        wav_file.setnchannels(1)      # Mono
        wav_file.setsampwidth(2)      # 16-bit
        wav_file.setframerate(CONFIG['SAMPLE_RATE'])
        
        # Pack floats to 16-bit integers
        packed_data = []
        for s in samples:
            # Hard clip limiter at output to prevent digital wrapping
            s = max(-1.0, min(1.0, s))
            packed_data.append(struct.pack('h', int(s * 32767.0)))
            
        wav_file.writeframes(b''.join(packed_data))
        
    print(f"SUCCESS. Generated {output_file}")
    print("Open this file to hear the procedure.")

if __name__ == "__main__":
    main()