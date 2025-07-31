import ccxt
import pandas as pd
import numpy as np
from datetime import datetime

class BacktestEngine:
    """
    Backtests a dynamic concentrated liquidity strategy for PancakeSwap
    using historical Binance data for the WBNB/USDT pair.
    """

    def __init__(self, config):
        """
        Initializes the backtesting engine with the given configuration.
        """
        self.config = config
        print("📈 Initializing Backtesting Engine for PancakeSwap (WBNB/USDT)...")
        
        # --- State Management ---
        # Manages the state of our portfolio and position throughout the simulation.
        self.balance_usd = self.config['SIMULATION_CAPITAL_USD']
        self.in_position = False
        self.entry_price = 0.0
        self.token0_amount = 0.0  # Represents WBNB
        self.token1_amount = 0.0  # Represents USDT
        self.initial_position_value = 0.0
        self.total_fees_earned = 0.0
        self.price_range_min = 0.0
        self.price_range_max = 0.0
        
        self.exchange = ccxt.binance()

    def fetch_data(self):
        """
        Fetches historical hourly data for the specified pair from Binance.
        """
        print(f"📡 Fetching historical data for {self.config['PAIR']} from Binance...")
        try:
            # Fetch the last 30 days of hourly OHLCV (Open, High, Low, Close, Volume) data.
            since = self.exchange.parse8601((datetime.utcnow() - pd.Timedelta(days=30)).isoformat())
            ohlcv = self.exchange.fetch_ohlcv(self.config['PAIR'], '1h', since=since)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            print(f"✅ Successfully fetched {len(df)} hours of data.")
            return df
        except Exception as e:
            print(f"❌ Failed to fetch data: {e}")
            return None

    def _calculate_range(self, data_slice):
        """
        Calculates the optimal liquidity range based on a 2-hour data slice.
        The range is set based on the mean price and standard deviation.
        """
        average_price = data_slice['close'].mean()
        price_std_dev = data_slice['close'].std()
        
        # If volatility is very low or zero, use a small percentage as a fallback.
        if pd.isna(price_std_dev) or price_std_dev == 0:
            price_std_dev = average_price * 0.01 
            
        self.price_range_min = average_price - (price_std_dev * self.config['VOLATILITY_MULTIPLIER'])
        self.price_range_max = average_price + (price_std_dev * self.config['VOLATILITY_MULTIPLIER'])

    def _estimate_fees(self, position_value, hourly_volume, current_price):
        """
        Estimates the trading fees earned in one hour.
        This is a simplified model and can be tuned with the FEE_ESTIMATE_SCALAR.
        """
        hourly_volume_usd = hourly_volume * current_price
        
        if hourly_volume_usd == 0:
            return 0.0
            
        our_share_of_activity = position_value / hourly_volume_usd
        estimated_fees = (hourly_volume_usd * self.config['FEE_TIER']) * our_share_of_activity * self.config['FEE_ESTIMATE_SCALAR']
        return min(estimated_fees, position_value * 0.001) 

    def _calculate_il(self, current_price):
        """
        Calculates the impermanent loss as a percentage.
        """
        if self.entry_price == 0:
            return 0.0
        price_ratio = current_price / self.entry_price
        il = (2 * np.sqrt(price_ratio) / (1 + price_ratio)) - 1
        return il * 100

    def _print_status_row(self, timestamp, status, price, pos_value, il, fees, pnl, alert):
        """
        Prints a single formatted row of output.
        """
        ts_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        price_str = f"${price:,.2f}"
        pos_val_str = f"${pos_value:,.2f}"
        il_str = f"{il:.2f}%"
        fees_str = f"${fees:.2f}"
        pnl_str = f"${pnl:.2f}"
        print(f"{ts_str:<22} {status:<18} {price_str:<14} {pos_val_str:<14} {il_str:<10} {fees_str:<12} {pnl_str:<12} {alert}")

    def run(self):
        """
        Main backtesting loop that iterates through the historical data.
        """
        data = self.fetch_data()
        if data is None:
            return

        header = f"{'Timestamp (UTC)':<22} {'Status':<18} {'Current Price':<14} {'Position Value':<14} {'IL':<10} {'Fees Earned':<12} {'Total PnL':<12} {'Alert'}"
        print(header)
        print("-" * len(header))

        for i in range(self.config['LOOKBACK_PERIOD_HOURS'], len(data)):
            current_row = data.iloc[i]
            current_price = current_row['close']
            current_volume = current_row['volume']
            timestamp = current_row['timestamp']

            status, alert = "", ""
            position_value, il_percent, fees_this_period, total_pnl = 0.0, 0.0, 0.0, 0.0

            if self.in_position:
                if self.price_range_min <= current_price <= self.price_range_max:
                    status = "IN RANGE (ACTIVE)"
                    position_value = (self.token0_amount * current_price) + self.token1_amount
                    il_percent = self._calculate_il(current_price)
                    fees_this_period = self._estimate_fees(position_value, current_volume, current_price)
                    self.total_fees_earned += fees_this_period
                    total_pnl = (position_value - self.initial_position_value) + self.total_fees_earned
                else:
                    status = "EXITED POSITION"
                    final_position_value = (self.token0_amount * current_price) + self.token1_amount
                    total_pnl = (final_position_value - self.initial_position_value) + self.total_fees_earned
                    alert = f"Exited at ${current_price:,.2f}. Final PnL: ${total_pnl:,.2f}"
                    self.balance_usd += final_position_value
                    
                    self.in_position = False
                    self.total_fees_earned = 0.0
                    position_value = 0.0 
            else:
                status = "OUT OF POSITION"
                lookback_data = data.iloc[i-self.config['LOOKBACK_PERIOD_HOURS']:i]
                self._calculate_range(lookback_data)
                
                if self.price_range_min <= current_price <= self.price_range_max:
                    status = "POSITION OPENED"
                    investment_amount = self.balance_usd * self.config['INVESTMENT_PERCENT']
                    self.balance_usd -= investment_amount
                    
                    self.in_position = True
                    self.entry_price = current_price
                    self.initial_position_value = investment_amount
                    
                    self.token1_amount = investment_amount / 2  # USDT
                    self.token0_amount = (investment_amount / 2) / current_price # WBNB
                    
                    position_value = self.initial_position_value
                    alert = f"Entered at ${current_price:,.2f}. Range: [${self.price_range_min:,.2f} - ${self.price_range_max:,.2f}]"
            
            self._print_status_row(timestamp, status, current_price, position_value, il_percent, fees_this_period, total_pnl, alert)
            
            if status == "EXITED POSITION":
                print("-" * len(header))


if __name__ == '__main__':
    # --- Configuration for WBNB/USDT on PancakeSwap ---
    simulation_config = {
        "PAIR": "BNB/USDT",  # Use BNB/USDT for fetching data from Binance
        "FEE_TIER": 0.0005,  # Represents the 0.05% fee tier
        "SIMULATION_CAPITAL_USD": 1000.0,
        "INVESTMENT_PERCENT": 0.5, 
        "LOOKBACK_PERIOD_HOURS": 2,
        "VOLATILITY_MULTIPLIER": 1.5,
        "FEE_ESTIMATE_SCALAR": 0.1 
    }

    engine = BacktestEngine(simulation_config)
    engine.run()