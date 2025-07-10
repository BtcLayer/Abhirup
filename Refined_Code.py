import logging
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import pandas as pd
import numpy as np
import traceback
from datetime import datetime

# Configure logging
def setup_logging():
    """Set up comprehensive logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('trader_clustering.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def cluster_traders_large(df, n_clusters=7, batch_size=100):
    """
    Cluster traders in batches using Mini-Batch K-Means with robust error handling
    
    Parameters:
    df (pd.DataFrame): Input dataframe containing trader data
    n_clusters (int): Number of clusters to create (default: 7)
    batch_size (int): Number of accounts to process in each batch (default: 100)
    
    Returns:
    pd.DataFrame: DataFrame with cluster assignments and features
    """
    try:
        logger.info("Starting clustering process")
        start_time = datetime.now()
        
        # Feature extraction function with NaN handling
        def extract_features(trader_data):
            try:
                monthly_data = trader_data.groupby('Month').agg(
                    Cumulative_PnL=('Cumulative PnL', 'last'),
                    Timestamp=('Timestamp IST', 'last')
                ).reset_index()
                
                if monthly_data.empty:
                    logger.warning(f"No monthly data for account {trader_data['Account'].iloc[0]}")
                    return None
                
                timeline_features = monthly_data.set_index('Timestamp')['Cumulative_PnL']
                
                monthly_changes = timeline_features.diff().dropna()
                trend_stability = monthly_changes.std() if not monthly_changes.empty else 0
                
                cumulative_max = timeline_features.cummax()
                drawdown = cumulative_max - timeline_features
                max_drawdown = drawdown.max() if not drawdown.empty else 0
                recovery_factor = timeline_features.iloc[-1] / max_drawdown if max_drawdown > 0 else 10
                
                trades = trader_data['Closed PnL'].dropna()
                n_trades = len(trades)
                
                if n_trades > 0:
                    wins = trades > 0
                    win_rate = wins.mean()
                    win_sum = trades[wins].sum()
                    loss_sum = trades[~wins].sum()
                    profit_factor = win_sum / abs(loss_sum) if loss_sum < 0 else 10
                    trade_skew = trades.skew() if n_trades > 2 else 0
                    trade_kurt = trades.kurtosis() if n_trades > 3 else 0
                else:
                    win_rate = profit_factor = trade_skew = trade_kurt = 0
                
                trade_density = n_trades / len(monthly_data) if len(monthly_data) > 0 else 0
                
                return {
                    'Cumulative_PnL': timeline_features.iloc[-1],
                    'Timeline_Length': len(monthly_data),
                    'Trend_Stability': trend_stability,
                    'Max_Drawdown': max_drawdown,
                    'Recovery_Factor': recovery_factor,
                    'Win_Rate': win_rate,
                    'Profit_Factor': profit_factor,
                    'Trade_Skewness': trade_skew,
                    'Trade_Kurtosis': trade_kurt,
                    'Trade_Density': trade_density,
                    'Account': trader_data['Account'].iloc[0]
                }
            except Exception as e:
                logger.error(f"Error extracting features for account {trader_data['Account'].iloc[0] if not trader_data.empty else 'unknown'}: {str(e)}")
                logger.error(traceback.format_exc())
                return None
        
        # Get unique accounts
        unique_accounts = df['Account'].unique()
        n_accounts = len(unique_accounts)
        logger.info(f"Total accounts to process: {n_accounts}")
        
        # Initialize MiniBatchKMeans
        mbk = MiniBatchKMeans(
            n_clusters=n_clusters,
            random_state=42,
            batch_size=batch_size,
            compute_labels=True,
            n_init=3
        )
        
        # Initialize storage
        all_features = []
        processed_accounts = 0
        skipped_accounts = 0
        
        # Process accounts in batches
        for i in range(0, n_accounts, batch_size):
            batch_accounts = unique_accounts[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: accounts {i} to {min(i+batch_size, n_accounts)-1}")
            
            try:
                batch_df = df[df['Account'].isin(batch_accounts)]
                batch_features = []
                
                for account, trader_data in batch_df.groupby('Account'):
                    try:
                        features = extract_features(trader_data)
                        if features is not None:
                            batch_features.append(features)
                            processed_accounts += 1
                        else:
                            skipped_accounts += 1
                    except Exception as e:
                        logger.error(f"Error processing account {account}: {str(e)}")
                        skipped_accounts += 1
                        continue
                
                if batch_features:
                    batch_feature_df = pd.DataFrame(batch_features)
                    all_features.append(batch_feature_df)
                
            except Exception as e:
                logger.error(f"Error processing batch {i//batch_size + 1}: {str(e)}")
                logger.error(traceback.format_exc())
                continue
        
        if not all_features:
            logger.error("No features extracted - cannot perform clustering")
            return pd.DataFrame()
        
        # Combine all features
        feature_df = pd.concat(all_features, ignore_index=True)
        logger.info(f"Successfully processed {processed_accounts} accounts, skipped {skipped_accounts} accounts")
        
        # Handle missing/infinite values
        numeric_cols = feature_df.select_dtypes(include=np.number).columns
        for col in numeric_cols:
            initial_nans = feature_df[col].isna().sum()
            if initial_nans > 0:
                logger.warning(f"Column {col} has {initial_nans} NaN values - filling with median")
            
            feature_df[col] = feature_df[col].replace([np.inf, -np.inf], np.nan)
            median_val = feature_df[col].median()
            feature_df[col] = feature_df[col].fillna(median_val)
        
        # Standardize features
        scaler = StandardScaler()
        features_to_scale = feature_df.drop('Account', axis=1)
        
        try:
            scaled_features = scaler.fit_transform(features_to_scale)
            
            # Perform clustering with MiniBatchKMeans
            feature_df['Cluster'] = mbk.fit_predict(scaled_features)
            
            # Add PCA components for visualization
            pca = PCA(n_components=2)
            principal_components = pca.fit_transform(scaled_features)
            feature_df['PC1'] = principal_components[:, 0]
            feature_df['PC2'] = principal_components[:, 1]
            
            logger.info(f"Clustering completed successfully in {datetime.now() - start_time}")
            logger.info(f"Cluster distribution:\n{feature_df['Cluster'].value_counts()}")
            
            return feature_df
        
        except Exception as e:
            logger.error(f"Error during clustering: {str(e)}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    except Exception as e:
        logger.error(f"Fatal error in clustering process: {str(e)}")
        logger.error(traceback.format_exc())
        return pd.DataFrame()

def generate_cluster_files(merged_df, n_clusters=7):
    """Generate separate CSV files for each cluster with Account and Closed PnL"""
    try:
        logger.info("Generating cluster-specific files...")
        
        # Ensure we have the required columns
        if 'Account' not in merged_df.columns or 'Closed PnL' not in merged_df.columns:
            raise ValueError("Missing required columns in dataframe")
        
        for cluster_num in range(n_clusters):
            try:
                # Filter for current cluster and select columns
                cluster_df = merged_df[merged_df['Cluster'] == cluster_num][['Account', 'Closed PnL']]
                
                # Remove duplicates (keep last record per account)
                cluster_df = cluster_df.drop_duplicates(subset=['Account'], keep='last')
                
                # Save to CSV
                cluster_filename = f'Cluster {cluster_num}.csv'
                cluster_df.to_csv(cluster_filename, index=False)
                logger.info(f"Saved {cluster_filename} with {len(cluster_df)} accounts")
                
            except Exception as e:
                logger.error(f"Error generating Cluster {cluster_num} file: {str(e)}")
                logger.error(traceback.format_exc())
        
        logger.info("Cluster files generation completed")
        return True
    except Exception as e:
        logger.error(f"Error in cluster files generation: {str(e)}")
        logger.error(traceback.format_exc())
        return False

# Main execution
if __name__ == "__main__":
    logger.info("Starting trader clustering application")
    
    try:
        # Load and preprocess data
        logger.info("Loading data...")
        df = pd.read_csv("simple_straight.csv")
        
        logger.info("Preprocessing data...")
        df['Closed PnL'] = df['Closed PnL'].replace('-', np.nan).astype(float)
        df['Timestamp IST'] = pd.to_datetime(df['Timestamp IST'])
        df = df.sort_values(['Account', 'Timestamp IST'])
        df['Cumulative PnL'] = df.groupby('Account')['Closed PnL'].cumsum()
        df['Month'] = df['Timestamp IST'].dt.to_period('M')
        
        # Perform clustering
        logger.info("Starting clustering...")
        clustered_data = cluster_traders_large(df, n_clusters=7, batch_size=100)
        
        if not clustered_data.empty:
            # Merge with original data
            logger.info("Merging results with original data...")
            merged_df = df.merge(right=clustered_data, on='Account')
            
            # Save main results
            merged_df.to_csv('clustered_traders_results.csv', index=False)
            logger.info("Main results saved successfully")
            
            # Generate cluster-specific files
            generate_cluster_files(merged_df)
            
            logger.info("Process completed successfully")
        else:
            logger.error("Clustering failed - no results to save")
    
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        logger.error(traceback.format_exc())