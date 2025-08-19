# liquidity_bot/core/strategy_engine.py
from datetime import datetime  # <--- ADD THIS LINE
from . import services
import numpy as np
from . import services      # Use a dot (.) for a file in the same directory
import config             # Import from the root directory directly
from utils import helpers # This line was already correct

class StrategyEngine:
    def __init__(self, trading_pair, investment_capital):
        """
        Initializes the trading bot engine.
        :param trading_pair: The pair to trade, e.g., "WETH/USDC".
        :param investment_capital: The amount in USD to invest.
        """
        print(f"Initializing Strategy Engine for {trading_pair} with ${investment_capital}...")

        # --- Basic Setup ---
        self.trading_pair = trading_pair
        self.investment_capital = float(investment_capital)
        self.state = 'SEARCHING'  # Initial state
        self.current_position = {}
        self.log_row=None
        # --- Dynamic Chain and Pool Setup ---
        base_token = trading_pair.split('/')[1] # e.g., 'USDC' from 'WETH/USDC'
        self.chain_name = config.TOKEN_TO_CHAIN_MAP.get(base_token)

        if not self.chain_name:
            raise ValueError(f"Could not determine chain for token {base_token}")

        print(f"Detected chain: {self.chain_name}")
        self.chain_config = config.CHAIN_CONFIG[self.chain_name]
        
        # Get pool details from our config
        pool_info = config.KNOWN_POOLS[self.chain_name].get(trading_pair)
        if not pool_info:
            raise ValueError(f"Pool details not found for {trading_pair} on {self.chain_name}")

        self.pool_address = pool_info['pool_address']
        self.token0_config = pool_info['token0']
        self.token1_config = pool_info['token1']
        
        # --- Initialize Services ---
        self.w3 = services.get_web3_instance(self.chain_config)
# In core/strategy_engine.py

    def _calculate_dynamic_range(self):
        """
        Calculates the dynamic price range using a two-tiered fallback system.
        1. Tries to find the direct crypto-to-crypto pair on all exchanges.
        2. If that fails, it builds a synthetic price history using USDT pairs.
        """
        # --- Tier 1: Attempt to Fetch Direct Pair ---
        base, quote = self.trading_pair.split('/')
        base_cex = base.replace('WETH', 'ETH').replace('WBNB', 'BNB')
        quote_cex = quote.replace('WETH', 'ETH').replace('WBNB', 'BNB')
        cex_pair_direct = f"{base_cex}/{quote_cex}"

        print(f"\n--- Tier 1 Search: Looking for direct pair '{cex_pair_direct}' on all exchanges ---")
        direct_prices = services.get_historical_data(cex_pair_direct, config.LOOKBACK_HOURS)

        if direct_prices:
            # Success with Tier 1
            print(f"✅ Direct pair data found.")
            final_prices = np.array(direct_prices)
        else:
            # --- Tier 2: Fallback to Synthetic Pair History ---
            print(f"\n--- Tier 2 Search: Building synthetic history for '{cex_pair_direct}' via USDT ---")
            base_usdt_pair = f"{base_cex}/USDT"
            quote_usdt_pair = f"{quote_cex}/USDT"
            
            base_prices_usdt = services.get_historical_data(base_usdt_pair, config.LOOKBACK_HOURS)
            quote_prices_usdt = services.get_historical_data(quote_usdt_pair, config.LOOKBACK_HOURS)

            if not base_prices_usdt or not quote_prices_usdt:
                print("❌ Synthetic history failed: Could not fetch one or both USDT pairs from any exchange.")
                return None, None

            min_len = min(len(base_prices_usdt), len(quote_prices_usdt))
            base_prices_usdt = np.array(base_prices_usdt[-min_len:])
            quote_prices_usdt = np.array(quote_prices_usdt[-min_len:])

            if np.any(quote_prices_usdt == 0):
                print("Error: Quote price is zero, cannot create synthetic history.")
                return None, None
            
            final_prices = base_prices_usdt / quote_prices_usdt

        # --- Final Calculation (applies to both tiers) ---
        std_dev = np.std(final_prices)
        mean_price = np.mean(final_prices)
        lower_bound = mean_price - (std_dev * config.VOLATILITY_MULTIPLIER)
        upper_bound = mean_price + (std_dev * config.VOLATILITY_MULTIPLIER)

        print(f"✅ Successfully calculated dynamic range: [{lower_bound:.8f} - {upper_bound:.8f}]")
        return lower_bound, upper_bound

    def _check_for_entry(self):
        """Checks if the current price is within the calculated range to enter a position."""
        print("\nState: SEARCHING. Looking for an entry point...")
        
        lower, upper = self._calculate_dynamic_range()
        if lower is None:
            return
        # NEW CORRECT LINE
        current_price = services.get_onchain_price(
            self.w3, 
            self.pool_address, 
            self.token0_config, 
            self.token1_config
        )
        if current_price is None:
            return

        # print(f"Current on-chain price for {self.trading_pair}: ${current_price:,.4f}")
        print(f"Current on-chain price for {self.trading_pair}: {helpers.format_price(current_price)}")
        if lower <= current_price <= upper:
            print(f"✅ ENTRY SIGNAL: Current price is within the dynamic range.")
            # In a real scenario, we would execute the add_liquidity transaction here.
            # For now, we just simulate the entry.
            self.state = 'IN_POSITION'
# In the `_check_for_entry` method, update the self.current_position dictionary
            self.current_position = {
                'entry_price': current_price,
                'lower_bound': lower,
                'upper_bound': upper,
                'capital': self.investment_capital,
                'entry_timestamp': datetime.now() # <-- ADD THIS LINE
            }
            print(f"Calculated dynamic range: [{helpers.format_price(lower)} - {helpers.format_price(upper)}]")
            print(f"--- FAKING ENTRY: State changed to IN_POSITION ---")
            # Inside the _check_for_entry method in the `if` block

            # --- ADD THIS LOGGING CODE ---
            self.log_row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.trading_pair,
                "ENTER",
                self.current_position['entry_price'],
                f"Range: {helpers.format_price(self.current_position['lower_bound'])} - {helpers.format_price(self.current_position['upper_bound'])}",
                self.investment_capital
            ]
            # --- END OF LOGGING CODE ---
            services.log_to_google_sheet(self.log_row)
        else:
            print(f"❌ HOLD SIGNAL: Current price is outside the dynamic range.")

# In core/strategy_engine.py

    def _check_for_exit(self):
        """Checks if the current price has moved out of the position's range and calculates full PnL."""
        print(f"\nState: IN_POSITION. Monitoring position with range [{helpers.format_price(self.current_position['lower_bound'])} - {helpers.format_price(self.current_position['upper_bound'])}]")

        current_price = services.get_onchain_price(
            self.w3, 
            self.pool_address, 
            self.token0_config, 
            self.token1_config
        )
        if current_price is None:
            return
            
        print(f"Current on-chain price for {self.trading_pair}: {helpers.format_price(current_price)}")

        if not (self.current_position['lower_bound'] <= current_price <= self.current_position['upper_bound']):
            print(f"🛑 EXIT SIGNAL: Price has moved out of range.")
            print(f"--- FAKING EXIT: State changed to SEARCHING ---")

            # --- FULL PNL CALCULATION ---
            # 1. Calculate time in position to fetch relevant volume
            time_in_position_hours = (datetime.now() - self.current_position['entry_timestamp']).total_seconds() / 3600
            
            # 2. Get recent trading volume from CEX
            ccxt_pair = self.trading_pair.replace('WETH', 'ETH')
            recent_volume = services.get_recent_trading_volume(ccxt_pair, int(time_in_position_hours) + 1)
            
            # 3. Estimate fees earned
            pool_config = config.KNOWN_POOLS[self.chain_name][self.trading_pair]
            pool_fee_tier = pool_config['fee_tier_percent'] / 100
            pool_tvl = pool_config['tvl_usd']
            
            total_fees_generated = recent_volume * pool_fee_tier
            our_pool_share = self.investment_capital / pool_tvl
            estimated_fees_usd = total_fees_generated * our_pool_share

            # 4. Calculate Impermanent Loss
            entry_price = self.current_position['entry_price']
            price_ratio = current_price / entry_price
            impermanent_loss_pct = (2 * (price_ratio**0.5) / (1 + price_ratio)) - 1
            
            # 5. Calculate final position value (including IL and estimated fees)
            hodl_value = self.investment_capital * price_ratio
            final_position_value = (hodl_value * (1 + impermanent_loss_pct)) + estimated_fees_usd
            
            # 6. Calculate final PnL in USD
            pnl_usd = final_position_value - self.investment_capital
            # --- END OF FULL PNL CALCULATION ---

            self.log_row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.trading_pair,
                "EXIT",
                current_price,
                f"Exited Range: {helpers.format_price(self.current_position['lower_bound'])} - {helpers.format_price(self.current_position['upper_bound'])}",
                self.investment_capital,
                f"{impermanent_loss_pct:.4%}",
                estimated_fees_usd,         # New Column H: Estimated Fees
                final_position_value,       # New Column I: Final Value
                pnl_usd                     # New Column J: PnL (USD)
            ]
            self.current_position = {}
            services.log_to_google_sheet(self.log_row)
        else:
            print(f"✅ HOLD SIGNAL: Price remains in range. Position active.")

    def run_strategy_cycle(self):
        """The main loop of the strategy logic."""
        try:
            if self.state == 'SEARCHING':
                self._check_for_entry()
            if self.state == 'IN_POSITION':
                self._check_for_exit()
        except Exception as e:
            print(f"The error is {self.state}")