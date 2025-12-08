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
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Install rich for fancy visuals: pip install rich")
    print("   Running in basic mode...\n")

# ============================================================================
# ASCII CHART GENERATOR (no deps needed)
# ============================================================================

def ascii_chart(data, width=60, height=12, title=""):
    """Generate ASCII price chart"""
    if len(data) < 2:
        return "Not enough data for chart"

    # sample data to fit width
    if len(data) > width:
        step = len(data) // width
        data = data[::step][:width]

    min_val = min(data)
    max_val = max(data)
    range_val = max_val - min_val
    if range_val == 0:
        range_val = 1

    # normalize to height
    normalized = [(v - min_val) / range_val * (height - 1) for v in data]

    chart_lines = []
    for row in range(height - 1, -1, -1):
        line = ""
        for col, val in enumerate(normalized):
            if int(round(val)) == row:
                # color based on trend
                if col > 0 and data[col] >= data[col-1]:
                    line += "█"  # green up
                else:
                    line += "▄"  # red down
            elif int(round(val)) > row:
                line += "│"
            else:
                line += " "
        chart_lines.append(line)

    # add axis labels
    result = f"┌{'─' * (width + 10)}┐\n"
    result += f"│ {title:^{width + 8}} │\n"
    result += f"├{'─' * (width + 10)}┤\n"

    for i, line in enumerate(chart_lines):
        if i == 0:
            label = f"${max_val:,.0f}"
        elif i == height - 1:
            label = f"${min_val:,.0f}"
        else:
            label = ""
        result += f"│{label:>9} {line}│\n"

    result += f"└{'─' * (width + 10)}┘"
    return result

def mini_sparkline(data, width=20):
    """Tiny inline sparkline"""
    if len(data) < 2:
        return "─" * width

    chars = " ▂▃▄▅▆▇█"

    if len(data) > width:
        step = len(data) // width
        data = data[::step][:width]

    min_val = min(data)
    max_val = max(data)
    range_val = max_val - min_val
    if range_val == 0:
        return "▄" * len(data)

    result = ""
    for v in data:
        idx = int((v - min_val) / range_val * (len(chars) - 1))
        result += chars[idx]

    return result

# ============================================================================
# OPTIMIZED DDA SCALPER
# ============================================================================

class DDAScalperOptimized:
    def __init__(self, saccade_mult=4.0, min_profit_mult=2.5):
        self.P0_stable = 0.98
        self.P0_react = 0.0
        self.saccade_thresh = saccade_mult
        self.min_profit_mult = min_profit_mult
        self.k = 1.0
        self.F_prev = None
        self.price_history = []
        self.dda_history = []
        self.volatility = 0.0
        self.last_signal = "HOLD"
        self.signal_count = 0
        self.required_confirms = 2

    def update(self, price):
        self.price_history.append(price)

        if len(self.price_history) < 20:
            self.F_prev = price
            self.dda_history.append(price)
            return "WAIT", price, 0
        if len(self.price_history) > 500:
            self.price_history.pop(0)
            self.dda_history.pop(0)

        recent = self.price_history[-20:]
        self.volatility = np.std(recent)
        if self.volatility == 0:
            self.volatility = 0.01

        diff = price - self.F_prev
        error = np.abs(diff)
        raw_signal = "HOLD"

        if error > (self.saccade_thresh * self.volatility):
            effective_P0 = self.P0_react
            effective_m = 1.0
            if diff > 0:
                raw_signal = "LONG_ENTRY"
            else:
                raw_signal = "SHORT_ENTRY"
        else:
            effective_P0 = self.P0_stable
            effective_m = 1.0 - effective_P0
            exit_thresh = self.volatility * 0.5
            if price < self.F_prev - exit_thresh:
                raw_signal = "LONG_EXIT"
            elif price > self.F_prev + exit_thresh:
                raw_signal = "SHORT_EXIT"

        prior = effective_P0 * self.k * self.F_prev
        delta = price - self.price_history[-2]
        boost = 0.6 * delta
        F = prior + (effective_m * (price + boost))

        if raw_signal == "HOLD" or "EXIT" in raw_signal:
            err = price - F
            self.k += 0.001 * np.sign(err) * (np.abs(err)**0.5)
            self.k = np.clip(self.k, 0.9, 1.1)
        else:
            self.k = 1.0

        self.F_prev = F
        self.dda_history.append(F)

        if raw_signal == self.last_signal:
            self.signal_count += 1
        else:
            self.signal_count = 1
            self.last_signal = raw_signal

        if "EXIT" in raw_signal:
            return raw_signal, F, error
        elif self.signal_count >= self.required_confirms:
            return raw_signal, F, error
        else:
            return "HOLD", F, error

# ============================================================================
# VISUAL PORTFOLIO TRACKER
# ============================================================================

class VisualPortfolio:
    def __init__(self, initial_cash=1000.0, leverage=50, fee_rate=0.0005):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.leverage = leverage
        self.fee_rate = fee_rate
        self.position = None
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0
        self.total_fees = 0
        self.last_trade_time = 0
        self.cooldown_candles = 3
        self.candle_count = 0

        # VISUAL TRACKING
        self.trade_history = []  # list of trade dicts
        self.balance_history = [initial_cash]
        self.pnl_history = [0]
        self.equity_curve = [initial_cash]

    def get_min_profit_threshold(self, price):
        position_value = self.cash * self.leverage
        round_trip_fee = position_value * self.fee_rate * 2
        return round_trip_fee * 2.5

    def execute(self, signal, price, timestamp="", expected_move=0):
        self.candle_count += 1
        executed = False

        if self.position is None:
            if self.candle_count - self.last_trade_time < self.cooldown_candles:
                return None

            if "ENTRY" in signal:
                min_profit = self.get_min_profit_threshold(price)
                position_value = self.cash * self.leverage
                size_contracts = position_value / price
                expected_profit = expected_move * size_contracts

                if expected_profit < min_profit:
                    return {"type": "SKIP", "reason": f"Expected ${expected_profit:.2f} < min ${min_profit:.2f}"}

                direction = "LONG" if "LONG" in signal else "SHORT"
                fee = position_value * self.fee_rate
                self.cash -= fee
                self.total_fees += fee
                self.position = {
                    'type': direction, 
                    'entry': price, 
                    'size': size_contracts,
                    'entry_time': timestamp
                }
                self.last_trade_time = self.candle_count

                return {
                    "type": "OPEN",
                    "direction": direction,
                    "price": price,
                    "size": size_contracts,
                    "fee": fee,
                    "time": timestamp
                }
        else:
            close_long = (self.position['type'] == "LONG" and ("SHORT" in signal or "EXIT" in signal))
            close_short = (self.position['type'] == "SHORT" and ("LONG" in signal or "EXIT" in signal))

            if close_long or close_short:
                entry = self.position['entry']
                size = self.position['size']
                direction = self.position['type']

                if direction == "LONG":
                    pnl = (price - entry) * size
                else:
                    pnl = (entry - price) * size

                fee = (size * price) * self.fee_rate
                self.cash += pnl
                self.cash -= fee
                self.total_fees += fee
                self.total_pnl += pnl
                self.trades += 1

                if pnl > 0:
                    self.wins += 1
                else:
                    self.losses += 1

                # record trade
                trade_record = {
                    "id": self.trades,
                    "type": direction,
                    "entry": entry,
                    "exit": price,
                    "size": size,
                    "pnl": pnl,
                    "fee": fee,
                    "net": pnl - fee,
                    "balance": self.cash,
                    "entry_time": self.position.get('entry_time', ''),
                    "exit_time": timestamp
                }
                self.trade_history.append(trade_record)
                self.balance_history.append(self.cash)
                self.pnl_history.append(pnl)

                result = {
                    "type": "CLOSE",
                    "direction": direction,
                    "entry": entry,
                    "exit": price,
                    "pnl": pnl,
                    "fee": fee,
                    "balance": self.cash,
                    "time": timestamp
                }

                self.position = None
                self.last_trade_time = self.candle_count

                # check for re-entry
                if "ENTRY" in signal:
                    self.execute(signal, price, timestamp, expected_move)

                return result

        # track equity even when not trading
        current_equity = self.cash
        if self.position:
            if self.position['type'] == "LONG":
                current_equity += (price - self.position['entry']) * self.position['size']
            else:
                current_equity += (self.position['entry'] - price) * self.position['size']
        self.equity_curve.append(current_equity)

        return None

    def get_stats(self):
        win_rate = (self.wins / self.trades * 100) if self.trades > 0 else 0
        net_profit = self.cash - self.initial_cash
        avg_win = np.mean([t['pnl'] for t in self.trade_history if t['pnl'] > 0]) if self.wins > 0 else 0
        avg_loss = np.mean([t['pnl'] for t in self.trade_history if t['pnl'] < 0]) if self.losses > 0 else 0

        return {
            'final_balance': self.cash,
            'net_profit': net_profit,
            'total_trades': self.trades,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'total_fees': self.total_fees,
            'roi_pct': (net_profit / self.initial_cash) * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0
        }

# ============================================================================
# RICH VISUAL DASHBOARD
# ============================================================================

class TradingDashboard:
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None

    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def render_header(self):
        header = """
╔══════════════════════════════════════════════════════════════════════════════╗
║   ██████╗ ██████╗  █████╗     ███████╗ ██████╗ █████╗ ██╗     ██████╗ ███████╗██████╗  ║
║   ██╔══██╗██╔══██╗██╔══██╗    ██╔════╝██╔════╝██╔══██╗██║     ██╔══██╗██╔════╝██╔══██╗ ║
║   ██║  ██║██║  ██║███████║    ███████╗██║     ███████║██║     ██████╔╝█████╗  ██████╔╝ ║
║   ██║  ██║██║  ██║██╔══██║    ╚════██║██║     ██╔══██║██║     ██╔═══╝ ██╔══╝  ██╔══██╗ ║
║   ██████╔╝██████╔╝██║  ██║    ███████║╚██████╗██║  ██║███████╗██║     ███████╗██║  ██║ ║
║   ╚═════╝ ╚═════╝ ╚═╝  ╚═╝    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝     ╚══════╝╚═╝  ╚═╝ ║
║                           🔥 TURBO EDITION v2.0 🔥                            ║
╚══════════════════════════════════════════════════════════════════════════════╝"""
        return header

    def render_stats_panel(self, stats, position=None, current_price=0, volatility=0):
        """Render main stats"""
        roi_color = "\033[92m" if stats['roi_pct'] >= 0 else "\033[91m"
        pnl_color = "\033[92m" if stats['net_profit'] >= 0 else "\033[91m"
        reset = "\033[0m"

        pos_str = "FLAT"
        pos_pnl = 0
        if position:
            pos_str = f"{position['type']} @ ${position['entry']:,.2f}"
            if position['type'] == "LONG":
                pos_pnl = (current_price - position['entry']) * position['size']
            else:
                pos_pnl = (position['entry'] - current_price) * position['size']

        pos_color = "\033[92m" if pos_pnl >= 0 else "\033[91m"

        panel = f"""
┌─────────────────────────────────────┬─────────────────────────────────────┐
│         💰 ACCOUNT STATS            │         📊 TRADING STATS            │
├─────────────────────────────────────┼─────────────────────────────────────┤
│  Starting:     $1,000.00            │  Total Trades:  {stats['total_trades']:>6}              │
│  Balance:      ${stats['final_balance']:>10,.2f}         │  Wins:          {stats['wins']:>6}  ✅           │
│  {pnl_color}Net P&L:      ${stats['net_profit']:>+10,.2f}{reset}         │  Losses:        {stats['losses']:>6}  ❌           │
│  {roi_color}ROI:          {stats['roi_pct']:>+10.2f}%{reset}         │  Win Rate:      {stats['win_rate']:>5.1f}%             │
│  Fees Paid:    ${stats['total_fees']:>10,.2f}         │  Profit Factor: {stats['profit_factor']:>6.2f}             │
├─────────────────────────────────────┼─────────────────────────────────────┤
│         📍 CURRENT POSITION         │         🌡️  MARKET DATA             │
├─────────────────────────────────────┼─────────────────────────────────────┤
│  Position:  {pos_str:<24}│  Price:    ${current_price:>12,.2f}         │
│  {pos_color}Unrealized: ${pos_pnl:>+10,.2f}{reset}            │  Volatility: ${volatility:>10,.2f}         │
│  Leverage:  50x                     │  Spread:   ~0.01%                   │
└─────────────────────────────────────┴─────────────────────────────────────┘"""
        return panel

    def render_trade_table(self, trades, limit=8):
        """Render recent trades table"""
        if not trades:
            return "\n  📭 No trades yet...\n"

        header = """
┌─────┬──────────┬────────────────┬────────────────┬─────────────┬─────────────┬─────────────┐
│  #  │   TYPE   │     ENTRY      │      EXIT      │     P&L     │     FEE     │   BALANCE   │
├─────┼──────────┼────────────────┼────────────────┼─────────────┼─────────────┼─────────────┤"""

        rows = ""
        for t in trades[-limit:]:
            pnl_color = "\033[92m" if t['pnl'] >= 0 else "\033[91m"
            reset = "\033[0m"
            type_emoji = "🟢" if t['type'] == "LONG" else "🔴"

            rows += f"\n│ {t['id']:>3} │ {type_emoji} {t['type']:<5} │ ${t['entry']:>12,.2f} │ ${t['exit']:>12,.2f} │ {pnl_color}${t['pnl']:>+9,.2f}{reset} │ ${t['fee']:>9,.2f} │ ${t['balance']:>9,.2f} │"

        footer = "\n└─────┴──────────┴────────────────┴────────────────┴─────────────┴─────────────┴─────────────┘"

        return header + rows + footer

    def render_live_feed(self, feed_lines, limit=6):
        """Render live signal feed"""
        result = "\n┌─────────────────────────────────── 📡 LIVE FEED ───────────────────────────────────┐\n"

        for line in feed_lines[-limit:]:
            result += f"│ {line:<84} │\n"

        # pad if needed
        for _ in range(limit - len(feed_lines[-limit:])):
            result += f"│ {'':<84} │\n"

        result += "└────────────────────────────────────────────────────────────────────────────────────┘"
        return result

    def render_full_dashboard(self, stats, position, current_price, volatility, 
                               price_history, trades, feed_lines, signal):
        """Render the complete dashboard"""
        self.clear()

        print(self.render_header())
        print(self.render_stats_panel(stats, position, current_price, volatility))

        # Price chart
        if len(price_history) > 10:
            print("\n" + ascii_chart(price_history[-100:], width=70, height=10, 
                                     title=f"BTC/USDT 1m  |  Signal: {signal}  |  {mini_sparkline(price_history[-30:])}"))

        # Trade history
        print("\n  📜 RECENT TRADES:")
        print(self.render_trade_table(trades))

        # Live feed
        print(self.render_live_feed(feed_lines))

        # Footer
        print("\n  ⌨️  Press Ctrl+C to stop  |  🔄 Updates every 5s")

# ============================================================================
# MAIN RUNNERS
# ============================================================================

def run_visual_backtest():
    """Visual backtesting mode"""
    console = Console() if RICH_AVAILABLE else None

    print("\n" + "="*80)
    print("  📡 FETCHING HISTORICAL DATA FROM KRAKEN...")
    print("="*80)

    exchange = ccxt.kraken()

    # Fetch MORE history - 1000 candles (~16 hours)
    all_candles = []

    if RICH_AVAILABLE:
        with Progress(SpinnerColumn(), TextColumn("[bold blue]Fetching candles...")) as progress:
            task = progress.add_task("fetch", total=None)

            # fetch in chunks
            for i in range(2):
                if i == 0:
                    candles = exchange.fetch_ohlcv('BTC/USDT', '1m', limit=500)
                else:
                    since = candles[0][0] - (500 * 60 * 1000)  # go back 500 more minutes
                    older = exchange.fetch_ohlcv('BTC/USDT', '1m', since=since, limit=500)
                    candles = older + candles
                time.sleep(1)
            all_candles = candles
    else:
        for i in range(2):
            print(f"  Fetching batch {i+1}/2...")
            if i == 0:
                candles = exchange.fetch_ohlcv('BTC/USDT', '1m', limit=500)
            else:
                since = candles[0][0] - (500 * 60 * 1000)
                older = exchange.fetch_ohlcv('BTC/USDT', '1m', since=since, limit=500)
                candles = older + candles
            time.sleep(1)
        all_candles = candles

    print(f"  ✅ Fetched {len(all_candles)} candles ({len(all_candles)/60:.1f} hours of data)\n")

    # Grid search
    print("  🔬 RUNNING PARAMETER OPTIMIZATION...")
    print("  " + "-"*76)

    best_roi = -999
    best_params = {}
    results = []

    for saccade in [3.0, 3.5, 4.0, 4.5, 5.0]:
        for min_profit in [1.5, 2.0, 2.5, 3.0]:
            bot = DDAScalperOptimized(saccade_mult=saccade, min_profit_mult=min_profit)
            portfolio = VisualPortfolio(initial_cash=1000.0, leverage=50)

            for candle in all_candles:
                close_price = candle[4]
                timestamp = datetime.fromtimestamp(candle[0]/1000).strftime('%H:%M')
                signal, fair_val, expected_move = bot.update(close_price)
                if signal != "WAIT":
                    portfolio.execute(signal, close_price, timestamp, expected_move)

            # close open position
            if portfolio.position:
                portfolio.execute("EXIT", all_candles[-1][4], "", 0)

            stats = portfolio.get_stats()
            roi = stats['roi_pct']

            results.append({
                'saccade': saccade, 
                'min_profit': min_profit, 
                'roi': roi,
                'trades': stats['total_trades'],
                'win_rate': stats['win_rate']
            })

            roi_color = "\033[92m" if roi >= 0 else "\033[91m"
            reset = "\033[0m"
            print(f"  Saccade: {saccade} | MinProfit: {min_profit}x | {roi_color}ROI: {roi:>+7.2f}%{reset} | Trades: {stats['total_trades']:>3} | WR: {stats['win_rate']:.1f}%")

            if roi > best_roi:
                best_roi = roi
                best_params = {'saccade': saccade, 'min_profit': min_profit}

    print("  " + "-"*76)
    print(f"\n  🏆 BEST: Saccade={best_params['saccade']}, MinProfit={best_params['min_profit']}x → ROI: {best_roi:+.2f}%")

    # Run detailed backtest with best params
    print("\n" + "="*80)
    print("  📊 DETAILED BACKTEST WITH OPTIMAL PARAMS")
    print("="*80 + "\n")

    bot = DDAScalperOptimized(saccade_mult=best_params['saccade'], min_profit_mult=best_params['min_profit'])
    portfolio = VisualPortfolio(initial_cash=1000.0, leverage=50)
    dashboard = TradingDashboard()

    price_history = []
    feed_lines = []

    for i, candle in enumerate(all_candles):
        close_price = candle[4]
        timestamp = datetime.fromtimestamp(candle[0]/1000).strftime('%H:%M:%S')
        signal, fair_val, expected_move = bot.update(close_price)
        price_history.append(close_price)

        if signal != "WAIT":
            result = portfolio.execute(signal, close_price, timestamp, expected_move)

            # build feed line
            pos_str = portfolio.position['type'] if portfolio.position else "FLAT"
            feed_line = f"[{timestamp}] ${close_price:,.1f} | DDA: ${fair_val:,.1f} | {signal:<12} | {pos_str}"

            if result:
                if result['type'] == "OPEN":
                    feed_line += f" → 🚀 OPENED {result['direction']}"
                elif result['type'] == "CLOSE":
                    pnl_emoji = "✅" if result['pnl'] > 0 else "❌"
                    feed_line += f" → {pnl_emoji} CLOSED ${result['pnl']:+,.2f}"
                elif result['type'] == "SKIP":
                    feed_line += f" → ⏭️ SKIP"

            feed_lines.append(feed_line)

            # show progress every 100 candles
            if i % 100 == 0 and i > 0:
                stats = portfolio.get_stats()
                pct = (i / len(all_candles)) * 100
                print(f"  Progress: {pct:.0f}% | Trades: {stats['total_trades']} | Balance: ${stats['final_balance']:,.2f}")

    # close any open
    if portfolio.position:
        portfolio.execute("EXIT", all_candles[-1][4], "", 0)

    # Final dashboard
    stats = portfolio.get_stats()
    dashboard.render_full_dashboard(
        stats=stats,
        position=portfolio.position,
        current_price=price_history[-1],
        volatility=bot.volatility,
        price_history=price_history,
        trades=portfolio.trade_history,
        feed_lines=feed_lines,
        signal="BACKTEST COMPLETE"
    )

    # Equity curve
    print("\n  📈 EQUITY CURVE:")
    print(ascii_chart(portfolio.balance_history, width=70, height=8, title="Account Balance Over Time"))

    return best_params

def run_visual_live(saccade_mult=4.0, min_profit_mult=2.5):
    """Live trading with visual dashboard"""

    exchange = ccxt.kraken()
    bot = DDAScalperOptimized(saccade_mult=saccade_mult, min_profit_mult=min_profit_mult)
    portfolio = VisualPortfolio(initial_cash=1000.0, leverage=50)
    dashboard = TradingDashboard()

    feed_lines = []

    # Pre-warm
    print("\n  🔥 Pre-warming with historical data...")
    history = exchange.fetch_ohlcv('BTC/USDT', '1m', limit=100)
    for candle in history[:-1]:
        bot.update(candle[4])
    print(f"  ✅ Ready! Volatility: ${bot.volatility:.2f}\n")

    last_timestamp = 0

    try:
        while True:
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1m', limit=2)
            latest_candle = ohlcv[-2]
            timestamp = latest_candle[0]
            close_price = latest_candle[4]

            if timestamp != last_timestamp:
                dt = datetime.fromtimestamp(timestamp / 1000).strftime('%H:%M:%S')
                signal, fair_val, expected_move = bot.update(close_price)

                if signal != "WAIT":
                    result = portfolio.execute(signal, close_price, dt, expected_move)

                    # build feed line
                    pos_str = portfolio.position['type'] if portfolio.position else "FLAT"
                    feed_line = f"[{dt}] ${close_price:,.1f} | DDA: ${fair_val:,.1f} | {signal:<12} | {pos_str}"

                    if result:
                        if result['type'] == "OPEN":
                            feed_line += f" → 🚀 OPENED {result['direction']}"
                        elif result['type'] == "CLOSE":
                            pnl_emoji = "✅" if result['pnl'] > 0 else "❌"
                            feed_line += f" → {pnl_emoji} CLOSED ${result['pnl']:+,.2f}"
                        elif result['type'] == "SKIP":
                            feed_line += f" → ⏭️ SKIP"

                    feed_lines.append(feed_line)

                    # Render dashboard
                    stats = portfolio.get_stats()
                    dashboard.render_full_dashboard(
                        stats=stats,
                        position=portfolio.position,
                        current_price=close_price,
                        volatility=bot.volatility,
                        price_history=bot.price_history,
                        trades=portfolio.trade_history,
                        feed_lines=feed_lines,
                        signal=signal
                    )

                last_timestamp = timestamp

            time.sleep(5)

    except KeyboardInterrupt:
        print("\n\n  👋 Stopped by user!")
        stats = portfolio.get_stats()
        print(f"\n  Final Balance: ${stats['final_balance']:,.2f}")
        print(f"  Total P&L: ${stats['net_profit']:+,.2f}")
        print(f"  Trades: {stats['total_trades']} | Win Rate: {stats['win_rate']:.1f}%\n")

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--live":
        # get params from args or use defaults
        saccade = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
        min_profit = float(sys.argv[3]) if len(sys.argv) > 3 else 2.5
        run_visual_live(saccade_mult=saccade, min_profit_mult=min_profit)
    else:
        # run backtest first to find optimal params
        best = run_visual_backtest()

        print("\n" + "="*80)
        print("  💡 TO RUN LIVE WITH OPTIMAL PARAMS:")
        print(f"     python {sys.argv[0]} --live {best['saccade']} {best['min_profit']}")
        print("="*80 + "\n")