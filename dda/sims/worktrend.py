
"""
DDA v17.0 "SIMPLE RIDER" 
------------------------
Super simplified - just trend following with hysteresis band
"""
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')

class SimpleDDA:
    def __init__(self, smoothing=0.95):
        self.P0 = smoothing
        self.F = None
        self.prices = []
        
    def update(self, price):
        self.prices.append(price)
        
        if self.F is None:
            self.F = price
            return price
        
        # Simple exponential smoothing
        self.F = self.P0 * self.F + (1 - self.P0) * price
        return self.F


def run_simple_rider():
    print("📡 Downloading 2 YEARS of BTC-USD (1d)...")
    df = yf.download("BTC-USD", period="2y", interval="1d", progress=False)
    prices = df['Close'].values.flatten()
    
    print(f"✅ Loaded {len(prices)} candles (daily)\n")
    
    # Two DDAs for trend detection
    fast_dda = SimpleDDA(smoothing=0.90)  # 10-day-ish
    slow_dda = SimpleDDA(smoothing=0.97)  # 33-day-ish
    
    cash = 1000.0
    lev = 1.5
    fee = 0.001
    
    in_market = False
    entry_price = 0
    equity = [cash]
    trades = 0
    trade_log = []
    
    # HYSTERESIS BAND - prevents whipsaws
    # Only enter if fast is X% ABOVE slow
    # Only exit if fast is X% BELOW slow
    ENTRY_THRESHOLD = 1.005  # fast must be 0.5% above slow to enter
    EXIT_THRESHOLD = 0.995   # fast must be 0.5% below slow to exit
    
    print("Trading Rules:")
    print(f"  📈 BUY when: Fast DDA > Slow DDA × {ENTRY_THRESHOLD}")
    print(f"  📉 SELL when: Fast DDA < Slow DDA × {EXIT_THRESHOLD}")
    print(f"  💰 Leverage: {lev}x")
    print()
    
    for i in tqdm(range(len(prices)), desc="Riding"):
        price = float(prices[i])
        
        fast = fast_dda.update(price)
        slow = slow_dda.update(price)
        
        # Skip warmup
        if i < 20:
            equity.append(cash)
            continue
        
        # SIMPLE CROSSOVER WITH HYSTERESIS
        bullish = fast > slow * ENTRY_THRESHOLD
        bearish = fast < slow * EXIT_THRESHOLD
        
        # ENTRY
        if bullish and not in_market:
            in_market = True
            entry_price = price
            cash -= (cash * lev * fee)
            trades += 1
            trade_log.append(f"  Day {i:3d} | 📈 BUY  @ ${price:>10,.2f} | Fast: ${fast:,.0f} > Slow: ${slow:,.0f}")
            
        # EXIT
        elif bearish and in_market:
            in_market = False
            diff = price - entry_price
            pos_size = (cash * lev) / entry_price
            pnl = diff * pos_size
            cash += pnl
            cash -= (cash * lev * fee)
            trades += 1
            emoji = "✅" if pnl > 0 else "❌"
            pct = (pnl / (cash - pnl)) * 100
            trade_log.append(f"  Day {i:3d} | {emoji} SELL @ ${price:>10,.2f} | PnL: ${pnl:>+8,.2f} ({pct:>+5.1f}%)")
            
        # Mark to market
        curr = cash
        if in_market:
            diff = price - entry_price
            pos_size = (cash * lev) / entry_price
            curr += (diff * pos_size)
            
        equity.append(curr)
        
        if curr <= 0:
            print("💀 LIQUIDATED")
            break
    
    # Close open position
    if in_market:
        price = float(prices[-1])
        diff = price - entry_price
        pos_size = (cash * lev) / entry_price
        pnl = diff * pos_size
        cash += pnl
        trades += 1
        emoji = "✅" if pnl > 0 else "❌"
        trade_log.append(f"  END     | {emoji} CLOSE @ ${price:>10,.2f} | PnL: ${pnl:>+8,.2f}")
        equity[-1] = cash
    
    # Results
    final = float(equity[-1])
    start_price = float(prices[0])
    end_price = float(prices[-1])
    hodl = (1000.0 / start_price) * end_price
    
    print("\n" + "="*60)
    print("SIMPLE RIDER RESULTS")
    print("="*60)
    print(f"  Starting:     ${1000:,.2f}")
    print(f"  Final:        ${final:,.2f}")
    print(f"  Buy & Hold:   ${hodl:,.2f}")
    print(f"  Trades:       {trades}")
    print(f"  Fees Paid:    ~${trades * 0.003 * final:.2f}")
    
    # Trade log
    print("\n📜 TRADE LOG:")
    print("-" * 60)
    for t in trade_log:
        print(t)
    print("-" * 60)
    
    # Winner
    print()
    if final > hodl:
        pct = ((final - hodl) / hodl) * 100
        print(f"🏆 WINNER: SIMPLE RIDER (+{pct:.1f}% vs HODL)")
    elif final > 1000:
        pct = ((hodl - final) / hodl) * 100
        print(f"🎯 HODL wins by {pct:.1f}% but we made ${final - 1000:,.2f} profit!")
    else:
        pct = ((hodl - final) / hodl) * 100
        print(f"❌ HODL wins by {pct:.1f}%")
    
    # Calculate some stats
    if len(trade_log) >= 2:
        wins = sum(1 for t in trade_log if "✅" in t)
        losses = sum(1 for t in trade_log if "❌" in t)
        if wins + losses > 0:
            print(f"\n📊 Win Rate: {wins}/{wins+losses} = {wins/(wins+losses)*100:.0f}%")
    
    # Plot
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # 1. Price with DDA lines
    ax1 = axes[0]
    ax1.plot(prices, 'k-', alpha=0.7, label='BTC Price', linewidth=1)
    
    # Recalculate DDAs for plotting
    fast_line = []
    slow_line = []
    f_dda = SimpleDDA(smoothing=0.90)
    s_dda = SimpleDDA(smoothing=0.97)
    for p in prices:
        fast_line.append(f_dda.update(float(p)))
        slow_line.append(s_dda.update(float(p)))
    
    ax1.plot(fast_line, 'b-', label='Fast DDA (0.90)', linewidth=1.5)
    ax1.plot(slow_line, 'r-', label='Slow DDA (0.97)', linewidth=1.5)
    ax1.set_title("BTC Price with DDA Lines", fontsize=14)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("Price ($)")
    
    # 2. Equity curves
    ax2 = axes[1]
    scale_factor = 1000 / start_price
    hodl_line = [float(prices[min(i, len(prices)-1)]) * scale_factor for i in range(len(equity))]
    
    ax2.plot(equity, 'b-', label='Simple Rider', linewidth=2)
    ax2.plot(hodl_line, 'g--', alpha=0.6, label='Buy & Hold', linewidth=2)
    ax2.set_title("Portfolio Value Comparison", fontsize=14)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylabel("Portfolio ($)")
    
    # 3. Drawdown
    ax3 = axes[2]
    peak = np.maximum.accumulate(equity)
    drawdown = [(equity[i] - peak[i]) / peak[i] * 100 for i in range(len(equity))]
    ax3.fill_between(range(len(drawdown)), drawdown, 0, color='red', alpha=0.5)
    ax3.set_title("Drawdown (%)", fontsize=14)
    ax3.grid(True, alpha=0.3)
    ax3.set_ylabel("Drawdown %")
    ax3.set_xlabel("Days")
    
    plt.tight_layout()
    plt.savefig('simple_rider.png', dpi=150)
    print("\n✓ Chart saved to simple_rider.png")
    plt.show()
    
    return final, hodl, trades


if __name__ == "__main__":
    run_simple_rider()
