"""
DDA CRYPTO PREDATOR
-------------------
Ingestion Engine for High-Frequency Crypto Assets.

Logic:
1. The "Chop Killer": High Inertia during sideways movement (prevents overtrading).
2. The "Flash Eater": Saccadic Snap during breakouts/crashes (captures the move).
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE CRYPTO PREDATOR (Ingestion Engine)
# =============================================================================
@dataclass
class PredatorConfig:
    # MARKET REGIME SETTINGS
    # How stubborn are we during chop? (0.95 = Diamond Hands)
    P0_chop: float = 0.95
    # How fast do we react to a moon/crash? (0.0 = Instant)
    P0_breakout: float = 0.0
    
    # TRIGGER
    # How many Standard Deviations (Sigma) before we admit it's a breakout?
    # Crypto is volatile, so we need a high threshold (e.g., 3-4 sigma)
    saccade_thresh: float = 3.5 
    
    # Pre-Cognition (Trend Following)
    derivative_boost: float = 0.5
    
    # Volatility Window (for calculating dynamic sigma)
    vol_window: int = 20

class CryptoPredator:
    def __init__(self):
        self.c = PredatorConfig()
        self.k = 1.0
        self.F_prev = None # Fair Value Estimate
        self.price_history = []
        self.volatility = 0.0
        self.position = 0 # 1 = Long, -1 = Short, 0 = Cash
        self.trades = [] # Log trades
        
    def ingest(self, current_price):
        # 1. WARM UP (Need history for volatility)
        self.price_history.append(current_price)
        if len(self.price_history) < self.c.vol_window:
            self.F_prev = current_price
            return "WAIT", current_price
            
        # 2. CALCULATE DYNAMIC VOLATILITY (Rolling Std Dev)
        # We need to know what "Noise" looks like right now
        recent_prices = self.price_history[-self.c.vol_window:]
        self.volatility = np.std(recent_prices)
        if self.volatility == 0: self.volatility = 0.001 # Safety
        
        # 3. RETINAL SLIP (Price vs Fair Value)
        error = np.abs(current_price - self.F_prev)
        
        # 4. SACCADIC GATING (The Trade Decision)
        signal = "HOLD"
        
        if error > (self.c.saccade_thresh * self.volatility):
            # MODE: BREAKOUT (Saccade)
            effective_P0 = self.c.P0_breakout
            effective_m = 1.0
            
            # If price snapped UP -> BUY
            if current_price > self.F_prev:
                signal = "BUY (Breakout)"
            # If price snapped DOWN -> SELL
            else:
                signal = "SELL (Crash)"
                
        else:
            # MODE: CHOP (Fixate)
            effective_P0 = self.c.P0_chop
            effective_m = 1.0 - effective_P0
            signal = "WAIT"
            
        # 5. UPDATE FAIR VALUE (The DDA Core)
        # Calculate Trend (Derivative)
        delta = current_price - self.price_history[-2]
        
        # Apply Logic
        prior = effective_P0 * self.k * self.F_prev
        
        # Only apply Boost in Chop mode (to track slow trends). 
        # In Breakout, we just want the raw price.
        if signal == "WAIT":
            L = current_price + (self.c.derivative_boost * delta)
        else:
            L = current_price
            
        F = prior + (effective_m * L)
        
        # 6. ADAPTATION
        if signal == "WAIT":
            err = current_price - F
            # Gently adjust gain
            self.k += 0.001 * np.sign(err) * (np.abs(err)**0.5)
            self.k = np.clip(self.k, 0.9, 1.1)
        else:
            self.k = 1.0 # Reset on breakout
            
        self.F_prev = F
        return signal, F

# =============================================================================
# 2. MARKET GENERATOR (Jump Diffusion Model)
# =============================================================================
def generate_crypto_stream(steps=1000):
    # Geometric Brownian Motion + Poisson Jumps (Flash Crashes/Pumps)
    dt = 1/365
    mu = 0.5 # Drift (Bull Market)
    sigma = 0.5 # High Volatility
    
    prices = [10000.0]
    
    for _ in range(steps):
        # Normal Drift/Diffusion
        shock = np.random.normal(0, 1)
        price = prices[-1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * shock)
        
        # Jump Diffusion (Whale Manipulation / News)
        # 2% chance of massive move
        if np.random.random() < 0.02:
            jump_size = np.random.normal(0, 0.05) # +/- 5% instant candle
            price *= (1 + jump_size)
            
        prices.append(price)
        
    return prices

# =============================================================================
# 3. RUN SIMULATION
# =============================================================================
def run_ingest():
    print("💎 CONNECTING TO SIMULATED CRYPTO FEED...")
    prices = generate_crypto_stream(500)
    bot = CryptoPredator()
    
    dda_vals = []
    signals = []
    
    # Portfolio Tracking
    cash = 10000.0
    btc = 0.0
    portfolio_history = []
    
    print("🚀 INGESTING TICKS...")
    for p in prices:
        sig, val = bot.ingest(p)
        dda_vals.append(val)
        
        # Execute Strategy
        if "BUY" in sig and cash > 0:
            btc = cash / p
            cash = 0
            signals.append((len(dda_vals)-1, p, 'g^')) # Log Buy
        elif "SELL" in sig and btc > 0:
            cash = btc * p
            btc = 0
            signals.append((len(dda_vals)-1, p, 'rv')) # Log Sell
            
        # Mark to Market
        curr_val = cash + (btc * p)
        portfolio_history.append(curr_val)

    # Final Value
    final_val = portfolio_history[-1]
    bh_val = (10000 / prices[0]) * prices[-1] # Buy & Hold
    
    print("\n" + "="*50)
    print("TRADING RESULTS")
    print("="*50)
    print(f"Buy & Hold:   ${bh_val:,.2f}")
    print(f"DDA Predator: ${final_val:,.2f}")
    
    if final_val > bh_val:
        print(f"🏆 WINNER: DDA (+{((final_val-bh_val)/bh_val)*100:.1f}%)")
    else:
        print("🏆 WINNER: HODL")

    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
    
    # Price Chart
    ax1.plot(prices, 'k-', alpha=0.5, label='BTC/USD')
    ax1.plot(dda_vals, 'b-', lw=1, alpha=0.8, label='DDA Fair Value')
    
    # Plot Trades
    for t in signals:
        ax1.plot(t[0], t[1], t[2], markersize=10)
        
    ax1.set_title("DDA Crypto Ingestion: Saccadic Buy/Sell Signals")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Portfolio Chart
    ax2.plot(portfolio_history, 'r-', lw=2, label='DDA Portfolio')
    ax2.axhline(bh_val, color='g', linestyle='--', label='Buy & Hold Final')
    ax2.set_title("Equity Curve")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dda_crypto_sim.png')
    print("✓ Chart saved to dda_crypto_sim.png")

if __name__ == "__main__":
    run_ingest()