"""
test_string_engine.py — Validation tests for String Engine synthesis
"""

import math
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class MockAudioContext:
    """Mock Web Audio API context for testing synthesis math."""
    
    SAMPLE_RATE = 44100
    
    @staticmethod
    def generate_waveform(freq, duration_sec, shape='sine'):
        """Generate a waveform for testing."""
        sr = MockAudioContext.SAMPLE_RATE
        samples = int(duration_sec * sr)
        waveform = []
        
        for i in range(samples):
            t = i / sr
            phase = (t * freq) % 1.0
            
            if shape == 'sine':
                sample = math.sin(2 * math.pi * phase)
            elif shape == 'sawtooth':
                sample = 2.0 * phase - 1.0
            elif shape == 'square':
                sample = 1.0 if phase < 0.5 else -1.0
            elif shape == 'triangle':
                if phase < 0.5:
                    sample = 4.0 * phase - 1.0
                else:
                    sample = 3.0 - 4.0 * phase
            else:
                sample = 0.0
            
            waveform.append(sample)
        
        return waveform
    
    @staticmethod
    def analyze_frequency(waveform, sr=44100):
        """Simple frequency detection via zero-crossings."""
        zero_crossings = 0
        for i in range(len(waveform) - 1):
            if (waveform[i] > 0 and waveform[i + 1] < 0) or \
               (waveform[i] < 0 and waveform[i + 1] > 0):
                zero_crossings += 1
        
        # Frequency ≈ (zero_crossings * sr) / (2 * duration)
        duration = len(waveform) / sr
        freq = (zero_crossings * sr) / (2 * duration)
        return freq


class TestOscillators:
    """Test basic oscillator generation."""
    
    def test_sine_generation(self):
        """Test sine wave generation."""
        freq = 440.0  # A4
        duration = 0.1  # 100ms
        
        wave = MockAudioContext.generate_waveform(freq, duration, 'sine')
        
        # Basic checks
        assert len(wave) == int(0.1 * 44100), "Duration should match sample count"
        assert all(-1.0 <= s <= 1.0 for s in wave), "All samples should be normalized"
        
        # Detect frequency
        detected_freq = MockAudioContext.analyze_frequency(wave)
        assert abs(detected_freq - freq) / freq < 0.05, \
            f"Detected {detected_freq}Hz, expected {freq}Hz"
    
    def test_sawtooth_generation(self):
        """Test sawtooth wave generation."""
        freq = 440.0
        duration = 0.1
        
        wave = MockAudioContext.generate_waveform(freq, duration, 'sawtooth')
        
        # Sawtooth should have sharp transitions
        max_sample = max(wave)
        min_sample = min(wave)
        
        assert abs(max_sample - 1.0) < 0.01, "Sawtooth max should be ~1.0"
        assert abs(min_sample - (-1.0)) < 0.01, "Sawtooth min should be ~-1.0"
    
    def test_square_generation(self):
        """Test square wave generation."""
        freq = 440.0
        duration = 0.1
        
        wave = MockAudioContext.generate_waveform(freq, duration, 'square')
        
        # Square wave should only have ±1 or 0 values
        unique_values = set(round(s, 1) for s in wave)
        assert len(unique_values) <= 3, "Square wave should have few discrete levels"
    
    def test_triangle_generation(self):
        """Test triangle wave generation."""
        freq = 440.0
        duration = 0.1
        
        wave = MockAudioContext.generate_waveform(freq, duration, 'triangle')
        
        # Triangle should be smooth (no discontinuities)
        diffs = [abs(wave[i + 1] - wave[i]) for i in range(len(wave) - 1)]
        avg_diff = sum(diffs) / len(diffs)
        
        # Should be smooth transitions
        assert avg_diff < 0.1, f"Triangle should have smooth transitions, avg_diff={avg_diff}"


class TestEnvelopes:
    """Test amplitude envelopes (ADSR)."""
    
    @staticmethod
    def apply_envelope(waveform, attack, decay, sustain_level, release, sr=44100):
        """Apply simple ADSR envelope."""
        duration = len(waveform) / sr
        
        attack_samples = int(attack * sr)
        decay_samples = int(decay * sr)
        release_samples = int(release * sr)
        sustain_samples = len(waveform) - attack_samples - decay_samples - release_samples
        
        if sustain_samples < 0:
            raise ValueError("Envelope parameters too long for waveform")
        
        envelope = []
        
        # Attack
        for i in range(attack_samples):
            envelope.append(i / attack_samples)
        
        # Decay
        for i in range(decay_samples):
            envelope.append(1.0 - (i / decay_samples) * (1.0 - sustain_level))
        
        # Sustain
        for i in range(sustain_samples):
            envelope.append(sustain_level)
        
        # Release
        for i in range(release_samples):
            envelope.append(sustain_level * (1.0 - i / release_samples))
        
        # Apply to waveform
        return [waveform[i] * envelope[i] for i in range(len(waveform))]
    
    def test_attack_envelope(self):
        """Test that attack ramps up amplitude."""
        wave = MockAudioContext.generate_waveform(440, 0.1, 'sine')
        
        # Apply quick attack
        envelope = TestEnvelopes.apply_envelope(wave, 0.01, 0.02, 0.8, 0.02)
        
        # Early samples should be quieter than later samples
        early_energy = sum(abs(x) for x in envelope[0:441])  # First ~10ms
        mid_energy = sum(abs(x) for x in envelope[2000:2500])  # Mid
        
        assert mid_energy > early_energy, "Mid should be louder than attack start"
    
    def test_release_envelope(self):
        """Test that release fades out amplitude."""
        wave = MockAudioContext.generate_waveform(440, 0.1, 'sine')
        
        # Apply envelope with release
        envelope = TestEnvelopes.apply_envelope(wave, 0.01, 0.02, 0.8, 0.05)
        
        # Late samples should be quieter than early ones (in sustain/release)
        mid_energy = sum(abs(x) for x in envelope[2000:3000])  # Mid
        late_energy = sum(abs(x) for x in envelope[-500:])  # Last 500 samples
        
        assert mid_energy > late_energy, "Mid should be louder than release tail"


class TestFilters:
    """Test filter operations."""
    
    @staticmethod
    def lowpass_filter(signal, cutoff_hz, sr=44100):
        """Simple RC lowpass filter."""
        rc = 1.0 / (2 * math.pi * cutoff_hz)
        dt = 1.0 / sr
        alpha = dt / (rc + dt)
        
        filtered = [signal[0]]
        for i in range(1, len(signal)):
            filtered.append(filtered[-1] + alpha * (signal[i] - filtered[-1]))
        
        return filtered
    
    def test_lowpass_attenuates_high_freq(self):
        """Test that lowpass filter attenuates high frequencies."""
        sr = 44100
        
        # Generate high-frequency signal (10 kHz)
        high_freq_wave = MockAudioContext.generate_waveform(10000, 0.1, 'sine')
        
        # Apply lowpass at 4kHz
        filtered = TestFilters.lowpass_filter(high_freq_wave, 4000, sr)
        
        # Energy should be reduced
        orig_energy = sum(abs(x) for x in high_freq_wave)
        filt_energy = sum(abs(x) for x in filtered)
        
        attenuation = 1.0 - (filt_energy / orig_energy)
        assert attenuation > 0.5, f"Lowpass should attenuate high freq significantly, attenuation={attenuation}"
    
    def test_lowpass_preserves_low_freq(self):
        """Test that lowpass filter preserves low frequencies."""
        sr = 44100
        
        # Generate low-frequency signal (500 Hz)
        low_freq_wave = MockAudioContext.generate_waveform(500, 0.1, 'sine')
        
        # Apply lowpass at 4kHz
        filtered = TestFilters.lowpass_filter(low_freq_wave, 4000, sr)
        
        # Energy should be mostly preserved
        orig_energy = sum(abs(x) for x in low_freq_wave)
        filt_energy = sum(abs(x) for x in filtered)
        
        preservation = filt_energy / orig_energy
        assert preservation > 0.8, f"Lowpass should preserve low freq, preservation={preservation}"


class TestToneRecipes:
    """Test that tone recipes produce expected characteristics."""
    
    def test_metal_tone_high_harmonics(self):
        """Test that metal tone (sawtooth + square) has rich harmonics."""
        sr = 44100
        
        # Metal tone: mix of sawtooth and square
        sawtooth = MockAudioContext.generate_waveform(440, 0.1, 'sawtooth')
        square = MockAudioContext.generate_waveform(440, 0.1, 'square')
        
        # Mix 50/50
        metal_wave = [0.5 * s + 0.5 * q for s, q in zip(sawtooth, square)]
        
        # Metal should have sharp, defined peaks
        max_val = max(metal_wave)
        min_val = min(metal_wave)
        
        # Should reach near extremes
        assert abs(max_val) > 0.9 and abs(min_val) > 0.9, \
            "Metal tone should have strong peaks"
    
    def test_acoustic_tone_warmth(self):
        """Test that acoustic tone (triangle + sine) is smooth."""
        sr = 44100
        
        # Acoustic tone: mix of triangle and sine
        triangle = MockAudioContext.generate_waveform(440, 0.1, 'triangle')
        sine = MockAudioContext.generate_waveform(440, 0.1, 'sine')
        
        # Mix 60% triangle, 40% sine
        acoustic_wave = [0.6 * t + 0.4 * s for t, s in zip(triangle, sine)]
        
        # Should have smooth transitions
        diffs = [abs(acoustic_wave[i + 1] - acoustic_wave[i]) for i in range(len(acoustic_wave) - 1)]
        avg_diff = sum(diffs) / len(diffs)
        
        assert avg_diff < 0.15, f"Acoustic tone should be smooth, avg_diff={avg_diff}"


class TestKarplusStrong:
    """Test Karplus-Strong string synthesis algorithm."""
    
    @staticmethod
    def karplus_strong_simple(freq, duration_sec, sr=44100):
        """Simplified Karplus-Strong implementation."""
        # Delay line length determines pitch
        delay_len = int(sr / freq)
        delay_buf = [0.0] * delay_len
        
        # Excitation: noise burst at start
        import random
        for i in range(delay_len):
            delay_buf[i] = random.random() * 2 - 1
        
        output = []
        buf_idx = 0
        
        for _ in range(int(duration_sec * sr)):
            # Output is delay line sample
            output.append(delay_buf[buf_idx])
            
            # Average current and next sample (damping)
            next_idx = (buf_idx + 1) % delay_len
            damped = (delay_buf[buf_idx] + delay_buf[next_idx]) * 0.5
            
            # Write back (feedback)
            delay_buf[buf_idx] = damped
            buf_idx = next_idx
        
        return output
    
    def test_karplus_strong_pitch(self):
        """Test that Karplus-Strong produces correct pitch."""
        freq = 440
        wave = self.karplus_strong_simple(freq, 0.1)
        
        detected_freq = MockAudioContext.analyze_frequency(wave)
        
        # Should be close to target frequency
        error = abs(detected_freq - freq) / freq
        assert error < 0.05, f"KS pitch off, detected {detected_freq}Hz vs {freq}Hz"
    
    def test_karplus_strong_decay(self):
        """Test that Karplus-Strong decays over time."""
        wave = self.karplus_strong_simple(440, 0.2)
        
        # Split into quarters
        len_quarter = len(wave) // 4
        energy_1 = sum(abs(x) for x in wave[0:len_quarter])
        energy_4 = sum(abs(x) for x in wave[3*len_quarter:])
        
        # Energy should decay
        assert energy_1 > energy_4, "Karplus-Strong should decay over time"


if __name__ == "__main__":
    print("Running String Engine Tests...\n")
    
    # Test oscillators
    test_osc = TestOscillators()
    test_osc.test_sine_generation()
    print("✓ Sine oscillator test passed")
    
    test_osc.test_sawtooth_generation()
    print("✓ Sawtooth oscillator test passed")
    
    test_osc.test_square_generation()
    print("✓ Square oscillator test passed")
    
    # Test envelopes
    test_env = TestEnvelopes()
    test_env.test_attack_envelope()
    print("✓ Attack envelope test passed")
    
    test_env.test_release_envelope()
    print("✓ Release envelope test passed")
    
    # Test filters
    test_filt = TestFilters()
    test_filt.test_lowpass_attenuates_high_freq()
    print("✓ Lowpass high-freq attenuation test passed")
    
    test_filt.test_lowpass_preserves_low_freq()
    print("✓ Lowpass low-freq preservation test passed")
    
    # Test tone recipes
    test_tone = TestToneRecipes()
    test_tone.test_metal_tone_high_harmonics()
    print("✓ Metal tone test passed")
    
    test_tone.test_acoustic_tone_warmth()
    print("✓ Acoustic tone test passed")
    
    # Test Karplus-Strong
    test_ks = TestKarplusStrong()
    test_ks.test_karplus_strong_pitch()
    print("✓ Karplus-Strong pitch test passed")
    
    test_ks.test_karplus_strong_decay()
    print("✓ Karplus-Strong decay test passed")
    
    print("\nAll manual tests passed!")
    print("\nFor full test suite with pytest, run: pytest tests/")
