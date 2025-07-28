# simulation_engine.py

import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# The core libraries for interacting with the blockchain and exchanges
from web3 import Web3
import ccxt

# Import our configuration settings (assuming a config.py file)
# If you don't have one, create a config.py with the variables below
import config

# --- Setup Basic Logging (to a file, not the console) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(getattr(config, 'LOG_FILE', 'simulation.log'))
    ]
)

class SimulationEngine:
    """
    Runs a detailed DeFi simulation with corrected portfolio logic.
    """
    def __init__(self):
        logging.info("Initializing Final DeFi Simulation Engine...")
        print("🔌 Initializing Simulation Engine...")

        self.w3 = Web3(Web3.HTTPProvider(config.ALCHEMY_RPC_URL))
        if not self.w3.is_connected():
            logging.error("CRITICAL: Blockchain connection failed.")
            print("❌ CRITICAL: Could not connect to the Ethereum blockchain.")
            exit()
        logging.info("Blockchain connection successful.")
        print("✅ Successfully connected to Ethereum blockchain.")

        self.cex_exchange = ccxt.binance({'enableRateLimit': True})
        logging.info("CEX connection successful.")
        print("✅ Successfully connected to Binance public API.")

        self.pool_abi = '[{"inputs":[],"name":"slot0","outputs":[{"internalType":"uint160","name":"sqrtPriceX96","type":"uint160"},{"internalType":"int24","name":"tick","type":"int24"},{"internalType":"uint16","name":"observationIndex","type":"uint16"},{"internalType":"uint16","name":"observationCardinality","type":"uint16"},{"internalType":"uint16","name":"observationCardinalityNext","type":"uint16"},{"internalType":"uint8","name":"feeProtocol","type":"uint8"},{"internalType":"bool","name":"unlocked","type":"bool"}],"stateMutability":"view","type":"function"}]'
        self.pool_contract = self.w3.eth.contract(address=Web3.to_checksum_address(config.UNISWAP_POOL_ID), abi=self.pool_abi)
        
        # --- CORRECTED STATE MANAGEMENT ---
        self.balance_usd = config.SIMULATION_CAPITAL_USD # Available cash
        self.in_position = False
        self.entry_price = 0.0
        self.entry_gas_fee = 0.0
        self.exit_gas_fee = 0.0
        
        self.simulated_eth_amount = 0.0
        self.simulated_usdt_amount = 0.0
        
        self.initial_position_value_usd = 0.0
        self.simulated_fees_earned_total = 0.0
        
        self.price_range_min = 0.0
        self.price_range_max = 0.0

    def get_current_price_from_chain(self) -> float:
        try:
            slot0 = self.pool_contract.functions.slot0().call()
            sqrt_price_x96 = slot0[0]
            price = ((sqrt_price_x96 / 2**96)**2) * (10**(18-6))
            return price
        except Exception as e:
            logging.error(f"Failed to get live price from chain: {e}", exc_info=True)
            return 0.0

    def get_market_volume(self) -> float:
        try:
            ohlcv = self.cex_exchange.fetch_ohlcv('ETH/USDT', '1m', limit=1)
            return ohlcv[0][5] if ohlcv else 0.0
        except Exception as e:
            logging.warning(f"Could not fetch 1m volume data from Binance: {e}")
            return 0.0

    def get_historical_data(self) -> pd.DataFrame:
        try:
            since = self.cex_exchange.parse8601((datetime.utcnow() - timedelta(hours=config.RANGE_LOOKBACK_HOURS)).isoformat())
            ohlcv = self.cex_exchange.fetch_ohlcv('ETH/USDT', '1h', since=since, limit=config.RANGE_LOOKBACK_HOURS)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            if not df.empty:
                df['close'] = pd.to_numeric(df['close'])
            return df
        except Exception as e:
            logging.error(f"Could not fetch historical data from Binance: {e}")
            return pd.DataFrame()

    def _calculate_optimal_range(self, historical_data: pd.DataFrame):
        print(f"\n📈 Calculating optimal range based on last {config.RANGE_LOOKBACK_HOURS} hours...")
        if historical_data.empty:
            print("⚠️ Could not fetch historical data for range calculation. Exiting.")
            exit()
            
        average_price = historical_data['close'].mean()
        price_std_dev = historical_data['close'].std()
        self.price_range_min = average_price - (price_std_dev * config.VOLATILITY_MULTIPLIER)
        self.price_range_max = average_price + (price_std_dev * config.VOLATILITY_MULTIPLIER)
        print(f"✅ Optimal range calculated: ${self.price_range_min:,.2f} to ${self.price_range_max:,.2f}\n")

    def _get_dynamic_total_liquidity(self) -> float:
        base_liquidity = 50_000_000
        today = datetime.utcnow().weekday()
        multiplier = 0.85 if today >= 5 else 1.0
        noise = random.uniform(0.95, 1.05)
        return base_liquidity * multiplier * noise

    def _estimate_fees(self, volume_1m: float, current_price: float) -> float:
        if not self.in_position: return 0.0
        total_liquidity_in_pool = self._get_dynamic_total_liquidity()
        your_liquidity_value = (self.simulated_eth_amount * current_price) + self.simulated_usdt_amount
        if total_liquidity_in_pool == 0: return 0.0
        your_share_of_pool = your_liquidity_value / total_liquidity_in_pool
        volume_usd_1m = volume_1m * current_price
        fees = your_share_of_pool * volume_usd_1m * config.FEE_TIER 
        return fees

    def _calculate_il(self, current_price: float) -> float:
        if not self.in_position or self.entry_price == 0: return 0.0
        price_ratio = current_price / self.entry_price
        il = (2 * np.sqrt(price_ratio) / (1 + price_ratio)) - 1
        return il * 100

    def _print_status_row(self, status, price, pos_value, il, fees, pnl, alert):
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        price_str = f"${price:,.2f}"
        pos_val_str = f"${pos_value:,.2f}"
        il_str = f"{il:.2f}%"
        fees_str = f"${fees:.4f}"
        pnl_str = f"${pnl:,.2f}"
        print(f"{timestamp:<22} | {status:<18} | {price_str:<15} | {pos_val_str:<16} | {il_str:<8} | {fees_str:<12} | {pnl_str:<12} | {alert if alert else '---'}")

    def run(self):
        historical_data = self.get_historical_data()
        self._calculate_optimal_range(historical_data)
        
        header = (f"{'Timestamp (UTC)':<22} | {'Status':<18} | {'Current Price':<15} | "
                  f"{'Position Value':<16} | {'IL':<8} | {'Fees Earned':<12} | {'Total PnL':<12} | {'Alert'}")
        print(header)
        print("-" * len(header))
        
        while True:
            try:
                current_price = self.get_current_price_from_chain()
                volume_1m = self.get_market_volume()
                if current_price == 0.0:
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                status, alert = "OUT OF RANGE", ""
                il_percent, fees_this_interval, total_pnl, position_value = 0.0, 0.0, 0.0, 0.0

                if self.in_position:
                    position_value = (self.simulated_eth_amount * current_price) + self.simulated_usdt_amount
                    il_percent = self._calculate_il(current_price)
                    fees_this_interval = self._estimate_fees(volume_1m, current_price)
                    self.simulated_fees_earned_total += fees_this_interval
                    total_pnl = (position_value - self.initial_position_value_usd) + self.simulated_fees_earned_total - (self.entry_gas_fee + self.exit_gas_fee)
                    
                    if self.price_range_min <= current_price <= self.price_range_max:
                        status = "IN RANGE (ACTIVE)"
                        if il_percent < config.IL_EXIT_THRESHOLD_PERCENT:
                            alert = f"IL Alert! Breach ({il_percent:.2f}%)"
                    else:
                        status = "EXITED POSITION"
                        alert = f"Exited: Price out of range at ${current_price:,.2f}"
                        self.exit_gas_fee = config.SIMULATED_GAS_FEE_USD
                        self.balance_usd += position_value # Add liquidated assets back to cash balance
                        total_pnl = (position_value - self.initial_position_value_usd) + self.simulated_fees_earned_total - (self.entry_gas_fee + self.exit_gas_fee)
                        
                        # Reset position state
                        self.in_position = False
                        self.simulated_eth_amount = 0.0
                        self.simulated_usdt_amount = 0.0
                        
                else: # Not in position
                    total_pnl = self.balance_usd - config.SIMULATION_CAPITAL_USD
                    if self.price_range_min <= current_price <= self.price_range_max:
                        status, alert = "POSITION OPENED", f"Entered at ${current_price:,.2f}"
                        
                        # --- CORRECTED INVESTMENT LOGIC ---
                        investment_usd = self.balance_usd * 0.5
                        self.balance_usd -= investment_usd # Decrease available cash
                        
                        self.in_position = True
                        self.entry_price = current_price
                        self.entry_gas_fee = config.SIMULATED_GAS_FEE_USD
                        self.exit_gas_fee = 0.0
                        self.simulated_fees_earned_total = 0.0

                        self.initial_position_value_usd = investment_usd # This is the actual amount invested
                        self.simulated_usdt_amount = self.initial_position_value_usd / 2
                        self.simulated_eth_amount = (self.initial_position_value_usd / 2) / current_price
                        position_value = self.initial_position_value_usd
                        total_pnl = -self.entry_gas_fee # At entry, PnL is just the cost of gas

                self._print_status_row(status, current_price, position_value, il_percent, fees_this_interval, total_pnl, alert)
                
                if status == "EXITED POSITION":
                    print("-" * len(header))

                time.sleep(config.LOOP_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                print("\n🛑 Shutdown signal received. Stopping simulation.")
                break
            except Exception as e:
                logging.error(f"An unexpected error occurred: {e}", exc_info=True)
                print(f"\n💥 An unexpected error occurred: {e}. Check simulation.log for details.")
                time.sleep(config.LOOP_INTERVAL_SECONDS)

if __name__ == '__main__':
    engine = SimulationEngine()
    engine.run()