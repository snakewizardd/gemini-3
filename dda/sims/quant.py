"""
DDA QUANT FACTORY (v12.1 FIXED)
-------------------------------
Professional Grade Walk-Forward Optimization Engine.
Fixes: Added missing 'time' import.
"""
import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from itertools import product
from tqdm import tqdm
import os
import time  # <--- FIXED: This was missing
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE STRATEGY: DDA v11.0
# =============================================================================
class DDAScalper:
    def __init__(self, saccade_thresh=3.0, min_profit_mult=2.5, P0_stable=0.98):
        self.P0_stable = P0_stable
        self.P0_react = 0.0
        self.saccade_thresh = saccade_thresh
        self.min_profit_mult = min_profit_mult
        
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

        recent = self.price_history[-20:]
        self.volatility = np.std(recent)
        if self.volatility == 0: self.volatility = 0.01

        diff = price - self.F_prev
        error = abs(diff)
        signal = "HOLD"
        
        if error > (self.saccade_thresh * self.volatility):
            effective_P0 = self.P0_react
            effective_m = 1.0
            if diff > 0: signal = "LONG_ENTRY"
            else:        signal = "SHORT_ENTRY"
        else:
            effective_P0 = self.P0_stable
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
        return signal, F, abs(diff)

# =============================================================================
# 2. THE BACKTESTER
# =============================================================================
class Backtester:
    def __init__(self, data, params, initial_capital=1000.0, leverage=10.0, fee=0.0005):
        self.data = data
        self.params = params
        self.capital = initial_capital
        self.leverage = leverage
        self.fee = fee
        self.equity_curve = [initial_capital]
        self.trades = []
        
    def run(self):
        bot = DDAScalper(
            saccade_thresh=self.params['thresh'],
            min_profit_mult=self.params['profit_mult'],
            P0_stable=self.params['p0']
        )
        
        position = None 
        cash = self.capital
        
        # Iterate through rows efficiently
        prices = self.data['close'].values
        
        for price in prices:
            sig, val, move = bot.update(price)
            
            # 1. ENTRY
            if position is None:
                if "ENTRY" in sig:
                    position_value = cash * self.leverage
                    fee_cost = position_value * self.fee * 2 
                    expected_profit = (move / price) * position_value
                    
                    if expected_profit > (fee_cost * bot.min_profit_mult):
                        direction = "LONG" if "LONG" in sig else "SHORT"
                        size = position_value / price
                        cash -= (position_value * self.fee)
                        position = {'type': direction, 'entry': price, 'size': size}
            
            # 2. EXIT
            elif position is not None:
                is_exit = False
                if position['type'] == "LONG" and ("SHORT" in sig or "EXIT" in sig): is_exit = True
                if position['type'] == "SHORT" and ("LONG" in sig or "EXIT" in sig): is_exit = True
                
                if is_exit:
                    entry = position['entry']
                    size = position['size']
                    
                    if position['type'] == "LONG": pnl = (price - entry) * size
                    else: pnl = (entry - price) * size
                    
                    cash += pnl
                    cash -= (size * price * self.fee)
                    self.trades.append(pnl)
                    position = None
            
            # Mark to Market
            current_eq = cash
            if position:
                entry = position['entry']
                size = position['size']
                if position['type'] == "LONG": u_pnl = (price - entry) * size
                else: u_pnl = (entry - price) * size
                current_eq += u_pnl
            
            self.equity_curve.append(current_eq)
            if current_eq <= 0: break 
            
        return current_eq, self.equity_curve, self.trades

# =============================================================================
# 3. DATA MANAGER
# =============================================================================
def get_data(symbol='BTC/USDT', timeframe='5m', days=60):
    safe_sym = symbol.replace('/','_')
    filename = f"{safe_sym}_{timeframe}_{days}d.csv"
    
    if os.path.exists(filename):
        print(f"📂 Loading data from {filename}...")
        return pd.read_csv(filename)
    
    print(f"📡 Downloading {days} days of {symbol} from Kraken...")
    exchange = ccxt.kraken()
    since = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
    all_candles = []
    
    pbar = tqdm(total=days*288, desc="Fetching Candles", unit="candle")
    
    while since < exchange.milliseconds():
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since, limit=720)
            if not candles: break
            
            since = candles[-1][0] + 1
            all_candles += candles
            pbar.update(len(candles))
            time.sleep(0.5) # Rate limit
        except Exception as e:
            print(f"Error: {e}")
            break
            
    pbar.close()
    df = pd.DataFrame(all_candles, columns=['time', 'open', 'high', 'low', 'close', 'vol'])
    df.to_csv(filename, index=False)
    return df

# =============================================================================
# 4. OPTIMIZER
# =============================================================================
def optimize():
    # Load 60 days
    df = get_data(days=60)
    
    # Split Data (Train / Test)
    split_idx = int(len(df) * 0.7)
    train_data = df.iloc[:split_idx]
    test_data = df.iloc[split_idx:]
    
    print(f"\n🔬 TRAINING PHASE ({len(train_data)} candles)...")
    
    # Grid Search
    params_grid = list(product(
        [2.5, 3.0, 3.5, 4.0], # thresh
        [2.0, 2.5, 3.0],      # profit_mult
        [0.95, 0.98, 0.99]    # p0
    ))
    
    best_score = -99999
    best_params = None
    
    print(f"   Testing {len(params_grid)} combinations...")
    for th, mult, p0 in tqdm(params_grid):
        p = {'thresh': th, 'profit_mult': mult, 'p0': p0}
        final_eq, curve, trades = Backtester(train_data, p).run()
        
        if final_eq > best_score:
            best_score = final_eq
            best_params = p
            
    print("\n" + "="*60)
    print("🏆 BEST TRAINING PARAMETERS")
    print(f"   {best_params}")
    print(f"   Training PnL: ${best_score - 1000:.2f}")
    print("="*60)
    
    # VALIDATION
    print(f"\n🧪 VALIDATION PHASE ({len(test_data)} candles)...")
    print("   Running on UNSEEN DATA (The Future)...")
    
    final_eq, curve, trades = Backtester(test_data, best_params).run()
    
    buy_hold = (test_data.iloc[-1]['close'] - test_data.iloc[0]['close']) / test_data.iloc[0]['close'] * 1000
    
    print(f"\n📊 FINAL RESULTS")
    print(f"----------------")
    print(f"Start Balance: $1,000.00")
    print(f"Final Balance: ${final_eq:,.2f}")
    print(f"Net Profit:    ${final_eq - 1000:,.2f}")
    print(f"Total Trades:  {len(trades)}")
    print(f"Buy & Hold:    ${1000 + buy_hold:,.2f}")
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(curve, 'r-', label='DDA Equity')
    plt.title(f"DDA Walk-Forward Validation\nNet: ${final_eq - 1000:.2f}")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig('dda_quant_result.png')
    print("✓ Chart saved to dda_quant_result.png")

if __name__ == "__main__":
    optimize()