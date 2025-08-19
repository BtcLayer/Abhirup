# liquidity_bot/core/services.py

import os
import time
import math
import ccxt
from web3 import Web3
from dotenv import load_dotenv
import traceback
import gspread,config

# Load environment variables from .env file
load_dotenv()

# --- INITIALIZE EXTERNAL CONNECTIONS ---

# Initialize CCXT exchange client (KuCoin)
# We use this for reliable historical data
# In core/services.py

# --- INITIALIZE EXTERNAL CONNECTIONS ---

# Initialize multiple CCXT exchange clients in a prioritized list
exchange_names = ['kucoin', 'binance', 'gateio']
exchanges = []
for name in exchange_names:
    try:
        exchange_class = getattr(ccxt, name)
        exchange = exchange_class()
        exchange.load_markets()
        exchanges.append(exchange)
        print(f"Successfully initialized {name} client.")
    except Exception as e:
        print(f"Could not initialize {name} client: {e}")
# A minimal ABI for a Uniswap V3 style pool to get the current price
# In core/services.py

# A minimal ABI for a Uniswap V3 style pool to get the current price
# In core/services.py

# A minimal ABI for a Uniswap V3 style pool to get the current price
MINIMAL_POOL_ABI = [
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            { "internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160" },
            { "internalType": "int24", "name": "tick", "type": "int24" },
            { "internalType": "uint16", "name": "observationIndex", "type": "uint16" },
            { "internalType": "uint16", "name": "observationCardinality", "type": "uint16" },
            { "internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16" },
            { "internalType": "uint8", "name": "feeProtocol", "type": "uint8" },
            { "internalType": "bool", "name": "unlocked", "type": "bool" }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"type": "address", "name": ""}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"type": "address", "name": ""}],
        "stateMutability": "view",
        "type": "function"
    }
]

def get_web3_instance(chain_config):
    """Initializes and returns a Web3 instance for a given chain."""
    alchemy_api_key = os.getenv("ALCHEMY_API_KEY")
    if not alchemy_api_key:
        raise ValueError("ALCHEMY_API_KEY not found in .env file!")
    
    rpc_url = f"{chain_config['rpc_url']}{alchemy_api_key}"
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if w3.is_connected():
        print(f"Web3 connected successfully to chain ID {chain_config['chain_id']}.")
        return w3
    else:
        raise ConnectionError("Failed to connect to Web3 provider.")

# In core/services.py
# In core/services.py


# Replace the entire get_onchain_price function with this one:
# In core/services.py

def get_onchain_price(w3, pool_address, token0_config, token1_config):
    """
    Fetches the current price from a Uniswap V3 style pool.
    The price is returned in the standard format: amount of token0 per token1.
    """
    pool_contract = w3.eth.contract(address=w3.to_checksum_address(pool_address), abi=MINIMAL_POOL_ABI)
    
    try:
        # We now explicitly ask for data from the 'latest' block to be more robust.
        slot0_data = pool_contract.functions.slot0().call(block_identifier='latest')

        if isinstance(slot0_data, (list, tuple)):
            sqrt_price_x96 = slot0_data[0]
        else:
            sqrt_price_x96 = slot0_data
        
        raw_price_t1_per_t0 = (sqrt_price_x96 / 2**96)**2
        
        if raw_price_t1_per_t0 == 0:
            return None
            
        price_t0_per_t1 = 1 / raw_price_t1_per_t0
        
        adjusted_price = price_t0_per_t1 * (10**token1_config['decimals'] / 10**token0_config['decimals'])
        
        return adjusted_price
    except Exception as e:
        print("--- ERROR DETAILS ---")
        print(f"Caught Exception: {e}")
        traceback.print_exc()
        print("--- END ERROR DETAILS ---")
        return None

    except Exception as e:
        print(f"--- ERROR DETAILS ---")
        print(f"Caught Exception: {e}")
        # This will print the full, detailed traceback to find the exact line
        traceback.print_exc()
        print(f"--- END ERROR DETAILS ---")
        return None
# Add this function to the end of core/services.py

def log_to_google_sheet(data_row):
    """
    Logs a list of data as a new row to the configured Google Sheet.
    
    :param data_row: A list of values to append (e.g., [timestamp, pair, action, price]).
    """
    try:
        # Authenticate with Google Sheets using the JSON credentials file
        gc = gspread.service_account(filename=config.GCP_CREDENTIALS_FILENAME)
        
        # Open the spreadsheet and the specific worksheet
        sh = gc.open(config.SHEET_NAME).worksheet(config.WORKSHEET_NAME)
        
        # Append the data as a new row
        sh.append_row(data_row)
        print(f"✅ Successfully logged action to Google Sheet: {data_row[2]}")

    except FileNotFoundError:
        print(f"❌ Google Sheets Error: Credentials file not found at '{config.GCP_CREDENTIALS_FILENAME}'.")
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ Google Sheets Error: Spreadsheet named '{config.SHEET_NAME}' not found.")
    except gspread.exceptions.WorksheetNotFound:
        print(f"❌ Google Sheets Error: Worksheet named '{config.WORKSHEET_NAME}' not found.")
    except Exception as e:
        print(f"❌ An unexpected error occurred with Google Sheets: {e}")

# In core/services.py

def get_historical_data(trading_pair, lookback_hours):
    """
    Fetches historical OHLCV data by trying a chain of exchanges.
    It tries KuCoin, then Binance, then Gate.io until it finds the data.
    """
    if not exchanges:
        print("No CCXT exchange clients available.")
        return []

    since = exchanges[0].parse8601(exchanges[0].iso8601(int(time.time() * 1000) - lookback_hours * 60 * 60 * 1000))

    for exchange in exchanges:
        try:
            # Attempt to fetch data from the current exchange
            print(f"Attempting to fetch {trading_pair} from {exchange.name}...")
            ohlcv = exchange.fetch_ohlcv(trading_pair, '1h', since)

            # If data is found (list is not empty), process and return it
            if ohlcv:
                print(f"✅ Success! Found data for {trading_pair} on {exchange.name}.")
                closing_prices = [candle[4] for candle in ohlcv]
                return closing_prices

        except Exception as e:
            # This error means the market doesn't exist on this exchange, which is okay.
            print(f"Info: Could not fetch from {exchange.name} ({e.__class__.__name__}). Trying next exchange...")
            continue # Move to the next exchange in the list

    # This line is reached only if the loop completes without finding the data on any exchange
    print(f"❌ Data for {trading_pair} not found on any of the configured exchanges.")
    return []
# Add this function to core/services.py

# In core/services.py

def get_recent_trading_volume(trading_pair, hours_to_check):
    """
    Fetches the total trading volume by trying a chain of exchanges.
    Volume is correctly calculated and returned in the quote currency (e.g., USD).
    """
    if not exchanges:
        print("No CCXT exchange clients available.")
        return 0

    since = exchanges[0].parse8601(exchanges[0].iso8601(int(time.time() * 1000) - hours_to_check * 60 * 60 * 1000))

    # This loop tries each exchange until it finds the data.
    for exchange in exchanges:
        try:
            print(f"Attempting to fetch volume for {trading_pair} from {exchange.name}...")
            ohlcv = exchange.fetch_ohlcv(trading_pair, '1h', since)
            
            if ohlcv:
                # --- CORRECTED VOLUME CALCULATION ---
                # We multiply the base volume (candle[5]) by the closing price (candle[4])
                # for each candle to get the volume in the quote currency (USD).
                total_quote_volume = sum(candle[5] * candle[4] for candle in ohlcv)
                
                print(f"✅ Success! Found volume data on {exchange.name}.")
                print(f"Fetched total volume for {trading_pair} in last {hours_to_check}h: ${total_quote_volume:,.2f}")
                return total_quote_volume

        except Exception as e:
            print(f"Info: Could not fetch volume from {exchange.name} ({e.__class__.__name__}). Trying next exchange...")
            continue

    print(f"❌ Volume data for {trading_pair} not found on any of the configured exchanges.")
    return 0