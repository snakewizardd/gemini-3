"""
DDA v15.0 "TREND COMMANDER"
---------------------------
Strategy: Asymmetric Trend Following.
Logic: 
  1. Bull Mode (Price > DDA): 2x Leverage.
  2. Bear Mode (Price < DDA): 0x Leverage (Cash).
  3. NO SHORTING. Never short a parabolic asset.
"""
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')

class DDA_Commander:
    def __init__(self):
        # COMMANDER SETTINGS (The "Heavy" Tune)
        # We want to stay in the trade for MONTHS, not hours.
        self.P0_stable = 0.999   # Extremely heavy inertia
        self.P0_react = 0.0      # Instant cut on crash
        
        # Only react if the crash is catastrophic (10-sigma)
        self.saccade_thresh = 10.0 
        self.derivative_boost = 0.2 # Gentle prediction
        
        self.k = 1.0
        self.F_prev = None
        self.price_history = []
        self.volatility = 0.0
        
    def update(self, price):
        self.price_history.append(price)
        if len(self.price_history) < 50:
            self.F_prev = price
            return "WAIT", price
        if len(self.price_history) > 200: self.price_history.pop(0)

        recent = self.price_history[-50:] 
        self.volatility = np.std(recent) or 0.01

        diff = price - self.F_prev
        error = abs(diff)
        
        # SACCADIC CRASH PROTECTION
        # Only trigger if market is melting down
        if error > (self.saccade_thresh * self.volatility):
            effective_P0 = self.P0_react
            effective_m = 1.0
        else:
            effective_P0 = self.P0_stable
            effective_m = 1.0 - effective_P0
            
        prior = effective_P0 * self.k * self.F_prev
        delta = price - self.price_history[-2]
        boost = self.derivative_boost * delta 
        F = prior + (effective_m * (price + boost))
        
        # Adaptation
        err = price - F
        self.k += 0.00001 * np.sign(err) * (abs(err)**0.5) # Glacial learning
        self.k = np.clip(self.k, 0.99, 1.01)
            
        self.F_prev = F
        return F

def run_commander():
    print("📡 Downloading 2 YEARS of BTC-USD (1h)...")
    df = yf.download("BTC-USD", period="2y", interval="1h", progress=False)
    prices = df['Close'].values
    
    print(f"✅ Loaded {len(prices)} candles")
    
    bot = DDA_Commander()
    cash = 1000.0
    lev = 2.0 # Responsible Leverage
    fee = 0.001 
    
    in_market = False
    entry_price = 0
    equity = [cash]
    trades = 0
    
    dda_line = []
    
    for i in tqdm(range(len(prices)), desc="Commanding"):
        price = float(prices[i])
        
        # 1. UPDATE DDA LINE
        res = bot.update(price)
        if isinstance(res, tuple): val = res[1]
        else: val = res
        dda_line.append(val)
        
        if isinstance(res, tuple) and res[0] == "WAIT":
            equity.append(cash)
            continue
            
        # 2. DECISION LOGIC (The Filter)
        # If Price > DDA Line: We are in a Bull Trend -> BE LONG (2x)
        # If Price < DDA Line: We are in a Bear/Correction -> BE CASH (0x)
        
        bull_trend = price > val
        
        # ENTRY (Cash -> Long)
        if bull_trend and not in_market:
            in_market = True
            entry_price = price
            cash -= (cash * lev * fee) # Entry Fee
            trades += 1
            
        # EXIT (Long -> Cash)
        elif not bull_trend and in_market:
            in_market = False
            # PnL Calc
            diff = price - entry_price
            pos_size = (cash * lev) / entry_price
            pnl = diff * pos_size
            
            cash += pnl
            cash -= (cash * lev * fee) # Exit Fee
            trades += 1
            
        # MARK TO MARKET
        curr = cash
        if in_market:
            diff = price - entry_price
            pos_size = (cash * lev) / entry_price
            curr += (diff * pos_size)
            
        equity.append(curr)
        if curr <= 0: 
            print("💀 LIQUIDATED")
            break
            
    # RESULTS
    final = float(equity[-1])
    start_price = float(prices[0])
    end_price = float(prices[-1])
    hodl = (1000.0 / start_price) * end_price
    
    print("\n" + "="*50)
    print("TREND COMMANDER RESULTS")
    print("="*50)
    print(f"Final Cash:   ${final:,.2f}")
    print(f"Buy & Hold:   ${hodl:,.2f}")
    print(f"Trades:       {trades}")
    
    if final > hodl:
        print(f"\n🏆 WINNER: DDA (+{((final-hodl)/hodl)*100:.1f}%)")
    else:
        print(f"\n❌ WINNER: HODL")

    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(equity, 'r-', label='DDA 2x Equity')
    
    # Scale HODL for comparison
    scale_factor = 1000 / start_price
    plt.plot(prices * scale_factor, 'g--', alpha=0.5, label='Buy & Hold')
    
    plt.title("DDA Trend Commander vs HODL")
    plt.yscale('log')
    plt.legend()
    plt.savefig('dda_commander.png')
    print("✓ Proof saved.")

if __name__ == "__main__":
    run_commander()