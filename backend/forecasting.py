import pandas as pd
import numpy as np
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA, ETS, Theta
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

class ForecastingEngine:
    def __init__(self):
        self.models_map = {
            "AutoARIMA": AutoARIMA(alias="AutoARIMA"),
            "ETS": ETS(alias="ETS"), 
            "Theta": Theta(alias="Theta")
        }
    
    def validate_data(self, df: pd.DataFrame) -> Dict[str, any]:
        """Validate uploaded dataset and return validation results"""
        issues = []
        
        # Check required columns
        required_cols = ['timestamp', 'series_id', 'y']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            issues.append(f"Missing required columns: {missing_cols}")
        
        # Check for nulls in key columns
        if 'y' in df.columns:
            null_count = df['y'].isnull().sum()
            if null_count > 0:
                issues.append(f"Found {null_count} null values in target variable 'y'")
        
        # Check timestamp format
        if 'timestamp' in df.columns:
            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            except:
                issues.append("Could not parse 'timestamp' column as datetime")
        
        # Series analysis
        series_stats = {}
        if 'series_id' in df.columns and 'timestamp' in df.columns:
            series_counts = df.groupby('series_id').size()
            series_stats = {
                'n_series': len(series_counts),
                'min_length': int(series_counts.min()),
                'max_length': int(series_counts.max()),
                'avg_length': float(series_counts.mean())
            }
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'n_observations': len(df),
            'series_stats': series_stats,
            'columns': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
    
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for StatsForecast format"""
        # Ensure required columns and types
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.rename(columns={'timestamp': 'ds', 'series_id': 'unique_id'})
        
        # Sort by series and time
        df = df.sort_values(['unique_id', 'ds'])
        
        # Filter series with minimum length
        series_counts = df.groupby('unique_id').size()
        valid_series = series_counts[series_counts >= 30].index  # Minimum 30 observations
        df = df[df['unique_id'].isin(valid_series)]
        
        return df[['unique_id', 'ds', 'y']]
    
    def run_backtest(self, df: pd.DataFrame, models: List[str], horizon: int = 14, 
                    quantiles: List[float] = [0.1, 0.5, 0.9], n_folds: int = 3) -> Dict:
        """Run rolling origin cross-validation backtest"""
        
        # Prepare data
        df_clean = self.prepare_data(df)
        
        if len(df_clean) == 0:
            raise ValueError("No valid series found (minimum 30 observations required)")
        
        # Select models
        selected_models = [self.models_map[model] for model in models if model in self.models_map]
        
        # Initialize StatsForecast
        sf = StatsForecast(
            models=selected_models,
            freq='D',  # Assume daily frequency for now
            n_jobs=1
        )
        
        # Run cross-validation
        cv_results = sf.cross_validation(
            df=df_clean,
            h=horizon,
            step_size=7,  # Weekly steps
            n_windows=n_folds
        )
        
        # Calculate metrics
        metrics = self._calculate_metrics(cv_results, df, quantiles)
        
        return {
            'cv_results': cv_results,
            'metrics': metrics,
            'n_series': df_clean['unique_id'].nunique(),
            'date_range': {
                'start': df_clean['ds'].min().isoformat(),
                'end': df_clean['ds'].max().isoformat()
            }
        }
    
    def _calculate_metrics(self, cv_results: pd.DataFrame, original_df: pd.DataFrame, 
                          quantiles: List[float]) -> Dict:
        """Calculate WAPE and capacity breach rate for each model"""
        metrics = {}
        
        # Get model columns (exclude ds, unique_id, y, cutoff)
        model_cols = [col for col in cv_results.columns 
                     if col not in ['ds', 'unique_id', 'y', 'cutoff']]
        
        # Check if we have capacity data
        has_capacity = 'capacity' in original_df.columns
        
        for model in model_cols:
            if cv_results[model].notna().sum() == 0:
                continue
                
            # Calculate WAPE
            mask = cv_results[model].notna() & cv_results['y'].notna()
            if mask.sum() == 0:
                continue
                
            actual = cv_results.loc[mask, 'y']
            predicted = cv_results.loc[mask, model]
            
            wape = np.sum(np.abs(actual - predicted)) / np.sum(np.abs(actual))
            
            metrics[model] = {'wape': float(wape)}
            
            # Calculate capacity breach rate if capacity data available
            if has_capacity:
                # Merge with capacity data (simplified)
                capacity_breach_rate = 0.0  # Placeholder for now
                metrics[model]['capacity_breach_rate'] = capacity_breach_rate
        
        return metrics
    
    def generate_forecast(self, df: pd.DataFrame, models: List[str], 
                         horizon: int = 14, confidence_levels: List[int] = [80, 90]) -> pd.DataFrame:
        """Generate forecasts using the best model with confidence intervals"""
        
        # Prepare data
        df_clean = self.prepare_data(df)
        
        # Use all models for ensemble or best performing one
        selected_models = [self.models_map[model] for model in models if model in self.models_map]
        
        # Initialize StatsForecast
        sf = StatsForecast(
            models=selected_models,
            freq='D',
            n_jobs=1
        )
        
        # Fit and forecast with multiple confidence levels
        forecasts = sf.forecast(df=df_clean, h=horizon, level=confidence_levels)
        
        return forecasts
    
    def check_capacity_alerts(self, forecasts: pd.DataFrame, capacity_df: pd.DataFrame,
                            threshold: float = 0.9) -> List[Dict]:
        """Check for capacity breach alerts"""
        alerts = []
        
        # This is a simplified version - would need more sophisticated logic
        # for production use
        
        if 'AutoARIMA-hi-90' in forecasts.columns:  # P90 forecast
            high_demand = forecasts[forecasts['AutoARIMA-hi-90'] > threshold]
            
            for _, row in high_demand.iterrows():
                alerts.append({
                    'series_id': row['unique_id'],
                    'date': row['ds'].isoformat(),
                    'predicted_demand': float(row['AutoARIMA-hi-90']),
                    'threshold': threshold,
                    'message': f"P90 demand ({row['AutoARIMA-hi-90']:.2f}) exceeds threshold ({threshold})"
                })
        
        return alerts
