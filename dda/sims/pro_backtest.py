"""
DDA v13.1 PROFESSIONAL BACKTEST (Fixed & Tuned)
-----------------------------------------------
Fixes:
1. Numpy formatting crash (float conversion).
2. Strategy Tuning: Increased Threshold to 4.0 to stop over-trading.
"""
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')

class DDA_Pro:
    def __init__(self, thresh=4.0, p0=0.99): # <--- TUNED: Stiffer P0, Higher Thresh
        self.c = {'thresh': thresh, 'p0': p0}
        self.k = 1.0
        self.F_prev = None
        self.price_history = []
        self.volatility = 0.0
        
    def update(self, price, regime_trend):
        self.price_history.append(price)
        if len(self.price_history) < 20:
            self.F_prev = price
            return "WAIT", price
        if len(self.price_history) > 100: self.price_history.pop(0)

        recent = self.price_history[-20:]
        self.volatility = np.std(recent) or 0.01

        diff = price - self.F_prev
        error = abs(diff)
        signal = "HOLD"
        
        if error > (self.c['thresh'] * self.volatility):
            effective_P0 = 0.0
            effective_m = 1.0
            
            # REGIME FILTER
            if diff > 0 and regime_trend == 1: 
                signal = "LONG_ENTRY"
            elif diff < 0 and regime_trend == -1: 
                signal = "SHORT_ENTRY"
        else:
            effective_P0 = self.c['p0']
            effective_m = 1.0 - effective_P0
            if price < self.F_prev: signal = "LONG_EXIT"
            if price > self.F_prev: signal = "SHORT_EXIT"

        prior = effective_P0 * self.k * self.F_prev
        delta = price - self.price_history[-2]
        boost = 0.6 * delta 
        F = prior + (effective_m * (price + boost))
        
        if "ENTRY" not in signal:
            err = price - F
            self.k += 0.001 * np.sign(err) * (abs(err)**0.5)
            self.k = np.clip(self.k, 0.9, 1.1)
        else: self.k = 1.0
            
        self.F_prev = F
        return signal, F

def get_data():
    print("📡 Downloading 2 YEARS of BTC-USD (1h)...")
    df = yf.download("BTC-USD", period="2y", interval="1h", progress=False)
    # 240-hour SMA (10 Days) for Trend Filter
    df['SMA_Trend'] = df['Close'].rolling(window=240).mean()
    df.dropna(inplace=True)
    return df

def run_simulation():
    df = get_data()
    prices = df['Close'].values
    smas = df['SMA_Trend'].values
    dates = df.index
    
    print(f"✅ Loaded {len(prices)} candles")
    
    # PARAMETERS (Tuned for Stability)
    bot = DDA_Pro(thresh=4.0, p0=0.99)
    
    cash = 1000.0
    lev = 2.0 
    fee = 0.001 
    
    position = 0
    entry_price = 0
    equity = []
    trades = []
    
    for i in tqdm(range(len(prices)), desc="Simulating"):
        price = prices[i]
        sma = smas[i]
        regime = 1 if price > sma else -1
        
        sig, val = bot.update(price, regime)
        
        if position == 0:
            if "ENTRY" in sig:
                position = 1 if "LONG" in sig else -1
                entry_price = price
                cash -= (cash * lev * fee)
        else:
            is_exit = False
            if position == 1 and ("SHORT" in sig or "EXIT" in sig): is_exit = True
            if position == -1 and ("LONG" in sig or "EXIT" in sig): is_exit = True
            
            if is_exit:
                diff = (price - entry_price) if position == 1 else (entry_price - price)
                pos_size = (cash * lev) / entry_price
                pnl = diff * pos_size
                cash += pnl
                cash -= (cash * lev * fee) 
                trades.append(pnl)
                position = 0
                
        equity.append(cash)
        if cash <= 0: break
        
    # FIX: Explicit float conversion
    final = float(equity[-1])
    hodl = float((1000 / prices[0]) * prices[-1])
    
    print("\n" + "="*50)
    print("2-YEAR BACKTEST RESULTS")
    print("="*50)
    print(f"Start Cash:   $1,000.00")
    print(f"Final Cash:   ${final:,.2f}")
    print(f"Buy & Hold:   ${hodl:,.2f}")
    print(f"Trades:       {len(trades)}")
    
    if final > hodl:
        print(f"\n🏆 WINNER: DDA (+{((final-hodl)/hodl)*100:.1f}%)")
    else:
        print(f"\n❌ WINNER: HODL (DDA Underperformed)")
        
    plt.figure(figsize=(12, 6))
    plt.plot(equity, 'r-', label='DDA Equity')
    
    scale = 1000 / prices[0]
    plt.plot(prices * scale, 'g--', alpha=0.5, label='Buy & Hold')
    
    plt.title("DDA v13 Pro: 2-Year Performance")
    plt.yscale('log')
    plt.legend()
    plt.savefig('dda_pro_proof.png')
    print("✓ Chart saved.")

if __name__ == "__main__":
    run_simulation()