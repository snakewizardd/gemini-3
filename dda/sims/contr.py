
"""
DDA v21.0 "CONTRARIAN OLIVER"
-----------------------------
1. BUY THE BLOOD: Enter when price crashes BELOW DDA (oversold)
2. OLIVER METHOD: Pyramid into winners, never add to losers
3. SELL THE GREED: Exit when price goes FAR ABOVE DDA (overbought)

This is MEAN REVERSION, not trend following!
"""
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')

class ContrarianDDA:
    def __init__(self, smoothing=0.97):
        self.P0 = smoothing
        self.F = None
        self.prices = []
        
    def update(self, price):
        self.prices.append(price)
        if len(self.prices) > 100:
            self.prices.pop(0)
            
        if self.F is None:
            self.F = price
            return price, 0, 0
        
        self.F = self.P0 * self.F + (1 - self.P0) * price
        
        # How far is price from "fair value" (DDA)?
        deviation = (price - self.F) / self.F * 100  # as percentage
        
        # Volatility for adaptive thresholds
        if len(self.prices) >= 20:
            volatility = np.std(self.prices[-20:]) / np.mean(self.prices[-20:]) * 100
        else:
            volatility = 2.0
        
        return self.F, deviation, volatility


def run_contrarian_oliver():
    print("📡 Downloading 2 YEARS of BTC-USD (1d)...")
    df = yf.download("BTC-USD", period="2y", interval="1d", progress=False)
    prices = df['Close'].values.flatten()
    highs = df['High'].values.flatten()
    lows = df['Low'].values.flatten()
    
    print(f"✅ Loaded {len(prices)} candles (daily)\n")
    
    dda = ContrarianDDA(smoothing=0.97)
    
    initial_cash = 1000.0
    cash = initial_cash
    lev = 1.5
    fee = 0.001
    
    # Position tracking for OLIVER METHOD (pyramiding)
    position = None  # {'entry': price, 'size': btc_amount, 'cost_basis': avg_price}
    equity = [cash]
    trades = 0
    trade_log = []
    
    # CONTRARIAN THRESHOLDS
    OVERSOLD_PCT = -8.0      # Buy when price is 8% BELOW DDA
    OVERBOUGHT_PCT = 8.0     # Sell when price is 8% ABOVE DDA
    
    # OLIVER METHOD: Pyramid levels
    # Add to position if it's winning and we get another oversold signal
    PYRAMID_LEVELS = 3       # Max 3 entries per position
    PYRAMID_THRESHOLD = -5.0 # Add more if still 5% below DDA AND in profit
    
    # Risk management
    STOP_LOSS_PCT = -15.0    # Cut losses at 15%
    
    pyramid_count = 0
    
    print("="*70)
    print("CONTRARIAN OLIVER STRATEGY")
    print("="*70)
    print(f"  🩸 BUY THE BLOOD:  Price < DDA by {abs(OVERSOLD_PCT)}%")
    print(f"  🤑 SELL THE GREED: Price > DDA by {OVERBOUGHT_PCT}%")
    print(f"  📈 PYRAMID:        Up to {PYRAMID_LEVELS}x, add when down {abs(PYRAMID_THRESHOLD)}% & winning")
    print(f"  🛑 STOP LOSS:      {abs(STOP_LOSS_PCT)}%")
    print(f"  💰 Leverage:       {lev}x")
    print("="*70 + "\n")
    
    for i in tqdm(range(len(prices)), desc="Trading"):
        price = float(prices[i])
        high = float(highs[i])
        low = float(lows[i])
        
        fair_value, deviation, volatility = dda.update(price)
        
        if i < 30:
            equity.append(cash)
            continue
        
        # Current P&L if in position
        current_pnl_pct = 0
        if position:
            current_pnl_pct = (price - position['cost_basis']) / position['cost_basis'] * 100
        
        # =============================================
        # CONTRARIAN ENTRY: Buy when OVERSOLD
        # =============================================
        oversold = deviation < OVERSOLD_PCT
        
        if oversold and position is None:
            # INITIAL ENTRY - Buy the blood!
            invest_amount = cash * 0.33 * lev  # Start with 1/3 of capital
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
            
            trade_log.append(f"  Day {i:3d} | 🩸 BUY #1 @ ${price:>10,.2f} | Dev: {deviation:>+5.1f}% | Size: {size:.4f} BTC")
        
        # =============================================
        # OLIVER METHOD: Pyramid into WINNERS
        # =============================================
        elif position and pyramid_count < PYRAMID_LEVELS:
            # Only add if:
            # 1. Still oversold (price below DDA)
            # 2. Current position is PROFITABLE (Oliver method - add to winners!)
            # 3. Haven't maxed out pyramid levels
            
            still_oversold = deviation < PYRAMID_THRESHOLD
            position_profitable = current_pnl_pct > 2.0  # At least 2% profit
            
            if still_oversold and position_profitable and cash > 100:
                # Add to position
                add_amount = cash * 0.5 * lev  # Add half of remaining
                add_size = add_amount / price
                add_fee = add_amount * fee
                cash -= (add_amount / lev) + add_fee
                
                # Update cost basis (weighted average)
                total_cost = position['cost_basis'] * position['size'] + price * add_size
                total_size = position['size'] + add_size
                new_cost_basis = total_cost / total_size
                
                position['size'] = total_size
                position['cost_basis'] = new_cost_basis
                position['invested'] += add_amount / lev
                pyramid_count += 1
                trades += 1
                
                trade_log.append(f"  Day {i:3d} | 📈 ADD #{pyramid_count} @ ${price:>10,.2f} | Dev: {deviation:>+5.1f}% | P&L: {current_pnl_pct:>+5.1f}% | Total: {total_size:.4f} BTC")
        
        # =============================================
        # EXIT CONDITIONS
        # =============================================
        if position:
            overbought = deviation > OVERBOUGHT_PCT
            stop_loss_hit = current_pnl_pct < STOP_LOSS_PCT
            
            # SELL THE GREED or STOP LOSS
            if overbought or stop_loss_hit:
                exit_value = position['size'] * price
                exit_fee = exit_value * fee
                pnl = (price - position['cost_basis']) * position['size']
                
                cash += position['invested'] + pnl - exit_fee
                
                reason = "🤑 OVERBOUGHT" if overbought else "🛑 STOP LOSS"
                emoji = "✅" if pnl > 0 else "❌"
                pnl_pct = current_pnl_pct * lev
                
                trade_log.append(f"  Day {i:3d} | {emoji} SELL  @ ${price:>10,.2f} | Dev: {deviation:>+5.1f}% | PnL: ${pnl:>+8,.2f} ({pnl_pct:>+5.1f}%) | {reason}")
                
                position = None
                pyramid_count = 0
                trades += 1
        
        # =============================================
        # MARK TO MARKET
        # =============================================
        curr = cash
        if position:
            curr += position['invested'] + (price - position['cost_basis']) * position['size']
        
        equity.append(curr)
        
        if curr <= 0:
            print("💀 LIQUIDATED")
            break
    
    # Close any open position at end
    if position:
        price = float(prices[-1])
        pnl = (price - position['cost_basis']) * position['size']
        cash += position['invested'] + pnl
        pnl_pct = (price - position['cost_basis']) / position['cost_basis'] * 100 * lev
        emoji = "✅" if pnl > 0 else "❌"
        trade_log.append(f"  END     | {emoji} CLOSE @ ${price:>10,.2f} | PnL: ${pnl:>+8,.2f} ({pnl_pct:>+5.1f}%)")
        equity[-1] = cash
        trades += 1
    
    # =============================================
    # RESULTS
    # =============================================
    final = float(equity[-1])
    start_price = float(prices[0])
    hodl = (initial_cash / start_price) * float(prices[-1])
    
    print("\n" + "="*80)
    print("CONTRARIAN OLIVER RESULTS")
    print("="*80)
    print(f"  Starting:     ${initial_cash:,.2f}")
    print(f"  Final:        ${final:,.2f}  ({(final/initial_cash-1)*100:>+.1f}%)")
    print(f"  HODL:         ${hodl:,.2f}  ({(hodl/initial_cash-1)*100:>+.1f}%)")
    print(f"  Trades:       {trades}")
    
    print("\n📜 TRADE LOG:")
    print("-" * 90)
    for t in trade_log:
        print(t)
    print("-" * 90)
    
    # Stats
    wins = sum(1 for t in trade_log if "✅" in t)
    losses = sum(1 for t in trade_log if "❌" in t)
    
    if final > hodl:
        print(f"\n🏆 BEAT HODL BY {((final-hodl)/hodl)*100:>+.1f}%!!!")
    elif final > initial_cash:
        print(f"\n🎯 HODL wins by {((hodl-final)/hodl)*100:.1f}% | Still made ${final-initial_cash:,.2f}")
    else:
        print(f"\n❌ Lost ${initial_cash-final:,.2f}")
    
    if wins + losses > 0:
        print(f"📊 Win Rate: {wins}/{wins+losses} = {wins/(wins+losses)*100:.0f}%")
    
    # Max drawdown
    peak = np.maximum.accumulate(equity)
    dd = [(peak[i] - equity[i]) / peak[i] * 100 if peak[i] > 0 else 0 for i in range(len(equity))]
    max_dd = max(dd)
    print(f"📉 Max Drawdown: {max_dd:.1f}%")
    
    # Profit factor
    winning_trades = [t for t in trade_log if "✅" in t]
    losing_trades = [t for t in trade_log if "❌" in t]
    print(f"📈 Winning Trades: {len(winning_trades)} | Losing: {len(losing_trades)}")
    
    # =============================================
    # PLOT
    # =============================================
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # 1. Equity curve
    ax1 = axes[0]
    scale = initial_cash / start_price
    hodl_line = [float(prices[min(i, len(prices)-1)]) * scale for i in range(len(equity))]
    
    ax1.plot(equity, 'b-', linewidth=2, label=f'Contrarian Oliver ${final:,.0f}')
    ax1.plot(hodl_line, 'g--', alpha=0.6, linewidth=2, label=f'HODL ${hodl:,.0f}')
    ax1.fill_between(range(len(equity)), equity, hodl_line,
                     where=[e > h for e, h in zip(equity, hodl_line)],
                     color='blue', alpha=0.3)
    ax1.fill_between(range(len(equity)), equity, hodl_line,
                     where=[e <= h for e, h in zip(equity, hodl_line)],
                     color='red', alpha=0.3)
    ax1.set_title("Contrarian Oliver vs HODL", fontsize=14)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("Portfolio Value ($)")
    
    # 2. Price deviation from DDA
    ax2 = axes[1]
    dda2 = ContrarianDDA(smoothing=0.97)
    deviations = []
    for p in prices:
        _, dev, _ = dda2.update(float(p))
        deviations.append(dev)
    
    ax2.plot(deviations, 'purple', alpha=0.7)
    ax2.axhline(y=OVERSOLD_PCT, color='green', linestyle='--', label=f'Buy Zone (<{OVERSOLD_PCT}%)')
    ax2.axhline(y=OVERBOUGHT_PCT, color='red', linestyle='--', label=f'Sell Zone (>{OVERBOUGHT_PCT}%)')
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax2.fill_between(range(len(deviations)), deviations, OVERSOLD_PCT,
                     where=[d < OVERSOLD_PCT for d in deviations],
                     color='green', alpha=0.3, label='Oversold (BUY)')
    ax2.fill_between(range(len(deviations)), deviations, OVERBOUGHT_PCT,
                     where=[d > OVERBOUGHT_PCT for d in deviations],
                     color='red', alpha=0.3, label='Overbought (SELL)')
    ax2.set_title("Price Deviation from DDA (Fair Value)", fontsize=14)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylabel("Deviation %")
    
    # 3. Drawdown
    ax3 = axes[2]
    ax3.fill_between(range(len(dd)), [-x for x in dd], 0, color='red', alpha=0.5)
    ax3.set_title(f"Drawdown (Max: {max_dd:.1f}%)", fontsize=14)
    ax3.set_ylabel("Drawdown %")
    ax3.set_xlabel("Days")
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('contrarian_oliver.png', dpi=150)
    print("\n✓ Saved contrarian_oliver.png")
    plt.show()
    
    return final, hodl, trades


if __name__ == "__main__":
    run_contrarian_oliver()
