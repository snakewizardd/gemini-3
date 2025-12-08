
import time
import numpy as np
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# Optional import: only needed if you run backtests/live printing with real data.
# Install with: pip install ccxt
try:
    import ccxt
except ImportError:
    ccxt = None


class DDAScalperOptimized:
    """
    DDA scalper with:
      - Raised saccade threshold (default 4.0x volatility)
      - Signal confirmation (2 consecutive matching signals)
      - Adaptive k calibration with mild clipping
    Returns: (signal, fair_value, expected_move)
      signal ∈ {"WAIT","HOLD","LONG_ENTRY","SHORT_ENTRY","LONG_EXIT","SHORT_EXIT"}
      fair_value = computed F
      expected_move = |price - F_prev|, used for fee-aware filtering upstream
    """

    def __init__(self, saccade_mult: float = 4.0, min_profit_mult: float = 2.5):
        # Tuned params
        self.P0_stable = 0.98
        self.P0_react = 0.0
        self.saccade_thresh = saccade_mult
        self.min_profit_mult = min_profit_mult

        self.k = 1.0
        self.F_prev = None
        self.price_history = []
        self.volatility = 0.0

        # Confirmation
        self.last_signal = "HOLD"
        self.signal_count = 0
        self.required_confirms = 2

    def update(self, price: float):
        price = float(price)
        self.price_history.append(price)

        # Warm-up
        if len(self.price_history) < 20:
            if self.F_prev is None:
                self.F_prev = price
            return "WAIT", price, 0.0

        # Keep window bounded
        if len(self.price_history) > 100:
            self.price_history.pop(0)

        recent = self.price_history[-20:]
        self.volatility = float(np.std(recent))
        if self.volatility == 0.0:
            self.volatility = 0.01

        diff = price - self.F_prev
        error = abs(diff)
        raw_signal = "HOLD"

        # ENTRY: only on sufficiently large moves
        if error > (self.saccade_thresh * self.volatility):
            effective_P0 = self.P0_react
            effective_m = 1.0
            raw_signal = "LONG_ENTRY" if diff > 0 else "SHORT_ENTRY"
        else:
            # EXIT bias requires counter-move above threshold; otherwise HOLD
            effective_P0 = self.P0_stable
            effective_m = 1.0 - effective_P0
            exit_thresh = self.volatility * 0.5
            if price < self.F_prev - exit_thresh:
                raw_signal = "LONG_EXIT"
            elif price > self.F_prev + exit_thresh:
                raw_signal = "SHORT_EXIT"

        # Fair-value update with small momentum boost
        prior = effective_P0 * self.k * self.F_prev
        delta = price - self.price_history[-2]
        boost = 0.6 * delta
        F = prior + (effective_m * (price + boost))

        # Calibrate k unless entering
        if raw_signal == "HOLD" or ("EXIT" in raw_signal):
            err = price - F
            self.k += 0.001 * np.sign(err) * (abs(err) ** 0.5)
            self.k = float(np.clip(self.k, 0.9, 1.1))
        else:
            self.k = 1.0

        self.F_prev = F

        # Confirmation
        if raw_signal == self.last_signal:
            self.signal_count += 1
        else:
            self.signal_count = 1
            self.last_signal = raw_signal

        # Only emit confirmed entries; exits are immediate
        if "EXIT" in raw_signal:
            return raw_signal, F, error
        elif self.signal_count >= self.required_confirms:
            return raw_signal, F, error
        else:
            return "HOLD", F, error


class PaperPortfolioOptimized:
    """
    Simple paper portfolio model:
      - Tracks cash, leveraged position size (BTC contracts), PnL, fees, cooldown
      - Applies fee rate per side (e.g., 0.0005 = 0.05%)
      - Requires expected profit >= profit_mult * round-trip fees before entering
    """

    def __init__(
        self,
        initial_cash: float = 1000.0,
        leverage: float = 50.0,
        fee_rate: float = 0.0005,
        profit_mult: float = 2.5,
        cooldown_candles: int = 3,
    ):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.leverage = leverage
        self.fee_rate = fee_rate
        self.profit_mult = profit_mult

        self.position = None  # {'type': 'LONG'/'SHORT', 'entry': price, 'size': btc}
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0.0
        self.total_fees = 0.0

        # Cooldown
        self.last_trade_time = 0
        self.cooldown_candles = cooldown_candles
        self.candle_count = 0

    def get_min_profit_threshold(self, price: float):
        """Minimum profit needed to beat fees by profit_mult."""
        position_value = self.cash * self.leverage
        round_trip_fee = position_value * self.fee_rate * 2.0
        return round_trip_fee * self.profit_mult

    def execute(self, signal: str, price: float, expected_move: float = 0.0, verbose: bool = True):
        self.candle_count += 1
        price = float(price)

        # Flat -> consider entry
        if self.position is None:
            # Enforce cooldown
            if self.candle_count - self.last_trade_time < self.cooldown_candles:
                return

            if "ENTRY" in signal:
                min_profit = self.get_min_profit_threshold(price)
                position_value = self.cash * self.leverage
                size_contracts = position_value / price
                expected_profit = expected_move * size_contracts

                if expected_profit < min_profit:
                    if verbose:
                        print(f"   ⏭️ SKIP - expected ${expected_profit:.2f} < min ${min_profit:.2f}")
                    return

                direction = "LONG" if "LONG" in signal else "SHORT"
                fee = position_value * self.fee_rate
                self.cash -= fee
                self.total_fees += fee
                self.position = {'type': direction, 'entry': price, 'size': size_contracts}
                self.last_trade_time = self.candle_count
                if verbose:
                    print(f"🚀 OPEN {direction} @ ${price:.2f} | Size: {size_contracts:.6f} BTC | Fee: ${fee:.2f}")
            return

        # In-position -> consider exit/flip
        close_long = (self.position['type'] == "LONG" and ("SHORT" in signal or "EXIT" in signal))
        close_short = (self.position['type'] == "SHORT" and ("LONG" in signal or "EXIT" in signal))

        if close_long or close_short:
            entry = self.position['entry']
            size = self.position['size']

            pnl = (price - entry) * size if self.position['type'] == "LONG" else (entry - price) * size
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

            if verbose:
                color = "🟢" if pnl > 0 else "🔴"
                print(f"{color} CLOSE {self.position['type']} @ ${price:.2f} | PnL: ${pnl:.2f} | Fee: ${fee:.2f} | Bal: ${self.cash:.2f}")

            self.position = None
            self.last_trade_time = self.candle_count

            # If the signal was a flip (e.g. EXIT + ENTRY), re-enter immediately
            if "ENTRY" in signal:
                self.execute(signal, price, expected_move, verbose)

    def get_stats(self):
        win_rate = (self.wins / self.trades * 100.0) if self.trades > 0 else 0.0
        net_profit = self.cash - self.initial_cash
        return {
            'final_balance': self.cash,
            'net_profit': net_profit,
            'total_trades': self.trades,
            'wins': self.wins,
            'losses': self.losses,
            'win_rate': win_rate,
            'total_fees': self.total_fees,
            'roi_pct': (net_profit / self.initial_cash) * 100.0 if self.initial_cash > 0 else 0.0,
        }


def extract_closes(candles):
    """
    Accepts either:
      - list of OHLCV rows: [ts, open, high, low, close, vol]
      - list of floats (already closes)
    Returns list of floats (closes).
    """
    closes = []
    for c in candles:
        if isinstance(c, (list, tuple)) and len(c) >= 5:
            closes.append(float(c[4]))
        else:
            closes.append(float(c))
    return closes


def run_backtest(candles, saccade_mult: float = 4.0, min_profit_mult: float = 2.5, verbose: bool = False):
    """Backtest over historical close prices."""
    closes = extract_closes(candles)
    bot = DDAScalperOptimized(saccade_mult=saccade_mult, min_profit_mult=min_profit_mult)
    portfolio = PaperPortfolioOptimized(initial_cash=1000.0, leverage=50.0, fee_rate=0.0005, profit_mult=min_profit_mult)

    for close_price in closes:
        signal, fair_val, expected_move = bot.update(close_price)
        if signal != "WAIT":
            portfolio.execute(signal, close_price, expected_move, verbose=verbose)

    # Close any open position at end
    if portfolio.position:
        final_price = closes[-1]
        portfolio.execute("EXIT", final_price, 0.0, verbose=verbose)

    return portfolio.get_stats()


def grid_search_params(candles):
    """Find optimal params via grid search over saccade and profit multiplier."""
    print("\n🔬 GRID SEARCH FOR OPTIMAL PARAMS...")
    print("=" * 60)

    best_roi = -1e9
    best_params = {}

    for saccade in [3.0, 3.5, 4.0, 4.5, 5.0]:
        for min_profit in [1.5, 2.0, 2.5, 3.0]:
            stats = run_backtest(candles, saccade_mult=saccade, min_profit_mult=min_profit, verbose=False)
            roi = stats['roi_pct']
            print(f"Saccade: {saccade:.1f} | MinProfit: {min_profit:.1f}x | ROI: {roi:+.2f}% | Trades: {stats['total_trades']} | WR: {stats['win_rate']:.1f}%")
            if roi > best_roi:
                best_roi = roi
                best_params = {'saccade': saccade, 'min_profit': min_profit, 'stats': stats}

    print("=" * 60)
    print(f"\n🏆 BEST PARAMS: Saccade={best_params['saccade']}, MinProfit={best_params['min_profit']}x")
    print(f"   ROI: {best_roi:+.2f}% | WinRate: {best_params['stats']['win_rate']:.1f}%")
    return best_params


def run_backtest_mode():
    """Fetch historical data (Kraken BTC/USDT 1m) and run grid search + detailed backtest."""
    if ccxt is None:
        raise RuntimeError("ccxt is not installed. Install it with: pip install ccxt")

    print("📡 FETCHING HISTORICAL DATA FROM KRAKEN...")
    exchange = ccxt.kraken()

    # Grab ~8+ hours of 1m candles
    candles = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=500)
    print(f"✅ Got {len(candles)} candles for backtesting\n")

    # RUN GRID SEARCH
    best = grid_search_params(candles)

    # DETAILED BACKTEST with best params
    print("\n📊 DETAILED BACKTEST WITH OPTIMAL PARAMS:")
    print("=" * 60)
    stats = run_backtest(
        candles,
        saccade_mult=best['saccade'],
        min_profit_mult=best['min_profit'],
        verbose=True
    )

    print("\n" + "=" * 60)
    print("📈 FINAL STATS:")
    print(f"   Starting Balance: $1,000.00")
    print(f"   Final Balance:    ${stats['final_balance']:.2f}")
    print(f"   Net Profit:       ${stats['net_profit']:+.2f}")
    print(f"   ROI:              {stats['roi_pct']:+.2f}%")
    print(f"   Total Trades:     {stats['total_trades']}")
    print(f"   Win Rate:         {stats['win_rate']:.1f}%")
    print(f"   Total Fees Paid:  ${stats['total_fees']:.2f}")

    return best


def run_live_optimized(saccade_mult: float = 4.0, min_profit_mult: float = 2.5):
    """
    Live printing (paper-only): streams recent 1m candles, computes signals,
    and prints paper trades. NO real orders are placed.
    """
    if ccxt is None:
        raise RuntimeError("ccxt is not installed. Install it with: pip install ccxt")

    print(f"\n🔥 RUNNING LIVE WITH OPTIMIZED PARAMS")
    print(f"   Saccade Threshold: {saccade_mult}x volatility")
    print(f"   Min Profit Requirement: {min_profit_mult}x fees")
    print("=" * 60)

    exchange = ccxt.kraken()
    bot = DDAScalperOptimized(saccade_mult=saccade_mult, min_profit_mult=min_profit_mult)
    portfolio = PaperPortfolioOptimized(initial_cash=1000.0, leverage=50.0, fee_rate=0.0005, profit_mult=min_profit_mult)

    # Pre-warm with prior candles (exclude the very last if still forming)
    print("🔥 PRE-WARMING with 30 candles...")
    history = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=30)
    for candle in history[:-1]:
        close = float(candle[4])
        bot.update(close)
    print(f"✅ Volatility baseline: ${bot.volatility:.4f}")

    last_timestamp = None

    while True:
        try:
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=2)
            latest_closed = ohlcv[-2]  # use the most recently CLOSED candle
            timestamp_ms = int(latest_closed[0])
            close_price = float(latest_closed[4])

            if timestamp_ms != last_timestamp:
                dt = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%H:%M:%S')
                signal, fair_val, expected_move = bot.update(close_price)
                pos_str = portfolio.position['type'] if portfolio.position else "FLAT"
                print(f"[{dt}] Price: {close_price:.1f} | DDA: {fair_val:.1f} | Sig: {signal} | Pos: {pos_str}")
                portfolio.execute(signal, close_price, expected_move, verbose=True)
                last_timestamp = timestamp_ms

            time.sleep(5)

        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    import sys

    # Usage:
    #   python night_scalper_turbo.py          -> backtest mode + grid search
    #   python night_scalper_turbo.py --live   -> live printing (paper-only)
    if len(sys.argv) > 1 and sys.argv[1] == "--live":
        run_live_optimized(saccade_mult=4.0, min_profit_mult=2.5)
    else:
        best = run_backtest_mode()
        print("\n" + "=" * 60)
        print("💡 TO RUN LIVE WITH THESE PARAMS:")
        print(f"   python {sys.argv[0]} --live")
