import ccxt
import gspread
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from time import sleep
import logging

# --- Setup Basic Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('papertrading.log'),
        logging.StreamHandler()
    ]
)

# ========================================================================
# CONFIGURATION (Edit these values)
# ========================================================================

# --- Google Sheets ---
# 🚨 Make sure your credentials.json file is in the same folder as this script.
GOOGLE_SHEETS_CREDENTIALS = "credentials1.json" 
# 🔑 Paste the key from your Google Sheet's URL here.
SPREADSHEET_KEY = "1_DZ6ztD5M2eUBKwPurz2Zcvvu3s8EFWsVTwV33o2zU8" 
WORKSHEET_NAME = "Sheet1"

# --- Strategy Parameters ---
PAIR = "ETH/USDT"
FEE_TIER = 0.003  # Represents 0.05%
SIMULATION_CAPITAL_USD = 1000.0
INVESTMENT_PERCENT = 0.5 # Use 100% of available capital for each position

# --- Dynamic Range & Timing ---
LOOKBACK_PERIOD_HOURS = 2
VOLATILITY_MULTIPLIER = 1.5
LOOP_INTERVAL_SECONDS = 60 # Check price every 60 seconds

# --- Fee Estimation ---
# Adjust this to make fee estimates more/less aggressive.
# A lower value is more conservative.
FEE_ESTIMATE_SCALAR = 0.1 

# ========================================================================

class PaperTradingBot:
    """
    Paper trades a dynamic concentrated liquidity strategy for PancakeSwap
    using live Binance data and logs results to Google Sheets.
    """

    def __init__(self):
        logging.info("Initializing Paper Trading Bot...")
        self.exchange = self._init_exchange()
        self.worksheet = self._init_google_sheets()

        # --- State Management ---
        self.balance_usd = SIMULATION_CAPITAL_USD
        self.in_position = False
        self.entry_price = 0.0
        self.token0_amount = 0.0  # ETH
        self.token1_amount = 0.0  # USDT
        self.initial_position_value = 0.0
        self.total_fees_earned = 0.0
        self.price_range_min = 0.0
        self.price_range_max = 0.0

    def _init_exchange(self):
        """Initializes a connection to the Binance exchange."""
        logging.info("Connecting to Binance (Public API)...")
        try:
            exchange = ccxt.binance({'enableRateLimit': True})
            exchange.load_markets()
            logging.info("✅ Successfully connected to Binance.")
            return exchange
        except Exception as e:
            logging.error(f"❌ Exchange connection failed: {e}")
            exit()

    def _init_google_sheets(self):
        """Initializes the connection to Google Sheets."""
        if not SPREADSHEET_KEY or SPREADSHEET_KEY == "YOUR_GOOGLE_SHEET_KEY_HERE":
            logging.warning("⚠️ Google Sheet key not provided. Skipping sheet logging.")
            return None
        logging.info("Connecting to Google Sheets...")
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS, scopes=scopes)
            client = gspread.authorize(creds)
            spreadsheet = client.open_by_key(SPREADSHEET_KEY)
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            logging.info(f"✅ Successfully connected to Google Sheet '{spreadsheet.title}'.")
            return worksheet
        except Exception as e:
            logging.error(f"❌ Google Sheets connection failed: {e}")
            return None

    def _get_market_data(self):
        """Fetches the latest price and 1-minute volume from Binance."""
        try:
            # Fetch the most recent 2 1-minute candles to ensure we get the last completed one.
            ohlcv = self.exchange.fetch_ohlcv(PAIR, '1m', limit=2)
            latest_candle = ohlcv[0] # The second to last candle is the last *completed* one
            return {'price': latest_candle[4], 'volume_1m': latest_candle[5]}
        except Exception as e:
            logging.warning(f"Could not fetch market data: {e}. Retrying...")
            return None

    def _calculate_dynamic_range(self):
        """Fetches the last 2 hours of data to calculate the liquidity range."""
        logging.info("Calculating dynamic range...")
        try:
            since = self.exchange.parse8601((datetime.utcnow() - timedelta(hours=LOOKBACK_PERIOD_HOURS)).isoformat())
            ohlcv = self.exchange.fetch_ohlcv(PAIR, '1h', since=since, limit=LOOKBACK_PERIOD_HOURS)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            average_price = df['close'].mean()
            price_std_dev = df['close'].std()

            if pd.isna(price_std_dev) or price_std_dev == 0:
                price_std_dev = average_price * 0.01

            self.price_range_min = average_price - (price_std_dev * VOLATILITY_MULTIPLIER)
            self.price_range_max = average_price + (price_std_dev * VOLATILITY_MULTIPLIER)
            logging.info(f"New range calculated: [${self.price_range_min:,.2f} - ${self.price_range_max:,.2f}]")
        except Exception as e:
            logging.error(f"❌ Failed to calculate dynamic range: {e}")

    def _estimate_fees(self, position_value, volume_1m, current_price):
        """Estimates fees earned in one minute."""
        if volume_1m == 0: return 0.0
        # This is a simplified model. A more complex one would model total pool TVL.
        volume_usd_1m = volume_1m * current_price
        our_share_of_activity = position_value / (volume_usd_1m * 1000) # Assume our liquidity is a small fraction
        estimated_fees = (volume_usd_1m * FEE_TIER) * our_share_of_activity * FEE_ESTIMATE_SCALAR
        return min(estimated_fees, position_value * 0.0001) # Cap fees

    def _calculate_il(self, current_price):
        """Calculates impermanent loss."""
        if self.entry_price == 0: return 0.0
        price_ratio = current_price / self.entry_price
        return ((2 * np.sqrt(price_ratio) / (1 + price_ratio)) - 1) * 100

    def _update_google_sheet(self, status, price, pos_value, il, fees, pnl, alert):
        """Appends a new row to the Google Sheet."""
        if not self.worksheet: return
        try:
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            row_data = [
                timestamp, status, f"${price:,.2f}", f"${pos_value:,.2f}",
                f"{il:.2f}%", f"${fees:.4f}", f"${pnl:.2f}", alert
            ]
            self.worksheet.append_row(row_data, value_input_option='USER_ENTERED')
        except Exception as e:
            logging.error(f"⚠️ Could not update Google Sheet: {e}")

    def run(self):
        """Main paper trading loop."""
        logging.info("🚀 Starting Paper Trading Bot...")
        
        while True:
            try:
                market_data = self._get_market_data()
                if not market_data:
                    sleep(LOOP_INTERVAL_SECONDS)
                    continue

                current_price = market_data['price']
                volume_1m = market_data['volume_1m']
                
                status, alert = "", ""
                position_value, il_percent, fees_this_period, total_pnl = 0.0, 0.0, 0.0, 0.0

                if self.in_position:
                    if self.price_range_min <= current_price <= self.price_range_max:
                        status = "IN RANGE (ACTIVE)"
                        position_value = (self.token0_amount * current_price) + self.token1_amount
                        il_percent = self._calculate_il(current_price)
                        fees_this_period = self._estimate_fees(position_value, volume_1m, current_price)
                        self.total_fees_earned += fees_this_period
                        total_pnl = (position_value - self.initial_position_value) + self.total_fees_earned
                    else:
                        status = "EXITED POSITION"
                        final_position_value = (self.token0_amount * current_price) + self.token1_amount
                        total_pnl = (final_position_value - self.initial_position_value) + self.total_fees_earned
                        alert = f"Exited at ${current_price:,.2f}. Final PnL: ${total_pnl:,.2f}"
                        logging.info(f"🔴 {alert}")
                        self.balance_usd += final_position_value
                        self.in_position = False
                        self.total_fees_earned = 0.0
                        position_value = 0.0
                else:
                    status = "OUT OF POSITION"
                    self._calculate_dynamic_range()
                    if self.price_range_min <= current_price <= self.price_range_max:
                        status = "POSITION OPENED"
                        investment_amount = self.balance_usd * INVESTMENT_PERCENT
                        self.balance_usd -= investment_amount
                        
                        self.in_position = True
                        self.entry_price = current_price
                        self.initial_position_value = investment_amount
                        self.token1_amount = investment_amount / 2
                        self.token0_amount = (investment_amount / 2) / current_price
                        
                        position_value = self.initial_position_value
                        alert = f"Entered at ${current_price:,.2f}. Range: [${self.price_range_min:,.2f} - ${self.price_range_max:,.2f}]"
                        logging.info(f"🟢 {alert}")

                # Log the current state to the console and Google Sheet
                log_message = f"Status: {status}, Price: ${current_price:,.2f}, PnL: ${total_pnl:,.2f}"
                logging.info(log_message)
                self._update_google_sheet(status, current_price, position_value, il_percent, fees_this_period, total_pnl, alert)

                sleep(LOOP_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                logging.info("\n🛑 Bot stopped by user.")
                break
            except Exception as e:
                logging.critical(f"\n💥 A critical error occurred: {e}", exc_info=True)
                sleep(LOOP_INTERVAL_SECONDS)


if __name__ == "__main__":
    bot = PaperTradingBot()
    bot.run()