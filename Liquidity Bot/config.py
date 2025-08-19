# core/config.py

# --- NETWORK & CHAIN CONFIGURATION ---

# A mapping of common tokens to their primary blockchain.
# This allows the bot to automatically select the right network.
# We can expand this list over time.
# In config.py
TOKEN_TO_CHAIN_MAP = {
    'ETH': 'ethereum',
    'WETH': 'ethereum',
    'USDC': 'ethereum',
    'USDT': 'ethereum',
    'DOGE': 'ethereum',
    'SHIB': 'ethereum',
    'LINK': 'ethereum',
    'PEPE': 'ethereum', # <-- ADD THIS LINE
    'CAKE': 'bsc',
    'BNB': 'bsc',
    'BUSD': 'bsc',
    'BTCB': 'bsc'
}

# A dictionary of RPC URLs for different blockchains.
# The bot will combine these with the API key from the .env file.
# In core/config.py

CHAIN_CONFIG = {
    'ethereum': {
        'rpc_url': 'https://eth-mainnet.g.alchemy.com/v2/P4HbegYwKoZjRtKYKJDai',  # <-- CHANGE THIS LINE
        'chain_id': 1
    },
    'bsc': {
        'rpc_url': 'https://bsc-mainnet.g.alchemy.com/v2/', # Keep this for BSC
        'chain_id': 56
    }
}


# --- STRATEGY PARAMETERS ---

# The fee tiers to check for when finding a liquidity pool.
FEE_TIERS = [500, 3000, 10000]

# The number of hours of historical data to look back at.
LOOKBACK_HOURS = 2

# Volatility multiplier for setting price range width.
VOLATILITY_MULTIPLIER = 1.5


# --- GOOGLE SHEETS ---

SHEET_NAME = "LiquidityBot_Performance"
WORKSHEET_NAME = "Live_Trades"
GCP_CREDENTIALS_FILENAME = "credentials.json"
# Add this to your config.py file

# --- POOL & TOKEN CONFIGURATION ---
# We store known pool addresses and token details here.
# This avoids complex, on-the-fly discovery for now.
KNOWN_POOLS = {
    # --- Ethereum Mainnet (Uniswap V3) ---
    'ethereum': {
        # 'WETH/USDC': {
        #     'pool_address': '0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640',
        #     'token0': {'symbol': 'USDC', 'decimals': 6},
        #     'token1': {'symbol': 'WETH', 'decimals': 18}
        # },
        # In config.py
'WETH/USDC': {
    'pool_address': '0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640',
    'fee_tier_percent': 0.05,  # Add the fee tier as a percentage     # Add the pool's approximate TVL in USD
    'token0': {'symbol': 'USDC', 'decimals': 6},
    'token1': {'symbol': 'WETH', 'decimals': 18}
},
        'WBTC/WETH': {
            'pool_address': '0xcbcdf9626bc03e24f779434178a73a0b4bad62ed',
            'token0': {'symbol': 'WBTC', 'decimals': 8},
            'token1': {'symbol': 'WETH', 'decimals': 18}
        },
        'WETH/USDT': {
            'pool_address': '0x11b815efb8f581194ae79006d24e0d814b7697f6',
            'token0': {'symbol': 'WETH', 'decimals': 18},
            'token1': {'symbol': 'USDT', 'decimals': 6}
        },
        'LINK/WETH': {
            'pool_address': '0xa6Cc3C2531FdaA6Ae1A3CA84c2855806728693e8',
            'token0': {'symbol': 'LINK', 'decimals': 18},
            'token1': {'symbol': 'WETH', 'decimals': 18}
        },
        # In config.py, inside the KNOWN_POOLS dictionary under 'ethereum'

'PEPE/WETH': {
    'pool_address': '0x11950d141ecb466130172826ea11323b46de4b74', # <-- VERIFY THIS ADDRESS
    'fee_tier_percent': 0.3,
    'tvl_usd': 20000000, 
    'token0': {'symbol': 'PEPE', 'decimals': 18},
    'token1': {'symbol': 'WETH', 'decimals': 18}
},
    },
    
    # --- Binance Smart Chain (PancakeSwap V3) ---
    'bsc': {
        'WBNB/USDT': {
            'pool_address': '0x36696169c63400971503e9A219BFa8222141c9f2',
            'token0': {'symbol': 'WBNB', 'decimals': 18},
            'token1': {'symbol': 'USDT', 'decimals': 18}
        },
        'WBNB/USDC': {
            'pool_address': '0x995d3190d3043859A5aB3235775353e322355034',
            'token0': {'symbol': 'WBNB', 'decimals': 18},
            'token1': {'symbol': 'USDC', 'decimals': 18}
        },
        'BTCB/WBNB': {
            'pool_address': '0x436592B45A95245100941052431a42E8245d4715',
            'token0': {'symbol': 'BTCB', 'decimals': 18},
            'token1': {'symbol': 'WBNB', 'decimals': 18}
        },
        'ETH/WBNB': {
             'pool_address': '0x7A71619a588b5F3537574581a6f87b819f243E4C',
             'token0': {'symbol': 'ETH', 'decimals': 18},
             'token1': {'symbol': 'WBNB', 'decimals': 18}
        },
        'CAKE/WBNB': {
            'pool_address': '0x166ae0b01c73DE9c2f6d2c9438258326E17aa769',
            'token0': {'symbol': 'CAKE', 'decimals': 18},
            'token1': {'symbol': 'WBNB', 'decimals': 18}
        }
    }
}