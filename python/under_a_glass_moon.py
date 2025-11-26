import math
import wave
import struct

def generate_tone(frequency, duration_ms, sample_rate=44100, volume=0.5):
    """Generates a list of samples for a sine wave tone."""
    num_samples = int(sample_rate * (duration_ms / 1000.0))
    samples = []
    for i in range(num_samples):
        # Apply a simple envelope (fade in/out) to avoid clicking
        envelope = 1.0
        if i < 500: envelope = i / 500.0
        if i > num_samples - 500: envelope = (num_samples - i) / 500.0
        
        # Simple Sine Wave
        value = volume * envelope * math.sin(2 * math.pi * frequency * (i / sample_rate))
        samples.append(value)
    return samples

def note_freq(string_base_freq, fret):
    """Calculates frequency of a note given string base freq and fret number."""
    return string_base_freq * (2 ** (fret / 12.0))

def save_wav(filename, samples, sample_rate=44100):
    """Saves the generated samples to a .wav file."""
    packed_samples = []
    max_amp = 32767  # 16-bit PCM
    for s in samples:
        # Clip samples
        s = max(-1.0, min(1.0, s))
        packed_samples.append(struct.pack('h', int(s * max_amp)))
    
    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)      # Mono
        wf.setsampwidth(2)      # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(packed_samples))
    print(f"Generated {filename}")

# Standard Guitar String Frequencies (Standard Tuning)
E2 = 82.41
A2 = 110.00
D3 = 146.83
G3 = 196.00  # We only need the G string for the first line
B3 = 246.94
E4 = 329.63

# The Main Intro Melody from the Tab (Line 1)
# G|o---6/11-|---/13--|--\9--|--\4-|-2---|--6--|--4/3-o|
# We simulate the target notes of the slides for clarity
melody = [
    # Note: (String Freq, Fret, Duration_ms)
    (G3, 11, 1200), # Slide to 11 (F#)
    (G3, 13, 1200), # Slide to 13 (G#)
    (G3, 9,  1200), # Slide down to 9 (E)
    (G3, 4,  1200), # Slide down to 4 (B)
    (G3, 2,  1200), # 2 (A)
    (G3, 6,  1200), # 6 (C#)
    (G3, 4,  600),  # 4 (B)
    (G3, 3,  600),  # Slide to 3 (A#)
    
    # Repeat phrase roughly
    (G3, 11, 1200),
    (G3, 13, 1200),
    (G3, 9,  1200),
    (G3, 4,  1200),
    (G3, 2,  1200),
    (G3, 6,  1200),
    (G3, 4,  400),
    (G3, 3,  400),
    (D3, 4,  800), # Ending the phrase on D string
]

# Compile the full audio data
full_audio = []
sample_rate = 44100

for string_freq, fret, duration in melody:
    freq = note_freq(string_freq, fret)
    full_audio.extend(generate_tone(freq, duration, sample_rate))

# Save the file
save_wav("under_a_glass_moon_intro.wav", full_audio)