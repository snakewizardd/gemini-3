"""
DDA "THE BRUSHSTROKE" — An Artistic Meditation
-----------------------------------------------
No competition. No benchmarks. Just flow.

DDA interpreted as a master calligrapher's hand:
- Raw input: The tremor of an unsteady hand
- DDA output: The flowing brushstroke of a Zen master

This demonstrates DDA's philosophical core:
"Trust the past, but feel the present. Flow, don't jerk."

Watch as chaos transforms into grace.
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')


@dataclass
class BrushConfig:
    """The brush's soul."""
    P0: float = 0.75           # Memory of where we've been
    m: float = 0.25            # Openness to the new stroke
    derivative_boost: float = 0.4  # Anticipation of motion
    ema_alpha: float = 0.15    # Smoothness of the wrist


class DDA_Brush:
    """
    A brush that remembers.
    
    The master calligrapher doesn't fight the tremor — 
    they let it pass through them, filtered by decades of practice.
    DDA is that practice, encoded in three lines.
    """
    
    def __init__(self):
        self.c = BrushConfig()
        self.x_prev = 0.0
        self.y_prev = 0.0
        self.ix_prev = 0.0
        self.iy_prev = 0.0
        self.dx = 0.0
        self.dy = 0.0
        self.k = 1.0
        self.init = False
        
    def stroke(self, x_raw, y_raw):
        """
        Transform a trembling hand into a flowing line.
        """
        if not self.init:
            self.x_prev = x_raw
            self.y_prev = y_raw
            self.ix_prev = x_raw
            self.iy_prev = y_raw
            self.init = True
            return x_raw, y_raw
        
        # The change in intention
        delta_x = x_raw - self.ix_prev
        delta_y = y_raw - self.iy_prev
        
        # Smooth the velocity (the wrist's rhythm)
        self.dx = (self.c.ema_alpha * delta_x) + ((1 - self.c.ema_alpha) * self.dx)
        self.dy = (self.c.ema_alpha * delta_y) + ((1 - self.c.ema_alpha) * self.dy)
        
        # Anticipate where the stroke wants to go
        Lx = x_raw + (self.c.derivative_boost * self.dx)
        Ly = y_raw + (self.c.derivative_boost * self.dy)
        
        # The fusion: past wisdom + present intention
        x_out = (self.c.P0 * self.k * self.x_prev) + (self.c.m * Lx)
        y_out = (self.c.P0 * self.k * self.y_prev) + (self.c.m * Ly)
        
        # Remember
        self.x_prev = x_out
        self.y_prev = y_out
        self.ix_prev = x_raw
        self.iy_prev = y_raw
        
        return x_out, y_out


def create_trembling_hand_path():
    """
    Simulate a hand drawing a flowing character,
    but with the natural tremor and imprecision of human movement.
    """
    # The intention: a smooth spiral into a flourish
    t = np.linspace(0, 4 * np.pi, 500)
    
    # Base path: an elegant spiral
    intention_x = t * np.cos(t) * 0.3
    intention_y = t * np.sin(t) * 0.3 + np.sin(t * 0.5) * 2
    
    # Human tremor: high-frequency noise + occasional jerks
    tremor_x = np.random.normal(0, 0.15, len(t))
    tremor_y = np.random.normal(0, 0.15, len(t))
    
    # Add occasional "hiccups" (hand slips)
    for _ in range(8):
        idx = np.random.randint(50, len(t) - 50)
        tremor_x[idx:idx+5] += np.random.normal(0, 0.5)
        tremor_y[idx:idx+5] += np.random.normal(0, 0.5)
    
    raw_x = intention_x + tremor_x
    raw_y = intention_y + tremor_y
    
    return raw_x, raw_y, intention_x, intention_y


def calculate_velocity(x, y):
    """Calculate velocity magnitude at each point for coloring."""
    vx = np.diff(x, prepend=x[0])
    vy = np.diff(y, prepend=y[0])
    return np.sqrt(vx**2 + vy**2)


def render_brushstroke():
    """
    Create the meditation.
    """
    print("🎨 THE BRUSHSTROKE")
    print("=" * 50)
    print("\"The master's hand trembles like anyone else's.")
    print(" What differs is what reaches the paper.\"")
    print("=" * 50)
    
    np.random.seed(42)
    
    # Generate the trembling intention
    raw_x, raw_y, intention_x, intention_y = create_trembling_hand_path()
    
    # The brush transforms
    brush = DDA_Brush()
    smooth_x, smooth_y = [], []
    
    for x, y in zip(raw_x, raw_y):
        sx, sy = brush.stroke(x, y)
        smooth_x.append(sx)
        smooth_y.append(sy)
    
    smooth_x = np.array(smooth_x)
    smooth_y = np.array(smooth_y)
    
    # --- THE CANVAS ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    fig.patch.set_facecolor('#f5f0e6')  # Rice paper
    
    for ax in axes:
        ax.set_facecolor('#f5f0e6')
        ax.set_aspect('equal')
        ax.axis('off')
    
    # Panel 1: The Intention (what the mind wanted)
    ax1 = axes[0]
    ax1.plot(intention_x, intention_y, 'k-', lw=2, alpha=0.8)
    ax1.set_title("意 The Intention", fontsize=14, fontweight='bold', 
                  fontfamily='serif', pad=15)
    
    # Panel 2: The Tremor (what the hand produced)
    ax2 = axes[1]
    velocity = calculate_velocity(raw_x, raw_y)
    points = np.array([raw_x, raw_y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    
    # Color by velocity (faster = darker)
    norm = plt.Normalize(velocity.min(), velocity.max())
    lc = LineCollection(segments, cmap='Greys', norm=norm, linewidths=1.5, alpha=0.7)
    lc.set_array(velocity)
    ax2.add_collection(lc)
    ax2.autoscale()
    ax2.set_title("震 The Tremor", fontsize=14, fontweight='bold',
                  fontfamily='serif', pad=15)
    
    # Panel 3: The Brushstroke (DDA output)
    ax3 = axes[2]
    velocity_smooth = calculate_velocity(smooth_x, smooth_y)
    points_smooth = np.array([smooth_x, smooth_y]).T.reshape(-1, 1, 2)
    segments_smooth = np.concatenate([points_smooth[:-1], points_smooth[1:]], axis=1)
    
    # Variable line width based on velocity (like ink flow)
    widths = 1 + 3 * (velocity_smooth / velocity_smooth.max())
    
    lc_smooth = LineCollection(segments_smooth, cmap='binary', 
                               norm=plt.Normalize(0, velocity_smooth.max()),
                               linewidths=widths, alpha=0.9)
    lc_smooth.set_array(velocity_smooth)
    ax3.add_collection(lc_smooth)
    ax3.autoscale()
    ax3.set_title("筆 The Brushstroke", fontsize=14, fontweight='bold',
                  fontfamily='serif', pad=15)
    
    plt.suptitle("DDA: The Algorithm of Flow", fontsize=18, fontweight='bold',
                 fontfamily='serif', y=0.98)
    
    plt.tight_layout()
    plt.savefig('dda_brushstroke.png', dpi=150, facecolor='#f5f0e6', 
                edgecolor='none', bbox_inches='tight')
    
    print("\n✓ Meditation saved to dda_brushstroke.png")
    print("\n\"Between tremor and paper, there is DDA.\"")


if __name__ == "__main__":
    render_brushstroke()
