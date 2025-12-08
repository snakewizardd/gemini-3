
"""
DDA NORTH STAR v1.0
═══════════════════
Your intuitive trading compass.
Run anytime to get a clear signal: BUY / SELL / HOLD

This is a DECISION SUPPORT TOOL - YOU make the final call.
"""
import yfinance as yf
import numpy as np
from datetime import datetime
import warnings
import sys

warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════════════════
# COLORS FOR TERMINAL
# ═══════════════════════════════════════════════════════════════════════════════
class C:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


# ═══════════════════════════════════════════════════════════════════════════════
# THE DDA CORE - Your "Fair Value" Calculator
# ═══════════════════════════════════════════════════════════════════════════════
class DDANorthStar:
    def __init__(self, smoothing=0.96):
        self.P0 = smoothing
        self.fair_value = None
        self.prices = []
        
    def calculate(self, prices):
        """Feed historical prices, get fair value and deviation"""
        self.prices = list(prices)
        
        # Initialize fair value
        self.fair_value = self.prices[0]
        
        # Run DDA through all prices
        for price in self.prices:
            self.fair_value = self.P0 * self.fair_value + (1 - self.P0) * price
        
        current_price = self.prices[-1]
        deviation = (current_price - self.fair_value) / self.fair_value * 100
        
        # Volatility (for context)
        if len(self.prices) >= 20:
            volatility = np.std(self.prices[-20:]) / np.mean(self.prices[-20:]) * 100
        else:
            volatility = 0
        
        return {
            'fair_value': self.fair_value,
            'current_price': current_price,
            'deviation': deviation,
            'volatility': volatility
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SIGNAL GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════
def get_signal(deviation, volatility):
    """
    Convert deviation into actionable signal
    
    OVERSOLD  (deviation < -5%):  BUY opportunity
    OVERBOUGHT (deviation > +6%): SELL opportunity  
    NEUTRAL:                      HOLD / Wait
    """
    
    # Thresholds (from your best performing strategy)
    OVERSOLD = -5.0
    OVERBOUGHT = 6.0
    
    # Strong thresholds
    VERY_OVERSOLD = -10.0
    VERY_OVERBOUGHT = 12.0
    
    if deviation <= VERY_OVERSOLD:
        return "🟢 STRONG BUY", "Price is significantly below fair value. Blood in the streets.", 5
    elif deviation <= OVERSOLD:
        return "🟢 BUY", "Price is below fair value. Good entry zone.", 4
    elif deviation >= VERY_OVERBOUGHT:
        return "🔴 STRONG SELL", "Price is significantly above fair value. Take profits.", 1
    elif deviation >= OVERBOUGHT:
        return "🔴 SELL", "Price is above fair value. Consider taking profits.", 2
    else:
        # Neutral zone - give directional hint
        if deviation > 3:
            return "🟡 HOLD (Warm)", "Approaching overbought. Watch for exit.", 3
        elif deviation < -3:
            return "🟡 HOLD (Cool)", "Approaching oversold. Watch for entry.", 3
        else:
            return "⚪ NEUTRAL", "Price is near fair value. No clear edge.", 3


def get_trend(prices, lookback=30):
    """Simple trend detection"""
    if len(prices) < lookback:
        return "UNKNOWN", 0
    
    recent = prices[-lookback:]
    start = np.mean(recent[:5])
    end = np.mean(recent[-5:])
    
    change = (end - start) / start * 100
    
    if change > 10:
        return "STRONG UPTREND", change
    elif change > 3:
        return "UPTREND", change
    elif change < -10:
        return "STRONG DOWNTREND", change
    elif change < -3:
        return "DOWNTREND", change
    else:
        return "SIDEWAYS", change


# ═══════════════════════════════════════════════════════════════════════════════
# THE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
def run_north_star(ticker="BTC-USD", period="60d", interval="1d"):
    """
    Run the North Star analysis
    
    Args:
        ticker: Asset to analyze (default: BTC-USD)
        period: How much history to load (default: 60d)
        interval: Candle size (default: 1d)
    """
    
    # Header
    print(f"\n{C.CYAN}{'═' * 70}")
    print(f"{'═' * 20}  DDA NORTH STAR  {'═' * 20}")
    print(f"{'═' * 70}{C.END}\n")
    
    # Fetch data
    print(f"  📡 Fetching {ticker} data...")
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    
    if df.empty:
        print(f"  {C.RED}❌ Failed to fetch data{C.END}")
        return
    
    prices = df['Close'].values.flatten()
    current_price = float(prices[-1])
    
    # Run DDA
    dda = DDANorthStar(smoothing=0.96)
    result = dda.calculate(prices)
    
    # Get signal
    signal, explanation, strength = get_signal(result['deviation'], result['volatility'])
    
    # Get trend
    trend, trend_change = get_trend(prices)
    
    # Calculate support/resistance levels
    fair_value = result['fair_value']
    buy_zone = fair_value * 0.95   # 5% below = buy zone
    sell_zone = fair_value * 1.06  # 6% above = sell zone
    
    # Time
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ═══════════════════════════════════════════════════════════════════════
    # DISPLAY
    # ═══════════════════════════════════════════════════════════════════════
    
    print(f"  📅 {now}")
    print(f"  📊 Asset: {C.BOLD}{ticker}{C.END}")
    print(f"  📈 Data: {len(prices)} candles ({interval})\n")
    
    # Main signal box
    print(f"  {'─' * 60}")
    
    # Color the signal
    if "BUY" in signal:
        sig_color = C.GREEN
    elif "SELL" in signal:
        sig_color = C.RED
    else:
        sig_color = C.YELLOW
    
    print(f"  │{' ' * 58}│")
    print(f"  │{sig_color}{C.BOLD}  SIGNAL: {signal:^47}{C.END}│")
    print(f"  │{' ' * 58}│")
    print(f"  {'─' * 60}\n")
    
    # Price info
    print(f"  {C.BOLD}📍 PRICE INFO:{C.END}")
    print(f"  ├─ Current Price:  ${current_price:>12,.2f}")
    print(f"  ├─ Fair Value:     ${fair_value:>12,.2f}  (DDA estimate)")
    
    # Deviation with color
    dev = result['deviation']
    if dev < -5:
        dev_color = C.GREEN
        dev_label = "OVERSOLD"
    elif dev > 6:
        dev_color = C.RED
        dev_label = "OVERBOUGHT"
    else:
        dev_color = C.YELLOW
        dev_label = "NEUTRAL"
    
    print(f"  └─ Deviation:      {dev_color}{dev:>+11.2f}%  ({dev_label}){C.END}\n")
    
    # Key levels
    print(f"  {C.BOLD}🎯 KEY LEVELS:{C.END}")
    print(f"  ├─ Buy Zone:       ${buy_zone:>12,.2f}  (< -5% from fair value)")
    print(f"  ├─ Fair Value:     ${fair_value:>12,.2f}  (equilibrium)")
    print(f"  └─ Sell Zone:      ${sell_zone:>12,.2f}  (> +6% from fair value)\n")
    
    # Trend
    if "UP" in trend:
        trend_color = C.GREEN
    elif "DOWN" in trend:
        trend_color = C.RED
    else:
        trend_color = C.YELLOW
    
    print(f"  {C.BOLD}📈 TREND (30d):{C.END}")
    print(f"  └─ {trend_color}{trend} ({trend_change:+.1f}%){C.END}\n")
    
    # Volatility
    vol = result['volatility']
    if vol > 4:
        vol_label = "HIGH ⚠️"
        vol_color = C.RED
    elif vol > 2:
        vol_label = "MODERATE"
        vol_color = C.YELLOW
    else:
        vol_label = "LOW"
        vol_color = C.GREEN
    
    print(f"  {C.BOLD}🌡️  VOLATILITY:{C.END}")
    print(f"  └─ {vol_color}{vol:.2f}% daily ({vol_label}){C.END}\n")
    
    # Explanation
    print(f"  {C.BOLD}💡 INTERPRETATION:{C.END}")
    print(f"  └─ {explanation}\n")
    
    # Visual meter
    print(f"  {C.BOLD}📊 DEVIATION METER:{C.END}")
    print(f"  ")
    print(f"      OVERSOLD          NEUTRAL          OVERBOUGHT")
    print(f"     ◄────────────────────┼────────────────────►")
    print(f"    -15%    -5%          0%          +6%    +15%")
    
    # Position marker
    meter_pos = int((dev + 15) / 30 * 50)  # Scale -15 to +15 onto 0-50
    meter_pos = max(0, min(50, meter_pos))
    meter_line = " " * meter_pos + "▲"
    print(f"    {meter_line}")
    print(f"    {' ' * meter_pos}{dev:+.1f}%\n")
    
    # Action guidance
    print(f"  {'─' * 60}")
    print(f"  {C.BOLD}🎮 SUGGESTED ACTION:{C.END}")
    
    if "STRONG BUY" in signal:
        print(f"  {C.GREEN}│ Consider BUYING. Price is deeply oversold.{C.END}")
        print(f"  {C.GREEN}│ This is historically a good entry point.{C.END}")
        print(f"  │ Suggested entry: ${current_price:,.2f} or lower")
        print(f"  │ Target: ${fair_value:,.2f} (fair value)")
        print(f"  │ Stop loss: ${current_price * 0.88:,.2f} (-12%)")
    elif "BUY" in signal:
        print(f"  {C.GREEN}│ Consider BUYING. Price is below fair value.{C.END}")
        print(f"  │ Suggested entry: ${current_price:,.2f}")
        print(f"  │ Target: ${sell_zone:,.2f} (overbought zone)")
        print(f"  │ Stop loss: ${current_price * 0.88:,.2f} (-12%)")
    elif "STRONG SELL" in signal:
        print(f"  {C.RED}│ Consider SELLING. Price is significantly overbought.{C.END}")
        print(f"  {C.RED}│ High probability of pullback to fair value.{C.END}")
        print(f"  │ Target: ${fair_value:,.2f} (fair value)")
    elif "SELL" in signal:
        print(f"  {C.RED}│ Consider SELLING or taking profits.{C.END}")
        print(f"  │ Price is above fair value.")
        print(f"  │ Target: ${fair_value:,.2f} (fair value)")
    else:
        print(f"  {C.YELLOW}│ WAIT. No clear edge right now.{C.END}")
        print(f"  │ Price is near fair value.")
        print(f"  │ Watch for price to reach buy zone (${buy_zone:,.2f})")
        print(f"  │ or sell zone (${sell_zone:,.2f})")
    
    print(f"  {'─' * 60}\n")
    
    # Disclaimer
    print(f"  {C.CYAN}⚠️  REMEMBER: This is a GUIDE, not financial advice.{C.END}")
    print(f"  {C.CYAN}    YOU make the final decision. Manage your risk.{C.END}\n")
    
    print(f"{C.CYAN}{'═' * 70}{C.END}\n")
    
    return {
        'signal': signal,
        'price': current_price,
        'fair_value': fair_value,
        'deviation': dev,
        'trend': trend,
        'buy_zone': buy_zone,
        'sell_zone': sell_zone
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-ASSET SCANNER
# ═══════════════════════════════════════════════════════════════════════════════
def scan_multiple(tickers=None):
    """Scan multiple assets for opportunities"""
    
    if tickers is None:
        tickers = ["BTC-USD", "ETH-USD", "SOL-USD", "AAPL", "SPY", "QQQ"]
    
    print(f"\n{C.CYAN}{'═' * 70}")
    print(f"{'═' * 20}  NORTH STAR SCANNER  {'═' * 17}")
    print(f"{'═' * 70}{C.END}\n")
    
    print(f"  {'Asset':<12} {'Price':>12} {'Fair Value':>12} {'Dev':>8} {'Signal':<20}")
    print(f"  {'─' * 66}")
    
    results = []
    
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="60d", interval="1d", progress=False)
            if df.empty:
                continue
                
            prices = df['Close'].values.flatten()
            
            dda = DDANorthStar(smoothing=0.96)
            result = dda.calculate(prices)
            
            signal, _, strength = get_signal(result['deviation'], result['volatility'])
            
            # Color based on signal
            if "BUY" in signal:
                color = C.GREEN
            elif "SELL" in signal:
                color = C.RED
            else:
                color = ""
            
            print(f"  {color}{ticker:<12} ${result['current_price']:>10,.2f} ${result['fair_value']:>10,.2f} {result['deviation']:>+7.1f}% {signal:<20}{C.END}")
            
            results.append({
                'ticker': ticker,
                'signal': signal,
                'deviation': result['deviation'],
                'strength': strength
            })
            
        except Exception as e:
            print(f"  {ticker:<12} {'Error':>12}")
    
    print(f"  {'─' * 66}\n")
    
    # Highlight opportunities
    buys = [r for r in results if "BUY" in r['signal']]
    sells = [r for r in results if "SELL" in r['signal']]
    
    if buys:
        print(f"  {C.GREEN}🟢 BUY OPPORTUNITIES:{C.END}")
        for b in sorted(buys, key=lambda x: x['deviation']):
            print(f"     • {b['ticker']}: {b['deviation']:+.1f}% from fair value")
        print()
    
    if sells:
        print(f"  {C.RED}🔴 SELL CANDIDATES:{C.END}")
        for s in sorted(sells, key=lambda x: -x['deviation']):
            print(f"     • {s['ticker']}: {s['deviation']:+.1f}% from fair value")
        print()
    
    if not buys and not sells:
        print(f"  {C.YELLOW}⚪ No strong signals at the moment.{C.END}\n")
    
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    
    # Parse command line args
    if len(sys.argv) > 1:
        arg = sys.argv[1].upper()
        
        if arg == "SCAN":
            # Scan multiple assets
            custom_tickers = sys.argv[2:] if len(sys.argv) > 2 else None
            scan_multiple(custom_tickers)
        else:
            # Single asset analysis
            run_north_star(ticker=arg)
    else:
        # Default: BTC analysis
        run_north_star("BTC-USD")
        
        print(f"\n  {C.CYAN}💡 TIP: You can analyze any asset:{C.END}")
        print(f"     python northstar.py ETH-USD")
        print(f"     python northstar.py AAPL")
        print(f"     python northstar.py SCAN              (scan multiple)")
        print(f"     python northstar.py SCAN BTC-USD ETH-USD TSLA\n")
