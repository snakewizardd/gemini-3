"""
DDA v11.0 LIVE EXECUTION ENGINE
-------------------------------
Connects DDA Logic to Real Crypto Markets via CCXT.
"""
import ccxt
import time
import pandas as pd
from datetime import datetime
from dda_scalper import DDAScalper # Assuming you saved your class in a file

# =============================================================================
# 1. CONFIGURATION
# =============================================================================
API_KEY = 'YOUR_API_KEY'
API_SECRET = 'YOUR_API_SECRET'
SYMBOL = 'BTC/USDT'
TIMEFRAME = '5m'
LEVERAGE = 50
POSITION_SIZE_USD = 100.0 # How much margin to use per bet

# SAFETY SWITCH: Set to True to actually lose money
REAL_MONEY_MODE = False 

# =============================================================================
# 2. CONNECT TO EXCHANGE
# =============================================================================
print(f"🔌 Connecting to Exchange...")
# Swap 'binance' for 'cryptocom', 'bybit', 'kraken', etc.
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'} # We want leverage
})

# Initialize the Predator Brain
bot = DDAScalper()

# =============================================================================
# 3. HELPER FUNCTIONS
# =============================================================================
def fetch_latest_price():
    # Fetch the last completed candle
    bars = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=2)
    # bars[-1] is the current open candle (incomplete)
    # bars[-2] is the last CLOSED candle (safe to trade)
    last_close = bars[-2][4] 
    timestamp = bars[-2][0]
    return last_close, timestamp

def execute_order(side):
    if not REAL_MONEY_MODE:
        print(f"⚠️ [PAPER] Simulating {side} Order for ${POSITION_SIZE_USD}")
        return

    try:
        # Calculate quantity based on current price
        ticker = exchange.fetch_ticker(SYMBOL)
        price = ticker['last']
        amount = (POSITION_SIZE_USD * LEVERAGE) / price
        
        # Place Market Order
        order = exchange.create_market_order(SYMBOL, side, amount)
        print(f"✅ ORDER EXECUTED: {side} {amount} contracts @ {price}")
        return order
    except Exception as e:
        print(f"❌ EXECUTION FAILED: {e}")

# =============================================================================
# 4. THE INFINITE LOOP
# =============================================================================
print("🚀 DDA SCALPER IS LIVE. Waiting for next candle...")
last_processed_time = 0

while True:
    try:
        # 1. GET DATA
        price, timestamp = fetch_latest_price()
        
        # Only process if this is a NEW candle
        if timestamp != last_processed_time:
            last_processed_time = timestamp
            human_time = datetime.fromtimestamp(timestamp/1000).strftime('%H:%M')
            
            # 2. THINK (DDA Logic)
            signal, fair_value = bot.update(price)
            
            print(f"[{human_time}] Price: {price} | DDA: {fair_value:.2f} | Signal: {signal}")
            
            # 3. ACT
            if "ENTRY" in signal:
                direction = 'buy' if "LONG" in signal else 'sell'
                print(f"🔥 SACCADE TRIGGERED: {direction.upper()}")
                execute_order(direction)
                
            elif "EXIT" in signal:
                # To exit a Long, we Sell. To exit a Short, we Buy.
                direction = 'sell' if "LONG" in signal else 'buy'
                print(f"🛑 TRAILING STOP TRIGGERED: Close Position")
                execute_order(direction)
        
        # Sleep to save API limits (Check every 30 seconds)
        time.sleep(30)
        
    except Exception as e:
        print(f"⚠️ NETWORK ERROR: {e}")
        time.sleep(60)