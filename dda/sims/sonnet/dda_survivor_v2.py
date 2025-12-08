"""
DDA PREDATOR v2.0 "THE SURVIVOR"
----------------------------------
Lessons learned from v1:
1. Don't fight the macro trend - use longer lookback for regime
2. Shorts are dangerous in crypto - use them sparingly or not at all
3. Hold winners, cut losers fast
4. Adapt position size to win rate

This version uses DDA the RIGHT way:
- Fast DDA derivative = Entry timing signal
- Slow DDA slope = Macro regime (20+ bars)
- Price vs Slow DDA = Position in trend
- Adaptive thresholds based on recent performance
"""
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from dataclasses import dataclass
import warnings

warnings.filterwarnings('ignore')

# =============================================================================
# DDA v7.0 ENGINE
# =============================================================================
@dataclass
class DDAConfig:
    P0: float = 0.70
    m: float = 0.30
    alpha: float = 0.001
    beta: float = 0.5
    derivative_boost: float = 0.6
    filter_alpha: float = 0.1
    k_min: float = 0.9
    k_max: float = 1.1

class DDA:
    def __init__(self, config: DDAConfig = None):
        self.c = config or DDAConfig()
        self.k = 1.0
        self.F_prev = 0.0
        self.I_prev = 0.0
        self.delta_filtered = 0.0
        self.initialized = False
        self.history = []
        
    def update(self, observation: float) -> tuple:
        if not self.initialized:
            self.F_prev = observation
            self.I_prev = observation
            self.initialized = True
            self.history.append(observation)
            return observation, 0.0, 1.0, 0.0
            
        delta_raw = observation - self.I_prev
        self.delta_filtered = (self.c.filter_alpha * delta_raw + 
                              (1 - self.c.filter_alpha) * self.delta_filtered)
        
        likelihood = observation + (self.c.derivative_boost * self.delta_filtered)
        prior = self.c.P0 * self.k * self.F_prev
        prediction = prior + self.c.m * likelihood
        
        error = observation - prediction
        adaptation = self.c.alpha * np.sign(error) * (np.abs(error) ** self.c.beta)
        self.k += adaptation
        self.k = np.clip(self.k, self.c.k_min, self.c.k_max)
        
        self.F_prev = prediction
        self.I_prev = observation
        self.history.append(prediction)
        
        return prediction, self.delta_filtered, self.k, error


# =============================================================================
# SURVIVOR STRATEGY
# =============================================================================
class DDASurvivorStrategy:
    """
    Philosophy:
    - LONG ONLY in crypto (too dangerous to short prolonged uptrends)
    - Use DDA slope for macro trend (20-bar lookback)
    - Enter on pullbacks to fast DDA in uptrends
    - Exit on momentum exhaustion or regime flip
    - Adaptive sizing based on recent win rate
    """
    
    def __init__(self, leverage=1.5, fee=0.001, allow_shorts=False):
        # Conservative fast DDA, very slow macro DDA
        self.fast_config = DDAConfig(P0=0.70, derivative_boost=0.6)  # ~10 bar
        self.macro_config = DDAConfig(P0=0.92, derivative_boost=0.3)  # ~30 bar
        
        self.dda_fast = DDA(self.fast_config)
        self.dda_macro = DDA(self.macro_config)
        
        self.leverage = leverage
        self.fee = fee
        self.allow_shorts = allow_shorts
        
        self.position = None
        self.cash = 1000.0
        self.initial_cash = 1000.0
        self.equity_curve = [self.cash]
        self.trades = []
        
        # Adaptive parameters
        self.base_position_size = 0.6
        self.recent_trades = []  # Track last 10 trades for adaptation
        
    def get_macro_trend(self, macro_history):
        """
        Determine trend by looking at macro DDA slope over 20 bars
        Returns: ('bull', 'bear', 'neutral'), slope_strength
        """
        if len(macro_history) < 25:
            return 'neutral', 0.0
        
        # Compare current vs 20 bars ago
        current = macro_history[-1]
        past = macro_history[-20]
        slope_pct = (current - past) / past * 100
        
        if slope_pct > 3.0:  # 3% rise over 20 bars
            return 'bull', min(slope_pct, 10.0)
        elif slope_pct < -3.0:  # 3% fall over 20 bars
            return 'bear', min(abs(slope_pct), 10.0)
        else:
            return 'neutral', abs(slope_pct)
    
    def adapt_position_size(self):
        """
        Reduce size after losses, increase after wins
        """
        if len(self.recent_trades) < 3:
            return self.base_position_size
        
        recent_pnls = [t['pnl'] for t in self.recent_trades[-10:]]
        win_rate = sum(1 for p in recent_pnls if p > 0) / len(recent_pnls)
        
        # Scale from 0.3x to 1.0x based on win rate
        multiplier = 0.3 + (win_rate * 0.7)
        
        return self.base_position_size * multiplier
    
    def run(self, df):
        prices = df['Close'].values
        
        print("\n" + "="*80)
        print("DDA SURVIVOR v2.0 - ADAPTIVE TREND RIDING")
        print("="*80)
        print(f"  🎯 Strategy:    LONG ONLY + Macro Trend Filter")
        print(f"  🧠 DDA Fast:    Entry timing (P0=0.70)")
        print(f"  📊 DDA Macro:   Trend regime (P0=0.92, 20-bar slope)")
        print(f"  💰 Leverage:    {self.leverage}x")
        print(f"  🛡️  Risk Mgmt:   Adaptive sizing + 6% stop")
        print("="*80 + "\n")
        
        for i in tqdm(range(len(prices)), desc="Trading"):
            price = float(prices[i])
            
            # Update DDAs
            fast_pred, fast_vel, fast_k, fast_err = self.dda_fast.update(price)
            macro_pred, macro_vel, macro_k, macro_err = self.dda_macro.update(price)
            
            if i < 30:
                self.equity_curve.append(self.cash)
                continue
            
            # Macro trend
            trend, trend_strength = self.get_macro_trend(self.dda_macro.history)
            
            # Deviation from fast DDA
            fast_dev = (price - fast_pred) / fast_pred * 100
            
            # Current P&L
            current_pnl_pct = 0
            if self.position:
                if self.position['type'] == 'long':
                    current_pnl_pct = (price - self.position['entry']) / self.position['entry'] * 100
                else:
                    current_pnl_pct = (self.position['entry'] - price) / self.position['entry'] * 100
            
            # ================================================================
            # ENTRIES
            # ================================================================
            if self.position is None:
                # LONG: Pullback in uptrend
                if (trend == 'bull' and 
                    fast_dev < -2.5 and  # Price below fast DDA
                    fast_vel > 0):       # But velocity is turning up
                    
                    size_mult = self.adapt_position_size()
                    invest_amount = self.cash * size_mult * self.leverage
                    
                    if invest_amount > 10:
                        size = invest_amount / price
                        entry_fee = invest_amount * self.fee
                        self.cash -= (invest_amount / self.leverage) + entry_fee
                        
                        self.position = {
                            'type': 'long',
                            'entry': price,
                            'entry_day': i,
                            'size': size,
                            'invested': invest_amount / self.leverage
                        }
                        
                        self.trades.append({
                            'day': i,
                            'action': 'LONG ENTRY',
                            'price': price,
                            'trend': trend,
                            'fast_dev': fast_dev,
                            'fast_vel': fast_vel
                        })
                
                # SHORT: Rally in downtrend (only if allowed)
                elif (self.allow_shorts and
                      trend == 'bear' and
                      fast_dev > 2.5 and
                      fast_vel < 0):
                    
                    size_mult = self.adapt_position_size() * 0.5  # Half size for shorts
                    invest_amount = self.cash * size_mult * self.leverage
                    
                    if invest_amount > 10:
                        size = invest_amount / price
                        entry_fee = invest_amount * self.fee
                        self.cash -= (invest_amount / self.leverage) + entry_fee
                        
                        self.position = {
                            'type': 'short',
                            'entry': price,
                            'entry_day': i,
                            'size': size,
                            'invested': invest_amount / self.leverage
                        }
                        
                        self.trades.append({
                            'day': i,
                            'action': 'SHORT ENTRY',
                            'price': price,
                            'trend': trend,
                            'fast_dev': fast_dev,
                            'fast_vel': fast_vel
                        })
            
            # ================================================================
            # EXITS
            # ================================================================
            elif self.position:
                exit_signal = False
                exit_reason = ""
                
                hold_time = i - self.position['entry_day']
                
                if self.position['type'] == 'long':
                    # Profit target: Price extends 4% above fast DDA
                    if fast_dev > 4.0:
                        exit_signal = True
                        exit_reason = "PROFIT TARGET"
                    
                    # Trend reversal
                    elif trend == 'bear' and hold_time > 5:
                        exit_signal = True
                        exit_reason = "TREND FLIP"
                    
                    # Stop loss: -6% (tighter than before)
                    elif current_pnl_pct < -6.0:
                        exit_signal = True
                        exit_reason = "STOP LOSS"
                    
                    # Time-based: Close after 100 bars regardless
                    elif hold_time > 100:
                        exit_signal = True
                        exit_reason = "TIME STOP"
                
                else:  # Short
                    if fast_dev < -4.0:
                        exit_signal = True
                        exit_reason = "PROFIT TARGET"
                    elif trend == 'bull' and hold_time > 5:
                        exit_signal = True
                        exit_reason = "TREND FLIP"
                    elif current_pnl_pct < -6.0:
                        exit_signal = True
                        exit_reason = "STOP LOSS"
                    elif hold_time > 50:  # Shorter time limit for shorts
                        exit_signal = True
                        exit_reason = "TIME STOP"
                
                if exit_signal:
                    if self.position['type'] == 'long':
                        pnl = (price - self.position['entry']) * self.position['size']
                    else:
                        pnl = (self.position['entry'] - price) * self.position['size']
                    
                    exit_fee = self.position['size'] * price * self.fee
                    self.cash += self.position['invested'] + pnl - exit_fee
                    
                    pnl_pct = current_pnl_pct * self.leverage
                    
                    self.trades.append({
                        'day': i,
                        'action': f"{self.position['type'].upper()} EXIT",
                        'price': price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'reason': exit_reason,
                        'hold_time': hold_time
                    })
                    
                    # Track for adaptation
                    self.recent_trades.append({'pnl': pnl, 'pnl_pct': pnl_pct})
                    
                    self.position = None
            
            # Mark to market
            equity = self.cash
            if self.position:
                if self.position['type'] == 'long':
                    unrealized = (price - self.position['entry']) * self.position['size']
                else:
                    unrealized = (self.position['entry'] - price) * self.position['size']
                equity += self.position['invested'] + unrealized
            
            self.equity_curve.append(equity)
            
            if equity <= 0:
                print(f"\n💀 LIQUIDATED at day {i}")
                break
        
        # Close final position
        if self.position:
            price = float(prices[-1])
            if self.position['type'] == 'long':
                pnl = (price - self.position['entry']) * self.position['size']
            else:
                pnl = (self.position['entry'] - price) * self.position['size']
            
            self.cash += self.position['invested'] + pnl
            self.equity_curve[-1] = self.cash
        
        return self.analyze_results(prices)
    
    def analyze_results(self, prices):
        final_equity = self.equity_curve[-1]
        hodl_value = (self.initial_cash / prices[0]) * prices[-1]
        
        print("\n" + "="*80)
        print("PERFORMANCE SUMMARY")
        print("="*80)
        print(f"  Initial:    ${self.initial_cash:,.2f}")
        print(f"  Final:      ${final_equity:,.2f}  ({(final_equity/self.initial_cash-1)*100:+.1f}%)")
        print(f"  HODL:       ${hodl_value:,.2f}  ({(hodl_value/self.initial_cash-1)*100:+.1f}%)")
        
        if final_equity > hodl_value:
            print(f"\n  🏆 BEAT HODL BY {(final_equity-hodl_value)/hodl_value*100:+.1f}%")
        elif final_equity > self.initial_cash:
            print(f"\n  📈 Profit but HODL wins by {(hodl_value-final_equity)/hodl_value*100:.1f}%")
        else:
            print(f"\n  📉 Loss: ${self.initial_cash-final_equity:,.2f}")
        
        exits = [t for t in self.trades if 'EXIT' in t['action']]
        if exits:
            wins = sum(1 for t in exits if t['pnl'] > 0)
            print(f"\n  Trades:     {len(self.trades)}")
            print(f"  Win Rate:   {wins}/{len(exits)} = {wins/len(exits)*100:.0f}%")
            
            if wins > 0:
                avg_win = np.mean([t['pnl_pct'] for t in exits if t['pnl'] > 0])
                print(f"  Avg Win:    {avg_win:+.1f}%")
            
            losses = len(exits) - wins
            if losses > 0:
                avg_loss = np.mean([t['pnl_pct'] for t in exits if t['pnl'] < 0])
                print(f"  Avg Loss:   {avg_loss:+.1f}%")
        
        equity_array = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity_array)
        dd = (peak - equity_array) / peak * 100
        print(f"\n  Max DD:     {np.max(dd):.1f}%")
        
        print("\n" + "="*80)
        print("TRADE LOG (Last 15)")
        print("="*80)
        for t in self.trades[-15:]:
            if 'ENTRY' in t['action']:
                print(f"  Day {t['day']:3d} | {t['action']:12s} @ ${t['price']:>10,.2f} | {t['trend']:7s} | Dev:{t['fast_dev']:>+5.1f}% Vel:{t['fast_vel']:>+6.1f}")
            else:
                emoji = "✅" if t['pnl'] > 0 else "❌"
                print(f"  Day {t['day']:3d} | {emoji} {t['action']:12s} @ ${t['price']:>10,.2f} | {t['reason']:15s} | PnL:{t['pnl_pct']:>+6.1f}% ({t['hold_time']:2d}d)")
        print("="*80)
        
        return {'final': final_equity, 'hodl': hodl_value, 'trades': self.trades}


def run_survivor():
    print("📡 Loading BTC data...")
    try:
        df = yf.download("BTC-USD", period="2y", interval="1d", progress=False)
        if len(df) == 0:
            raise ValueError("Empty")
    except:
        print("⚠️  Download failed, using synthetic data...")
        np.random.seed(42)
        days = 730
        base = np.linspace(40000, 100000, days)
        cycle = 15000 * np.sin(np.linspace(0, 4*np.pi, days))
        noise = np.random.normal(0, 2000, days).cumsum()
        prices = np.maximum(base + cycle + noise, 30000)
        
        df = pd.DataFrame({
            'Close': prices,
            'High': prices * 1.02,
            'Low': prices * 0.98
        })
    
    print(f"✅ {len(df)} candles loaded\n")
    
    strategy = DDASurvivorStrategy(leverage=1.5, fee=0.001, allow_shorts=False)
    results = strategy.run(df)
    
    # Plot
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    
    prices = df['Close'].values
    
    # Equity
    ax1 = axes[0]
    scale = strategy.initial_cash / prices[0]
    hodl = prices * scale
    
    ax1.plot(strategy.equity_curve, 'b-', linewidth=2.5, label=f"DDA Survivor ${results['final']:,.0f}")
    ax1.plot(hodl, 'gray', linewidth=2, alpha=0.6, label=f"HODL ${results['hodl']:,.0f}")
    ax1.set_title("DDA Survivor v2.0 Results", fontsize=16, fontweight='bold')
    ax1.legend(fontsize=12)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylabel("Portfolio Value ($)")
    
    # DDAs
    ax2 = axes[1]
    fast_dda = DDA(strategy.fast_config)
    macro_dda = DDA(strategy.macro_config)
    
    fast_line = [fast_dda.update(float(p))[0] for p in prices]
    macro_line = [macro_dda.update(float(p))[0] for p in prices]
    
    ax2.plot(prices, 'gray', alpha=0.4, linewidth=1, label='Price')
    ax2.plot(fast_line, 'b-', linewidth=1.5, label='Fast DDA (entries)')
    ax2.plot(macro_line, 'r-', linewidth=2, label='Macro DDA (trend)')
    ax2.set_title("DDA Tracking", fontsize=16, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylabel("BTC Price ($)")
    ax2.set_xlabel("Days")
    
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/dda_survivor_v2.png', dpi=150, bbox_inches='tight')
    print("\n✅ Chart saved!\n")
    plt.show()


if __name__ == "__main__":
    run_survivor()
