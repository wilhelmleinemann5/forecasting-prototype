#!/usr/bin/env python3
"""
Transform SSIB_Surge_Metrics.csv to the format expected by the forecasting prototype
"""
import pandas as pd
import numpy as np

def transform_ssib_data():
    """Transform the SSIB data to forecasting format"""
    
    # Read the original data
    df = pd.read_csv('sample_data.csv')
    
    print(f"Original data shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Date range: {df['date_part'].min()} to {df['date_part'].max()}")
    print(f"Unique trades: {df['trade'].nunique()}")
    
    # Transform to expected format
    transformed_df = df.rename(columns={
        'date_part': 'timestamp',
        'trade': 'series_id',
        'true_booked_ffe': 'y',
        'offer_rejected_vessel_sold_out': 'capacity'
    })
    
    # Keep only the required columns plus some useful features
    columns_to_keep = [
        'timestamp', 'series_id', 'y', 'capacity',
        'record_count', 'avg_offered_rate_online'
    ]
    
    # Filter columns that exist
    available_columns = [col for col in columns_to_keep if col in transformed_df.columns]
    transformed_df = transformed_df[available_columns]
    
    # Clean the data
    # Convert timestamp to datetime
    transformed_df['timestamp'] = pd.to_datetime(transformed_df['timestamp'])
    
    # Remove rows with null target values
    initial_rows = len(transformed_df)
    transformed_df = transformed_df.dropna(subset=['y'])
    print(f"Removed {initial_rows - len(transformed_df)} rows with null target values")
    
    # Sort by series and time
    transformed_df = transformed_df.sort_values(['series_id', 'timestamp'])
    
    # Filter series with enough data points (minimum 30 for forecasting)
    series_counts = transformed_df.groupby('series_id').size()
    valid_series = series_counts[series_counts >= 30].index
    transformed_df = transformed_df[transformed_df['series_id'].isin(valid_series)]
    
    print(f"Final data shape: {transformed_df.shape}")
    print(f"Valid series with >=30 observations: {len(valid_series)}")
    print(f"Date range: {transformed_df['timestamp'].min()} to {transformed_df['timestamp'].max()}")
    
    # Show sample data
    print("\nSample of transformed data:")
    print(transformed_df.head(10))
    
    # Save transformed data
    output_file = 'forecasting_data.csv'
    transformed_df.to_csv(output_file, index=False)
    print(f"\nTransformed data saved to: {output_file}")
    
    # Show summary stats
    print(f"\nSummary statistics:")
    print(transformed_df.describe())
    
    return transformed_df

if __name__ == "__main__":
    transform_ssib_data()
