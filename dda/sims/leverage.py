"""
DDA v11.0 "THE SCALPER" (50x Leverage Engine)
---------------------------------------------
Scenario: 5-Minute Crypto/Forex Charts.
Goal: Scalp "Micro-Breakouts" while filtering out "Chop" (Noise).

Mechanism:
1. High-Pass Filter: Only reacts to moves faster than the volatility floor.
2. Zero-Lag Entry: Enters the millisecond the Saccade triggers.
3. Trailing Stop: Uses DDA's "Fair Value" line as a dynamic stop-loss.
"""
import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# 1. THE SCALPER ENGINE (DDA v11)
# =============================================================================
@dataclass
class ScalperConfig:
    # THE CHOP FILTER
    P0_stable: float = 0.98    # Diamond Hands during noise
    P0_react: float = 0.0      # Instant entry on breakout
    
    # TRIGGER SENSITIVITY
    # Lower = More trades (Riskier)
    # Higher = Fewer trades (Safer)
    saccade_thresh: float = 2.5 # Sigma
    
    # EXIT LOGIC
    # If the derivative slows down this much, bail out.
    momentum_decay: float = 0.5 

class DDAScalper:
    def __init__(self):
        self.c = ScalperConfig()
        self.k = 1.0
        self.F_prev = None
        self.price_history = []
        self.volatility = 0.0
        self.position = 0 # 1=Long, -1=Short, 0=Flat
        self.entry_price = 0.0
        
    def update(self, price):
        # 1. Warm Up
        self.price_history.append(price)
        if len(self.price_history) < 20:
            self.F_prev = price
            return "WAIT", price

        # 2. Dynamic Volatility (The Noise Floor)
        # We look at the last 20 candles (100 mins) to define "Chop"
        recent = self.price_history[-20:]
        self.volatility = np.std(recent)
        if self.volatility == 0: self.volatility = 0.01

        # 3. RETINAL SLIP (Price vs Fair Value)
        # Is the current price "Impossible" given our model?
        diff = price - self.F_prev
        error = np.abs(diff)
        
        signal = "HOLD"
        
        # 4. SACCADIC ENTRY (The Sniper)
        if self.position == 0:
            if error > (self.c.saccade_thresh * self.volatility):
                # BREAKOUT DETECTED
                effective_P0 = self.c.P0_react
                effective_m = 1.0
                
                if diff > 0: signal = "LONG_ENTRY"
                else:        signal = "SHORT_ENTRY"
            else:
                # CHOP DETECTED
                effective_P0 = self.c.P0_stable
                effective_m = 1.0 - effective_P0
        
        # 5. SACCADIC EXIT (The Coward)
        # If we are in a trade, we look for momentum failure
        else:
            # We assume we are "locked on". High Inertia to ride the trend.
            effective_P0 = 0.8 
            effective_m = 0.2
            
            # EXIT TRIGGER: Price crosses back over our DDA Line (Trailing Stop)
            if self.position == 1 and price < self.F_prev:
                signal = "LONG_EXIT"
            elif self.position == -1 and price > self.F_prev:
                signal = "SHORT_EXIT"

        # 6. UPDATE LAW
        # DDA tracks the "Fair Value" (Red Line)
        prior = effective_P0 * self.k * self.F_prev
        # Trend Boost
        delta = price - self.price_history[-2]
        boost = 0.6 * delta 
        
        F = prior + (effective_m * (price + boost))
        
        # 7. ADAPT
        if signal == "HOLD":
            err = price - F
            self.k += 0.001 * np.sign(err) * (np.abs(err)**0.5)
            self.k = np.clip(self.k, 0.9, 1.1)
        else:
            self.k = 1.0 # Reset on switch
            
        self.F_prev = F
        return signal, F

# =============================================================================
# 2. 5-MINUTE CANDLE GENERATOR
# =============================================================================
def generate_5m_chart(candles=200):
    # Simulates a "Pump and Dump" then "Chop"
    # 1. Accumulation (Chop)
    # 2. PUMP (Vertical Move)
    # 3. Distribution (Chop)
    # 4. DUMP (Crash)
    
    prices = [100.0]
    
    for i in range(candles):
        prev = prices[-1]
        
        # Scenario Logic
        if i < 50:   trend = 0.0; vol = 0.2   # Chop
        elif i < 80: trend = 1.5; vol = 0.5   # PUMP (Long)
        elif i < 120: trend = 0.0; vol = 0.8  # High Vol Chop
        elif i < 140: trend = -2.0; vol = 1.0 # DUMP (Short)
        else:         trend = 0.0; vol = 0.1  # Dead Market
        
        # Generate Candle Close
        noise = np.random.normal(0, vol)
        close = prev + trend + noise
        prices.append(close)
        
    return prices

# =============================================================================
# 3. RUN SIMULATION
# =============================================================================
def run_scalp_sim():
    print("💹 LOADING 5-MINUTE CHART...")
    prices = generate_5m_chart(200)
    bot = DDAScalper()
    
    balance = 1000.0 # Starting Cash
    leverage = 50.0  # 50x Leverage
    
    in_position = False
    entry_price = 0
    position_size = 0
    pos_type = 0 # 1 or -1
    
    history_bal = []
    signals_idx = []
    signals_type = [] # '^' or 'v' or 'x'
    
    dda_line = []
    
    print("⚡ SCALPING ACTIVE...")
    
    for i, p in enumerate(prices):
        sig, val = bot.update(p)
        dda_line.append(val)
        
        # EXECUTION LOGIC
        if not in_position:
            if "ENTRY" in sig:
                # OPEN POSITION
                pos_type = 1 if "LONG" in sig else -1
                bot.position = pos_type
                
                # Fees: 0.05% Taker
                fee = (balance * leverage) * 0.0005
                balance -= fee
                
                entry_price = p
                position_size = (balance * leverage) / p # Contracts
                in_position = True
                
                signals_idx.append(i)
                signals_type.append('g^' if pos_type==1 else 'rv')
                
        else:
            if "EXIT" in sig:
                # CLOSE POSITION
                diff = (p - entry_price) * pos_type
                pnl = diff * position_size
                
                balance += pnl
                # Fees
                fee = (balance * leverage) * 0.0005
                balance -= fee
                
                in_position = False
                bot.position = 0
                
                signals_idx.append(i)
                signals_type.append('kx')
        
        # Mark to Market (for liquidation check)
        if in_position:
            unrealized = ((p - entry_price) * pos_type) * position_size
            curr_bal = balance + unrealized
            if curr_bal <= 0: # LIQUIDATION
                balance = 0
                print("💀 LIQUIDATED!")
                break
        else:
            curr_bal = balance
            
        history_bal.append(curr_bal)

    print("\n" + "="*50)
    print("50x LEVERAGE RESULTS")
    print("="*50)
    print(f"Start Balance: $1,000.00")
    print(f"End Balance:   ${history_bal[-1]:,.2f}")
    
    gain = ((history_bal[-1] - 1000)/1000)*100
    print(f"PnL: {gain:+.1f}%")

    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    
    ax1.plot(prices, 'k-', alpha=0.6, label='Price (5m)')
    ax1.plot(dda_line, 'b-', lw=1, alpha=0.8, label='DDA Fair Value')
    
    # Plot signals
    for j in range(len(signals_idx)):
        ax1.plot(signals_idx[j], prices[signals_idx[j]], signals_type[j], ms=10)
        
    ax1.set_title("DDA Scalper: 50x Leverage Entries")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(history_bal, 'g-', lw=2, label='Account Balance')
    ax2.set_title("Equity Curve")
    ax2.set_ylabel("USD")
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dda_scalper.png')
    print("✓ Trade log saved.")

if __name__ == "__main__":
    run_scalp_sim()