
"""
DDA v21.2 "CONTRARIAN OLIVER LIVE"
----------------------------------
LIVE TRADING on Kraken with short volatile windows
Uses WebSocket for real-time data, REST for orders

⚠️ PAPER TRADING MODE BY DEFAULT - Set LIVE_MODE=True to trade real money
"""
import asyncio
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime
from collections import deque
import websockets
import requests
import numpy as np

# ============================================
# CONFIGURATION
# ============================================
LIVE_MODE = False  # ⚠️ SET TO True FOR REAL TRADING
PAIR = "XBT/USD"   # BTC/USD on Kraken
WS_PAIR = "XBT/USD"

# Get these from Kraken: Settings > API > Generate New Key
API_KEY = "YOUR_API_KEY_HERE"
API_SECRET = "YOUR_API_SECRET_HERE"

# Strategy parameters for SHORT TIMEFRAME (1-5 min candles)
TIMEFRAME_SECONDS = 60  # 1-minute candles
LOOKBACK_CANDLES = 50   # 50 candles for DDA warmup

# Contrarian thresholds (tighter for volatile short-term)
OVERSOLD_PCT = -2.5      # Buy when 2.5% below DDA
OVERBOUGHT_PCT = 2.5     # Sell when 2.5% above DDA
STOP_LOSS_PCT = -1.5     # Tight stop for scalping
TAKE_PROFIT_PCT = 2.0    # Take profit at 2%

# Position sizing
TRADE_SIZE_USD = 100     # Trade $100 per position
MAX_POSITIONS = 1        # Only 1 position at a time

# ============================================
# DDA ENGINE (same as backtest)
# ============================================
class LiveDDA:
    def __init__(self, fast_smooth=0.85, slow_smooth=0.95):
        self.fast_smooth = fast_smooth
        self.slow_smooth = slow_smooth
        self.fast_dda = None
        self.slow_dda = None
        self.prices = deque(maxlen=100)
        
    def update(self, price):
        self.prices.append(price)
        
        if self.fast_dda is None:
            self.fast_dda = price
            self.slow_dda = price
            return price, price, 0, 0
        
        self.fast_dda = self.fast_smooth * self.fast_dda + (1 - self.fast_smooth) * price
        self.slow_dda = self.slow_smooth * self.slow_dda + (1 - self.slow_smooth) * price
        
        deviation = (price - self.slow_dda) / self.slow_dda * 100
        
        if len(self.prices) >= 20:
            volatility = np.std(list(self.prices)[-20:]) / np.mean(list(self.prices)[-20:]) * 100
        else:
            volatility = 1.0
            
        return self.fast_dda, self.slow_dda, deviation, volatility


# ============================================
# KRAKEN API HELPERS
# ============================================
class KrakenAPI:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.kraken.com"
        
    def _sign(self, urlpath, data):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        return base64.b64encode(mac.digest()).decode()
    
    def _private_request(self, endpoint, data=None):
        if data is None:
            data = {}
        urlpath = f"/0/private/{endpoint}"
        data['nonce'] = int(time.time() * 1000)
        
        headers = {
            'API-Key': self.api_key,
            'API-Sign': self._sign(urlpath, data)
        }
        
        response = requests.post(
            f"{self.base_url}{urlpath}",
            headers=headers,
            data=data
        )
        return response.json()
    
    def _public_request(self, endpoint, params=None):
        response = requests.get(
            f"{self.base_url}/0/public/{endpoint}",
            params=params
        )
        return response.json()
    
    def get_ticker(self, pair="XBTUSD"):
        result = self._public_request("Ticker", {"pair": pair})
        if result.get('error'):
            print(f"❌ Ticker error: {result['error']}")
            return None
        return result.get('result', {})
    
    def get_balance(self):
        return self._private_request("Balance")
    
    def get_ohlc(self, pair="XBTUSD", interval=1):
        """Get OHLC data. interval in minutes."""
        result = self._public_request("OHLC", {"pair": pair, "interval": interval})
        if result.get('error'):
            print(f"❌ OHLC error: {result['error']}")
            return None
        return result.get('result', {})
    
    def place_order(self, pair, side, volume, order_type="market", price=None):
        """Place an order on Kraken"""
        data = {
            "pair": pair,
            "type": side,  # "buy" or "sell"
            "ordertype": order_type,
            "volume": str(volume),
        }
        if price and order_type == "limit":
            data["price"] = str(price)
            
        if not LIVE_MODE:
            data["validate"] = "true"  # Validate only, don't execute
            
        return self._private_request("AddOrder", data)
    
    def cancel_order(self, txid):
        return self._private_request("CancelOrder", {"txid": txid})
    
    def get_open_orders(self):
        return self._private_request("OpenOrders")


# ============================================
# LIVE TRADING BOT
# ============================================
class ContrOliverLive:
    def __init__(self):
        self.dda = LiveDDA(fast_smooth=0.85, slow_smooth=0.95)
        self.api = KrakenAPI(API_KEY, API_SECRET)
        
        # State
        self.position = None
        self.entry_price = 0
        self.position_size = 0
        self.trade_log = []
        self.equity = []
        self.last_price = 0
        self.candle_prices = deque(maxlen=LOOKBACK_CANDLES)
        self.current_candle = {'open': 0, 'high': 0, 'low': 0, 'close': 0, 'volume': 0}
        self.candle_start_time = 0
        
        # Stats
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0
        
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")
        
    def init_from_history(self):
        """Load historical candles to warm up DDA"""
        self.log("📊 Loading historical data to warm up DDA...")
        
        ohlc_data = self.api.get_ohlc(pair="XBTUSD", interval=1)
        if ohlc_data:
            # Kraken returns data keyed by pair name
            for key in ohlc_data:
                if key != 'last':
                    candles = ohlc_data[key]
                    for candle in candles[-LOOKBACK_CANDLES:]:
                        close_price = float(candle)
                        self.dda.update(close_price)
                        self.candle_prices.append(close_price)
                    self.log(f"✅ Loaded {len(candles)} historical candles")
                    break
    
    def check_signals(self, price, deviation):
        """Check for entry/exit signals"""
        
        # === EXIT LOGIC ===
        if self.position:
            pnl_pct = (price - self.entry_price) / self.entry_price * 100
            
            # Take profit
            if pnl_pct >= TAKE_PROFIT_PCT:
                self.close_position(price, "🤑 TAKE PROFIT")
                return
            
            # Stop loss
            if pnl_pct <= STOP_LOSS_PCT:
                self.close_position(price, "🛑 STOP LOSS")
                return
            
            # Overbought exit
            if deviation > OVERBOUGHT_PCT:
                self.close_position(price, "📈 OVERBOUGHT")
                return
        
        # === ENTRY LOGIC ===
        if not self.position:
            # Oversold - BUY THE BLOOD
            if deviation < OVERSOLD_PCT:
                self.open_position(price, deviation)
    
    def open_position(self, price, deviation):
        """Open a new position"""
        size_btc = TRADE_SIZE_USD / price
        
        self.log(f"🩸 BUY SIGNAL @ ${price:,.2f} | Dev: {deviation:+.2f}%")
        
        if LIVE_MODE:
            result = self.api.place_order(
                pair="XBTUSD",
                side="buy",
                volume=round(size_btc, 8),
                order_type="market"
            )
            if result.get('error'):
                self.log(f"❌ Order failed: {result['error']}")
                return
            self.log(f"✅ Order placed: {result}")
        else:
            self.log(f"📝 [PAPER] Would BUY {size_btc:.6f} BTC @ ${price:,.2f}")
        
        self.position = "long"
        self.entry_price = price
        self.position_size = size_btc
        
        self.trade_log.append({
            'time': datetime.now(),
            'action': 'BUY',
            'price': price,
            'size': size_btc,
            'deviation': deviation
        })
    
    def close_position(self, price, reason):
        """Close the current position"""
        if not self.position:
            return
            
        pnl = (price - self.entry_price) * self.position_size
        pnl_pct = (price - self.entry_price) / self.entry_price * 100
        
        self.log(f"{reason} @ ${price:,.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%)")
        
        if LIVE_MODE:
            result = self.api.place_order(
                pair="XBTUSD",
                side="sell",
                volume=round(self.position_size, 8),
                order_type="market"
            )
            if result.get('error'):
                self.log(f"❌ Order failed: {result['error']}")
                return
            self.log(f"✅ Order placed: {result}")
        else:
            self.log(f"📝 [PAPER] Would SELL {self.position_size:.6f} BTC @ ${price:,.2f}")
        
        # Update stats
        if pnl > 0:
            self.wins += 1
        else:
            self.losses += 1
        self.total_pnl += pnl
        
        self.trade_log.append({
            'time': datetime.now(),
            'action': 'SELL',
            'price': price,
            'size': self.position_size,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason
        })
        
        # Reset position
        self.position = None
        self.entry_price = 0
        self.position_size = 0
        
        # Print stats
        total_trades = self.wins + self.losses
        win_rate = (self.wins / total_trades * 100) if total_trades > 0 else 0
        self.log(f"📊 Stats: {self.wins}W/{self.losses}L ({win_rate:.0f}%) | Total PnL: ${self.total_pnl:+.2f}")
    
    def process_trade(self, trade_data):
        """Process incoming trade from websocket"""
        try:
            price = float(trade_data)
            volume = float(trade_data[1]())
            timestamp = float(trade_data[2]())
            
            self.last_price = price
            
            # Update candle
            if self.candle_start_time == 0:
                self.candle_start_time = timestamp
                self.current_candle = {
                    'open': price, 'high': price, 
                    'low': price, 'close': price, 'volume': volume
                }
            else:
                self.current_candle['high'] = max(self.current_candle['high'], price)
                self.current_candle['low'] = min(self.current_candle['low'], price)
                self.current_candle['close'] = price
                self.current_candle['volume'] += volume
            
            # Check if candle is complete
            if timestamp - self.candle_start_time >= TIMEFRAME_SECONDS:
                # Candle complete - update DDA and check signals
                close_price = self.current_candle['close']
                fast_dda, slow_dda, deviation, volatility = self.dda.update(close_price)
                
                self.log(f"🕯️ Candle: ${close_price:,.2f} | DDA: ${slow_dda:,.2f} | Dev: {deviation:+.2f}% | Vol: {volatility:.2f}%")
                
                # Check for signals
                self.check_signals(close_price, deviation)
                
                # Reset candle
                self.candle_start_time = timestamp
                self.current_candle = {
                    'open': price, 'high': price,
                    'low': price, 'close': price, 'volume': 0
                }
                
        except Exception as e:
            self.log(f"❌ Error processing trade: {e}")
    
    async def connect_websocket(self):
        """Connect to Kraken WebSocket and process trades"""
        uri = "wss://ws.kraken.com/"
        
        self.log(f"🔌 Connecting to Kraken WebSocket...")
        self.log(f"📈 Pair: {WS_PAIR}")
        self.log(f"⏱️ Timeframe: {TIMEFRAME_SECONDS}s candles")
        self.log(f"🎯 Buy: <{OVERSOLD_PCT}% | Sell: >{OVERBOUGHT_PCT}%")
        self.log(f"💰 Trade Size: ${TRADE_SIZE_USD}")
        self.log(f"{'🔴 LIVE MODE' if LIVE_MODE else '🟢 PAPER TRADING'}")
        print("=" * 60)
        
        async with websockets.connect(uri) as ws:
            # Subscribe to trades
            subscribe_msg = {
                "event": "subscribe",
                "pair": [WS_PAIR],
                "subscription": {"name": "trade"}
            }
            await ws.send(json.dumps(subscribe_msg))
            self.log(f"📡 Subscribed to {WS_PAIR} trades")
            
            # Also subscribe to ticker for reference
            ticker_msg = {
                "event": "subscribe", 
                "pair": [WS_PAIR],
                "subscription": {"name": "ticker"}
            }
            await ws.send(json.dumps(ticker_msg))
            
            while True:
                try:
                    message = await ws.recv()
                    data = json.loads(message)
                    
                    # Skip system messages
                    if isinstance(data, dict):
                        if data.get('event') in ['systemStatus', 'subscriptionStatus', 'heartbeat']:
                            continue
                    
                    # Process trade data
                    if isinstance(data, list) and len(data) >= 4:
                        channel_name = data[-2]
                        
                        if channel_name == "trade":
                            trades = data[1]()
                            for trade in trades:
                                self.process_trade(trade)
                                
                except websockets.ConnectionClosed:
                    self.log("🔌 Connection closed, reconnecting...")
                    await asyncio.sleep(5)
                    break
                except Exception as e:
                    self.log(f"❌ WebSocket error: {e}")
                    await asyncio.sleep(1)
    
    async def run(self):
        """Main run loop"""
        print("=" * 60)
        print("🚀 CONTRARIAN OLIVER LIVE - Kraken Edition")
        print("=" * 60)
        
        # Initialize with historical data
        self.init_from_history()
        
        # Connect and run
        while True:
            try:
                await self.connect_websocket()
            except Exception as e:
                self.log(f"❌ Error: {e}")
                self.log("🔄 Reconnecting in 10 seconds...")
                await asyncio.sleep(10)


# ============================================
# SIMPLE POLLING VERSION (no websocket)
# ============================================
def run_polling_mode():
    """
    Simpler version that polls REST API instead of websocket.
    Good for testing without dealing with websocket complexity.
    """
    print("=" * 60)
    print("🚀 CONTRARIAN OLIVER LIVE - Polling Mode")
    print("=" * 60)
    
    bot = ContrOliverLive()
    bot.init_from_history()
    
    print(f"\n{'🔴 LIVE MODE' if LIVE_MODE else '🟢 PAPER TRADING'}")
    print(f"📈 Pair: {PAIR}")
    print(f"⏱️ Polling every {TIMEFRAME_SECONDS}s")
    print(f"🎯 Buy: <{OVERSOLD_PCT}% | Sell: >{OVERBOUGHT_PCT}%")
    print("=" * 60 + "\n")
    
    while True:
        try:
            # Get current ticker
            ticker = bot.api.get_ticker("XBTUSD")
            if ticker:
                for key in ticker:
                    price = float(ticker[key]['c'])  # Last trade price
                    
                    # Update DDA
                    fast_dda, slow_dda, deviation, volatility = bot.dda.update(price)
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    # Position status
                    pos_str = ""
                    if bot.position:
                        pnl_pct = (price - bot.entry_price) / bot.entry_price * 100
                        pos_str = f" | 📍 PnL: {pnl_pct:+.2f}%"
                    
                    print(f"[{timestamp}] BTC: ${price:,.2f} | DDA: ${slow_dda:,.2f} | Dev: {deviation:+.2f}%{pos_str}")
                    
                    # Check signals
                    bot.check_signals(price, deviation)
                    break
            
            time.sleep(TIMEFRAME_SECONDS)
            
        except KeyboardInterrupt:
            print("\n\n🛑 Stopped by user")
            print(f"\n📊 FINAL STATS:")
            print(f"   Wins: {bot.wins}")
            print(f"   Losses: {bot.losses}")
            print(f"   Total PnL: ${bot.total_pnl:+.2f}")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)


# ============================================
# ENTRY POINT
# ============================================
if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 60)
    print("  CONTRARIAN OLIVER LIVE v21.2")
    print("  Kraken Real-Time Trading Bot")
    print("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1]() == "--ws":
        # WebSocket mode
        print("\n🔌 Running in WebSocket mode...")
        bot = ContrOliverLive()
        asyncio.run(bot.run())
    else:
        # Polling mode (simpler, good for testing)
        print("\n📊 Running in Polling mode...")
        print("   (Use --ws flag for WebSocket mode)\n")
        run_polling_mode()
