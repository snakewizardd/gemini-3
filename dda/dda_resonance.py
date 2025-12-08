"""
DDA "THE RESONANCE" — Sinusoidal Harmony
-----------------------------------------
DDA finding the rhythm in chaos.

A visualization of DDA tracking layered sinusoidal signals:
- Multiple frequencies interfering
- Noise corrupting the harmony
- DDA finding and following the fundamental pulse

Creates beautiful Lissajous-like spirals showing phase relationships.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')


@dataclass
class ResonanceConfig:
    P0: float = 0.80           
    m: float = 0.20            
    derivative_boost: float = 0.5
    ema_alpha: float = 0.2


class DDA_Resonator:
    """DDA tuned to find the signal in the noise."""
    
    def __init__(self):
        self.c = ResonanceConfig()
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.dF = 0.0
        self.k = 1.0
        self.init = False
        
    def resonate(self, signal):
        if not self.init:
            self.F_prev = signal
            self.I_prev = signal
            self.init = True
            return signal
        
        delta = signal - self.I_prev
        self.dF = (self.c.ema_alpha * delta) + ((1 - self.c.ema_alpha) * self.dF)
        
        L = signal + (self.c.derivative_boost * self.dF)
        F = (self.c.P0 * self.k * self.F_prev) + (self.c.m * L)
        
        self.F_prev = F
        self.I_prev = signal
        return F


def create_harmonic_signal(t, noise_level=0.5):
    """
    Create a complex signal from layered sinusoidals.
    Like multiple instruments playing together.
    """
    # The fundamental — the heartbeat
    fundamental = 2.0 * np.sin(2 * np.pi * 0.5 * t)
    
    # The third harmonic — adds richness
    third = 0.8 * np.sin(2 * np.pi * 1.5 * t)
    
    # The fifth harmonic — sparkle
    fifth = 0.4 * np.sin(2 * np.pi * 2.5 * t + np.pi/4)
    
    # The pure signal (chord)
    pure_signal = fundamental + third + fifth
    
    # Corruption: noise + random phase drift
    noise = np.random.normal(0, noise_level, len(t))
    
    # Corrupted signal (what we observe)
    noisy_signal = pure_signal + noise
    
    return pure_signal, noisy_signal, fundamental


def render_resonance():
    print("🎵 THE RESONANCE")
    print("=" * 50)
    print("\"In chaos, the algorithm finds the song.\"")
    print("=" * 50)
    
    np.random.seed(2024)
    
    # Time
    t = np.linspace(0, 8, 800)
    
    # Generate signals
    pure, noisy, fundamental = create_harmonic_signal(t, noise_level=0.6)
    
    # DDA finds the rhythm
    resonator = DDA_Resonator()
    filtered = np.array([resonator.resonate(s) for s in noisy])
    
    # --- VISUALIZATION ---
    fig = plt.figure(figsize=(14, 10))
    fig.patch.set_facecolor('#0a0a12')
    
    # Color palette: ocean vibes
    pure_color = '#00d4ff'      # Cyan
    noise_color = '#ff6b6b'     # Coral
    dda_color = '#ffd93d'       # Gold
    fundamental_color = '#6bcb77'  # Mint
    
    # === PANEL 1: The Waveforms ===
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.set_facecolor('#0a0a12')
    
    ax1.plot(t, pure, color=pure_color, lw=1.5, alpha=0.4, label='Pure Harmonic')
    ax1.plot(t, noisy, color=noise_color, lw=0.5, alpha=0.3, label='Noisy Observation')
    ax1.plot(t, filtered, color=dda_color, lw=2, alpha=0.9, label='DDA Resonance')
    
    ax1.set_title("Signal Recovery", color='white', fontsize=12, fontweight='bold')
    ax1.set_xlabel("Time", color='gray')
    ax1.set_ylabel("Amplitude", color='gray')
    ax1.legend(loc='upper right', facecolor='#1a1a2e', edgecolor='none', 
               labelcolor='white', fontsize=9)
    ax1.tick_params(colors='gray')
    ax1.grid(True, alpha=0.1, color='white')
    for spine in ax1.spines.values():
        spine.set_color('#333')
    
    # === PANEL 2: Phase Space (Lissajous) ===
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.set_facecolor('#0a0a12')
    
    # Create Lissajous by plotting signal vs its derivative
    dda_velocity = np.diff(filtered, prepend=filtered[0])
    
    # Color by time progression
    points = np.array([filtered, dda_velocity]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    
    norm = plt.Normalize(0, len(t))
    lc = LineCollection(segments, cmap='plasma', norm=norm, linewidths=1.5, alpha=0.8)
    lc.set_array(np.arange(len(t)))
    ax2.add_collection(lc)
    ax2.autoscale()
    
    ax2.set_title("Phase Portrait", color='white', fontsize=12, fontweight='bold')
    ax2.set_xlabel("Position (DDA Output)", color='gray')
    ax2.set_ylabel("Velocity (dF/dt)", color='gray')
    ax2.tick_params(colors='gray')
    ax2.set_aspect('equal')
    for spine in ax2.spines.values():
        spine.set_color('#333')
    
    # === PANEL 3: Harmonic Spiral ===
    ax3 = fig.add_subplot(2, 2, 3, projection='polar')
    ax3.set_facecolor('#0a0a12')
    
    # Create spiral using filtered signal as radius, time as angle
    theta = t * 2 * np.pi / 2  # Angular progression
    r = (filtered - filtered.min()) / (filtered.max() - filtered.min()) + 0.5
    
    # Plot as colored scatter
    colors = plt.cm.viridis(np.linspace(0, 1, len(t)))
    ax3.scatter(theta, r, c=colors, s=2, alpha=0.7)
    
    ax3.set_title("Harmonic Spiral", color='white', fontsize=12, fontweight='bold', pad=15)
    ax3.tick_params(colors='gray')
    ax3.grid(True, alpha=0.2, color='white')
    
    # === PANEL 4: Frequency Domain Intuition ===
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.set_facecolor('#0a0a12')
    
    # Simple FFT visualization
    from scipy.fft import fft, fftfreq
    
    n = len(t)
    dt = t[1] - t[0]
    
    # FFT of noisy vs DDA
    fft_noisy = np.abs(fft(noisy))[:n//2]
    fft_dda = np.abs(fft(filtered))[:n//2]
    freqs = fftfreq(n, dt)[:n//2]
    
    ax4.fill_between(freqs, fft_noisy, alpha=0.3, color=noise_color, label='Noisy Spectrum')
    ax4.plot(freqs, fft_dda, color=dda_color, lw=2, label='DDA Spectrum')
    
    # Mark the harmonics
    for f, label in [(0.5, 'f₁'), (1.5, 'f₃'), (2.5, 'f₅')]:
        ax4.axvline(f, color=fundamental_color, alpha=0.5, linestyle='--', lw=1)
        ax4.text(f + 0.05, ax4.get_ylim()[1] * 0.9, label, color=fundamental_color, fontsize=10)
    
    ax4.set_xlim(0, 4)
    ax4.set_title("Frequency Separation", color='white', fontsize=12, fontweight='bold')
    ax4.set_xlabel("Frequency", color='gray')
    ax4.set_ylabel("Magnitude", color='gray')
    ax4.legend(loc='upper right', facecolor='#1a1a2e', edgecolor='none',
               labelcolor='white', fontsize=9)
    ax4.tick_params(colors='gray')
    for spine in ax4.spines.values():
        spine.set_color('#333')
    
    plt.suptitle("DDA: The Resonance", fontsize=18, fontweight='bold', 
                 color='white', y=0.98)
    
    plt.tight_layout()
    plt.savefig('dda_resonance.png', dpi=150, facecolor='#0a0a12', 
                edgecolor='none', bbox_inches='tight')
    
    print("\n✓ Saved to dda_resonance.png")
    print("\n\"The harmonics were always there.")
    print(" DDA just knows how to listen.\"")


if __name__ == "__main__":
    render_resonance()
