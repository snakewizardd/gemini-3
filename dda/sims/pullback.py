
"""
DDA v18.0 "PULLBACK RIDER"
--------------------------
Buy dips in uptrends, not breakouts
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
        
    def update(self, price):
        if self.F is None:
            self.F = price
            return price
        self.F = self.P0 * self.F + (1 - self.P0) * price
        return self.F


def run_pullback_rider():
    print("📡 Downloading 2 YEARS of BTC-USD (1d)...")
    df = yf.download("BTC-USD", period="2y", interval="1d", progress=False)
    prices = df['Close'].values.flatten()
    highs = df['High'].values.flatten()
    lows = df['Low'].values.flatten()
    
    print(f"✅ Loaded {len(prices)} candles (daily)\n")
    
    # Trend DDA (slow - determines if we're in uptrend)
    trend_dda = SimpleDDA(smoothing=0.97)
    
    # Signal DDA (fast - for entries)
    signal_dda = SimpleDDA(smoothing=0.92)
    
    cash = 1000.0
    lev = 1.5
    fee = 0.001
    
    in_market = False
    entry_price = 0
    equity = [cash]
    trades = 0
    trade_log = []
    
    # Track recent high for trailing stop
    highest_since_entry = 0
    TRAILING_STOP = 0.12  # 12% from high = exit
    
    print("Trading Rules:")
    print("  📈 BUY: Uptrend (price > trend DDA) + pullback to signal DDA")
    print("  📉 SELL: Price drops 12% from high OR trend breaks")
    print(f"  💰 Leverage: {lev}x\n")
    
    for i in tqdm(range(len(prices)), desc="Riding"):
        price = float(prices[i])
        high = float(highs[i])
        low = float(lows[i])
        
        trend = trend_dda.update(price)
        signal = signal_dda.update(price)
        
        if i < 30:
            equity.append(cash)
            continue
        
        # TREND FILTER
        uptrend = price > trend * 0.98  # price within 2% of trend line = ok
        
        # PULLBACK DETECTION
        # Price pulled back to touch or dip below signal DDA
        pullback = low <= signal * 1.02
        
        # Price bouncing (closing above signal)
        bouncing = price > signal
        
        if in_market:
            highest_since_entry = max(highest_since_entry, high)
            drawdown = (highest_since_entry - low) / highest_since_entry
            
            # EXIT CONDITIONS
            trend_break = price < trend * 0.95  # 5% below trend = gtfo
            trailing_stop_hit = drawdown > TRAILING_STOP
            
            if trend_break or trailing_stop_hit:
                in_market = False
                diff = price - entry_price
                pos_size = (cash * lev) / entry_price
                pnl = diff * pos_size
                cash += pnl
                cash -= abs(cash * lev * fee)
                trades += 1
                
                reason = "TREND BREAK" if trend_break else f"TRAILING STOP ({drawdown*100:.1f}%)"
                emoji = "✅" if pnl > 0 else "❌"
                pct = (diff / entry_price) * 100 * lev
                trade_log.append(f"  Day {i:3d} | {emoji} SELL @ ${price:>10,.2f} | PnL: ${pnl:>+8,.2f} ({pct:>+5.1f}%) | {reason}")
                highest_since_entry = 0
        
        else:
            # ENTRY: Uptrend + Pullback + Bounce
            if uptrend and pullback and bouncing:
                in_market = True
                entry_price = price
                highest_since_entry = high
                cash -= abs(cash * lev * fee)
                trades += 1
                trade_log.append(f"  Day {i:3d} | 📈 BUY  @ ${price:>10,.2f} | Trend: ${trend:,.0f} | Signal: ${signal:,.0f}")
        
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
    hodl = (1000.0 / start_price) * float(prices[-1])
    
    print("\n" + "="*60)
    print("PULLBACK RIDER RESULTS")
    print("="*60)
    print(f"  Starting:     ${1000:,.2f}")
    print(f"  Final:        ${final:,.2f}")
    print(f"  HODL:         ${hodl:,.2f}")
    print(f"  Trades:       {trades}")
    
    print("\n📜 TRADE LOG:")
    print("-" * 70)
    for t in trade_log:
        print(t)
    print("-" * 70)
    
    if final > hodl:
        print(f"\n🏆 WINNER: PULLBACK RIDER! (+{((final-hodl)/hodl)*100:.1f}% vs HODL)")
    elif final > 1000:
        print(f"\n🎯 HODL wins but we made ${final-1000:,.2f} profit")
    else:
        print(f"\n❌ Lost money")
    
    # Stats
    wins = sum(1 for t in trade_log if "✅" in t)
    losses = sum(1 for t in trade_log if "❌" in t)
    if wins + losses > 0:
        print(f"📊 Win Rate: {wins}/{wins+losses} = {wins/(wins+losses)*100:.0f}%")
    
    # Plot
    fig, ax = plt.subplots(2, 1, figsize=(14, 10))
    
    scale = 1000 / start_price
    hodl_line = [float(prices[min(i, len(prices)-1)]) * scale for i in range(len(equity))]
    
    ax[0].plot(equity, 'b-', label='Pullback Rider', linewidth=2)
    ax[0].plot(hodl_line, 'g--', alpha=0.6, label='HODL', linewidth=2)
    ax[0].set_title("Pullback Rider vs HODL")
    ax[0].legend()
    ax[0].grid(True, alpha=0.3)
    ax[0].set_ylabel("Portfolio ($)")
    
    # Drawdown
    peak = np.maximum.accumulate(equity)
    dd = [(equity[i] - peak[i]) / peak[i] * 100 if peak[i] > 0 else 0 for i in range(len(equity))]
    ax[1].fill_between(range(len(dd)), dd, 0, color='red', alpha=0.5)
    ax[1].set_title("Drawdown %")
    ax[1].set_ylabel("Drawdown %")
    ax[1].set_xlabel("Days")
    ax[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('pullback_rider.png', dpi=150)
    print("\n✓ Saved pullback_rider.png")
    plt.show()


if __name__ == "__main__":
    run_pullback_rider()
