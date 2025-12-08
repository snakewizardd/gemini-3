"""
DDA v11.0 "NIGHT SCALPER" (Forward Testing Engine)
--------------------------------------------------
Runs the DDA Scalper on LIVE Binance data (Public API).
Simulates a 50x Leverage Portfolio in memory.
No API Keys required. No Real Money at risk.
"""
import ccxt
import time
import numpy as np
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE BRAIN: DDA v11.0 (Embedded)
# =============================================================================
class DDAScalper:
    def __init__(self):
        # CONFIGURATION (The "Scalper" Tune)
        self.P0_stable = 0.98    # Diamond Hands during chop
        self.P0_react = 0.0      # Instant snap on breakout
        self.saccade_thresh = 2.5 # Sensitivity (Sigma)
        
        # State
        self.k = 1.0
        self.F_prev = None
        self.price_history = []
        self.volatility = 0.0
        
    def update(self, price):
        # 1. Warm Up & History
        self.price_history.append(price)
        if len(self.price_history) < 20:
            self.F_prev = price
            return "WAIT", price
            
        # Keep history manageable
        if len(self.price_history) > 100: self.price_history.pop(0)

        # 2. Dynamic Volatility (Noise Floor)
        recent = self.price_history[-20:]
        self.volatility = np.std(recent)
        if self.volatility == 0: self.volatility = 0.01

        # 3. Retinal Slip
        diff = price - self.F_prev
        error = np.abs(diff)
        
        signal = "HOLD"
        
        # 4. Saccadic Gating
        # If error > 2.5x Noise, we have a breakout
        if error > (self.saccade_thresh * self.volatility):
            effective_P0 = self.P0_react
            effective_m = 1.0
            
            # Generate Signal
            if diff > 0: signal = "LONG_ENTRY"
            else:        signal = "SHORT_ENTRY"
        else:
            effective_P0 = self.P0_stable
            effective_m = 1.0 - effective_P0
            
            # Check for Exits (Loss of Momentum)
            # If we were Long, but price fell below DDA line -> Exit
            if price < self.F_prev: signal = "LONG_EXIT"
            # If we were Short, but price rose above DDA line -> Exit
            if price > self.F_prev: signal = "SHORT_EXIT"

        # 5. Update Law (Pre-Cognitive Boost)
        prior = effective_P0 * self.k * self.F_prev
        delta = price - self.price_history[-2]
        boost = 0.6 * delta 
        
        F = prior + (effective_m * (price + boost))
        
        # 6. Adapt Gain
        if signal == "HOLD" or "EXIT" in signal:
            err = price - F
            self.k += 0.001 * np.sign(err) * (np.abs(err)**0.5)
            self.k = np.clip(self.k, 0.9, 1.1)
        else:
            self.k = 1.0 # Reset on entry
            
        self.F_prev = F
        return signal, F

# =============================================================================
# 2. THE PAPER TRADER (Simulated Portfolio)
# =============================================================================
class PaperPortfolio:
    def __init__(self, initial_cash=1000.0, leverage=50):
        self.cash = initial_cash
        self.leverage = leverage
        self.position = None # {'type': 'LONG'/'SHORT', 'entry': 0.0, 'size': 0.0}
        self.trades = 0
        
    def execute(self, signal, price):
        # OPEN POSITION
        if self.position is None:
            if "ENTRY" in signal:
                direction = "LONG" if "LONG" in signal else "SHORT"
                # Go all in (Leveraged)
                margin = self.cash
                position_value = margin * self.leverage
                size_contracts = position_value / price
                
                # Pay Taker Fee (0.05%)
                fee = position_value * 0.0005
                self.cash -= fee
                
                self.position = {'type': direction, 'entry': price, 'size': size_contracts}
                print(f"🚀 OPEN {direction} @ ${price:.2f} | Size: {size_contracts:.4f} BTC")
        
        # CLOSE POSITION
        else:
            # Check logic: Close Long on SHORT_ENTRY or LONG_EXIT
            close_long = (self.position['type'] == "LONG" and ("SHORT" in signal or "EXIT" in signal))
            close_short = (self.position['type'] == "SHORT" and ("LONG" in signal or "EXIT" in signal))
            
            if close_long or close_short:
                entry = self.position['entry']
                size = self.position['size']
                
                # Calc PnL
                if self.position['type'] == "LONG":
                    pnl = (price - entry) * size
                else:
                    pnl = (entry - price) * size
                    
                self.cash += pnl
                
                # Pay Taker Fee
                exit_value = size * price
                fee = exit_value * 0.0005
                self.cash -= fee
                
                # Log
                color = "🟢" if pnl > 0 else "🔴"
                print(f"{color} CLOSE {self.position['type']} @ ${price:.2f} | PnL: ${pnl:.2f} | Bal: ${self.cash:.2f}")
                
                self.position = None
                self.trades += 1
                
                # Check for instant flip (Stop and Reverse)
                if "ENTRY" in signal:
                    self.execute(signal, price)

# =============================================================================
# 3. LIVE LOOP (Binance Public API)
# =============================================================================
def run_live():
    print(f"📡 CONNECTING TO KRAKEN (BTC/USDT 5m)...")
    
    # CHANGE THIS LINE:
    # exchange = ccxt.binance()
    
    # TO THIS:
    exchange = ccxt.kraken() 
    
    bot = DDAScalper()
    portfolio = PaperPortfolio(initial_cash=1000.0, leverage=50)
    
    last_timestamp = 0
    print(f"💼 STARTING BALANCE: $1,000.00 (50x LEVERAGE)")
    print("⏳ Waiting for candle close...")
    
    while True:
        try:
            # Get latest 2 candles
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '5m', limit=2)
            # ohlcv[-1] is the current open candle (changing)
            # ohlcv[-2] is the last CLOSED candle (final)
            
            latest_candle = ohlcv[-2]
            timestamp = latest_candle[0]
            close_price = latest_candle[4]
            
            # Process only on new candle close
            if timestamp != last_timestamp:
                dt = datetime.fromtimestamp(timestamp / 1000).strftime('%H:%M')
                
                # RUN DDA
                signal, fair_val = bot.update(close_price)
                
                # Log Status
                pos_str = portfolio.position['type'] if portfolio.position else "FLAT"
                print(f"[{dt}] Price: {close_price:.1f} | DDA: {fair_val:.1f} | Sig: {signal} | Pos: {pos_str}")
                
                # EXECUTE
                portfolio.execute(signal, close_price)
                
                last_timestamp = timestamp
            
            # Check liquidation live (using current open candle price)
            current_price = ohlcv[-1][4]
            if portfolio.position:
                entry = portfolio.position['entry']
                size = portfolio.position['size']
                unrealized = (current_price - entry) * size if portfolio.position['type'] == "LONG" else (entry - current_price) * size
                equity = portfolio.cash + unrealized
                
                if equity <= 0:
                    print(f"💀 LIQUIDATED at ${current_price:.2f}!")
                    break
                    
            # Wait 10 seconds before polling again
            time.sleep(10)
            
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_live()