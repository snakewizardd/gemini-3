"""
DDA v11.0 VISUAL SCALPER (Live GUI)
-----------------------------------
Real-time visualization of the Predator Algorithm trading BTC/USDT.
Connects to Kraken (Public API). No Keys required.
"""
import ccxt
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime
import warnings
import threading

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE BRAIN: DDA v11.0 (Embedded)
# =============================================================================
class DDAScalper:
    def __init__(self):
        self.P0_stable = 0.98; self.P0_react = 0.0; self.saccade_thresh = 2.5
        self.k = 1.0; self.F_prev = None; self.price_history = []; self.volatility = 0.0
        
    def update(self, price):
        self.price_history.append(price)
        if len(self.price_history) < 20:
            self.F_prev = price
            return "WAIT", price
        if len(self.price_history) > 100: self.price_history.pop(0)

        recent = self.price_history[-20:]
        self.volatility = np.std(recent)
        if self.volatility == 0: self.volatility = 0.01

        diff = price - self.F_prev
        error = np.abs(diff)
        signal = "HOLD"
        
        if error > (self.saccade_thresh * self.volatility):
            effective_P0 = self.P0_react; effective_m = 1.0
            if diff > 0: signal = "LONG_ENTRY"
            else:        signal = "SHORT_ENTRY"
        else:
            effective_P0 = self.P0_stable; effective_m = 1.0 - effective_P0
            if price < self.F_prev: signal = "LONG_EXIT"
            if price > self.F_prev: signal = "SHORT_EXIT"

        prior = effective_P0 * self.k * self.F_prev
        delta = price - self.price_history[-2]
        boost = 0.6 * delta 
        F = prior + (effective_m * (price + boost))
        
        if signal == "HOLD" or "EXIT" in signal:
            err = price - F
            self.k += 0.001 * np.sign(err) * (np.abs(err)**0.5)
            self.k = np.clip(self.k, 0.9, 1.1)
        else: self.k = 1.0
            
        self.F_prev = F
        return signal, F

# =============================================================================
# 2. DATA CONTAINER
# =============================================================================
class LiveData:
    def __init__(self):
        self.times = []
        self.prices = []
        self.dda_vals = []
        self.balance_history = []
        self.signals_idx = []
        self.signals_type = [] # 'g^', 'rv', 'kx'
        
        # Portfolio State
        self.cash = 1000.0
        self.leverage = 50
        self.position = None
        self.bot = DDAScalper()
        self.exchange = ccxt.kraken()
        self.last_ts = 0

# Global State
state = LiveData()

# =============================================================================
# 3. TRADING LOGIC (Runs inside Animation Loop)
# =============================================================================
def update_logic(i):
    try:
        # Fetch Data (1m Candle)
        ohlcv = state.exchange.fetch_ohlcv('BTC/USDT', '1m', limit=2)
        candle = ohlcv[-2] # Closed Candle
        ts = candle[0]
        price = candle[4]
        
        # Only update if new candle
        if ts == state.last_ts:
            return
            
        state.last_ts = ts
        dt = datetime.fromtimestamp(ts/1000).strftime('%H:%M')
        
        # Run Brain
        sig, val = state.bot.update(price)
        
        # Update Arrays
        state.times.append(dt)
        state.prices.append(price)
        state.dda_vals.append(val)
        
        # Keep window small
        if len(state.times) > 100:
            state.times.pop(0); state.prices.pop(0); state.dda_vals.pop(0); state.balance_history.pop(0)
            # Adjust signal indices
            state.signals_idx = [x-1 for x in state.signals_idx if x > 0]
            
        # EXECUTION LOGIC
        executed = False
        
        if state.position is None:
            if "ENTRY" in sig:
                direction = "LONG" if "LONG" in sig else "SHORT"
                margin = state.cash; size = (margin * state.leverage) / price
                fee = (margin * state.leverage) * 0.0005; state.cash -= fee
                state.position = {'type': direction, 'entry': price, 'size': size}
                
                state.signals_idx.append(len(state.prices)-1)
                state.signals_type.append('g^' if direction=="LONG" else 'rv')
                executed = True
                print(f"[{dt}] 🚀 OPEN {direction} @ {price}")
        else:
            close_long = (state.position['type'] == "LONG" and ("SHORT" in sig or "EXIT" in sig))
            close_short = (state.position['type'] == "SHORT" and ("LONG" in sig or "EXIT" in sig))
            
            if close_long or close_short:
                entry = state.position['entry']; size = state.position['size']
                if state.position['type'] == "LONG": pnl = (price - entry) * size
                else: pnl = (entry - price) * size
                
                state.cash += pnl
                fee = (size * price) * 0.0005; state.cash -= fee
                
                state.signals_idx.append(len(state.prices)-1)
                state.signals_type.append('kx')
                state.position = None
                executed = True
                print(f"[{dt}] 💰 CLOSE @ {price} | PnL: ${pnl:.2f}")
                
        state.balance_history.append(state.cash)
        
        if not executed:
            print(f"[{dt}] Price: {price} | DDA: {val:.1f} | Sig: {sig}")

        # --- UPDATE PLOTS ---
        ax1.clear(); ax2.clear()
        
        # Plot 1: Price vs DDA
        ax1.plot(state.prices, 'k-', alpha=0.6, label='BTC Price')
        ax1.plot(state.dda_vals, 'b-', lw=1.5, alpha=0.8, label='DDA Fair Value')
        
        # Plot Signals
        for j, idx in enumerate(state.signals_idx):
            if idx < len(state.prices):
                marker = state.signals_type[j]
                color = 'green' if 'g' in marker else ('red' if 'r' in marker else 'black')
                m_style = '^' if '^' in marker else ('v' if 'v' in marker else 'x')
                ax1.plot(idx, state.prices[idx], marker=m_style, color=color, markersize=10)

        ax1.set_title(f"DDA Predator Node | BTC/USDT (1m) | {dt}")
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Equity
        ax2.plot(state.balance_history, 'g-', lw=2)
        ax2.set_title(f"Account Balance: ${state.cash:,.2f}")
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()

    except Exception as e:
        print(f"Wait... {e}")

# =============================================================================
# 4. INITIALIZE
# =============================================================================
print("🔥 PRE-WARMING BRAIN...")
# Pre-load 30 mins
hist = state.exchange.fetch_ohlcv('BTC/USDT', '1m', limit=30)
for c in hist[:-1]:
    state.bot.update(c[4])
print("✅ BRAIN READY. LAUNCHING GUI...")

# Setup Plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]})
ani = animation.FuncAnimation(fig, update_logic, interval=5000) # Check every 5s
plt.show()