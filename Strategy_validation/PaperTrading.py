import ccxt
import gspread
import numpy as np
import os
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from time import sleep
import random

# ========================================================================
# CONFIGURATION (Edit these values)
# ========================================================================
# --- Google Sheets ---
# 🚨 Make sure credentials.json is in the same folder as this script
GOOGLE_SHEETS_CREDENTIALS = "credentials.json"
# 🔑 Paste the key from your Google Sheet's URL here
SPREADSHEET_KEY = "1cUD41LW8KyWMnp9xflX6ZR6XI2382i107p-eVw0qdPo" 
WORKSHEET_NAME = "Sheet1"

# --- Strategy Parameters ---
SYMBOL = "ETH/USDT"
INITIAL_BALANCE_USD = 10000
FEE_TIER = 0.0005
IL_REBALANCE_THRESHOLD = -2.0
LOOP_INTERVAL_SECONDS = 60 # Fetches the last completed 1m candle

# --- Dynamic Range Configuration ---
VOLATILITY_MULTIPLIER = 1.5 
RANGE_LOOKBACK_DAYS = 14

# ========================================================================

class ConcentratedLiquidityBot:
    def __init__(self):
        self.exchange = self._init_exchange()
        self.worksheet = self._init_google_sheets()

        # Dynamic range will be set here
        self.price_range_min = 0
        self.price_range_max = 0

        # Strategy State
        self.balance_usd = INITIAL_BALANCE_USD
        self.asset_amount = 0
        self.entry_price = 0
        self.is_in_position = False
        self.total_fees_earned = 0

    def _init_exchange(self):
        """
        Initializes a public, unauthenticated connection to the live Binance exchange.
        """
        print("🔌 Connecting to Binance (Public API)...")
        try:
            # No API keys are needed for fetching public market data
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'},
            })
            exchange.load_markets()
            print("✅ Successfully connected to Binance Public API.")
            return exchange
        except Exception as e:
            print(f"❌ Exchange connection failed: {e}")
            exit()

    def _init_google_sheets(self):
        """Initializes the connection to Google Sheets using a key."""
        print("📝 Connecting to Google Sheets...")
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS, scopes=scopes)
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(SPREADSHEET_KEY)
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            print(f"✅ Successfully connected to Google Sheet '{spreadsheet.title}'.")
            return worksheet
        except Exception as e:
            print(f"❌ Google Sheets connection failed: {e}")
            return None

    def _calculate_optimal_range(self):
        """
        Fetches historical data to calculate a dynamic price range based on recent volatility.
        """
        print(f"\n📈 Calculating optimal range based on last {RANGE_LOOKBACK_DAYS} days of data...")
        try:
            since = self.exchange.parse8601((datetime.utcnow() - timedelta(days=RANGE_LOOKBACK_DAYS)).isoformat())
            ohlcv = self.exchange.fetch_ohlcv(SYMBOL, '1h', since=since)
            
            if not ohlcv:
                print("⚠️ Could not fetch historical data for range calculation. Exiting.")
                exit()

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['close'] = pd.to_numeric(df['close'])
            
            average_price = df['close'].mean()
            price_std_dev = df['close'].std()

            self.price_range_min = average_price - (price_std_dev * VOLATILITY_MULTIPLIER)
            self.price_range_max = average_price + (price_std_dev * VOLATILITY_MULTIPLIER)

            print(f"✅ Optimal range calculated:")
            print(f"   - Average Price: ${average_price:,.2f}")
            print(f"   - Price Volatility (Std Dev): ${price_std_dev:,.2f}")
            print(f"   - New Range MIN: ${self.price_range_min:,.2f}")
            print(f"   - New Range MAX: ${self.price_range_max:,.2f}\n")

        except Exception as e:
            print(f"❌ Failed to calculate optimal range: {e}. Exiting.")
            exit()

    def _get_market_data(self):
        """Fetches the latest completed 1-minute OHLCV candle."""
        try:
            # Fetch the most recent 1-minute candle
            ohlcv = self.exchange.fetch_ohlcv(SYMBOL, '1m', limit=1)
            if not ohlcv:
                return None
            
            latest_candle = ohlcv[0]
            # Return the close price and volume of that candle
            return {'price': latest_candle[4], 'volume_1m': latest_candle[5]}
        except ccxt.BaseError as e:
            print(f"⚠️ Could not fetch market data: {e}. Retrying...")
            return None

    def _calculate_il(self, current_price):
        if not self.is_in_position or self.entry_price == 0:
            return 0.0
        price_ratio = current_price / self.entry_price
        il = (2 * np.sqrt(price_ratio) / (1 + price_ratio)) - 1
        return il * 100

    def _get_dynamic_total_liquidity(self):
        """
        Simulates the total liquidity in a pool, making it dynamic.
        In a real scenario, this would be a complex query. Here, we simulate it
        based on the day of the week to mimic real-world fluctuations.
        """
        base_liquidity = 50_000_000  # $50M baseline
        today = datetime.utcnow().weekday() # Monday is 0, Sunday is 6

        # Assume liquidity dips slightly on weekends
        if today >= 5: # Saturday or Sunday
            multiplier = 0.85 # 85% of weekday liquidity
        else: # Weekday
            multiplier = 1.0

        # Add a small random fluctuation to simulate market noise
        noise = random.uniform(0.95, 1.05)
        
        return base_liquidity * multiplier * noise

    def _estimate_fees(self, volume_1m):
        """Estimates fees based on the volume of the last 1-minute candle."""
        if not self.is_in_position:
            return 0.0
        
        # This now calls the function for a dynamic, more realistic value
        total_liquidity_in_pool = self._get_dynamic_total_liquidity()
        
        your_liquidity_value = self.asset_amount * self.entry_price
        # Handle case where total liquidity might be zero to avoid division errors
        if total_liquidity_in_pool == 0:
            return 0.0
            
        your_share_of_pool = your_liquidity_value / total_liquidity_in_pool
        
        # We use the volume from the 1-minute candle directly
        volume_usd_1m = volume_1m * self.entry_price # Approximate value
        fees = your_share_of_pool * volume_usd_1m * FEE_TIER
        return fees

    def _update_google_sheet(self, data, status, il_percent, fees, pnl, alert):
        if not self.worksheet:
            print("-> Sheet not available. Skipping update.")
            return
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            position_value = self.asset_amount * data['price'] if self.is_in_position else 0
            row = [
                timestamp, status, f"${data['price']:,.2f}", f"${position_value:,.2f}",
                f"{il_percent:.2f}%", f"${fees:,.6f}", f"${pnl:,.2f}", alert
            ]
            self.worksheet.append_row(row, value_input_option='USER_ENTERED')
            print(f"  -> Sheet Updated: {status} | PnL: ${pnl:,.2f} | Alert: {alert if alert else 'None'}")
        except Exception as e:
            print(f"⚠️ Could not update Google Sheet: {e}")

    def run(self):
        self._calculate_optimal_range()
        
        print("🚀 Starting Concentrated Liquidity Simulator (using public data)...")
        while True:
            data = self._get_market_data()
            if not data:
                sleep(LOOP_INTERVAL_SECONDS)
                continue

            current_price = data['price']
            status = "OUT OF RANGE"
            alert = ""

            if self.is_in_position:
                il_percent = self._calculate_il(current_price)
                fees_this_interval = self._estimate_fees(data['volume_1m'])
                self.total_fees_earned += fees_this_interval
                
                current_value = self.asset_amount * current_price
                initial_value = self.asset_amount * self.entry_price
                pnl = (current_value - initial_value) + self.total_fees_earned

                if self.price_range_min <= current_price <= self.price_range_max:
                    status = "IN RANGE (ACTIVE)"
                    if il_percent < IL_REBALANCE_THRESHOLD:
                        alert = "IL THRESHOLD HIT! REBALANCE NEEDED."
                else:
                    status = "OUT OF RANGE (IDLE)"
                    alert = f"PRICE MOVED OUT OF RANGE! EXIT POSITION."
                    self.balance_usd += self.asset_amount * current_price
                    self.asset_amount = 0
                    self.is_in_position = False
                    print(f"🔴 Exited position at ${current_price:,.2f}")

                self._update_google_sheet(data, status, il_percent, fees_this_interval, pnl, alert)

            else:
                if self.price_range_min <= current_price <= self.price_range_max:
                    self.is_in_position = True
                    self.entry_price = current_price
                    investment_usd = self.balance_usd * 0.5
                    self.asset_amount = investment_usd / current_price
                    self.balance_usd -= investment_usd
                    self.total_fees_earned = 0
                    
                    status = "POSITION OPENED"
                    alert = f"Entered position at ${current_price:,.2f}"
                    print(f"🟢 {alert}")
                    self._update_google_sheet(data, status, 0, 0, 0, alert)
                else:
                    pnl = self.balance_usd - INITIAL_BALANCE_USD
                    self._update_google_sheet(data, status, 0, 0, pnl, alert)
            
            sleep(LOOP_INTERVAL_SECONDS)

if __name__ == "__main__":
    try:
        bot = ConcentratedLiquidityBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user.")
    except Exception as e:
        print(f"\n💥 A critical error occurred: {e}")