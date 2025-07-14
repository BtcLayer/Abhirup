import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pathlib import Path
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("Starting trading analysis script")

        # Define output directories
        output_dirs = {
            'equity': 'equity_curve',
            'drawdown': 'drawdown_curve',
            'asset': 'asset_allocation_curve',
            'behavior': 'behavior_analysis'
        }

        # Create directories if they don't exist
        for dir_path in output_dirs.values():
            Path(dir_path).mkdir(parents=True, exist_ok=True)

        # Load data files
        try:
            logger.info("Loading data files...")
            df = pd.read_csv(r"/home/ec2-user/Abhirup/simple_straight.csv")
            df2 = pd.read_csv(r"/home/ec2-user/Abhirup/Top_traders_hyperliquid_rank_30_06.csv")
            df4 = pd.read_csv(r"/home/ec2-user/Abhirup/Cluster 1.csv")
            logger.info("Data files loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load data files: {str(e)}", exc_info=True)
            raise

        # Data processing
        try:
            logger.info("Processing data...")
            data = df[df['Account'].isin(list(df2['account'].unique()))]
            df2.rename(columns={'account':'Account'}, inplace=True)
            df3 = data.merge(right=df2, on='Account')
            
            # Numeric conversions and calculations
            df3['Closed PnL'] = df3['Closed PnL'].replace('-', np.nan).astype(float)
            df3['Timestamp IST'] = pd.to_datetime(df3['Timestamp IST'])
            df3['approx_trade_duration'] = df3.groupby('Account')['Timestamp IST'].diff().dt.total_seconds()
            df3['equity_curve'] = df3.groupby(['Account', pd.Grouper(key='Timestamp IST', freq='D')])['Closed PnL'].cumsum()
            
            # Risk metrics
            min_drawdown = 0.001
            df3['calmar_ratio'] = df3['ROI_Profit_Percent'] / np.maximum(abs(df3['max_drawdown']), min_drawdown)
            df3['calmar_ratio'] = df3['calmar_ratio'].replace([np.inf, -np.inf], np.nan)
            
            # Trading behavior metrics
            threshold = df3['trading_frequency'].median()
            df3['overtrading_flag'] = (df3['trading_frequency'] > threshold).astype(int)
            df3['consistency_score'] = df3.groupby('Account')['Closed PnL'].transform('std')
            
            # Clean up columns
            cols_to_drop = ['normalized_win_rate', 'normalized_average_return',
                          'normalized_sharpe_ratio', 'normalized_profit_factor',
                          'normalized_maximum_drawdown', 'normalized_ROI_Profit_Percent',
                          'normalized_trading_frequency', 'normalized_trader_consistency',
                          'Ranking_Score', 'rank']
            df3.drop(columns=cols_to_drop, axis=1, inplace=True)
            
            # More calculations
            loss_threshold = -0.05
            df3['is_stop_loss_hit'] = (df3['Closed PnL'] / df3['Size USD'] <= loss_threshold).astype(int)
            df3['stop_loss_hit_rate'] = df3.groupby('Account')['is_stop_loss_hit'].transform('mean')
            df3['loss_pct'] = np.where(df3['Closed PnL'] < 0, df3['Closed PnL'] / df3['Size USD'], 0)
            df3['avg_loss_magnitude'] = df3.groupby('Account')['loss_pct'].transform('mean')
            
            # Position sizing
            df3['total_equity'] = df3.groupby('Account')['sum_pnl'].transform('max')
            df3['position_size_pct'] = df3['Size USD'] / (df3['total_equity'] + 1e-6)
            df3['implied_leverage'] = df3['total_volume'] / (df3['total_equity'] + 1e-6)
            
            # Trust score
            df3['trust_score'] = (df3['total_volume'] * 0.5 + df3['sum_pnl'] * 0.5)
            df3['trust_score'] = (df3['trust_score'] - df3['trust_score'].min()) / (df3['trust_score'].max() - df3['trust_score'].min())
            
            # Filter and strategy classification
            df3 = df3[df3['approx_trade_duration'] >= 0]
            conditions = [
                (df3['trading_frequency'] > 8000) & (df3['approx_trade_duration'] < 1800),
                (df3['approx_trade_duration'] > 86400),
                (df3['trading_frequency'] < 1000)
            ]
            choices = ['scalping', 'swing', 'hodl']
            df3['strategy_type'] = np.select(conditions, choices, default='unknown')
            
            # Time-based metrics
            df3['month'] = df3['Timestamp IST'].dt.to_period('M')
            monthly_pnl = df3.groupby(['Account', 'month', 'Coin'])['Closed PnL'].sum().reset_index()
            btc_monthly = df3[df3['Coin'] == 'BTC'].groupby('month')['Closed PnL'].sum()
            df3['market_condition'] = df3['month'].map(btc_monthly.apply(lambda x: 'bull' if x > 0 else 'bear'))
            
            # Additional metrics for original df
            df3['avg_win_size'] = df3['total_positive_pnl'] / df3['no_of_wins']
            df3['risk_reward_ratio'] = df3['avg_win_size'] / abs(df3['avg_loss_per_trade'])
            
            # Filter to cluster accounts
            df = df[df['Account'].isin(list(df4['Account'].unique()))]
            
            logger.info("Data processing completed successfully")
        except Exception as e:
            logger.error(f"Error during data processing: {str(e)}", exc_info=True)
            raise

        def plot_interactive_asset_allocation(account_id):
            try:
                account_data = df[df['Account'] == account_id]
                if len(account_data) == 0:
                    logger.warning(f"No data for account {account_id}")
                    return None
                
                asset_allocation = account_data.groupby('Coin')['Size USD'].sum().reset_index()
                
                plt.figure(figsize=(8, 8))
                colors = plt.cm.tab20.colors
                plt.pie(asset_allocation['Size USD'], 
                       labels=asset_allocation['Coin'],
                       autopct='%1.1f%%',
                       startangle=90,
                       colors=colors,
                       wedgeprops={'linewidth': 1, 'edgecolor': 'white'})
                plt.title(f'Asset Allocation: Account {account_id}', pad=20)
                plt.tight_layout()
                
                logger.debug(f"Generated asset allocation for account {account_id}")
                return plt
                
            except Exception as e:
                logger.error(f"Error generating asset allocation for account {account_id}: {str(e)}", exc_info=True)
                return None

            

        # Process accounts and generate plots
        unique_accounts = df['Account'].unique()
        logger.info(f"Found {len(unique_accounts)} accounts to process")
        
        success_count = 0
        error_count = 0
        
        for i, account in enumerate(unique_accounts, 1):
            try:
                logger.info(f"Processing account {i}/{len(unique_accounts)}: {account}")
                
                # Equity Curve
                fig = plot_interactive_equity_curve(account)
                if fig:
                    output_path = os.path.join(output_dirs['equity'], f"{account}.png")
                    fig.savefig(output_path, dpi=100, bbox_inches='tight')
                    plt.close()
                    logger.debug(f"Saved equity curve for {account}")
                
                # Drawdown Curve
                fig = plot_interactive_drawdown(account)
                if fig:
                    output_path = os.path.join(output_dirs['drawdown'], f"{account}.png")
                    fig.savefig(output_path, dpi=100, bbox_inches='tight')
                    plt.close()
                    logger.debug(f"Saved drawdown curve for {account}")
                
                # Asset Allocation
                fig = plot_interactive_asset_allocation(account)
                if fig:
                    output_path = os.path.join(output_dirs['asset'], f"{account}.png")
                    fig.savefig(output_path, dpi=100, bbox_inches='tight')
                    plt.close()
                    logger.debug(f"Saved asset allocation for {account}")
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to process account {account}: {str(e)}", exc_info=True)
                continue

        # Generate behavior analysis plots
        try:
            logger.info("Generating behavior analysis plots")
            save_behavior_analysis_plots()
            logger.info("Behavior analysis plots generated successfully")
        except Exception as e:
            logger.error(f"Error generating behavior analysis plots: {str(e)}", exc_info=True)
            raise

        logger.info(f"Script completed. Successfully processed {success_count} accounts, {error_count} failures")
        
    except Exception as e:
        logger.critical(f"Script failed: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("Script execution finished")

if __name__ == "__main__":
    main()