
"""
DDA v21.1 "CONTRARIAN OLIVER PRO"
---------------------------------
HYBRID APPROACH:
1. TREND FILTER: Detect if we're trending or ranging
2. RANGING MARKET: Mean reversion (buy blood, sell greed)
3. TRENDING MARKET: Ride the trend with trailing stop
4. OLIVER METHOD: Always pyramid into winners

The key insight: Don't fight the trend, but BUY THE DIPS in trends!
"""
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')


class HybridDDA:
    """Enhanced DDA with trend detection"""
    def __init__(self, fast_smooth=0.92, slow_smooth=0.97):
        self.fast_smooth = fast_smooth
        self.slow_smooth = slow_smooth
        self.fast_dda = None
        self.slow_dda = None
        self.prices = []
        
    def update(self, price):
        self.prices.append(price)
        if len(self.prices) > 100:
            self.prices.pop(0)
        
        # Initialize
        if self.fast_dda is None:
            self.fast_dda = price
            self.slow_dda = price
            return price, price, 0, 0, 'NEUTRAL'
        
        # Update DDAs
        self.fast_dda = self.fast_smooth * self.fast_dda + (1 - self.fast_smooth) * price
        self.slow_dda = self.slow_smooth * self.slow_dda + (1 - self.slow_smooth) * price
        
        # Deviation from slow DDA (fair value)
        deviation = (price - self.slow_dda) / self.slow_dda * 100
        
        # Volatility
        if len(self.prices) >= 20:
            volatility = np.std(self.prices[-20:]) / np.mean(self.prices[-20:]) * 100
        else:
            volatility = 3.0
        
        # TREND DETECTION
        # Compare fast vs slow DDA + price momentum
        dda_spread = (self.fast_dda - self.slow_dda) / self.slow_dda * 100
        
        # Check 30-day momentum
        if len(self.prices) >= 30:
            momentum = (price - self.prices[-30]) / self.prices[-30] * 100
        else:
            momentum = 0
        
        # Regime detection
        if dda_spread > 2.0 and momentum > 10:
            regime = 'BULL_TREND'
        elif dda_spread < -2.0 and momentum < -10:
            regime = 'BEAR_TREND'
        else:
            regime = 'RANGING'
        
        return self.fast_dda, self.slow_dda, deviation, volatility, regime


class OliverManager:
    """Oliver Method: Build on wins, cut losses"""
    def __init__(self, base_size=0.4, max_pyramids=3, size_mult=1.5):
        self.base_size = base_size
        self.max_pyramids = max_pyramids
        self.size_mult = size_mult
        self.consecutive_wins = 0
        
    def record_win(self):
        self.consecutive_wins += 1
        
    def record_loss(self):
        self.consecutive_wins = 0
        
    def get_entry_size(self):
        """After wins, start with bigger size"""
        multiplier = min(1 + (self.consecutive_wins * 0.25), 2.0)  # Cap at 2x
        return self.base_size * multiplier


def run_contrarian_oliver_pro():
    print("=" * 70)
    print("DDA v21.1 'CONTRARIAN OLIVER PRO' - Hybrid Trend + Mean Reversion")
    print("=" * 70)
    
    print("\n📡 Downloading 2 YEARS of BTC-USD (1d)...")
    df = yf.download("BTC-USD", period="2y", interval="1d", progress=False)
    prices = df['Close'].values.flatten()
    highs = df['High'].values.flatten()
    lows = df['Low'].values.flatten()
    
    print(f"✅ Loaded {len(prices)} candles (daily)\n")
    
    dda = HybridDDA(fast_smooth=0.92, slow_smooth=0.97)
    oliver = OliverManager(base_size=0.4, max_pyramids=3, size_mult=1.5)
    
    initial_cash = 1000.0
    cash = initial_cash
    fee = 0.001
    
    position = None
    pyramid_count = 0
    equity = [cash]
    trades = 0
    trade_log = []
    
    # === ADAPTIVE THRESHOLDS ===
    # These change based on regime!
    RANGING_OVERSOLD = -7.0
    RANGING_OVERBOUGHT = 7.0
    
    TREND_BUYDIP = -5.0       # In bull trend, buy smaller dips
    TREND_OVERBOUGHT = 15.0   # In bull trend, let it run much further!
    
    STOP_LOSS_PCT = -12.0     # Tighter stop
    TRAILING_STOP_PCT = 0.15  # 15% trailing in trends
    
    highest_since_entry = 0
    entry_regime = None
    
    print("📊 HYBRID STRATEGY RULES:")
    print(f"  📈 BULL TREND: Buy dips at {TREND_BUYDIP}%, sell at {TREND_OVERBOUGHT}%")
    print(f"  📊 RANGING:    Buy at {RANGING_OVERSOLD}%, sell at {RANGING_OVERBOUGHT}%")
    print(f"  🛑 STOP LOSS:  {abs(STOP_LOSS_PCT)}%")
    print(f"  📉 TRAILING:   {TRAILING_STOP_PCT*100}% from high (in trends)")
    print("=" * 70 + "\n")
    
    regime_history = []
    
    for i in tqdm(range(len(prices)), desc="🎯 Hybrid Trading"):
        price = float(prices[i])
        high = float(highs[i])
        low = float(lows[i])
        
        fast_dda, slow_dda, deviation, volatility, regime = dda.update(price)
        regime_history.append(regime)
        
        if i < 50:  # Longer warmup for trend detection
            equity.append(cash)
            continue
        
        # Current P&L
        current_pnl_pct = 0
        if position:
            current_pnl_pct = (price - position['cost_basis']) / position['cost_basis'] * 100
            highest_since_entry = max(highest_since_entry, price)
        
        # === ADAPTIVE THRESHOLDS BASED ON REGIME ===
        if regime == 'BULL_TREND':
            buy_threshold = TREND_BUYDIP
            sell_threshold = TREND_OVERBOUGHT
            use_trailing = True
        elif regime == 'BEAR_TREND':
            buy_threshold = RANGING_OVERSOLD - 3  # Need deeper dip in bear
            sell_threshold = RANGING_OVERBOUGHT - 3  # Exit faster
            use_trailing = False
        else:  # RANGING
            buy_threshold = RANGING_OVERSOLD
            sell_threshold = RANGING_OVERBOUGHT
            use_trailing = False
        
        # === ENTRY LOGIC ===
        oversold = deviation < buy_threshold
        
        if oversold and position is None:
            # INITIAL ENTRY
            entry_size = oliver.get_entry_size()
            invest_amount = cash * entry_size
            size = invest_amount / price
            entry_fee = invest_amount * fee
            cash -= invest_amount + entry_fee
            
            position = {
                'entry': price,
                'size': size,
                'cost_basis': price,
                'invested': invest_amount
            }
            pyramid_count = 1
            highest_since_entry = price
            entry_regime = regime
            trades += 1
            
            regime_emoji = "🐂" if regime == 'BULL_TREND' else ("🐻" if regime == 'BEAR_TREND' else "📊")
            trade_log.append(f"  Day {i:3d} | 🩸 BUY #1 @ ${price:>10,.2f} | Dev: {deviation:>+5.1f}% | {regime_emoji} {regime}")
        
        # === OLIVER PYRAMIDING ===
        elif position and pyramid_count < oliver.max_pyramids:
            still_oversold = deviation < buy_threshold + 2  # Slightly higher threshold for adds
            position_profitable = current_pnl_pct > 1.5
            
            if still_oversold and position_profitable and cash > 50:
                add_pct = 0.5 if pyramid_count == 1 else 0.3
                add_amount = cash * add_pct
                add_size = add_amount / price
                add_fee = add_amount * fee
                cash -= add_amount + add_fee
                
                total_cost = position['cost_basis'] * position['size'] + price * add_size
                total_size = position['size'] + add_size
                new_cost_basis = total_cost / total_size
                
                position['size'] = total_size
                position['cost_basis'] = new_cost_basis
                position['invested'] += add_amount
                pyramid_count += 1
                trades += 1
                
                trade_log.append(f"  Day {i:3d} | 📈 ADD #{pyramid_count} @ ${price:>10,.2f} | Dev: {deviation:>+5.1f}% | P&L: {current_pnl_pct:>+5.1f}%")
        
        # === EXIT LOGIC ===
        if position:
            overbought = deviation > sell_threshold
            stop_loss_hit = current_pnl_pct < STOP_LOSS_PCT
            
            # Trailing stop (only in trends when profitable)
            trailing_stop_hit = False
            if use_trailing and current_pnl_pct > 10:  # Only after 10% profit
                trail_price = highest_since_entry * (1 - TRAILING_STOP_PCT)
                if price < trail_price:
                    trailing_stop_hit = True
            
            if overbought or stop_loss_hit or trailing_stop_hit:
                exit_value = position['size'] * price
                exit_fee = exit_value * fee
                pnl = (price - position['cost_basis']) * position['size']
                
                cash += position['invested'] + pnl - exit_fee
                
                if overbought:
                    reason = "🤑 OVERBOUGHT"
                elif trailing_stop_hit:
                    reason = "📉 TRAILING"
                else:
                    reason = "🛑 STOP LOSS"
                
                emoji = "✅" if pnl > 0 else "❌"
                pnl_pct = current_pnl_pct
                
                if pnl > 0:
                    oliver.record_win()
                else:
                    oliver.record_loss()
                
                trade_log.append(f"  Day {i:3d} | {emoji} SELL  @ ${price:>10,.2f} | Dev: {deviation:>+5.1f}% | PnL: ${pnl:>+8,.2f} ({pnl_pct:>+5.1f}%) | {reason}")
                
                position = None
                pyramid_count = 0
                highest_since_entry = 0
                entry_regime = None
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
        pnl_pct = (price - position['cost_basis']) / position['cost_basis'] * 100
        emoji = "✅" if pnl > 0 else "❌"
        
        if pnl > 0:
            oliver.record_win()
        else:
            oliver.record_loss()
            
        trade_log.append(f"  END     | {emoji} CLOSE @ ${price:>10,.2f} | PnL: ${pnl:>+8,.2f} ({pnl_pct:>+5.1f}%)")
        equity[-1] = cash
        trades += 1
    
    # === RESULTS ===
    final = float(equity[-1])
    start_price = float(prices[0])
    hodl = (initial_cash / start_price) * float(prices[-1])
    
    print("\n" + "=" * 80)
    print("🏆 CONTRARIAN OLIVER PRO RESULTS")
    print("=" * 80)
    print(f"  💵 Starting:     ${initial_cash:,.2f}")
    print(f"  💰 Final:        ${final:,.2f}  ({(final/initial_cash-1)*100:>+.1f}%)")
    print(f"  📊 HODL:         ${hodl:,.2f}  ({(hodl/initial_cash-1)*100:>+.1f}%)")
    print(f"  🔄 Trades:       {trades}")
    
    print("\n📜 TRADE LOG:")
    print("-" * 95)
    for t in trade_log:
        print(t)
    print("-" * 95)
    
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
    
    # Regime breakdown
    bull_count = sum(1 for r in regime_history if r == 'BULL_TREND')
    bear_count = sum(1 for r in regime_history if r == 'BEAR_TREND')
    range_count = sum(1 for r in regime_history if r == 'RANGING')
    total = len(regime_history)
    print(f"\n📈 Regime Breakdown:")
    print(f"   🐂 Bull Trend: {bull_count}/{total} days ({bull_count/total*100:.0f}%)")
    print(f"   🐻 Bear Trend: {bear_count}/{total} days ({bear_count/total*100:.0f}%)")  
    print(f"   📊 Ranging:    {range_count}/{total} days ({range_count/total*100:.0f}%)")
    
    # === PLOT ===
    fig, axes = plt.subplots(4, 1, figsize=(14, 14))
    
    # 1. Equity curve
    ax1 = axes
    scale = initial_cash / start_price
    hodl_line = [float(prices[min(i, len(prices)-1)]) * scale for i in range(len(equity))]
    
    ax1.plot(equity, 'b-', linewidth=2, label=f'Oliver Pro ${final:,.0f}')
    ax1.plot(hodl_line, 'g--', alpha=0.6, linewidth=2, label=f'HODL ${hodl:,.0f}')
    ax1.fill_between(range(len(equity)), equity, hodl_line,
                     where=[e > h for e, h in zip(equity, hodl_line)],
                     color='blue', alpha=0.3)
    ax1.fill_between(range(len(equity)), equity, hodl_line,
                     where=[e <= h for e, h in zip(equity, hodl_line)],
                     color='red', alpha=0.3)
    ax1.set_title("Contrarian Oliver Pro vs HODL", fontsize=14)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("Portfolio Value ($)")
    
    # 2. Price with regime coloring
    ax2 = axes[1]()
    ax2.plot(prices, 'black', alpha=0.8, linewidth=1)
    
    # Color background by regime
    for j in range(len(regime_history)):
        if regime_history[j] == 'BULL_TREND':
            ax2.axvspan(j, j+1, alpha=0.2, color='green')
        elif regime_history[j] == 'BEAR_TREND':
            ax2.axvspan(j, j+1, alpha=0.2, color='red')
    
    ax2.set_title("BTC Price with Regime Detection (Green=Bull, Red=Bear, White=Ranging)", fontsize=14)
    ax2.set_ylabel("Price ($)")
    ax2.grid(True, alpha=0.3)
    
    # 3. Deviation from DDA
    ax3 = axes
    dda2 = HybridDDA(fast_smooth=0.92, slow_smooth=0.97)
    deviations = []
    for p in prices:
        _, _, dev, _, _ = dda2.update(float(p))
        deviations.append(dev)
    
    ax3.plot(deviations, 'purple', alpha=0.7)
    ax3.axhline(y=RANGING_OVERSOLD, color='green', linestyle='--', label=f'Range Buy ({RANGING_OVERSOLD}%)')
    ax3.axhline(y=RANGING_OVERBOUGHT, color='red', linestyle='--', label=f'Range Sell ({RANGING_OVERBOUGHT}%)')
    ax3.axhline(y=TREND_OVERBOUGHT, color='orange', linestyle=':', label=f'Trend Sell ({TREND_OVERBOUGHT}%)')
    ax3.axhline(y=0, color='black', alpha=0.3)
    ax3.set_title("Price Deviation from DDA", fontsize=14)
    ax3.legend(loc='upper right')
    ax3.grid(True, alpha=0.3)
    ax3.set_ylabel("Deviation %")
    
    # 4. Drawdown
    ax4 = axes
    ax4.fill_between(range(len(dd)), [-x for x in dd], 0, color='red', alpha=0.5)
    ax4.set_title(f"Drawdown (Max: {max_dd:.1f}%)", fontsize=14)
    ax4.set_ylabel("Drawdown %")
    ax4.set_xlabel("Days")
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('contrarian_oliver_pro.png', dpi=150)
    print("\n✅ Saved contrarian_oliver_pro.png")
    plt.show()
    
    return final, hodl, trades


if __name__ == "__main__":
    run_contrarian_oliver_pro()
