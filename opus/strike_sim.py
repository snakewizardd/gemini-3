
#!/usr/bin/env python3
"""
🎯 STRIKE PICKER v5 - ALWAYS SHOWS PICKS FOR EVERY WINDOW
"""

import websocket
import json
import threading
import time
import os
from datetime import datetime, timedelta
from collections import deque
import numpy as np

price_history = deque(maxlen=500)
current_price = 0.0

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# ============ INDICATORS ============

def calc_ema(prices, period):
    if len(prices) < period:
        return prices[-1] if prices else 0
    prices_arr = np.array(prices[-period*2:])
    multiplier = 2 / (period + 1)
    ema = prices_arr[0]
    for price in prices_arr[1:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    prices_arr = np.array(prices[-(period+1):])
    deltas = np.diff(prices_arr)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains) if len(gains) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0.0001
    if avg_loss == 0:
        avg_loss = 0.0001
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_momentum(prices, period=10):
    if len(prices) < period:
        return 0
    start_price = prices[-period]
    end_price = prices[-1]
    if start_price == 0:
        return 0
    return ((end_price - start_price) / start_price) * 100

def calc_volatility(prices, period=20):
    if len(prices) < period:
        return 0.5
    recent = prices[-period:]
    if len(recent) < 2:
        return 0.5
    returns = []
    for i in range(1, len(recent)):
        if recent[i-1] != 0:
            returns.append((recent[i] - recent[i-1]) / recent[i-1])
    if not returns:
        return 0.5
    return np.std(returns) * 100

# ============ SIGNAL CALCULATION ============

def get_signal(prices):
    """Returns signal from -100 to +100"""
    if len(prices) < 30:
        return 0, []
    
    p = list(prices)
    signal = 0
    reasons = []
    
    # Indicators
    ema9 = calc_ema(p, 9)
    ema21 = calc_ema(p, 21)
    rsi = calc_rsi(p, 14)
    mom = calc_momentum(p, 10)
    mom_short = calc_momentum(p, 5)
    
    # 1. RSI Signal
    if rsi > 60:
        signal += 25
        reasons.append(f"RSI {rsi:.0f} bullish 🟢")
    elif rsi > 55:
        signal += 15
        reasons.append(f"RSI {rsi:.0f} leaning up 🟢")
    elif rsi < 40:
        signal -= 25
        reasons.append(f"RSI {rsi:.0f} bearish 🔴")
    elif rsi < 45:
        signal -= 15
        reasons.append(f"RSI {rsi:.0f} leaning down 🔴")
    
    # 2. EMA Crossover
    if ema9 > ema21:
        diff = ((ema9 - ema21) / ema21) * 100
        signal += min(25, diff * 100)
        reasons.append(f"EMA9 > EMA21 🟢")
    else:
        diff = ((ema21 - ema9) / ema9) * 100
        signal -= min(25, diff * 100)
        reasons.append(f"EMA9 < EMA21 🔴")
    
    # 3. Momentum
    if mom > 0.05:
        signal += 25
        reasons.append(f"Momentum +{mom:.2f}% 🟢🟢")
    elif mom > 0.02:
        signal += 15
        reasons.append(f"Momentum +{mom:.2f}% 🟢")
    elif mom < -0.05:
        signal -= 25
        reasons.append(f"Momentum {mom:.2f}% 🔴🔴")
    elif mom < -0.02:
        signal -= 15
        reasons.append(f"Momentum {mom:.2f}% 🔴")
    
    # 4. Short momentum confirms
    if mom_short > 0.03 and mom > 0:
        signal += 15
        reasons.append(f"Accelerating UP 🚀")
    elif mom_short < -0.03 and mom < 0:
        signal -= 15
        reasons.append(f"Accelerating DOWN 📉")
    
    return max(-100, min(100, signal)), reasons

# ============ WINDOWS & STRIKES ============

def get_windows():
    now = datetime.now()
    mins = now.minute
    next_min = (mins // 5 + 1) * 5
    if next_min >= 60:
        next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        next_time = now.replace(minute=next_min, second=0, microsecond=0)
    
    windows = []
    for i in range(4):
        wt = next_time + timedelta(minutes=i*5)
        secs = int((wt - now).total_seconds())
        windows.append({
            'time': wt.strftime('%H:%M'),
            'secs': max(0, secs),
            'mins': (i+1) * 5
        })
    return windows

def get_strikes(price, mins):
    # Wider spacing for longer windows
    spacing = price * (0.0002 + mins * 0.00002)
    return [
        round(price - 2*spacing, 0),
        round(price - spacing, 0),
        round(price, 0),
        round(price + spacing, 0),
        round(price + 2*spacing, 0),
    ]

def calc_yes_prob(current, strike, signal, mins):
    # Base: distance from strike
    dist = (strike - current) / current * 100
    base = 50 - (dist * 15)
    
    # Signal adjustment
    sig_adj = signal * 0.25
    
    # Time adjustment (longer = closer to 50)
    time_adj = (mins / 30) * (50 - abs(base + sig_adj - 50)) * 0.2
    
    prob = base + sig_adj
    if prob > 50:
        prob -= time_adj
    else:
        prob += time_adj
    
    return max(10, min(90, prob))

def payout(prob):
    # Higher payout near 50%
    risk = 1 - abs(prob - 50) / 50
    return round(1.2 + risk * 0.7, 2)

# ============ MAIN DISPLAY ============

def display():
    global current_price
    
    while True:
        if current_price == 0 or len(price_history) < 20:
            clear_screen()
            print("⏳ Loading price data...")
            print(f"   Samples: {len(price_history)}/20")
            if current_price > 0:
                print(f"   BTC: ${current_price:,.0f}")
            time.sleep(1)
            continue
        
        clear_screen()
        now = datetime.now()
        prices = list(price_history)
        signal, reasons = get_signal(prices)
        windows = get_windows()
        
        # Header
        if signal > 25:
            bias = "🟢🟢 BULLISH"
        elif signal > 10:
            bias = "🟢 Lean UP"
        elif signal < -25:
            bias = "🔴🔴 BEARISH"
        elif signal < -10:
            bias = "🔴 Lean DOWN"
        else:
            bias = "⚪ NEUTRAL"
        
        print("═" * 64)
        print(f"  💰 BTC ${current_price:,.0f}  │  Signal: {signal:+.0f}  │  {bias}")
        print("═" * 64)
        
        # Reasons
        for r in reasons[:3]:
            print(f"  • {r}")
        print("")
        
        # Each window with picks
        for w in windows:
            strikes = get_strikes(current_price, w['mins'])
            
            # Find best YES and best NO for this window
            best_yes = {'strike': None, 'prob': 0, 'pay': 0}
            best_no = {'strike': None, 'prob': 0, 'pay': 0}
            
            print(f"  ┌─ {w['time']} ({w['mins']}min) ─ closes in {w['secs']//60}:{w['secs']%60:02d} " + "─" * 30)
            print(f"  │ {'STRIKE':<11}│{'YES':^14}│{'NO':^14}│ PICK")
            print(f"  │ {'':<11}│{'%':>5} {'PAY':>5}   │{'%':>5} {'PAY':>5}   │")
            print(f"  ├" + "─" * 62)
            
            for i, strike in enumerate(strikes):
                yes_p = calc_yes_prob(current_price, strike, signal, w['mins'])
                no_p = 100 - yes_p
                yes_pay = payout(yes_p)
                no_pay = payout(no_p)
                
                # Track best
                if yes_p > best_yes['prob']:
                    best_yes = {'strike': strike, 'prob': yes_p, 'pay': yes_pay}
                if no_p > best_no['prob']:
                    best_no = {'strike': strike, 'prob': no_p, 'pay': no_pay}
                
                # Pick indicator
                zone = " ◀" if i == 2 else "  "
                if yes_p >= 65:
                    pick = "✅ YES"
                elif no_p >= 65:
                    pick = "✅ NO"
                elif yes_p >= 58:
                    pick = "👀 yes"
                elif no_p >= 58:
                    pick = "👀 no"
                else:
                    pick = "   —"
                
                print(f"  │ ${strike:<10,.0f}│{yes_p:>5.0f}% {yes_pay:>4}x  │{no_p:>5.0f}% {no_pay:>4}x  │ {pick}{zone}")
            
            # Window recommendation
            print(f"  ├" + "─" * 62)
            if best_yes['prob'] >= best_no['prob'] and best_yes['prob'] >= 55:
                print(f"  │ 🎯 PICK: ${best_yes['strike']:,.0f} YES ↑  ({best_yes['prob']:.0f}% @ {best_yes['pay']}x)")
            elif best_no['prob'] > best_yes['prob'] and best_no['prob'] >= 55:
                print(f"  │ 🎯 PICK: ${best_no['strike']:,.0f} NO ↓  ({best_no['prob']:.0f}% @ {best_no['pay']}x)")
            else:
                print(f"  │ 🎯 PICK: Nearest strike, {'YES ↑' if signal > 0 else 'NO ↓' if signal < 0 else 'flip coin'}")
            print(f"  └" + "─" * 62)
            print("")
        
        # Footer
        print("═" * 64)
        print(f"  ✅ = strong (65%+)  👀 = decent (58%+)  ◀ = current price zone")
        print(f"  Updated: {now.strftime('%H:%M:%S')}")
        print("═" * 64)
        
        time.sleep(1)

# ============ WEBSOCKET ============

def on_message(ws, message):
    global current_price
    try:
        data = json.loads(message)
        if data.get('type') == 'ticker' and 'price' in data:
            current_price = float(data['price'])
            price_history.append(current_price)
    except:
        pass

def on_error(ws, error):
    print(f"WS Error: {error}")

def on_close(ws, a, b):
    time.sleep(2)
    start_ws()

def on_open(ws):
    print("✅ Connected to Coinbase!")
    ws.send(json.dumps({
        "type": "subscribe",
        "product_ids": ["BTC-USD"],
        "channels": ["ticker"]
    }))

def start_ws():
    ws = websocket.WebSocketApp(
        "wss://ws-feed.exchange.coinbase.com",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    ws.run_forever()

if __name__ == "__main__":
    print("🚀 STRIKE PICKER v5")
    print("Loading...")
    
    t = threading.Thread(target=start_ws, daemon=True)
    t.start()
    
    time.sleep(3)
    display()
