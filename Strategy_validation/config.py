# config.py

# ===================================================================
# DATA SOURCE CONFIGURATION (Alchemy)
# ===================================================================
# Your personal, reliable gateway to the Ethereum blockchain.
# 🚨 PASTE YOUR ALCHEMY HTTPS URL HERE.
ALCHEMY_RPC_URL = "https://eth-mainnet.g.alchemy.com/v2/RmoFnGYZ3M0DDzRVlyYGe"


# ===================================================================
# STRATEGY CONFIGURATION
# ===================================================================
# The unique ID of the specific Uniswap pool we want to monitor.
# This ID corresponds to the ETH / USDT 0.30% fee tier pool.
UNISWAP_POOL_ID = "0x11b815efb8f581194ae79006d24e0d814b7697f6"
FEE_TIER=0.0005

# ===================================================================
# SIMULATION PARAMETERS
# ===================================================================
SIMULATION_CAPITAL_USD = 1000.0
# A realistic, average gas fee (in USD) for an on-chain transaction.
SIMULATED_GAS_FEE_USD = 0.1

# The interval in seconds for the main simulation loop.
LOOP_INTERVAL_SECONDS = 30


# ===================================================================
# STRATEGY PARAMETERS
# ===================================================================
RANGE_LOOKBACK_HOURS = 2 # 2 days
VOLATILITY_MULTIPLIER = 1.5
IL_EXIT_THRESHOLD_PERCENT = -2.0


# ===================================================================
# FILE PATHS
# ===================================================================
LOG_FILE = 'defi_simulation.log'