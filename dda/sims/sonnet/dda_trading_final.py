"""
DDA TRADING STRATEGY - FINAL OPTIMIZED VERSION
-----------------------------------------------
Based on your proven DDA v7.0 framework that beats Kalman by 95.5%.

Key Learnings Applied:
1. Use MEDIUM-speed DDA (P0=0.88) for trend - not too fast, not too slow
2. 20-bar slope detection for regime (your "Smart Oliver" used P0=0.96 which is too laggy)
3. Trade less frequently but with higher conviction
4. Trailing stops + minimum hold periods
5. Adaptive position sizing

This is the "Goldilocks" version - not too aggressive, not too conservative.
"""

import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm

class DDA:
    """DDA v7.0 - Your proven algorithm"""
    def __init__(self, P0=0.88, boost=0.5, alpha_filter=0.1):
        self.P0 = P0
        self.m = 1.0 - P0
        self.boost = boost
        self.alpha_filter = alpha_filter
        
        self.F = None
        self.I_prev = None
        self.dF_smooth = 0.0
        self.k = 1.0
        self.history = []
        
    def update(self, price):
        if self.F is None:
            self.F = price
            self.I_prev = price
            self.history.append(price)
            return price, 0.0
        
        # Raw derivative
        dF_raw = price - self.I_prev
        
        # Smooth it (noise rejection)
        self.dF_smooth = self.alpha_filter * dF_raw + (1 - self.alpha_filter) * self.dF_smooth
        
        # Pre-cognitive projection
        L = price + self.boost * self.dF_smooth
        
        # Bayesian update
        self.F = self.P0 * self.k * self.F + self.m * L
        
        # Adapt k (meta-learning)
        error = price - self.F
        self.k += 0.001 * np.sign(error) * (abs(error) ** 0.5)
        self.k = np.clip(self.k, 0.9, 1.1)
        
        self.I_prev = price
        self.history.append(self.F)
        
        return self.F, self.dF_smooth


class DDATradingStrategy:
    """Optimized DDA trading strategy"""
    
    def __init__(self):
        # The magic number: P0=0.88 (12-day EMA equivalent but with DDA's advantages)
        self.dda = DDA(P0=0.88, boost=0.5)
        
        # Portfolio
        self.cash = 1000.0
        self.initial_cash = 1000.0
        self.position = None
        self.equity_curve = [self.cash]
        self.trades = []
        
        # Parameters
        self.leverage = 1.5
        self.fee = 0.001
        
        # Adaptive state
        self.recent_wins = []
        
    def get_trend(self):
        """20-bar slope of DDA"""
        if len(self.dda.history) < 25:
            return 'neutral', 0
        
        now = self.dda.history[-1]
        past = self.dda.history[-20]
        slope = (now - past) / past * 100
        
        if slope > 2.5:
            return 'bull', min(slope, 12.0)
        elif slope < -2.5:
            return 'bear', min(abs(slope), 12.0)
        return 'neutral', abs(slope)
    
    def run(self, df):
        prices = df['Close'].values
        
        print("\n" + "="*70)
        print("DDA TRADING STRATEGY - FINAL VERSION")
        print("="*70)
        print(f"  Algorithm:  DDA v7.0 (P₀=0.88, γ=0.5)")
        print(f"  Regime:     20-bar slope detection")
        print(f"  Leverage:   {self.leverage}x")
        print(f"  Entry:      Pullbacks in uptrends only")
        print(f"  Exits:      Trailing stop + trend reversal")
        print("="*70 + "\n")
        
        for i in tqdm(range(len(prices)), desc="Trading"):
            price = float(prices[i])
            
            # Update DDA
            fair_value, velocity = self.dda.update(price)
            
            if i < 25:
                self.equity_curve.append(self.cash)
                continue
            
            # Market state
            trend, trend_strength = self.get_trend()
            deviation = (price - fair_value) / fair_value * 100
            
            # Position state
            if self.position:
                days_held = i - self.position['day']
                pnl_pct = (price - self.position['entry']) / self.position['entry'] * 100
                
                # Track peak for trailing stop
                if 'peak' not in self.position:
                    self.position['peak'] = pnl_pct
                else:
                    self.position['peak'] = max(self.position['peak'], pnl_pct)
            
            # =================================================================
            # ENTRY
            # =================================================================
            if self.position is None and self.cash > 50:
                # LONG: Strong uptrend + pullback + velocity turning up
                if (trend == 'bull' and 
                    trend_strength > 3.0 and
                    deviation < -3.0 and
                    velocity > 0):
                    
                    # Adaptive sizing (reduce after losses)
                    if len(self.recent_wins) >= 3:
                        win_rate = sum(self.recent_wins[-5:]) / len(self.recent_wins[-5:])
                        size_mult = 0.4 + (win_rate * 0.5)  # 0.4x to 0.9x
                    else:
                        size_mult = 0.7
                    
                    invest = self.cash * size_mult * self.leverage
                    
                    if invest >= 20:
                        size = invest / price
                        fee = invest * self.fee
                        self.cash -= (invest / self.leverage) + fee
                        
                        self.position = {
                            'entry': price,
                            'day': i,
                            'size': size,
                            'invested': invest / self.leverage
                        }
                        
                        self.trades.append({
                            'day': i,
                            'action': 'LONG',
                            'price': price,
                            'dev': deviation,
                            'vel': velocity
                        })
            
            # =================================================================
            # EXIT
            # =================================================================
            elif self.position:
                exit_signal = False
                reason = ""
                
                # 1. Profit target (6% above fair value)
                if deviation > 6.0 and days_held >= 3:
                    exit_signal = True
                    reason = "TARGET"
                
                # 2. Trend reversal
                elif trend == 'bear' and days_held >= 5:
                    exit_signal = True
                    reason = "REVERSAL"
                
                # 3. Trailing stop (lock in gains)
                elif pnl_pct > 12 and pnl_pct < self.position['peak'] - 8:
                    exit_signal = True
                    reason = "TRAILING"
                
                # 4. Hard stop
                elif pnl_pct < -6.5:
                    exit_signal = True
                    reason = "STOP"
                
                # 5. Time stop
                elif days_held > 120:
                    exit_signal = True
                    reason = "TIME"
                
                # Execute
                if exit_signal:
                    pnl = (price - self.position['entry']) * self.position['size']
                    fee = self.position['size'] * price * self.fee
                    self.cash += self.position['invested'] + pnl - fee
                    
                    pnl_pct_lev = pnl_pct * self.leverage
                    
                    self.trades.append({
                        'day': i,
                        'action': 'EXIT',
                        'price': price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct_lev,
                        'reason': reason,
                        'hold': days_held
                    })
                    
                    self.recent_wins.append(1 if pnl > 0 else 0)
                    self.position = None
            
            # Mark to market
            equity = self.cash
            if self.position:
                equity += self.position['invested'] + (price - self.position['entry']) * self.position['size']
            
            self.equity_curve.append(equity)
            
            if equity <= 0:
                print(f"\n💀 LIQUIDATED at day {i}")
                break
        
        # Close final
        if self.position:
            price = float(prices[-1])
            pnl = (price - self.position['entry']) * self.position['size']
            self.cash += self.position['invested'] + pnl
            self.equity_curve[-1] = self.cash
        
        return self.report(prices)
    
    def report(self, prices):
        final = self.equity_curve[-1]
        hodl = (self.initial_cash / prices[0]) * prices[-1]
        
        print("\n" + "="*70)
        print("RESULTS")
        print("="*70)
        print(f"  Starting: ${self.initial_cash:,.2f}")
        print(f"  Final:    ${final:,.2f}  ({(final/self.initial_cash-1)*100:+.1f}%)")
        print(f"  HODL:     ${hodl:,.2f}  ({(hodl/self.initial_cash-1)*100:+.1f}%)")
        
        if final > hodl:
            print(f"\n  🏆 BEAT HODL by {(final-hodl)/hodl*100:+.1f}%!")
        elif final > self.initial_cash:
            print(f"\n  ✅ Profitable (HODL outperformed by {(hodl-final)/hodl*100:.1f}%)")
        else:
            print(f"\n  ❌ Loss: ${self.initial_cash-final:,.2f}")
        
        exits = [t for t in self.trades if t['action'] == 'EXIT']
        if exits:
            wins = [t for t in exits if t['pnl'] > 0]
            print(f"\n  Trades: {len(exits)} completed")
            print(f"  Wins:   {len(wins)}/{len(exits)} ({len(wins)/len(exits)*100:.0f}%)")
            
            if wins:
                avg_win = np.mean([t['pnl_pct'] for t in wins])
                print(f"  Avg Win:  +{avg_win:.1f}%")
            
            if len(wins) < len(exits):
                avg_loss = np.mean([t['pnl_pct'] for t in exits if t['pnl'] <= 0])
                print(f"  Avg Loss: {avg_loss:.1f}%")
        
        equity = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / peak * 100
        print(f"\n  Max DD:   {np.max(dd):.1f}%")
        
        print("\n" + "="*70)
        print("RECENT TRADES")
        print("="*70)
        for t in self.trades[-10:]:
            if t['action'] == 'LONG':
                print(f"  Day {t['day']:3d} | ENTRY ${t['price']:>10,.2f} | Dev:{t['dev']:>+5.1f}% Vel:{t['vel']:>+6.1f}")
            else:
                e = "✅" if t['pnl'] > 0 else "❌"
                print(f"  Day {t['day']:3d} | {e} EXIT ${t['price']:>10,.2f} | {t['reason']:8s} | {t['pnl_pct']:>+6.1f}% ({t['hold']:2d}d)")
        print("="*70)
        
        return {'final': final, 'hodl': hodl}


if __name__ == "__main__":
    print("📡 Loading data...")
    try:
        df = yf.download("BTC-USD", period="2y", interval="1d", progress=False)
        if len(df) == 0:
            raise ValueError()
    except:
        print("⚠️  Network issue, using synthetic BTC data...")
        np.random.seed(42)
        days = 730
        trend = np.linspace(40000, 100000, days)
        cycle = 15000 * np.sin(np.linspace(0, 4*np.pi, days))
        noise = np.random.normal(0, 2000, days).cumsum()
        prices = np.maximum(trend + cycle + noise, 30000)
        df = pd.DataFrame({'Close': prices})
    
    print(f"✅ Loaded {len(df)} candles\n")
    
    strategy = DDATradingStrategy()
    results = strategy.run(df)
    
    # Quick plot
    fig, ax = plt.subplots(figsize=(14, 7))
    
    prices = df['Close'].values
    scale = strategy.initial_cash / prices[0]
    
    ax.plot(strategy.equity_curve, 'b-', linewidth=2.5, label=f"DDA Strategy ${results['final']:,.0f}")
    ax.plot(prices * scale, 'gray', linewidth=2, alpha=0.6, label=f"HODL ${results['hodl']:,.0f}")
    ax.set_title("DDA v7.0 Trading Strategy - Final Results", fontsize=15, fontweight='bold')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.set_ylabel("Portfolio Value ($)", fontsize=12)
    ax.set_xlabel("Days", fontsize=12)
    
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/dda_trading_final.png', dpi=150)
    print("\n✅ Chart saved to outputs/dda_trading_final.png\n")
    plt.show()
