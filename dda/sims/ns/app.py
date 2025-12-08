
"""
DDA NORTH STAR v1.0 - WEB EDITION
═════════════════════════════════
Real-time web interface for your trading compass
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import yfinance as yf
import numpy as np
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)

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
        self.fair_value = self.prices[0]
        
        for price in self.prices:
            self.fair_value = self.P0 * self.fair_value + (1 - self.P0) * price
        
        current_price = self.prices[-1]
        deviation = (current_price - self.fair_value) / self.fair_value * 100
        
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


def get_signal(deviation, volatility):
    """Convert deviation into actionable signal"""
    OVERSOLD = -5.0
    OVERBOUGHT = 6.0
    VERY_OVERSOLD = -10.0
    VERY_OVERBOUGHT = 12.0
    
    if deviation <= VERY_OVERSOLD:
        return "STRONG BUY", "Price is significantly below fair value. Blood in the streets.", 5, "buy-strong"
    elif deviation <= OVERSOLD:
        return "BUY", "Price is below fair value. Good entry zone.", 4, "buy"
    elif deviation >= VERY_OVERBOUGHT:
        return "STRONG SELL", "Price is significantly above fair value. Take profits.", 1, "sell-strong"
    elif deviation >= OVERBOUGHT:
        return "SELL", "Price is above fair value. Consider taking profits.", 2, "sell"
    else:
        if deviation > 3:
            return "HOLD (Warm)", "Approaching overbought. Watch for exit.", 3, "hold-warm"
        elif deviation < -3:
            return "HOLD (Cool)", "Approaching oversold. Watch for entry.", 3, "hold-cool"
        else:
            return "NEUTRAL", "Price is near fair value. No clear edge.", 3, "neutral"


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


def get_action_guidance(signal, current_price, fair_value, sell_zone):
    """Generate action guidance text"""
    if "STRONG BUY" in signal:
        return {
            "action": "Consider BUYING",
            "reason": "Price is deeply oversold. This is historically a good entry point.",
            "entry": f"${current_price:,.2f} or lower",
            "target": f"${fair_value:,.2f} (fair value)",
            "stop_loss": f"${current_price * 0.88:,.2f} (-12%)"
        }
    elif "BUY" in signal:
        return {
            "action": "Consider BUYING",
            "reason": "Price is below fair value.",
            "entry": f"${current_price:,.2f}",
            "target": f"${sell_zone:,.2f} (overbought zone)",
            "stop_loss": f"${current_price * 0.88:,.2f} (-12%)"
        }
    elif "STRONG SELL" in signal:
        return {
            "action": "Consider SELLING",
            "reason": "Price is significantly overbought. High probability of pullback.",
            "target": f"${fair_value:,.2f} (fair value)",
            "entry": None,
            "stop_loss": None
        }
    elif "SELL" in signal:
        return {
            "action": "Consider SELLING or taking profits",
            "reason": "Price is above fair value.",
            "target": f"${fair_value:,.2f} (fair value)",
            "entry": None,
            "stop_loss": None
        }
    else:
        return {
            "action": "WAIT",
            "reason": "No clear edge right now. Price is near fair value.",
            "watch_buy": f"${fair_value * 0.95:,.2f}",
            "watch_sell": f"${fair_value * 1.06:,.2f}",
            "entry": None,
            "target": None,
            "stop_loss": None
        }


# ═══════════════════════════════════════════════════════════════════════════════
# API ROUTES
# ═══════════════════════════════════════════════════════════════════════════════
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze/<ticker>')
def analyze(ticker):
    """Analyze a single asset"""
    try:
        ticker = ticker.upper()
        df = yf.download(ticker, period="60d", interval="1d", progress=False)
        
        if df.empty:
            return jsonify({"error": f"Failed to fetch data for {ticker}"}), 404
        
        prices = df['Close'].values.flatten()
        current_price = float(prices[-1])
        
        dda = DDANorthStar(smoothing=0.96)
        result = dda.calculate(prices)
        
        signal, explanation, strength, signal_class = get_signal(result['deviation'], result['volatility'])
        trend, trend_change = get_trend(prices)
        
        fair_value = result['fair_value']
        buy_zone = fair_value * 0.95
        sell_zone = fair_value * 1.06
        
        vol = result['volatility']
        if vol > 4:
            vol_label = "HIGH"
        elif vol > 2:
            vol_label = "MODERATE"
        else:
            vol_label = "LOW"
        
        action_guidance = get_action_guidance(signal, current_price, fair_value, sell_zone)
        
        # Price history for chart (last 60 days)
        price_history = [{"date": str(df.index[i].date()), "price": float(prices[i])} for i in range(len(prices))]
        
        return jsonify({
            "ticker": ticker,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "candles": len(prices),
            "signal": signal,
            "signal_class": signal_class,
            "explanation": explanation,
            "strength": strength,
            "current_price": current_price,
            "fair_value": fair_value,
            "deviation": result['deviation'],
            "buy_zone": buy_zone,
            "sell_zone": sell_zone,
            "trend": trend,
            "trend_change": trend_change,
            "volatility": vol,
            "volatility_label": vol_label,
            "action_guidance": action_guidance,
            "price_history": price_history
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/scan')
def scan():
    """Scan multiple assets"""
    tickers = ["BTC-USD", "ETH-USD", "SOL-USD", "AAPL", "SPY", "QQQ", "TSLA", "NVDA"]
    results = []
    
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="60d", interval="1d", progress=False)
            if df.empty:
                continue
                
            prices = df['Close'].values.flatten()
            
            dda = DDANorthStar(smoothing=0.96)
            result = dda.calculate(prices)
            signal, _, strength, signal_class = get_signal(result['deviation'], result['volatility'])
            
            results.append({
                'ticker': ticker,
                'price': float(result['current_price']),
                'fair_value': float(result['fair_value']),
                'deviation': float(result['deviation']),
                'signal': signal,
                'signal_class': signal_class,
                'strength': strength
            })
            
        except Exception:
            continue
    
    return jsonify({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "results": results
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
