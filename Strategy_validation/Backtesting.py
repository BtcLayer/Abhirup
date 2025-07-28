import pandas as pd
import ccxt
from datetime import datetime, timedelta
import time
import numpy as np
from tqdm import tqdm

# ========================================================================
# CONFIGURATION
# ========================================================================
YOUR_LIQUIDITY = 1000  # Your simulated liquidity in USD
FEE_TIER = 0.0005        # 0.05% fee tier
MONTHS_TO_ANALYZE = 6
SYMBOL = 'ETH/USDT'

# --- ✨ New Dynamic Range Configuration ✨ ---
# Adjust how "tight" the automatically calculated range is.
# 1.0 = Tighter range (potentially more fees, higher risk)
# 1.5 = Balanced (default)
# 2.0 = Wider range (less fees, lower risk)
VOLATILITY_MULTIPLIER = 1.5

# ========================================================================

# Initialize exchange with rate limiting
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'fetchOHLCVWarning': False,
        'defaultType': 'spot'
    }
})

def fetch_historical_data(symbol, timeframe, months):
    """Fetch OHLCV data in chunks with a progress bar."""
    print(f"Fetching {months} months of historical data for {symbol}...")
    end_date = datetime.now()
    # Fetch a bit more data to ensure we have full months
    start_date = end_date - timedelta(days=30 * months + 5)
    
    all_ohlcv = []
    current_since = int(start_date.timestamp() * 1000)
    end_timestamp = int(end_date.timestamp() * 1000)
    
    with tqdm(total=end_timestamp - current_since, unit='ms', desc='Fetching data') as pbar:
        while current_since < end_timestamp:
            try:
                ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=current_since,
                    limit=1000
                )
                if not ohlcv:
                    break
                
                all_ohlcv.extend(ohlcv)
                last_ts = ohlcv[-1][0]
                pbar.update(last_ts - current_since + 1)
                current_since = last_ts + 1
                
                time.sleep(exchange.rateLimit / 2000)
            except Exception as e:
                print(f"\nError fetching data: {e}")
                break
    return all_ohlcv

def calculate_profit_with_dynamic_range(df):
    """
    Calculates monthly profit by first determining an optimal range for each month.
    """
    results = []
    df['month'] = df['time'].dt.to_period('M')
    
    for month, month_df in df.groupby('month'):
        if month_df.empty:
            continue

        # --- 1. Calculate Optimal Range for THIS month ---
        average_price = month_df['close'].mean()
        price_std_dev = month_df['close'].std()
        
        # Handle cases with no volatility (e.g., very short data period)
        if pd.isna(price_std_dev) or price_std_dev == 0:
            price_std_dev = average_price * 0.05 # Assume 5% volatility

        price_min = average_price - (price_std_dev * VOLATILITY_MULTIPLIER)
        price_max = average_price + (price_std_dev * VOLATILITY_MULTIPLIER)
        
        monthly_profit = 0
        active_hours = 0
        
        # --- 2. Calculate Profit using the determined range ---
        for _, row in month_df.iterrows():
            exec_price = (row['high'] + row['low'] + 2 * row['close']) / 4
            
            if price_min <= exec_price <= price_max:
                # Simplified simulation of market conditions
                liquidity = 25_000_000 * (0.8 + 0.4 * (exec_price - price_min) / (price_max - price_min))
                volume_mult = 0.2 + 0.1 * np.sin(row['time'].day * 0.5)
                
                volume_usd = row['volume'] * exec_price * volume_mult
                your_share = YOUR_LIQUIDITY / liquidity
                monthly_profit += your_share * (volume_usd * FEE_TIER)
                active_hours += 1
        
        results.append({
            'Month': month.strftime('%Y-%m'),
            'Total Profit ($)': round(monthly_profit, 2),
            'Active Hours': active_hours,
            'Total Hours': len(month_df),
            'In Range (%)': round((active_hours / len(month_df)) * 100, 1) if len(month_df) > 0 else 0,
            'Optimal Range': f"${price_min:,.0f} - ${price_max:,.0f}"
        })
    
    return pd.DataFrame(results)

# ========================================================================
# Main Execution
# ========================================================================
if __name__ == "__main__":
    ohlcv_data = fetch_historical_data(SYMBOL, '1h', MONTHS_TO_ANALYZE)
    
    if not ohlcv_data:
        print("Failed to fetch data. Please check your internet connection or API status.")
        exit()
    
    df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['time'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['volume'] = pd.to_numeric(df['volume'])
    
    print(f"\nData Range: {df['time'].min().date()} to {df['time'].max().date()}")
    print(f"Total Data Points: {len(df):,}")
    
    results_df = calculate_profit_with_dynamic_range(df)
    
    # Display results
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 120)
    print("\n--- Monthly Profit Analysis with Dynamic Range ---")
    print(results_df.to_string(index=False))
    
    # Summary statistics
    total_profit = results_df['Total Profit ($)'].sum()
    active_months = sum(results_df['Total Profit ($)'] > 0)
    
    print(f"\n--- Key Insights ---")
    print(f"- Total Profit ({len(results_df)} months): ${total_profit:,.2f}")
    if not results_df.empty:
        print(f"- Most Profitable Month: ${results_df['Total Profit ($)'].max():,.2f}")
        print(f"- Average Monthly Profit: ${results_df['Total Profit ($)'].mean():,.2f}")
    print(f"----------------------")
