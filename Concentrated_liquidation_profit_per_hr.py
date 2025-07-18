import pandas as pd
import ccxt
from datetime import datetime, timedelta
import numpy as np

# Configuration
YOUR_LIQUIDITY = 10_000  # USD
PRICE_MIN, PRICE_MAX = 3000, 3500
FEE_TIER = 0.0005  # 0.05% fee tier
DAYS_TO_ANALYZE = 7

# 1. Fetch OHLCV data (Binance as price reference)
exchange = ccxt.binance()
ohlcv = exchange.fetch_ohlcv('ETH/USDT', '1h', limit=24*DAYS_TO_ANALYZE)
df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
df['time'] = pd.to_datetime(df['timestamp'], unit='ms')

# 2. Dynamic Parameter Engine (Simulates market conditions)
def get_market_conditions(date, current_price):
    """Returns daily-changing parameters (replace with real API calls)"""
    # Base values (typical for ETH/USDC 0.05% pool)
    base_liquidity = 25_000_000  # $25M baseline
    
    # Liquidity fluctuates with price position in range
    if current_price < 3200:
        liquidity_mult = 0.8 + 0.2*(current_price - PRICE_MIN)/(3200 - PRICE_MIN)
    else:
        liquidity_mult = 1.0 - 0.2*(current_price - 3200)/(PRICE_MAX - 3200)
    
    # Volume multiplier follows weekly patterns (lower on weekends)
    weekday_factor = 0.15 if date.weekday() >= 5 else 0.20  # Sat/Sun vs weekdays
    
    return {
        'dex_volume_multiplier': weekday_factor + 0.05 * np.sin(date.day * 0.5),  # 15-25% range
        'total_liquidity': base_liquidity * liquidity_mult  # $20M-$30M range
    }

# 3. Core Calculation
results = []
for days in range(1, DAYS_TO_ANALYZE + 1):
    day_mask = df['time'] > (df['time'].iloc[-1] - pd.Timedelta(f'{days}d'))
    day_df = df[day_mask].copy()
    
    daily_pnl = []
    for _, row in day_df.iterrows():
        # Calculate execution price (weighted average)
        exec_price = (row['high'] + row['low'] + 2*row['close'])/4
        
        # Only process hours where price was in range
        if PRICE_MIN <= exec_price <= PRICE_MAX:
            params = get_market_conditions(row['time'].date(), exec_price)
            
            # Calculate volume that actually crossed your range
            volume_usd = row['volume'] * exec_price * params['dex_volume_multiplier']
            
            # Your share of fees
            your_share = YOUR_LIQUIDITY / params['total_liquidity']
            hourly_pnl = your_share * (volume_usd * FEE_TIER)
            daily_pnl.append(hourly_pnl)
    
    # Aggregate results
    avg_pnl = np.mean(daily_pnl) if daily_pnl else 0
    active_hours = len(daily_pnl)
    
    # Get latest parameters for display
    latest_params = get_market_conditions(day_df['time'].iloc[-1].date(), 
                                        day_df['close'].iloc[-1])
    
    results.append({
        'Period': f'Last {days} day(s)',
        'Avg $/hr': f"${avg_pnl:.4f}",
        'DEX Volume %': f"{latest_params['dex_volume_multiplier']:.1%}",
        'Liquidity': f"${latest_params['total_liquidity']/1e6:.1f}M",
        'Active Hours': active_hours,
        'Price Range': f"{day_df['low'].min():.0f}-{day_df['high'].max():.0f}"
    })

# 4. Display Results
print(f"\n{'Period':<12} | {'Avg $/hr':<10} | {'Active Hours':<12} | {'ETH Price Range'}")
print("-" * 85)
for r in results:
    print(f"{r['Period']:<12} | {r['Avg $/hr']:<10} | {r['Active Hours']:<12} | {r['Price Range']}")

# 5. Summary Statistics
total_volume = sum(p['volume'] for p in results if 'volume' in p)
print(f"\nKey Insights:")
print(f"- Your liquidity share: {YOUR_LIQUIDITY/25_000_000:.6%} (of $25M baseline)")
print(f"- Max observed hourly profit: ${max(float(r['Avg $/hr'][1:]) for r in results):.4f}")
print(f"- Average active hours/day: {sum(r['Active Hours'] for r in results)/DAYS_TO_ANALYZE:.1f}")