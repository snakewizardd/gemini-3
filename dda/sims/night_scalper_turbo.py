import ccxt
import time
import numpy as np
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# [KEEP THE DDA CLASS EXACTLY THE SAME AS BEFORE]
class DDAScalper:
    def __init__(self):
        self.P0_stable = 0.98; self.P0_react = 0.0; self.saccade_thresh = 2.5
        self.k = 1.0; self.F_prev = None; self.price_history = []; self.volatility = 0.0
        
    def update(self, price):
        self.price_history.append(price)
        # We need at least 20 candles to calculate volatility
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

# [KEEP PORTFOLIO SAME]
class PaperPortfolio:
    def __init__(self, initial_cash=1000.0, leverage=50):
        self.cash = initial_cash; self.leverage = leverage; self.position = None; self.trades = 0
    def execute(self, signal, price):
        if self.position is None:
            if "ENTRY" in signal:
                direction = "LONG" if "LONG" in signal else "SHORT"
                margin = self.cash; position_value = margin * self.leverage
                size_contracts = position_value / price
                fee = position_value * 0.0005; self.cash -= fee
                self.position = {'type': direction, 'entry': price, 'size': size_contracts}
                print(f"🚀 OPEN {direction} @ ${price:.2f} | Size: {size_contracts:.4f} BTC")
        else:
            close_long = (self.position['type'] == "LONG" and ("SHORT" in signal or "EXIT" in signal))
            close_short = (self.position['type'] == "SHORT" and ("LONG" in signal or "EXIT" in signal))
            if close_long or close_short:
                entry = self.position['entry']; size = self.position['size']
                if self.position['type'] == "LONG": pnl = (price - entry) * size
                else: pnl = (entry - price) * size
                self.cash += pnl
                fee = (size * price) * 0.0005; self.cash -= fee
                color = "🟢" if pnl > 0 else "🔴"
                print(f"{color} CLOSE {self.position['type']} @ ${price:.2f} | PnL: ${pnl:.2f} | Bal: ${self.cash:.2f}")
                self.position = None; self.trades += 1
                if "ENTRY" in signal: self.execute(signal, price)

# =============================================================================
# THE TURBO LOOP
# =============================================================================
def run_live():
    print(f"📡 CONNECTING TO KRAKEN (BTC/USDT 1m)...")
    exchange = ccxt.kraken()
    bot = DDAScalper()
    portfolio = PaperPortfolio(initial_cash=1000.0, leverage=50)
    
    # 1. PRE-LOAD HISTORY (The Fix)
    print("🔥 PRE-WARMING BRAIN with last 30 minutes of data...")
    history = exchange.fetch_ohlcv('BTC/USDT', '1m', limit=30)
    
    # Feed history into DDA so it learns volatility INSTANTLY
    for candle in history[:-1]: # Skip the last one (it's still open)
        close = candle[4]
        bot.update(close)
        
    print(f"✅ BRAIN READY. Volatility baseline: ${bot.volatility:.2f}")
    print(f"💼 STARTING BALANCE: $1,000.00 (50x LEVERAGE)")
    
    last_timestamp = 0
    
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1m', limit=2)
            latest_candle = ohlcv[-2] # Last CLOSED candle
            timestamp = latest_candle[0]
            close_price = latest_candle[4]
            
            if timestamp != last_timestamp:
                dt = datetime.fromtimestamp(timestamp / 1000).strftime('%H:%M:%S')
                signal, fair_val = bot.update(close_price)
                
                pos_str = portfolio.position['type'] if portfolio.position else "FLAT"
                print(f"[{dt}] Price: {close_price:.1f} | DDA: {fair_val:.1f} | Sig: {signal} | Pos: {pos_str}")
                
                portfolio.execute(signal, close_price)
                last_timestamp = timestamp
            
            # Fast poll for 1m timeframe
            time.sleep(5) 
            
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_live()