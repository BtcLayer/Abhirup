# liquidity_bot/main.py

import os
import time
import getpass
from dotenv import load_dotenv
from core.strategy_engine import StrategyEngine

# Define the interval for the strategy cycle in seconds
CYCLE_INTERVAL = 60

def get_secure_keys():
    """
    Gets the private key and Alchemy key, prioritizing .env but falling back to user input.
    """
    load_dotenv()

    private_key = os.getenv("PRIVATE_KEY")
    alchemy_api_key = os.getenv("ALCHEMY_API_KEY")

    if not private_key:
        print("\nCould not find PRIVATE_KEY in .env file.")
        private_key = getpass.getpass("Please enter your wallet's private key: ")

    if not alchemy_api_key:
        print("\nCould not find ALCHEMY_API_KEY in .env file.")
        alchemy_api_key = getpass.getpass("Please enter your Alchemy API key: ")

    return private_key, alchemy_api_key

def main():
    """The main function to run the liquidity bot."""
    print("--- Welcome to the Liquidity Bot ---")
    print("This bot provides concentrated liquidity based on market volatility.")
    
    # --- Get User Input ---
    print("\nAvailable pairs in config: WETH/USDC, WBTC/WETH, WBNB/USDT, etc.")
    trading_pair = input("Enter the pair you want to trade (e.g., WETH/USDC): ")

    try:
        investment_capital = float(input("Enter the amount in USD you want to invest: "))
    except ValueError:
        print("Invalid amount. Please enter a number.")
        return

    # --- Securely Load Keys ---
    # Note: For this simulation, the keys are loaded but not used for transactions yet.
    pk, api_key = get_secure_keys()
    if not pk or not api_key:
        print("Private key and Alchemy API key are required. Exiting.")
        return

    # --- Initialize and Run the Bot ---
    try:
        engine = StrategyEngine(
            trading_pair=trading_pair,
            investment_capital=investment_capital
        )
        
        print(f"\n✅ Bot initialized successfully! Starting main loop (runs every {CYCLE_INTERVAL} seconds)...")
        print("Press Ctrl+C to stop the bot gracefully.")

        # Main loop
        while True:
            engine.run_strategy_cycle()
            time.sleep(CYCLE_INTERVAL)

    except ValueError as e:
        print(f"\n❌ Error initializing bot: {e}")
        print("Please check that the trading pair is in your config.py and try again.")
    except ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("Please check your Alchemy URL/key and internet connection.")
    except KeyboardInterrupt:
        print("\n\nBot stopped by user. Shutting down gracefully...")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    main()