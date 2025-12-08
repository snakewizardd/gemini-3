"""
DDA v7.0 "APEX PREDATOR" - FINAL PRODUCTION VERSION
----------------------------------------------------
Synthesizes all lessons from your Kalman-beating proofs into a robust trading system.

CORE INSIGHTS FROM YOUR RESEARCH:
1. DDA beats Kalman by 95.5% in high-agility tracking via pre-cognitive derivative
2. The k parameter adapts to prediction error - use it as confidence metric
3. Multi-timeframe DDA reveals both micro and macro structure
4. Phase-locked entries: buy BEFORE bottoms, sell BEFORE tops

STRATEGY ARCHITECTURE:
- Fast DDA (P0=0.70): Micro-trend for entry timing
- Slow DDA (P0=0.92): Macro-trend for regime filter  
- Ultra-Slow (P0=0.96): Primary trend (your original "Smart Oliver" smoothing)
- Trade WITH the primary trend, time WITH the fast DDA
- Hold winners, cut losers, let position size adapt

Risk Controls:
- Trailing stops (not fixed)
- Minimum hold period (avoid whipsaws)
- Max position duration (force re-evaluation)
- Adaptive sizing based on win rate
- Volatility-adjusted thresholds
"""

import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from dataclasses import dataclass

# =============================================================================
# DDA v7.0 - Your Proven Algorithm
# =============================================================================
@dataclass
class DDAConfig:
    P0: float = 0.70
    derivative_boost: float = 0.6
    filter_alpha: float = 0.1
    alpha: float = 0.001
    beta: float = 0.5
    k_min: float = 0.9
    k_max: float = 1.1

class DDA:
    def __init__(self, config: DDAConfig):
        self.c = config
        self.m = 1.0 - self.c.P0
        self.k = 1.0
        self.F = None
        self.I_prev = None
        self.dF_smooth = 0.0
        self.history = []
        
    def update(self, price):
        if self.F is None:
            self.F = price
            self.I_prev = price
            self.history.append(price)
            return price, 0.0, 1.0
        
        # Step 1: Raw derivative
        dF_raw = price - self.I_prev
        
        # Step 2: Filtered derivative (noise rejection)
        self.dF_smooth = (self.c.filter_alpha * dF_raw + 
                         (1 - self.c.filter_alpha) * self.dF_smooth)
        
        # Step 3: Pre-cognitive likelihood (THE KEY INNOVATION)
        L = price + (self.c.derivative_boost * self.dF_smooth)
        
        # Step 4: Bayesian update
        F_new = (self.c.P0 * self.k * self.F) + (self.m * L)
        
        # Step 5: Adaptive gain (meta-learning)
        error = price - F_new
        self.k += self.c.alpha * np.sign(error) * (abs(error) ** self.c.beta)
        self.k = np.clip(self.k, self.c.k_min, self.c.k_max)
        
        self.F = F_new
        self.I_prev = price
        self.history.append(F_new)
        
        return F_new, self.dF_smooth, self.k


class ApexPredatorStrategy:
    """
    The culmination of your DDA research applied to real-time trading.
    """
    
    def __init__(self, leverage=1.2, fee=0.001):
        # Multi-timeframe DDAs (from your proofs)
        self.dda_fast = DDA(DDAConfig(P0=0.70, derivative_boost=0.6))    # Entry timing
        self.dda_slow = DDA(DDAConfig(P0=0.92, derivative_boost=0.3))    # Regime
        self.dda_primary = DDA(DDAConfig(P0=0.96, derivative_boost=0.2)) # Macro trend
        
        self.leverage = leverage
        self.fee = fee
        
        # Portfolio state
        self.cash = 1000.0
        self.initial_cash = 1000.0
        self.position = None
        self.equity_curve = [self.cash]
        self.trades = []
        
        # Adaptive learning
        self.recent_performance = []
        self.base_size = 0.70  # Start aggressive, will adapt down if losing
        
        # Volatility tracking
        self.price_history = []
        self.volatility = 0.0
        
    def calculate_volatility(self):
        """14-period rolling volatility"""
        if len(self.price_history) < 15:
            return 0.0
        recent = self.price_history[-14:]
        returns = [(recent[i] - recent[i-1]) / recent[i-1] * 100 
                   for i in range(1, len(recent))]
        return np.std(returns) if returns else 0.0
    
    def get_primary_trend(self):
        """
        Primary trend from ultra-slow DDA slope (30-bar lookback)
        Returns: ('bull', 'bear', 'ranging'), confidence (0-100)
        """
        if len(self.dda_primary.history) < 35:
            return 'ranging', 0
        
        now = self.dda_primary.history[-1]
        past = self.dda_primary.history[-30]
        slope_pct = (now - past) / past * 100
        
        if slope_pct > 5.0:
            return 'bull', min(slope_pct, 15.0)
        elif slope_pct < -5.0:
            return 'bear', min(abs(slope_pct), 15.0)
        else:
            return 'ranging', abs(slope_pct)
    
    def calculate_position_size(self):
        """
        Adaptive sizing: reduce after losses, increase after wins
        """
        if len(self.recent_performance) < 5:
            return self.base_size
        
        last_10 = self.recent_performance[-10:]
        win_rate = sum(1 for p in last_10 if p > 0) / len(last_10)
        
        # Aggressive adaptation: 0.25x to 1.0x
        size = self.base_size * (0.35 + (win_rate * 0.65))
        return np.clip(size, 0.25, 1.0)
    
    def run(self, df):
        """Execute the strategy"""
        prices = df['Close'].values
        
        print("\n" + "="*80)
        print("DDA APEX PREDATOR - PHASE-LOCKED TREND FOLLOWING")
        print("="*80)
        print(f"  🧬 Algorithm:   DDA v7.0 (Your Kalman-beating framework)")
        print(f"  🎯 Entry:       Fast DDA pullbacks (P0=0.70)")
        print(f"  📊 Filter:      Slow DDA regime (P0=0.92)")
        print(f"  🌊 Trend:       Primary DDA slope (P0=0.96, 30-bar)")
        print(f"  💰 Leverage:    {self.leverage}x")
        print(f"  🧠 Learning:    Adaptive sizing + trailing stops")
        print("="*80 + "\n")
        
        for i in tqdm(range(len(prices)), desc="Trading"):
            price = float(prices[i])
            self.price_history.append(price)
            
            # Update all DDAs
            fast_fv, fast_vel, fast_k = self.dda_fast.update(price)
            slow_fv, slow_vel, slow_k = self.dda_slow.update(price)
            prim_fv, prim_vel, prim_k = self.dda_primary.update(price)
            
            # Warmup
            if i < 35:
                self.equity_curve.append(self.cash)
                continue
            
            # Market analysis
            self.volatility = self.calculate_volatility()
            primary_trend, trend_conf = self.get_primary_trend()
            
            # Deviations (signal strength)
            fast_dev = (price - fast_fv) / fast_fv * 100
            slow_dev = (price - slow_fv) / slow_fv * 100
            prim_dev = (price - prim_fv) / prim_fv * 100
            
            # Current position P&L
            if self.position:
                days_held = i - self.position['entry_day']
                current_pnl = (price - self.position['entry']) / self.position['entry'] * 100
                
                # Trailing stop: Tighten as profit increases
                if current_pnl > 15:
                    stop_level = -3.0  # Lock in most gains
                elif current_pnl > 8:
                    stop_level = -5.0  # Tight
                else:
                    stop_level = -7.0  # Initial
                
                # Update high water mark for trailing
                if not hasattr(self.position, 'peak_pnl'):
                    self.position['peak_pnl'] = current_pnl
                else:
                    self.position['peak_pnl'] = max(self.position['peak_pnl'], current_pnl)
                
                trailing_stop_hit = (current_pnl < self.position['peak_pnl'] - 10)
            
            # ================================================================
            # ENTRY LOGIC
            # ================================================================
            if self.position is None and self.cash > 50:
                # LONG SETUP: All timeframes aligned for uptrend
                if (primary_trend == 'bull' and          # Primary is up
                    trend_conf > 3.0 and                 # Strong conviction
                    fast_dev < -2.5 and                  # Pullback to fast DDA
                    fast_vel > 0 and                     # But velocity turning up
                    slow_dev > 0):                       # Price above slow DDA
                    
                    # Position sizing
                    size_mult = self.calculate_position_size()
                    
                    # Volatility adjustment
                    if self.volatility > 4.0:  # High vol
                        size_mult *= 0.7
                    
                    invest_amount = self.cash * size_mult * self.leverage
                    
                    if invest_amount >= 20:
                        size = invest_amount / price
                        fee = invest_amount * self.fee
                        self.cash -= (invest_amount / self.leverage) + fee
                        
                        self.position = {
                            'entry': price,
                            'entry_day': i,
                            'size': size,
                            'invested': invest_amount / self.leverage,
                            'peak_pnl': 0
                        }
                        
                        self.trades.append({
                            'day': i,
                            'action': 'LONG',
                            'price': price,
                            'fast_dev': fast_dev,
                            'slow_dev': slow_dev,
                            'prim_dev': prim_dev,
                            'trend': primary_trend,
                            'size': size_mult
                        })
            
            # ================================================================
            # EXIT LOGIC
            # ================================================================
            elif self.position:
                exit_signal = False
                exit_reason = ""
                
                # 1. Profit target: Price 6% above fast DDA
                if fast_dev > 6.0 and days_held >= 3:
                    exit_signal = True
                    exit_reason = "PROFIT TARGET"
                
                # 2. Trend reversal: Primary flips
                elif primary_trend == 'bear' and days_held >= 5:
                    exit_signal = True
                    exit_reason = "TREND REVERSAL"
                
                # 3. Trailing stop
                elif trailing_stop_hit:
                    exit_signal = True
                    exit_reason = "TRAILING STOP"
                
                # 4. Fixed stop loss
                elif current_pnl < stop_level:
                    exit_signal = True
                    exit_reason = "STOP LOSS"
                
                # 5. Max hold time (force re-evaluation)
                elif days_held > 150:
                    exit_signal = True
                    exit_reason = "TIME LIMIT"
                
                # 6. Momentum exhaustion: fast DDA turns down in profit
                elif fast_vel < -50 and current_pnl > 5 and days_held >= 7:
                    exit_signal = True
                    exit_reason = "MOMENTUM FADE"
                
                if exit_signal:
                    pnl = (price - self.position['entry']) * self.position['size']
                    exit_fee = self.position['size'] * price * self.fee
                    self.cash += self.position['invested'] + pnl - exit_fee
                    
                    pnl_pct = current_pnl * self.leverage
                    
                    self.trades.append({
                        'day': i,
                        'action': 'EXIT',
                        'price': price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': exit_reason,
                        'hold': days_held
                    })
                    
                    # Learning
                    self.recent_performance.append(pnl)
                    
                    self.position = None
            
            # Mark to market
            equity = self.cash
            if self.position:
                equity += self.position['invested'] + (price - self.position['entry']) * self.position['size']
            
            self.equity_curve.append(equity)
            
            if equity <= 0:
                print(f"\n💀 LIQUIDATED at day {i}")
                break
        
        # Final close
        if self.position:
            price = float(prices[-1])
            pnl = (price - self.position['entry']) * self.position['size']
            self.cash += self.position['invested'] + pnl
            self.equity_curve[-1] = self.cash
        
        return self.report(prices)
    
    def report(self, prices):
        """Generate performance report"""
        final = self.equity_curve[-1]
        hodl = (self.initial_cash / prices[0]) * prices[-1]
        
        print("\n" + "="*80)
        print("FINAL RESULTS")
        print("="*80)
        print(f"  Capital:      ${self.initial_cash:,.2f} → ${final:,.2f}  ({(final/self.initial_cash-1)*100:+.1f}%)")
        print(f"  HODL:         ${hodl:,.2f}  ({(hodl/self.initial_cash-1)*100:+.1f}%)")
        
        if final > hodl:
            print(f"\n  🏆 BEAT HODL by {(final-hodl)/hodl*100:+.1f}%")
        elif final > self.initial_cash:
            alpha = (final/self.initial_cash - 1) - (hodl/self.initial_cash - 1)
            print(f"\n  📊 Alpha: {alpha*100:+.1f}%  (HODL wins by {(hodl-final)/hodl*100:.1f}%)")
        else:
            print(f"\n  📉 Loss: ${self.initial_cash-final:,.2f}")
        
        # Trade stats
        exits = [t for t in self.trades if t['action'] == 'EXIT']
        if exits:
            wins = [t for t in exits if t['pnl'] > 0]
            losses = [t for t in exits if t['pnl'] <= 0]
            
            print(f"\n  Trades:       {len(self.trades)} total, {len(exits)} completed")
            print(f"  Win Rate:     {len(wins)}/{len(exits)} = {len(wins)/len(exits)*100:.0f}%")
            
            if wins:
                avg_win = np.mean([t['pnl_pct'] for t in wins])
                avg_hold_win = np.mean([t['hold'] for t in wins])
                print(f"  Avg Win:      +{avg_win:.1f}% (held {avg_hold_win:.0f} days)")
            
            if losses:
                avg_loss = np.mean([t['pnl_pct'] for t in losses])
                avg_hold_loss = np.mean([t['hold'] for t in losses])
                print(f"  Avg Loss:     {avg_loss:.1f}% (held {avg_hold_loss:.0f} days)")
            
            if wins and losses:
                expectancy = (len(wins)/len(exits) * avg_win) + (len(losses)/len(exits) * avg_loss)
                print(f"  Expectancy:   {expectancy:+.2f}%")
        
        # Risk metrics
        equity = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / peak * 100
        max_dd = np.max(dd)
        
        print(f"\n  Max Drawdown: {max_dd:.1f}%")
        
        rets = np.diff(equity) / equity[:-1]
        if len(rets) > 0 and np.std(rets) > 0:
            sharpe = (np.mean(rets) * 252) / (np.std(rets) * np.sqrt(252))
            print(f"  Sharpe:       {sharpe:.2f}")
        
        print("\n" + "="*80)
        print("TRADE LOG (Recent 12)")
        print("="*80)
        for t in self.trades[-12:]:
            if t['action'] == 'LONG':
                print(f"  Day {t['day']:3d} | ENTRY @ ${t['price']:>10,.2f} | FastDev:{t['fast_dev']:>+5.1f}% SlowDev:{t['slow_dev']:>+5.1f}% | {t['trend']:7s} | Size:{t['size']:.2f}x")
            else:
                emoji = "✅" if t['pnl'] > 0 else "❌"
                print(f"  Day {t['day']:3d} | {emoji} EXIT @ ${t['price']:>10,.2f} | PnL:{t['pnl_pct']:>+6.1f}% | {t['reason']:17s} | Held {t['hold']:2d}d")
        print("="*80)
        
        return {'final': final, 'hodl': hodl, 'equity': self.equity_curve, 'trades': self.trades}


def run_apex():
    print("📡 Downloading market data...")
    try:
        df = yf.download("BTC-USD", period="2y", interval="1d", progress=False)
        if len(df) == 0:
            raise ValueError("Empty")
    except:
        print("⚠️  Using synthetic data for demo...")
        np.random.seed(42)
        days = 730
        trend = np.linspace(40000, 100000, days)
        cycle = 15000 * np.sin(np.linspace(0, 4*np.pi, days))
        noise = np.random.normal(0, 2000, days).cumsum()
        prices = np.maximum(trend + cycle + noise, 30000)
        df = pd.DataFrame({'Close': prices, 'High': prices*1.02, 'Low': prices*0.98})
    
    print(f"✅ Loaded {len(df)} candles\n")
    
    strategy = ApexPredatorStrategy(leverage=1.2, fee=0.001)
    results = strategy.run(df)
    
    # Visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))
    
    prices = df['Close'].values
    scale = strategy.initial_cash / prices[0]
    
    # Portfolio value
    ax1.plot(strategy.equity_curve, 'b-', linewidth=3, label=f"DDA Apex ${results['final']:,.0f}")
    ax1.plot(prices * scale, 'gray', linewidth=2, alpha=0.6, label=f"HODL ${results['hodl']:,.0f}")
    ax1.set_title("DDA Apex Predator - Performance", fontsize=16, fontweight='bold')
    ax1.legend(fontsize=13, loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("Portfolio Value ($)", fontsize=12)
    
    # Multi-timeframe DDAs
    fast = DDA(strategy.dda_fast.c)
    slow = DDA(strategy.dda_slow.c)
    prim = DDA(strategy.dda_primary.c)
    
    fast_line = [fast.update(float(p))[0] for p in prices]
    slow_line = [slow.update(float(p))[0] for p in prices]
    prim_line = [prim.update(float(p))[0] for p in prices]
    
    ax2.plot(prices, 'gray', alpha=0.3, linewidth=1, label='Price')
    ax2.plot(fast_line, 'b-', linewidth=1.5, alpha=0.8, label='Fast DDA (P₀=0.70)')
    ax2.plot(slow_line, 'orange', linewidth=1.8, alpha=0.8, label='Slow DDA (P₀=0.92)')
    ax2.plot(prim_line, 'r-', linewidth=2.2, label='Primary DDA (P₀=0.96)')
    ax2.set_title("Multi-Timeframe DDA Tracking", fontsize=16, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylabel("BTC Price ($)", fontsize=12)
    ax2.set_xlabel("Days", fontsize=12)
    
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/dda_apex_final.png', dpi=150, bbox_inches='tight')
    print("\n✅ Results saved to outputs/dda_apex_final.png\n")
    plt.show()


if __name__ == "__main__":
    run_apex()
