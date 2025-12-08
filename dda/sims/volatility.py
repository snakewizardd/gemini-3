
"""
DDA v23.0 "SMART CONTRARIAN OLIVER"
-----------------------------------
Same as aggressive, but:
- Skip entries during high volatility (crashes in progress)
- Tighter pyramiding rules
"""
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')

class SmartContrarianDDA:
    def __init__(self, smoothing=0.96):
        self.P0 = smoothing
        self.F = None
        self.prices = []
        self.volatilities = []
        
    def update(self, price):
        self.prices.append(price)
        if len(self.prices) > 100:
            self.prices.pop(0)
            
        if self.F is None:
            self.F = price
            return price, 0, 0, False
        
        self.F = self.P0 * self.F + (1 - self.P0) * price
        deviation = (price - self.F) / self.F * 100
        
        # Calculate volatility
        if len(self.prices) >= 14:
            returns = [(self.prices[i] - self.prices[i-1]) / self.prices[i-1] * 100 
                      for i in range(1, len(self.prices[-14:]))]
            volatility = np.std(returns) if returns else 0
            self.volatilities.append(volatility)
            if len(self.volatilities) > 50:
                self.volatilities.pop(0)
        else:
            volatility = 0
        
        # Is volatility abnormally high? (crash/panic mode)
        avg_vol = np.mean(self.volatilities) if self.volatilities else volatility
        high_volatility = volatility > avg_vol * 1.8  # 80% above average = danger
        
        return self.F, deviation, volatility, high_volatility


def run_smart_oliver():
    print("📡 Downloading 2 YEARS of BTC-USD (1d)...")
    df = yf.download("BTC-USD", period="2y", interval="1d", progress=False)
    prices = df['Close'].values.flatten()
    highs = df['High'].values.flatten()
    lows = df['Low'].values.flatten()
    
    print(f"✅ Loaded {len(prices)} candles (daily)\n")
    
    dda = SmartContrarianDDA(smoothing=0.96)
    
    initial_cash = 1000.0
    cash = initial_cash
    lev = 2.0
    fee = 0.001
    
    position = None
    equity = [cash]
    trades = 0
    trade_log = []
    skipped = 0
    
    # THRESHOLDS (same as aggressive)
    OVERSOLD_PCT = -5.0
    OVERBOUGHT_PCT = 6.0
    PYRAMID_LEVELS = 3
    PYRAMID_THRESHOLD = -3.0
    STOP_LOSS_PCT = -12.0
    
    pyramid_count = 0
    
    print("="*70)
    print("SMART CONTRARIAN OLIVER (with Volatility Filter)")
    print("="*70)
    print(f"  🩸 BUY THE BLOOD:  Price < DDA by {abs(OVERSOLD_PCT)}%")
    print(f"  🤑 SELL THE GREED: Price > DDA by {OVERBOUGHT_PCT}%")
    print(f"  📈 PYRAMID:        Up to {PYRAMID_LEVELS}x")
    print(f"  🛑 STOP LOSS:      {abs(STOP_LOSS_PCT)}%")
    print(f"  ⚠️  VOL FILTER:    Skip entries during panic/crashes")
    print(f"  💰 Leverage:       {lev}x")
    print("="*70 + "\n")
    
    for i in tqdm(range(len(prices)), desc="Trading"):
        price = float(prices[i])
        
        fair_value, deviation, volatility, high_vol = dda.update(price)
        
        if i < 30:
            equity.append(cash)
            continue
        
        current_pnl_pct = 0
        if position:
            current_pnl_pct = (price - position['cost_basis']) / position['cost_basis'] * 100
        
        # ENTRY with VOLATILITY FILTER
        oversold = deviation < OVERSOLD_PCT
        
        if oversold and position is None:
            # NEW: Skip if volatility is spiking (catching falling knife)
            if high_vol:
                skipped += 1
                # Don't enter during panic - wait for dust to settle
            else:
                invest_amount = cash * 0.5 * lev
                size = invest_amount / price
                entry_fee = invest_amount * fee
                cash -= (invest_amount / lev) + entry_fee
                
                position = {
                    'entry': price,
                    'size': size,
                    'cost_basis': price,
                    'invested': invest_amount / lev
                }
                pyramid_count = 1
                trades += 1
                
                trade_log.append(f"  Day {i:3d} | 🩸 BUY #1 @ ${price:>10,.2f} | Dev: {deviation:>+5.1f}% | Vol: {volatility:.2f}")
        
        # PYRAMID (only if volatility is normal)
        elif position and pyramid_count < PYRAMID_LEVELS and not high_vol:
            still_oversold = deviation < PYRAMID_THRESHOLD
            position_profitable = current_pnl_pct > 1.5
            
            if still_oversold and position_profitable and cash > 50:
                add_amount = cash * 0.6 * lev
                add_size = add_amount / price
                add_fee = add_amount * fee
                cash -= (add_amount / lev) + add_fee
                
                total_cost = position['cost_basis'] * position['size'] + price * add_size
                total_size = position['size'] + add_size
                new_cost_basis = total_cost / total_size
                
                position['size'] = total_size
                position['cost_basis'] = new_cost_basis
                position['invested'] += add_amount / lev
                pyramid_count += 1
                trades += 1
                
                trade_log.append(f"  Day {i:3d} | 📈 ADD #{pyramid_count} @ ${price:>10,.2f} | Dev: {deviation:>+5.1f}% | P&L: {current_pnl_pct:>+5.1f}%")
        
        # EXIT
        if position:
            overbought = deviation > OVERBOUGHT_PCT
            stop_loss_hit = current_pnl_pct < STOP_LOSS_PCT
            
            if overbought or stop_loss_hit:
                pnl = (price - position['cost_basis']) * position['size']
                cash += position['invested'] + pnl - (position['size'] * price * fee)
                
                reason = "🤑 OVERBOUGHT" if overbought else "🛑 STOP LOSS"
                emoji = "✅" if pnl > 0 else "❌"
                pnl_pct = current_pnl_pct * lev
                
                trade_log.append(f"  Day {i:3d} | {emoji} SELL  @ ${price:>10,.2f} | Dev: {deviation:>+5.1f}% | PnL: ${pnl:>+8,.2f} ({pnl_pct:>+5.1f}%) | {reason}")
                
                position = None
                pyramid_count = 0
                trades += 1
        
        # Mark to market
        curr = cash
        if position:
            curr += position['invested'] + (price - position['cost_basis']) * position['size']
        
        equity.append(curr)
        
        if curr <= 0:
            print("💀 LIQUIDATED")
            break
    
    # Close open position
    if position:
        price = float(prices[-1])
        pnl = (price - position['cost_basis']) * position['size']
        cash += position['invested'] + pnl
        pnl_pct = (price - position['cost_basis']) / position['cost_basis'] * 100 * lev
        emoji = "✅" if pnl > 0 else "❌"
        trade_log.append(f"  END     | {emoji} CLOSE @ ${price:>10,.2f} | PnL: ${pnl:>+8,.2f} ({pnl_pct:>+5.1f}%)")
        equity[-1] = cash
        trades += 1
    
    # RESULTS
    final = float(equity[-1])
    start_price = float(prices[0])
    hodl = (initial_cash / start_price) * float(prices[-1])
    
    print("\n" + "="*80)
    print("SMART CONTRARIAN OLIVER RESULTS")
    print("="*80)
    print(f"  Starting:     ${initial_cash:,.2f}")
    print(f"  Final:        ${final:,.2f}  ({(final/initial_cash-1)*100:>+.1f}%)")
    print(f"  HODL:         ${hodl:,.2f}  ({(hodl/initial_cash-1)*100:>+.1f}%)")
    print(f"  Trades:       {trades}")
    print(f"  Skipped:      {skipped} (high volatility)")
    
    print("\n📜 TRADE LOG:")
    print("-" * 90)
    for t in trade_log:
        print(t)
    print("-" * 90)
    
    wins = sum(1 for t in trade_log if "✅" in t)
    losses = sum(1 for t in trade_log if "❌" in t)
    
    if final > hodl:
        print(f"\n🏆 BEAT HODL BY {((final-hodl)/hodl)*100:>+.1f}%!!!")
    elif final > initial_cash:
        print(f"\n🎯 HODL wins by {((hodl-final)/hodl)*100:.1f}% | Profit: ${final-initial_cash:,.2f}")
    else:
        print(f"\n❌ Lost ${initial_cash-final:,.2f}")
    
    if wins + losses > 0:
        print(f"📊 Win Rate: {wins}/{wins+losses} = {wins/(wins+losses)*100:.0f}%")
    
    peak = np.maximum.accumulate(equity)
    dd = [(peak[i] - equity[i]) / peak[i] * 100 if peak[i] > 0 else 0 for i in range(len(equity))]
    max_dd = max(dd)
    print(f"📉 Max Drawdown: {max_dd:.1f}%")
    
    returns = [(equity[i] - equity[i-1]) / equity[i-1] for i in range(1, len(equity)) if equity[i-1] > 0]
    if len(returns) > 0 and np.std(returns) > 0:
        sharpe = (np.mean(returns) * 365) / (np.std(returns) * np.sqrt(365))
        print(f"📊 Sharpe Ratio: {sharpe:.2f}")
    
    # Plot
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    ax1 = axes[0]
    scale = initial_cash / start_price
    hodl_line = [float(prices[min(i, len(prices)-1)]) * scale for i in range(len(equity))]
    ax1.plot(equity, 'b-', linewidth=2, label=f'Smart Oliver ${final:,.0f}')
    ax1.plot(hodl_line, 'g--', alpha=0.6, linewidth=2, label=f'HODL ${hodl:,.0f}')
    ax1.set_title("Smart Contrarian Oliver vs HODL", fontsize=14)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("$")
    
    ax2 = axes[1]
    dda2 = SmartContrarianDDA(smoothing=0.96)
    deviations = [dda2.update(float(p))[1] for p in prices]
    ax2.plot(deviations, 'purple', alpha=0.7)
    ax2.axhline(y=OVERSOLD_PCT, color='green', linestyle='--')
    ax2.axhline(y=OVERBOUGHT_PCT, color='red', linestyle='--')
    ax2.fill_between(range(len(deviations)), deviations, OVERSOLD_PCT,
                     where=[d < OVERSOLD_PCT for d in deviations], color='green', alpha=0.3)
    ax2.set_title("Deviation from Fair Value", fontsize=14)
    ax2.grid(True, alpha=0.3)
    
    ax3 = axes[2]
    ax3.fill_between(range(len(dd)), [-x for x in dd], 0, color='red', alpha=0.5)
    ax3.set_title(f"Drawdown (Max: {max_dd:.1f}%)", fontsize=14)
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('smart_oliver.png', dpi=150)
    print("\n✓ Saved smart_oliver.png")
    plt.show()


if __name__ == "__main__":
    run_smart_oliver()
