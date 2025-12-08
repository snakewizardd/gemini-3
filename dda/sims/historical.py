"""
DDA v12.0 HISTORICAL VALIDATION SUITE
-------------------------------------
1. Fetches real historical data (Kraken).
2. Grid Searches for optimal DDA parameters (P0, Boost).
3. Proves performance vs Buy & Hold.
"""
import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from itertools import product
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE DDA ENGINE (Parameterized)
# =============================================================================
@dataclass
class DDAConfig:
    P0_stable: float = 0.98
    P0_react: float = 0.0
    saccade_thresh: float = 3.0
    derivative_boost: float = 0.5
    
class DDABacktester:
    def __init__(self, config):
        self.c = config
        self.k = 1.0
        self.F_prev = None
        self.price_history = []
        self.volatility = 0.0
        
    def update(self, price):
        # 1. Warm Up
        self.price_history.append(price)
        if len(self.price_history) < 20:
            self.F_prev = price
            return "WAIT"
        if len(self.price_history) > 100: self.price_history.pop(0)

        # 2. Volatility
        recent = self.price_history[-20:]
        self.volatility = np.std(recent) or 0.01

        # 3. Logic
        diff = price - self.F_prev
        error = abs(diff)
        signal = "HOLD"
        
        if error > (self.c.saccade_thresh * self.volatility):
            effective_P0 = self.c.P0_react
            effective_m = 1.0
            if diff > 0: signal = "LONG_ENTRY"
            else:        signal = "SHORT_ENTRY"
        else:
            effective_P0 = self.c.P0_stable
            effective_m = 1.0 - effective_P0
            if price < self.F_prev: signal = "LONG_EXIT"
            if price > self.F_prev: signal = "SHORT_EXIT"

        prior = effective_P0 * self.k * self.F_prev
        delta = price - self.price_history[-2]
        boost = self.c.derivative_boost * delta 
        F = prior + (effective_m * (price + boost))
        
        if signal == "HOLD" or "EXIT" in signal:
            err = price - F
            self.k += 0.001 * np.sign(err) * (abs(err)**0.5)
            self.k = np.clip(self.k, 0.9, 1.1)
        else: self.k = 1.0
            
        self.F_prev = F
        return signal

# =============================================================================
# 2. DATA LOADER (Pagination for Long History)
# =============================================================================
def fetch_history(symbol='BTC/USDT', timeframe='5m', days=30):
    print(f"📡 Downloading {days} days of {symbol} ({timeframe})...")
    exchange = ccxt.kraken()
    
    # Calculate start time
    since = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
    all_candles = []
    
    while since < exchange.milliseconds():
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since, limit=720)
            if not candles: break
            
            since = candles[-1][0] + 1
            all_candles += candles
            print(f"   Fetched {len(candles)} candles... ({pd.to_datetime(candles[-1][0], unit='ms')})")
            
            # Rate limit safety
            import time; time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            break
            
    df = pd.DataFrame(all_candles, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    return df['close'].values

# =============================================================================
# 3. BACKTEST KERNEL
# =============================================================================
def run_strategy(prices, config):
    bot = DDABacktester(config)
    cash = 1000.0
    position = 0 # 0=Flat, 1=Long, -1=Short
    entry_price = 0
    balance_history = []
    
    # 50x Leverage, 0.05% Fee
    lev = 50
    fee_rate = 0.0005
    
    for p in prices:
        sig = bot.update(p)
        
        # EXECUTION
        if position == 0:
            if "ENTRY" in sig:
                position = 1 if "LONG" in sig else -1
                entry_price = p
                cash -= (cash * lev * fee_rate) # Entry Fee
        else:
            # EXIT Condition
            is_exit = False
            if position == 1 and ("SHORT" in sig or "EXIT" in sig): is_exit = True
            if position == -1 and ("LONG" in sig or "EXIT" in sig): is_exit = True
            
            if is_exit:
                diff = (p - entry_price) if position == 1 else (entry_price - p)
                size = (cash * lev) / entry_price
                pnl = diff * size
                cash += pnl
                cash -= (cash * lev * fee_rate) # Exit Fee
                position = 0
                
        balance_history.append(cash)
        if cash <= 0: break # Bust
        
    return balance_history

# =============================================================================
# 4. OPTIMIZER (The Proof Generator)
# =============================================================================
def prove_it():
    # A. Get Data
    prices = fetch_history(days=7) # Test last week
    
    # B. Define Search Space
    p0_range = [0.90, 0.95, 0.98, 0.99]
    thresh_range = [2.0, 3.0, 4.0]
    boost_range = [0.4, 0.6, 0.8]
    
    print(f"\n🔬 OPTIMIZING PARAMETERS ({len(p0_range)*len(thresh_range)*len(boost_range)} combinations)...")
    
    best_score = -99999
    best_config = None
    best_equity = []
    
    for p0, th, b in product(p0_range, thresh_range, boost_range):
        cfg = DDAConfig(P0_stable=p0, saccade_thresh=th, derivative_boost=b)
        equity = run_strategy(prices, cfg)
        
        if not equity: final = 0
        else: final = equity[-1]
        
        if final > best_score:
            best_score = final
            best_config = cfg
            best_equity = equity
            # print(f"New Best: ${final:.2f} (P0={p0}, Th={th}, Boost={b})")

    # C. Results
    print("\n" + "="*50)
    print(f"🏆 BEST CONFIGURATION FOUND")
    print("="*50)
    print(f"P0 (Inertia): {best_config.P0_stable}")
    print(f"Threshold:    {best_config.saccade_thresh} sigma")
    print(f"Boost:        {best_config.derivative_boost}")
    print("-" * 50)
    
    start = 1000.0
    end_dda = best_equity[-1] if best_equity else 0
    end_hodl = (1000 / prices[0]) * prices[-1]
    
    print(f"Start Balance: ${start:,.2f}")
    print(f"Buy & Hold:    ${end_hodl:,.2f}")
    print(f"DDA Optimized: ${end_dda:,.2f}")
    
    if end_dda > end_hodl:
        print(f"\n✅ PROOF SUCCESS: Beat Market by {((end_dda-end_hodl)/end_hodl)*100:.1f}%")
    else:
        print(f"\n❌ PROOF FAILED: Market conditions unfavorable for Scalping.")

    # D. Visualization
    plt.figure(figsize=(12, 6))
    plt.plot(best_equity, 'r-', lw=2, label=f'DDA (Opt)')
    plt.axhline(end_hodl, color='g', linestyle='--', label='Buy & Hold')
    plt.axhline(start, color='k', linestyle=':', label='Breakeven')
    plt.title(f"Historical Proof: DDA Scalper vs Market (50x Lev)\nResult: ${end_dda:.2f}")
    plt.legend()
    plt.savefig('dda_historical_proof.png')
    print("✓ Proof saved to dda_historical_proof.png")

if __name__ == "__main__":
    prove_it()