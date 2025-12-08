
"""
DDA v20.0 "MOMENTUM PATIENT"
----------------------------
Only buy when momentum is ACCELERATING, not just positive
"""
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')

class MomentumDDA:
    def __init__(self, price_smooth=0.97, momentum_smooth=0.9):
        self.price_P0 = price_smooth
        self.mom_P0 = momentum_smooth
        self.F = None
        self.momentum = 0
        self.smooth_momentum = 0
        self.prev_price = None
        
    def update(self, price):
        if self.F is None:
            self.F = price
            self.prev_price = price
            return price, 0, 0
        
        # Price DDA
        self.F = self.price_P0 * self.F + (1 - self.price_P0) * price
        
        # Raw momentum (rate of change)
        raw_mom = (price - self.prev_price) / self.prev_price * 100
        
        # Smoothed momentum
        self.smooth_momentum = self.mom_P0 * self.smooth_momentum + (1 - self.mom_P0) * raw_mom
        
        # Momentum acceleration (is momentum increasing?)
        mom_accel = raw_mom - self.smooth_momentum
        
        self.prev_price = price
        
        return self.F, self.smooth_momentum, mom_accel


def run_momentum_patient():
    print("📡 Downloading 2 YEARS of BTC-USD (1d)...")
    df = yf.download("BTC-USD", period="2y", interval="1d", progress=False)
    prices = df['Close'].values.flatten()
    highs = df['High'].values.flatten()
    lows = df['Low'].values.flatten()
    
    print(f"✅ Loaded {len(prices)} candles (daily)\n")
    
    dda = MomentumDDA(price_smooth=0.97, momentum_smooth=0.85)
    
    cash = 1000.0
    lev = 1.5
    fee = 0.001
    
    in_market = False
    entry_price = 0
    equity = [cash]
    trades = 0
    trade_log = []
    
    highest_since_entry = 0
    days_in_trade = 0
    days_since_exit = 999
    
    # Parameters
    TRAILING_STOP = 0.18        # 18% trailing stop
    TREND_BREAK = 0.06          # 6% below DDA = exit
    MIN_HOLD = 7                # 1 week minimum
    COOLDOWN = 5                # 5 day cooldown
    
    # NEW: Momentum requirements
    MIN_MOMENTUM = 0.3          # Need positive momentum
    MIN_ACCELERATION = 0.0      # Momentum must be accelerating (or at least not decelerating)
    
    print("Trading Rules:")
    print(f"  📈 BUY: Price > DDA + Momentum > {MIN_MOMENTUM}% + Accelerating")
    print(f"  📉 SELL: {TRAILING_STOP*100:.0f}% trailing OR {TREND_BREAK*100:.0f}% trend break")
    print(f"  ⏰ Hold: min {MIN_HOLD}d | Cooldown: {COOLDOWN}d")
    print(f"  💰 Leverage: {lev}x\n")
    
    for i in tqdm(range(len(prices)), desc="Trading"):
        price = float(prices[i])
        high = float(highs[i])
        low = float(lows[i])
        
        dda_val, momentum, acceleration = dda.update(price)
        
        if i < 30:
            equity.append(cash)
            continue
        
        if not in_market:
            days_since_exit += 1
        
        # ENTRY CONDITIONS
        price_above_dda = price > dda_val
        momentum_positive = momentum > MIN_MOMENTUM
        momentum_accelerating = acceleration >= MIN_ACCELERATION
        cooldown_passed = days_since_exit >= COOLDOWN
        
        # EXIT CONDITIONS (when in trade)
        if in_market:
            days_in_trade += 1
            highest_since_entry = max(highest_since_entry, high)
            drawdown_from_high = (highest_since_entry - low) / highest_since_entry
            
            below_trend = price < dda_val * (1 - TREND_BREAK)
            trailing_hit = drawdown_from_high > TRAILING_STOP
            can_exit = days_in_trade >= MIN_HOLD
            
            # NEW: Also exit if momentum turns strongly negative
            momentum_death = momentum < -1.0
            
            if can_exit and (below_trend or trailing_hit or momentum_death):
                in_market = False
                pnl = (price - entry_price) / entry_price * cash * lev
                cash += pnl
                cash -= abs(cash * lev * fee)
                trades += 1
                
                if below_trend:
                    reason = "TREND"
                elif momentum_death:
                    reason = "MOM DEATH"
                else:
                    reason = f"TRAIL {drawdown_from_high*100:.0f}%"
                
                emoji = "✅" if pnl > 0 else "❌"
                pct = (price - entry_price) / entry_price * 100 * lev
                trade_log.append(f"  Day {i:3d} | {emoji} SELL @ ${price:>10,.2f} | PnL: ${pnl:>+8,.2f} ({pct:>+6.1f}%) | {reason:10} | {days_in_trade}d")
                
                highest_since_entry = 0
                days_in_trade = 0
                days_since_exit = 0
        
        else:
            # ENTRY
            if price_above_dda and momentum_positive and momentum_accelerating and cooldown_passed:
                in_market = True
                entry_price = price
                highest_since_entry = high
                cash -= abs(cash * lev * fee)
                trades += 1
                days_in_trade = 0
                trade_log.append(f"  Day {i:3d} | 📈 BUY  @ ${price:>10,.2f} | DDA: ${dda_val:>10,.0f} | Mom: {momentum:>+5.2f}% | Accel: {acceleration:>+5.2f}")
        
        # Mark to market
        curr = cash
        if in_market:
            curr += (price - entry_price) / entry_price * cash * lev
        
        equity.append(curr)
        
        if curr <= 0:
            print("💀 LIQUIDATED")
            break
    
    # Close open position
    if in_market:
        price = float(prices[-1])
        pnl = (price - entry_price) / entry_price * cash * lev
        cash += pnl
        trades += 1
        emoji = "✅" if pnl > 0 else "❌"
        pct = (price - entry_price) / entry_price * 100 * lev
        trade_log.append(f"  END     | {emoji} CLOSE @ ${price:>10,.2f} | PnL: ${pnl:>+8,.2f} ({pct:>+6.1f}%)")
        equity[-1] = cash
    
    # Results
    final = float(equity[-1])
    start_price = float(prices[0])
    hodl = (1000.0 / start_price) * float(prices[-1])
    
    print("\n" + "="*80)
    print("MOMENTUM PATIENT RESULTS")
    print("="*80)
    print(f"  Starting:     ${1000:,.2f}")
    print(f"  Final:        ${final:,.2f}  ({(final/1000-1)*100:+.1f}%)")
    print(f"  HODL:         ${hodl:,.2f}  ({(hodl/1000-1)*100:+.1f}%)")
    print(f"  Trades:       {trades}")
    
    print("\n📜 TRADE LOG:")
    print("-" * 95)
    for t in trade_log:
        print(t)
    print("-" * 95)
    
    # Stats
    wins = sum(1 for t in trade_log if "✅" in t)
    losses = sum(1 for t in trade_log if "❌" in t)
    
    if final > hodl:
        print(f"\n🏆 BEAT HODL BY {((final-hodl)/hodl)*100:+.1f}%!")
    elif final > 1000:
        print(f"\n🎯 HODL wins by {((hodl-final)/hodl)*100:.1f}% | Still made ${final-1000:,.2f}")
    else:
        print(f"\n❌ Lost ${1000-final:,.2f}")
    
    if wins + losses > 0:
        print(f"📊 Win Rate: {wins}/{wins+losses} = {wins/(wins+losses)*100:.0f}%")
    
    # Max drawdown
    peak = np.maximum.accumulate(equity)
    dd = [(peak[i] - equity[i]) / peak[i] * 100 if peak[i] > 0 else 0 for i in range(len(equity))]
    max_dd = max(dd)
    print(f"📉 Max Drawdown: {max_dd:.1f}%")
    
    # Plot
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # Equity
    ax1 = axes[0]
    scale = 1000 / start_price
    hodl_line = [float(prices[min(i, len(prices)-1)]) * scale for i in range(len(equity))]
    ax1.plot(equity, 'b-', linewidth=2, label=f'Strategy ${final:,.0f}')
    ax1.plot(hodl_line, 'g--', alpha=0.6, linewidth=2, label=f'HODL ${hodl:,.0f}')
    ax1.set_title("Momentum Patient vs HODL", fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("$")
    
    # Drawdown
    ax2 = axes[1]
    ax2.fill_between(range(len(dd)), [-x for x in dd], 0, color='red', alpha=0.5)
    ax2.set_title(f"Drawdown (Max: {max_dd:.1f}%)")
    ax2.set_ylabel("DD %")
    ax2.grid(True, alpha=0.3)
    
    # Price with DDA
    ax3 = axes[2]
    ax3.plot(prices, 'k-', alpha=0.7, label='BTC')
    # Recalc DDA for plot
    dda2 = MomentumDDA(0.97, 0.85)
    dda_line = [dda2.update(float(p))[0] for p in prices]
    ax3.plot(dda_line, 'b-', label='DDA')
    ax3.set_title("BTC Price & DDA")
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_xlabel("Days")
    
    plt.tight_layout()
    plt.savefig('momentum_patient.png', dpi=150)
    print("\n✓ Saved momentum_patient.png")
    plt.show()


if __name__ == "__main__":
    run_momentum_patient()
