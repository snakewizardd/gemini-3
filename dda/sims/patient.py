
"""
DDA v19.0 "PATIENT RIDER"
-------------------------
Wider stops, fewer trades, let winners RUN
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


def run_patient_rider():
    print("📡 Downloading 2 YEARS of BTC-USD (1d)...")
    df = yf.download("BTC-USD", period="2y", interval="1d", progress=False)
    prices = df['Close'].values.flatten()
    highs = df['High'].values.flatten()
    lows = df['Low'].values.flatten()
    
    print(f"✅ Loaded {len(prices)} candles (daily)\n")
    
    # SLOWER DDAs = more patience
    trend_dda = SimpleDDA(smoothing=0.98)   # was 0.97
    signal_dda = SimpleDDA(smoothing=0.94)  # was 0.92
    
    cash = 1000.0
    lev = 1.5
    fee = 0.001
    
    in_market = False
    entry_price = 0
    equity = [cash]
    trades = 0
    trade_log = []
    
    highest_since_entry = 0
    
    # KEY CHANGES:
    TRAILING_STOP = 0.20       # 20% from high (was 12%)
    TREND_BREAK_PCT = 0.08     # 8% below trend to exit (was 5%)
    MIN_HOLD_DAYS = 14         # NEW: Hold at least 2 weeks
    COOLDOWN_DAYS = 7          # NEW: Wait 7 days after exit before re-entry
    
    days_in_trade = 0
    days_since_exit = 999  # start high so we can enter immediately
    
    print("Trading Rules:")
    print(f"  📈 BUY: Uptrend + pullback to signal DDA + {COOLDOWN_DAYS}d cooldown")
    print(f"  📉 SELL: {TRAILING_STOP*100:.0f}% trailing stop OR {TREND_BREAK_PCT*100:.0f}% trend break")
    print(f"  ⏰ Min hold: {MIN_HOLD_DAYS} days")
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
        
        if not in_market:
            days_since_exit += 1
        
        uptrend = price > trend * 0.98
        pullback = low <= signal * 1.02
        bouncing = price > signal
        
        if in_market:
            days_in_trade += 1
            highest_since_entry = max(highest_since_entry, high)
            drawdown = (highest_since_entry - low) / highest_since_entry
            
            # EXIT CONDITIONS (with minimum hold)
            trend_break = price < trend * (1 - TREND_BREAK_PCT)
            trailing_stop_hit = drawdown > TRAILING_STOP
            
            can_exit = days_in_trade >= MIN_HOLD_DAYS
            
            if can_exit and (trend_break or trailing_stop_hit):
                in_market = False
                diff = price - entry_price
                pos_size = (cash * lev) / entry_price
                pnl = diff * pos_size
                cash += pnl
                cash -= abs(cash * lev * fee)
                trades += 1
                
                reason = "TREND BREAK" if trend_break else f"TRAILING ({drawdown*100:.0f}%)"
                emoji = "✅" if pnl > 0 else "❌"
                pct = (diff / entry_price) * 100 * lev
                trade_log.append(f"  Day {i:3d} | {emoji} SELL @ ${price:>10,.2f} | PnL: ${pnl:>+8,.2f} ({pct:>+6.1f}%) | {reason} | Held {days_in_trade}d")
                
                highest_since_entry = 0
                days_in_trade = 0
                days_since_exit = 0
        
        else:
            # ENTRY with cooldown
            if uptrend and pullback and bouncing and days_since_exit >= COOLDOWN_DAYS:
                in_market = True
                entry_price = price
                highest_since_entry = high
                cash -= abs(cash * lev * fee)
                trades += 1
                days_in_trade = 0
                trade_log.append(f"  Day {i:3d} | 📈 BUY  @ ${price:>10,.2f} | Trend: ${trend:>10,.0f} | Signal: ${signal:>10,.0f}")
        
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
        pct = (diff / entry_price) * 100 * lev
        trade_log.append(f"  END     | {emoji} CLOSE @ ${price:>10,.2f} | PnL: ${pnl:>+8,.2f} ({pct:>+6.1f}%) | END OF DATA | Held {days_in_trade}d")
        equity[-1] = cash
    
    # Results
    final = float(equity[-1])
    start_price = float(prices[0])
    hodl = (1000.0 / start_price) * float(prices[-1])
    
    print("\n" + "="*70)
    print("PATIENT RIDER RESULTS")
    print("="*70)
    print(f"  Starting:     ${1000:,.2f}")
    print(f"  Final:        ${final:,.2f}")
    print(f"  HODL:         ${hodl:,.2f}")
    print(f"  Trades:       {trades}")
    print(f"  Fees:         ~${trades * 0.003 * final:.2f}")
    
    print("\n📜 TRADE LOG:")
    print("-" * 85)
    for t in trade_log:
        print(t)
    print("-" * 85)
    
    # Stats
    wins = sum(1 for t in trade_log if "✅" in t)
    losses = sum(1 for t in trade_log if "❌" in t)
    total_closed = wins + losses
    
    if final > hodl:
        print(f"\n🏆 WINNER: PATIENT RIDER! (+{((final-hodl)/hodl)*100:.1f}% vs HODL)")
    elif final > 1000:
        gap = ((hodl - final) / hodl) * 100
        print(f"\n🎯 HODL wins by {gap:.1f}% but we made ${final-1000:,.2f} profit!")
    else:
        print(f"\n❌ Lost ${1000-final:,.2f}")
    
    if total_closed > 0:
        print(f"📊 Win Rate: {wins}/{total_closed} = {wins/total_closed*100:.0f}%")
    
    # Max drawdown
    peak = np.maximum.accumulate(equity)
    drawdowns = [(peak[i] - equity[i]) / peak[i] * 100 if peak[i] > 0 else 0 for i in range(len(equity))]
    max_dd = max(drawdowns)
    print(f"📉 Max Drawdown: {max_dd:.1f}%")
    
    # Plot
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    ax1 = axes[0]
    scale = 1000 / start_price
    hodl_line = [float(prices[min(i, len(prices)-1)]) * scale for i in range(len(equity))]
    
    ax1.plot(equity, 'b-', label=f'Patient Rider (${final:,.0f})', linewidth=2)
    ax1.plot(hodl_line, 'g--', alpha=0.6, label=f'HODL (${hodl:,.0f})', linewidth=2)
    ax1.fill_between(range(len(equity)), equity, hodl_line, 
                     where=[e > h for e, h in zip(equity, hodl_line)],
                     color='blue', alpha=0.2, label='Outperforming')
    ax1.fill_between(range(len(equity)), equity, hodl_line,
                     where=[e <= h for e, h in zip(equity, hodl_line)],
                     color='red', alpha=0.2, label='Underperforming')
    ax1.set_title("Patient Rider vs HODL (2 Year Daily)", fontsize=14)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("Portfolio Value ($)")
    
    ax2 = axes[1]
    ax2.fill_between(range(len(drawdowns)), [-d for d in drawdowns], 0, color='red', alpha=0.5)
    ax2.set_title(f"Drawdown (Max: {max_dd:.1f}%)", fontsize=14)
    ax2.set_ylabel("Drawdown %")
    ax2.set_xlabel("Days")
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('patient_rider.png', dpi=150)
    print("\n✓ Saved patient_rider.png")
    plt.show()
    
    return final, hodl, trades


if __name__ == "__main__":
    run_patient_rider()
