import ccxt
import time
import numpy as np
from datetime import datetime
import warnings
import os
import sys

warnings.filterwarnings('ignore')

# ============================================================================
# RICH VISUALS SETUP
# ============================================================================
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install rich for visuals: pip install rich")

# ============================================================================
# ASCII CHART GENERATOR
# ============================================================================
def ascii_chart(data, width=60, height=10, title=""):
    if len(data) < 2: return ""
    
    # Sampling
    if len(data) > width:
        step = len(data) // width
        data = data[::step][:width]

    min_val, max_val = min(data), max(data)
    range_val = max_val - min_val or 1
    
    # Normalize
    normalized = [(v - min_val) / range_val * (height - 1) for v in data]
    
    # Build Grid
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    
    for col, y in enumerate(normalized):
        row = int(round(height - 1 - y))
        # Color based on trend
        char = "█" if col > 0 and data[col] >= data[col-1] else "░"
        if 0 <= row < height:
            grid[row][col] = char
            
    # Render
    lines = [f"│ {''.join(row)} │" for row in grid]
    
    # Border & Axis
    top = f"┌{'─' * (width + 2)}┐"
    bot = f"└{'─' * (width + 2)}┘"
    
    # Add labels
    lines[0] += f" ${max_val:,.0f}"
    lines[-1] += f" ${min_val:,.0f}"
    
    return f"\n{title}\n{top}\n" + "\n".join(lines) + f"\n{bot}"

# ============================================================================
# DDA BRAIN
# ============================================================================
class DDAScalperOptimized:
    def __init__(self, saccade_mult=4.0):
        self.P0_stable = 0.98; self.P0_react = 0.0
        self.saccade_thresh = saccade_mult
        self.k = 1.0; self.F_prev = None; self.price_history = []
        self.volatility = 0.0
        
    def update(self, price):
        self.price_history.append(price)
        if len(self.price_history) < 20:
            self.F_prev = price
            return "WAIT", price, 0.0
        if len(self.price_history) > 100: self.price_history.pop(0)

        recent = self.price_history[-20:]
        self.volatility = np.std(recent) or 0.01

        diff = price - self.F_prev
        error = abs(diff)
        signal = "HOLD"
        
        if error > (self.saccade_thresh * self.volatility):
            effective_P0 = self.P0_react; effective_m = 1.0
            signal = "LONG_ENTRY" if diff > 0 else "SHORT_ENTRY"
        else:
            effective_P0 = self.P0_stable; effective_m = 1.0 - effective_P0
            if price < self.F_prev: signal = "LONG_EXIT"
            if price > self.F_prev: signal = "SHORT_EXIT"

        prior = effective_P0 * self.k * self.F_prev
        delta = price - self.price_history[-2]
        boost = 0.6 * delta 
        F = prior + (effective_m * (price + boost))
        
        # Adapt
        if "ENTRY" not in signal:
            err = price - F
            self.k += 0.001 * np.sign(err) * (abs(err)**0.5)
            self.k = np.clip(self.k, 0.9, 1.1)
        else: self.k = 1.0
            
        self.F_prev = F
        return signal, F, error

# ============================================================================
# PORTFOLIO
# ============================================================================
class PaperPortfolio:
    def __init__(self, cash=1000.0, leverage=50):
        self.cash = cash; self.leverage = leverage
        self.position = None; self.trades = []
        self.balance_history = [cash]
        
    def execute(self, signal, price, dt):
        if not self.position:
            if "ENTRY" in signal:
                direction = "LONG" if "LONG" in signal else "SHORT"
                margin = self.cash; size = (margin * self.leverage) / price
                fee = (margin * self.leverage) * 0.0005; self.cash -= fee
                self.position = {'type': direction, 'entry': price, 'size': size}
                return f"🚀 OPEN {direction}"
        else:
            close_long = (self.position['type'] == "LONG" and ("SHORT" in signal or "EXIT" in signal))
            close_short = (self.position['type'] == "SHORT" and ("LONG" in signal or "EXIT" in signal))
            
            if close_long or close_short:
                entry = self.position['entry']; size = self.position['size']
                pnl = (price - entry) * size if self.position['type'] == "LONG" else (entry - price) * size
                self.cash += pnl
                fee = (size * price) * 0.0005; self.cash -= fee
                
                self.trades.append({'pnl': pnl, 'dt': dt})
                self.position = None
                return f"💰 CLOSE | PnL: ${pnl:.2f}"
                
        self.balance_history.append(self.cash)
        return None

# ============================================================================
# REPLAY ENGINE
# ============================================================================
def run_replay():
    console = Console()
    console.clear()
    
    # 1. Fetch Data
    with Progress(SpinnerColumn(), TextColumn("[bold blue]Downloading 1000 Candles...")) as progress:
        task = progress.add_task("fetch", total=None)
        exchange = ccxt.kraken()
        # Fetch 2 batches to get ~16 hours
        candles = exchange.fetch_ohlcv('BTC/USDT', '1m', limit=720)
        older = exchange.fetch_ohlcv('BTC/USDT', '1m', since=candles[0][0] - (720*60*1000), limit=720)
        all_candles = older + candles
    
    # 2. Setup
    bot = DDAScalperOptimized()
    portfolio = PaperPortfolio()
    prices = []
    
    console.print(f"[bold green]✅ Loaded {len(all_candles)} candles. Starting Replay...[/bold green]")
    time.sleep(1)
    
    # 3. Loop
    for i, candle in enumerate(all_candles):
        ts = candle[0]
        price = candle[4]
        dt = datetime.fromtimestamp(ts/1000).strftime('%H:%M')
        prices.append(price)
        
        # Run Logic
        sig, val, err = bot.update(price)
        action_msg = portfolio.execute(sig, price, dt)
        
        # RENDER FRAME (Every 5th candle to speed up replay)
        if i % 5 == 0 or action_msg:
            console.clear()
            
            # Header
            header = f"""
[bold white]DDA HISTORICAL REPLAY[/bold white]
[dim]{dt}[/dim] | Price: [cyan]${price:,.2f}[/cyan] | DDA: [blue]${val:,.2f}[/blue]
Position: [yellow]{portfolio.position['type'] if portfolio.position else 'FLAT'}[/yellow]
Balance: [green]${portfolio.cash:,.2f}[/green] | ROI: [bold]{((portfolio.cash-1000)/1000)*100:+.2f}%[/bold]
            """
            console.print(header)
            
            # Chart
            console.print(ascii_chart(prices[-60:], title="BTC/USDT (1m)"))
            
            # Trade Log
            if portfolio.trades:
                last_trade = portfolio.trades[-1]
                color = "green" if last_trade['pnl'] > 0 else "red"
                console.print(f"Last Trade: [{color}]${last_trade['pnl']:+.2f}[/{color}]")
            
            # Action Log
            if action_msg:
                console.print(f"\n[bold yellow]⚡ {action_msg}[/bold yellow]")
                time.sleep(0.5) # Pause on action so you can see it
            
            time.sleep(0.01) # Fast forward speed

    # Final Stats
    console.print("\n[bold]🏁 REPLAY COMPLETE[/bold]")
    console.print(f"Final Balance: ${portfolio.cash:,.2f}")

if __name__ == "__main__":
    run_replay()