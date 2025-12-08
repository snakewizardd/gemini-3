"""
DDA MACRO QUANT (v12.2)
-----------------------
Timeframe: 1 Hour (1h) - Beats the Fee Wall.
Data: Robust Fetcher with Retry Logic.
"""
import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from itertools import product
from tqdm import tqdm
import os
import time
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE MACRO STRATEGY (DDA v12)
# =============================================================================
class DDAMacro:
    def __init__(self, saccade_thresh=3.0, min_profit_mult=2.5, P0_stable=0.98):
        self.c = {'thresh': saccade_thresh, 'profit_mult': min_profit_mult, 'p0': P0_stable}
        self.k = 1.0
        self.F_prev = None
        self.price_history = []
        self.volatility = 0.0
        
    def update(self, price):
        self.price_history.append(price)
        if len(self.price_history) < 20:
            self.F_prev = price
            return "WAIT", price, 0.0
        if len(self.price_history) > 100: self.price_history.pop(0)

        # Volatility Baseline
        recent = self.price_history[-20:]
        self.volatility = np.std(recent) or 0.01

        diff = price - self.F_prev
        error = abs(diff)
        signal = "HOLD"
        
        # Saccadic Logic (Breakout Detection)
        if error > (self.c['thresh'] * self.volatility):
            effective_P0 = 0.0
            effective_m = 1.0
            if diff > 0: signal = "LONG_ENTRY"
            else:        signal = "SHORT_ENTRY"
        else:
            effective_P0 = self.c['p0']
            effective_m = 1.0 - effective_P0
            # Trailing Stop
            if price < self.F_prev: signal = "LONG_EXIT"
            if price > self.F_prev: signal = "SHORT_EXIT"

        # Update
        prior = effective_P0 * self.k * self.F_prev
        delta = price - self.price_history[-2]
        boost = 0.6 * delta 
        F = prior + (effective_m * (price + boost))
        
        # Adapt
        if "ENTRY" not in signal:
            err = price - F
            self.k += 0.001 * np.sign(err) * (abs(err)**0.5)
            self.k = np.clip(self.k, 0.9, 1.1)
        else: self.k = 1.0
            
        self.F_prev = F
        return signal, F, abs(diff)

# =============================================================================
# 2. ROBUST DATA LOADER (Retries)
# =============================================================================
def get_macro_data(days=180): # 6 Months of data
    symbol = 'BTC/USDT'
    timeframe = '1h' # <--- KEY CHANGE
    filename = f"{symbol.replace('/','_')}_{timeframe}_{days}d.csv"
    
    if os.path.exists(filename):
        print(f"📂 Loading cached data from {filename}...")
        return pd.read_csv(filename)
    
    print(f"📡 Downloading {days} days of {symbol} ({timeframe}) from Kraken...")
    exchange = ccxt.kraken()
    # 1h candles = 24 per day
    total_candles = days * 24
    since = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
    all_candles = []
    
    pbar = tqdm(total=total_candles, unit="candle")
    
    retries = 3
    while since < exchange.milliseconds():
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since, limit=720)
            if not candles: break
            
            since = candles[-1][0] + 1
            all_candles += candles
            pbar.update(len(candles))
            time.sleep(0.5)
            retries = 3 # Reset retries on success
        except Exception as e:
            print(f"\n⚠️ Network Error: {e}. Retrying ({retries} left)...")
            retries -= 1
            time.sleep(2)
            if retries == 0: break
            
    pbar.close()
    if len(all_candles) == 0: raise ValueError("No data downloaded!")
    
    df = pd.DataFrame(all_candles, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df.to_csv(filename, index=False)
    return df

# =============================================================================
# 3. BACKTESTER
# =============================================================================
def run_backtest(df, params):
    bot = DDAMacro(params['thresh'], params['profit_mult'], params['p0'])
    cash = 1000.0
    lev = 5.0 # Lower leverage for Macro (safer)
    fee = 0.0005
    
    position = None
    equity = [cash]
    trades = 0
    
    prices = df['close'].values
    
    for price in prices:
        sig, val, move = bot.update(price)
        
        # ENTRY
        if position is None:
            if "ENTRY" in sig:
                # Filter: Is the move big enough?
                pos_val = cash * lev
                cost = pos_val * fee * 2
                expected = (move/price) * pos_val
                
                if expected > (cost * params['profit_mult']):
                    direction = 1 if "LONG" in sig else -1
                    size = pos_val / price
                    cash -= (pos_val * fee)
                    position = {'dir': direction, 'entry': price, 'size': size}
        
        # EXIT
        elif position is not None:
            is_exit = False
            if position['dir'] == 1 and ("SHORT" in sig or "EXIT" in sig): is_exit = True
            if position['dir'] == -1 and ("LONG" in sig or "EXIT" in sig): is_exit = True
            
            if is_exit:
                diff = (price - position['entry']) * position['dir']
                pnl = diff * position['size']
                cash += pnl
                cash -= (position['size'] * price * fee)
                position = None
                trades += 1
                
        # Mark to Market
        curr = cash
        if position:
            diff = (price - position['entry']) * position['dir']
            curr += diff * position['size']
        
        equity.append(curr)
        if curr < 0: break
        
    return curr, equity, trades

# =============================================================================
# 4. RUNNER
# =============================================================================
if __name__ == "__main__":
    # 1. Get Data
    df = get_macro_data(days=180) # 6 Months
    
    # 2. Split
    split = int(len(df) * 0.7)
    train = df.iloc[:split]
    test = df.iloc[split:]
    
    # 3. Optimize
    print(f"\n🔬 OPTIMIZING on {len(train)} hours of data...")
    # Tighter grid for speed
    grid = list(product([2.5, 3.0, 4.0], [2.0, 3.0], [0.95, 0.98]))
    
    best_res = -99999
    best_p = None
    
    for th, mult, p0 in tqdm(grid):
        p = {'thresh': th, 'profit_mult': mult, 'p0': p0}
        res, _, _ = run_backtest(train, p)
        if res > best_res:
            best_res = res
            best_p = p
            
    print(f"\n🏆 BEST SETTINGS: {best_p}")
    print(f"   Training Result: ${best_res:.2f}")
    
    # 4. Validate
    print(f"\n🧪 VALIDATING on {len(test)} hours (Unseen)...")
    end_bal, curve, num_trades = run_backtest(test, best_p)
    
    hodl = (1000 / test.iloc[0]['close']) * test.iloc[-1]['close']
    
    print("\n" + "="*40)
    print("FINAL 1H MACRO RESULTS")
    print("="*40)
    print(f"Start:      $1,000.00")
    print(f"DDA Macro:  ${end_bal:,.2f}")
    print(f"Buy & Hold: ${hodl:,.2f}")
    print(f"Trades:     {num_trades}")
    
    if end_bal > hodl:
        print(f"\n✅ SUCCESS: Beat Market by {((end_bal-hodl)/hodl)*100:.1f}%")
    else:
        print(f"\n❌ FAIL: Market beat Algo")
        
    plt.plot(curve, label='DDA Equity')
    plt.title("DDA 1h Macro Strategy")
    plt.legend()
    plt.savefig('dda_macro_proof.png')
    print("✓ Chart saved.")