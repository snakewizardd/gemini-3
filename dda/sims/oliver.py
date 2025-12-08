
"""
DDA v20.0 "OLIVER RIDER"
-------------------------
Anti-Martingale: Build positions on WINS, shrink on LOSSES
Uses DDA decision engine with ATR-based dynamic stops
"""
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import warnings

warnings.filterwarnings('ignore')


class SimpleDDA:
    """Dynamic Decision Average - your core engine"""
    def __init__(self, smoothing=0.95):
        self.P0 = smoothing
        self.F = None
        
    def update(self, price):
        if self.F is None:
            self.F = price
            return price
        self.F = self.P0 * self.F + (1 - self.P0) * price
        return self.F
    
    def reset(self):
        self.F = None


class OliverPositionManager:
    """
    Anti-Martingale Position Sizing
    - After WIN: Increase size by multiplier (build on strength)
    - After LOSS: Reset to base size (protect capital)
    """
    def __init__(self, base_risk=0.02, max_risk=0.08, win_multiplier=1.5):
        self.base_risk = base_risk      # 2% base risk per trade
        self.max_risk = max_risk        # 8% max risk (caps pyramiding)
        self.win_multiplier = win_multiplier  # 1.5x after each win
        self.current_risk = base_risk
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        
    def record_win(self):
        self.consecutive_wins += 1
        self.consecutive_losses = 0
        # Pyramid up after win
        self.current_risk = min(
            self.base_risk * (self.win_multiplier ** self.consecutive_wins),
            self.max_risk
        )
        
    def record_loss(self):
        self.consecutive_losses += 1
        self.consecutive_wins = 0
        # Reset to base after loss
        self.current_risk = self.base_risk
        
    def get_position_size(self, capital, entry_price, stop_price):
        """Calculate position size based on current risk level"""
        risk_amount = capital * self.current_risk
        stop_distance = abs(entry_price - stop_price)
        if stop_distance == 0:
            return 0
        qty = risk_amount / stop_distance
        return qty
    
    def get_status(self):
        return f"Risk: {self.current_risk*100:.1f}% | Wins: {self.consecutive_wins} | Losses: {self.consecutive_losses}"


def calculate_atr(highs, lows, closes, period=14, index=None):
    """Average True Range for dynamic stops"""
    if index is None:
        index = len(closes) - 1
    if index < period:
        return (highs[index] - lows[index])
    
    tr_values = []
    for i in range(index - period + 1, index + 1):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i-1] if i > 0 else closes[i]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(tr)
    return np.mean(tr_values)


def run_oliver_rider():
    print("=" * 70)
    print("DDA v20.0 'OLIVER RIDER' - Anti-Martingale Pyramiding")
    print("=" * 70)
    print("\n📡 Downloading 2 YEARS of BTC-USD (1d)...")
    
    df = yf.download("BTC-USD", period="2y", interval="1d", progress=False)
    prices = df['Close'].values.flatten()
    highs = df['High'].values.flatten()
    lows = df['Low'].values.flatten()
    
    print(f"✅ Loaded {len(prices)} candles (daily)\n")
    
    # === DDA ENGINES (fine-tuned) ===
    trend_dda = SimpleDDA(smoothing=0.97)    # Trend detection
    signal_dda = SimpleDDA(smoothing=0.92)   # Entry signal (faster)
    momentum_dda = SimpleDDA(smoothing=0.85) # Momentum confirmation (fastest)
    
    # === OLIVER POSITION MANAGER ===
    oliver = OliverPositionManager(
        base_risk=0.02,       # Start with 2% risk
        max_risk=0.10,        # Max 10% after consecutive wins
        win_multiplier=1.6    # 1.6x size after each win
    )
    
    # === TRADING PARAMETERS ===
    starting_capital = 1000.0
    cash = starting_capital
    fee_rate = 0.001
    
    # ATR-based stops
    ATR_STOP_MULT = 2.5       # Stop at 2.5x ATR below entry
    ATR_TRAIL_MULT = 3.0      # Trail at 3.0x ATR from high
    TREND_BREAK_ATR = 2.0     # Exit if price drops 2x ATR below trend
    
    # Timing
    MIN_HOLD_DAYS = 7         # Reduced - let Oliver method handle sizing
    COOLDOWN_DAYS = 3         # Shorter cooldown
    WARMUP_PERIOD = 30
    
    # State
    in_market = False
    entry_price = 0
    stop_price = 0
    position_qty = 0
    highest_since_entry = 0
    days_in_trade = 0
    days_since_exit = 999
    
    equity = [cash]
    trade_log = []
    trades = 0
    
    print("📊 OLIVER METHOD RULES:")
    print(f"  🎯 Base Risk: {oliver.base_risk*100:.0f}% per trade")
    print(f"  📈 After WIN: Size x{oliver.win_multiplier} (max {oliver.max_risk*100:.0f}%)")
    print(f"  📉 After LOSS: Reset to {oliver.base_risk*100:.0f}%")
    print(f"  🛑 Stop: {ATR_STOP_MULT}x ATR | Trail: {ATR_TRAIL_MULT}x ATR")
    print(f"  ⏰ Min Hold: {MIN_HOLD_DAYS}d | Cooldown: {COOLDOWN_DAYS}d\n")
    
    for i in tqdm(range(len(prices)), desc="🚀 Oliver Riding"):
        price = float(prices[i])
        high = float(highs[i])
        low = float(lows[i])
        
        # Update DDAs
        trend = trend_dda.update(price)
        signal = signal_dda.update(price)
        momentum = momentum_dda.update(price)
        
        # Calculate ATR
        atr = calculate_atr(highs, lows, prices, period=14, index=i)
        
        # Warmup period
        if i < WARMUP_PERIOD:
            equity.append(cash)
            continue
        
        if not in_market:
            days_since_exit += 1
        
        # === ENTRY CONDITIONS ===
        uptrend = price > trend * 0.99           # Price near or above trend
        pullback_zone = low <= signal * 1.02     # Touched signal area
        momentum_up = momentum > signal          # Fast DDA above slow
        bouncing = price > signal                # Closed above signal
        volatility_ok = atr / price < 0.06       # Not too volatile (< 6%)
        
        # === POSITION MANAGEMENT ===
        if in_market:
            days_in_trade += 1
            highest_since_entry = max(highest_since_entry, high)
            
            # Dynamic trailing stop based on ATR
            trail_stop = highest_since_entry - (atr * ATR_TRAIL_MULT)
            current_stop = max(stop_price, trail_stop)  # Only moves up
            
            # Exit conditions
            trailing_hit = low <= current_stop
            trend_break = price < trend - (atr * TREND_BREAK_ATR)
            
            can_exit = days_in_trade >= MIN_HOLD_DAYS
            
            # Check for profit-taking (partial concept - we'll exit fully but record)
            profit_pct = (price - entry_price) / entry_price
            
            if can_exit and (trailing_hit or trend_break):
                # === EXIT ===
                exit_price = max(current_stop, low) if trailing_hit else price
                pnl = (exit_price - entry_price) * position_qty
                cash += pnl
                fee = abs(position_qty * exit_price * fee_rate)
                cash -= fee
                trades += 1
                
                # Record result for Oliver method
                if pnl > 0:
                    oliver.record_win()
                    emoji = "✅"
                else:
                    oliver.record_loss()
                    emoji = "❌"
                
                pct_gain = (pnl / (entry_price * position_qty)) * 100
                reason = "TRAIL STOP" if trailing_hit else "TREND BREAK"
                
                trade_log.append({
                    'day': i,
                    'action': 'SELL',
                    'price': exit_price,
                    'pnl': pnl,
                    'pct': pct_gain,
                    'reason': reason,
                    'held': days_in_trade,
                    'win': pnl > 0,
                    'oliver_status': oliver.get_status()
                })
                
                print(f"\n  Day {i:3d} | {emoji} SELL @ ${exit_price:,.0f} | PnL: ${pnl:+,.0f} ({pct_gain:+.1f}%) | {reason} | {oliver.get_status()}")
                
                # Reset state
                in_market = False
                entry_price = 0
                stop_price = 0
                position_qty = 0
                highest_since_entry = 0
                days_in_trade = 0
                days_since_exit = 0
        
        else:
            # === ENTRY ===
            if (uptrend and pullback_zone and bouncing and momentum_up and 
                volatility_ok and days_since_exit >= COOLDOWN_DAYS):
                
                entry_price = price
                stop_price = price - (atr * ATR_STOP_MULT)
                highest_since_entry = high
                
                # Oliver position sizing
                position_qty = oliver.get_position_size(cash, entry_price, stop_price)
                position_value = position_qty * entry_price
                
                # Pay entry fee
                fee = position_value * fee_rate
                cash -= fee
                
                in_market = True
                days_in_trade = 0
                trades += 1
                
                trade_log.append({
                    'day': i,
                    'action': 'BUY',
                    'price': entry_price,
                    'stop': stop_price,
                    'qty': position_qty,
                    'risk_pct': oliver.current_risk * 100,
                    'oliver_status': oliver.get_status()
                })
                
                print(f"\n  Day {i:3d} | 📈 BUY  @ ${price:,.0f} | Stop: ${stop_price:,.0f} | {oliver.get_status()}")
        
        # === MARK TO MARKET ===
        current_equity = cash
        if in_market:
            unrealized = (price - entry_price) * position_qty
            current_equity += unrealized
        
        equity.append(current_equity)
        
        # Circuit breaker
        if current_equity <= starting_capital * 0.3:
            print("\n💀 CIRCUIT BREAKER - 70% drawdown, stopping")
            break
    
    # === CLOSE OPEN POSITION ===
    if in_market:
        final_price = float(prices[-1])
        pnl = (final_price - entry_price) * position_qty
        cash += pnl
        trades += 1
        
        if pnl > 0:
            oliver.record_win()
            emoji = "✅"
        else:
            oliver.record_loss()
            emoji = "❌"
        
        pct_gain = (pnl / (entry_price * position_qty)) * 100
        trade_log.append({
            'day': len(prices)-1,
            'action': 'CLOSE',
            'price': final_price,
            'pnl': pnl,
            'pct': pct_gain,
            'reason': 'END OF DATA',
            'held': days_in_trade,
            'win': pnl > 0
        })
        
        print(f"\n  END     | {emoji} CLOSE @ ${final_price:,.0f} | PnL: ${pnl:+,.0f} ({pct_gain:+.1f}%) | END OF DATA")
        equity[-1] = cash
    
    # === RESULTS ===
    final = float(equity[-1])
    start_price = float(prices)
    end_price = float(prices[-1])
    hodl = (starting_capital / start_price) * end_price
    
    # Trade stats
    wins = sum(1 for t in trade_log if t.get('win', False))
    losses = sum(1 for t in trade_log if 'pnl' in t and not t.get('win', True))
    total_closed = wins + losses
    
    win_pnls = [t['pnl'] for t in trade_log if t.get('win', False) and 'pnl' in t]
    loss_pnls = [t['pnl'] for t in trade_log if 'pnl' in t and not t.get('win', True)]
    
    avg_win = np.mean(win_pnls) if win_pnls else 0
    avg_loss = np.mean(loss_pnls) if loss_pnls else 0
    
    print("\n" + "=" * 70)
    print("🏆 OLIVER RIDER RESULTS")
    print("=" * 70)
    print(f"  💵 Starting:      ${starting_capital:,.2f}")
    print(f"  💰 Final:         ${final:,.2f}")
    print(f"  📊 HODL:          ${hodl:,.2f}")
    print(f"  📈 Strategy:      {((final-starting_capital)/starting_capital)*100:+.1f}%")
    print(f"  📈 HODL:          {((hodl-starting_capital)/starting_capital)*100:+.1f}%")
    print(f"  🔄 Total Trades:  {trades}")
    
    if final > hodl:
        outperform = ((final - hodl) / hodl) * 100
        print(f"\n  🏆 OLIVER WINS! Beats HODL by {outperform:.1f}%")
    else:
        underperform = ((hodl - final) / hodl) * 100
        print(f"\n  📉 HODL wins by {underperform:.1f}%")
    
    print("\n📊 TRADE STATISTICS:")
    print("-" * 40)
    if total_closed > 0:
        print(f"  Win Rate:        {wins}/{total_closed} = {wins/total_closed*100:.0f}%")
        print(f"  Avg Win:         ${avg_win:+,.2f}")
        print(f"  Avg Loss:        ${avg_loss:+,.2f}")
        if avg_loss != 0:
            print(f"  Win/Loss Ratio:  {abs(avg_win/avg_loss):.2f}")
    
    # Max drawdown
    peak = np.maximum.accumulate(equity)
    drawdowns = [(peak[i] - equity[i]) / peak[i] * 100 if peak[i] > 0 else 0 
                 for i in range(len(equity))]
    max_dd = max(drawdowns)
    print(f"  Max Drawdown:    {max_dd:.1f}%")
    
    # Sharpe-like metric (simplified)
    returns = np.diff(equity) / equity[:-1]
    if len(returns) > 0 and np.std(returns) > 0:
        sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252)
        print(f"  Sharpe Ratio:    {sharpe:.2f}")
    
    # === DETAILED TRADE LOG ===
    print("\n📜 TRADE LOG:")
    print("-" * 90)
    for t in trade_log:
        if t['action'] == 'BUY':
            print(f"  Day {t['day']:3d} | 📈 BUY  @ ${t['price']:>10,.2f} | Stop: ${t['stop']:>10,.2f} | Risk: {t['risk_pct']:.1f}%")
        else:
            emoji = "✅" if t.get('win', False) else "❌"
            print(f"  Day {t['day']:3d} | {emoji} {t['action']:5s} @ ${t['price']:>10,.2f} | PnL: ${t['pnl']:>+9,.2f} ({t['pct']:>+6.1f}%) | {t['reason']} | Held {t['held']}d")
    print("-" * 90)
    
    # === PLOT ===
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # Equity curve
    ax1 = axes
    scale = starting_capital / start_price
    hodl_line = [float(prices[min(i, len(prices)-1)]) * scale for i in range(len(equity))]
    
    ax1.plot(equity, 'b-', label=f'Oliver Rider (${final:,.0f})', linewidth=2)
    ax1.plot(hodl_line, 'g--', alpha=0.6, label=f'HODL (${hodl:,.0f})', linewidth=2)
    ax1.fill_between(range(len(equity)), equity, hodl_line,
                     where=[e > h for e, h in zip(equity, hodl_line)],
                     color='blue', alpha=0.2, label='Outperforming')
    ax1.fill_between(range(len(equity)), equity, hodl_line,
                     where=[e <= h for e, h in zip(equity, hodl_line)],
                     color='red', alpha=0.2, label='Underperforming')
    
    # Mark trades
    for t in trade_log:
        day = t['day'] - WARMUP_PERIOD + 1
        if 0 <= day < len(equity):
            if t['action'] == 'BUY':
                ax1.axvline(x=day, color='green', alpha=0.3, linestyle='--')
            elif t.get('win', False):
                ax1.axvline(x=day, color='blue', alpha=0.3, linestyle='-')
            else:
                ax1.axvline(x=day, color='red', alpha=0.3, linestyle='-')
    
    ax1.set_title("Oliver Rider vs HODL (Anti-Martingale Pyramiding)", fontsize=14)
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("Portfolio Value ($)")
    
    # Drawdown
    ax2 = axes[1]()
    ax2.fill_between(range(len(drawdowns)), [-d for d in drawdowns], 0, color='red', alpha=0.5)
    ax2.set_title(f"Drawdown (Max: {max_dd:.1f}%)", fontsize=14)
    ax2.set_ylabel("Drawdown %")
    ax2.grid(True, alpha=0.3)
    
    # Position sizing over time (Oliver method visualization)
    ax3 = axes[2]()
    risk_history = []
    current_risk = oliver.base_risk
    for t in trade_log:
        if t['action'] == 'BUY':
            risk_history.append((t['day'], t['risk_pct']))
    
    if risk_history:
        days, risks = zip(*risk_history)
        ax3.bar(days, risks, color='purple', alpha=0.7, width=5)
        ax3.axhline(y=oliver.base_risk*100, color='gray', linestyle='--', label=f'Base Risk ({oliver.base_risk*100}%)')
        ax3.axhline(y=oliver.max_risk*100, color='red', linestyle='--', label=f'Max Risk ({oliver.max_risk*100}%)')
        ax3.set_title("Oliver Method: Position Risk % Per Trade", fontsize=14)
        ax3.set_ylabel("Risk %")
        ax3.set_xlabel("Day")
        ax3.legend()
        ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('oliver_rider.png', dpi=150)
    print("\n✅ Saved oliver_rider.png")
    plt.show()
    
    return final, hodl, trades, win_pnls, loss_pnls


if __name__ == "__main__":
    run_oliver_rider()
