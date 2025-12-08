"""
DDA v14.0 "THE SWING SURFER"
----------------------------
Timeframe: 1 Hour (Macro).
Strategy: Low Frequency, High Inertia.
Goal: Capture the 2024 Bull Run without getting chopped up.
"""
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')

class DDA_Swing:
    def __init__(self):
        # SWING SETTINGS (Glacial Pace)
        self.P0_stable = 0.995   # Extremely slow adaptation
        self.P0_react = 0.0      # Instant snap on regime change
        
        # Only react to massive moves (6-sigma events)
        self.saccade_thresh = 6.0 
        self.derivative_boost = 0.8
        
        self.k = 1.0
        self.F_prev = None
        self.price_history = []
        self.volatility = 0.0
        
    def update(self, price):
        self.price_history.append(price)
        if len(self.price_history) < 50: # Longer warmup
            self.F_prev = price
            return "WAIT", price
        if len(self.price_history) > 200: self.price_history.pop(0)

        # Longer volatility window (24h)
        recent = self.price_history[-24:] 
        self.volatility = np.std(recent) or 0.01

        diff = price - self.F_prev
        error = abs(diff)
        signal = "HOLD"
        
        # SACCADIC GATING
        if error > (self.saccade_thresh * self.volatility):
            effective_P0 = self.P0_react
            effective_m = 1.0
            # Only enter if we are breaking OUT
            if diff > 0: signal = "LONG_ENTRY"
            else:        signal = "SHORT_ENTRY"
        else:
            effective_P0 = self.P0_stable
            effective_m = 1.0 - effective_P0
            
            # Trend Following Exit
            # If price crosses the Slow DDA line, the trend is broken
            if price < self.F_prev: signal = "LONG_EXIT"
            if price > self.F_prev: signal = "SHORT_EXIT"

        prior = effective_P0 * self.k * self.F_prev
        delta = price - self.price_history[-2]
        boost = 0.6 * delta 
        F = prior + (effective_m * (price + boost))
        
        # Adaptation
        if "ENTRY" not in signal:
            err = price - F
            self.k += 0.0001 * np.sign(err) * (abs(err)**0.5) # Slower learning
            self.k = np.clip(self.k, 0.95, 1.05)
        else: self.k = 1.0
            
        self.F_prev = F
        return signal, F

def run_swing_test():
    print("📡 Downloading 2 YEARS of BTC-USD (1h)...")
    df = yf.download("BTC-USD", period="2y", interval="1h", progress=False)
    prices = df['Close'].values
    dates = df.index
    
    print(f"✅ Loaded {len(prices)} candles")
    
    bot = DDA_Swing()
    cash = 1000.0
    lev = 2.0 # 2x Leverage is safe for swings
    fee = 0.001
    
    position = 0
    entry_price = 0
    equity = [cash]
    trades = []
    
    for i in tqdm(range(len(prices)), desc="Surfing"):
        price = float(prices[i]) # Force float
        sig, val = bot.update(price)
        
        # EXECUTION
        if position == 0:
            if "ENTRY" in sig:
                # Basic Trend Filter: Don't short if price > 200h Avg
                # (Simplified for this script)
                position = 1 if "LONG" in sig else -1
                entry_price = price
                cash -= (cash * lev * fee)
        else:
            is_exit = False
            if position == 1 and ("SHORT" in sig or "LONG_EXIT" in sig): is_exit = True
            if position == -1 and ("LONG" in sig or "SHORT_EXIT" in sig): is_exit = True
            
            if is_exit:
                diff = (price - entry_price) if position == 1 else (entry_price - price)
                pos_size = (cash * lev) / entry_price
                pnl = diff * pos_size
                cash += pnl
                cash -= (cash * lev * fee)
                trades.append(pnl)
                position = 0
        
        # Mark to Market
        curr = cash
        if position != 0:
            diff = (price - entry_price) if position == 1 else (entry_price - price)
            curr += diff * ((cash * lev) / entry_price)
            
        equity.append(curr)
        if curr <= 0: break
        
    # RESULT
    final = float(equity[-1])
    hodl = float((1000 / prices[0]) * prices[-1])
    
    print("\n" + "="*50)
    print("SWING TRADER RESULTS")
    print("="*50)
    print(f"Final Cash:   ${final:,.2f}")
    print(f"Buy & Hold:   ${hodl:,.2f}")
    print(f"Trades:       {len(trades)}") # Expecting < 200
    
    if final > hodl:
        print(f"\n🏆 WINNER: DDA SWING (+{((final-hodl)/hodl)*100:.1f}%)")
    else:
        print(f"\n❌ WINNER: HODL")

    # PLOT (Fixed)
    plt.figure(figsize=(12, 6))
    
    # Convert list to numpy array to prevent matplotlib crash
    eq_arr = np.array(equity, dtype=float)
    
    plt.plot(eq_arr, 'r-', label='DDA Equity (2x)')
    
    # Scale HODL line
    prices_arr = np.array(prices, dtype=float)
    scale = 1000 / prices_arr[0]
    plt.plot(prices_arr * scale, 'g--', alpha=0.5, label='Buy & Hold')
    
    plt.title("DDA v14 Swing Trader: 2-Year Performance")
    plt.yscale('log')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('dda_swing_proof.png')
    print("✓ Chart saved.")

if __name__ == "__main__":
    run_swing_test()