from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import pandas as pd
import json
import os
from datetime import datetime
from typing import List

from . import models, schemas
from .models import get_db, create_tables
from .forecasting import ForecastingEngine

# Create tables on startup
create_tables()

app = FastAPI(title="Forecasting Prototype API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize forecasting engine
forecasting_engine = ForecastingEngine()

# Create uploads directory
os.makedirs("uploads", exist_ok=True)

@app.get("/")
async def root():
    return {"message": "Forecasting Prototype API", "version": "1.0.0"}

@app.post("/datasets/upload", response_model=schemas.DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = None,
    column_mapping: str = None,
    db: Session = Depends(get_db)
):
    """Upload and validate a CSV dataset with optional column mapping"""
    
    # Use filename if name not provided
    if not name:
        name = file.filename.replace('.csv', '')
    
    # Save uploaded file
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Read and validate data
    try:
        df = pd.read_csv(file_path)
        validation_result = forecasting_engine.validate_data(df)
        
        if not validation_result['is_valid']:
            raise HTTPException(status_code=400, detail=validation_result['issues'])
        
        # Create dataset record
        dataset = models.Dataset(
            name=name,
            filename=file.filename,
            schema_json=json.dumps(validation_result['dtypes']),
            column_mapping_json=column_mapping or "{}",
            n_series=validation_result['series_stats'].get('n_series', 0),
            n_observations=validation_result['n_observations']
        )
        
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        return schemas.DatasetResponse(
            id=dataset.id,
            name=dataset.name,
            filename=dataset.filename,
            upload_time=dataset.upload_time,
            n_series=dataset.n_series,
            n_observations=dataset.n_observations,
            schema=json.loads(dataset.schema_json)
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

@app.get("/datasets", response_model=List[schemas.DatasetResponse])
async def list_datasets(db: Session = Depends(get_db)):
    """List all uploaded datasets"""
    datasets = db.query(models.Dataset).all()
    return [
        schemas.DatasetResponse(
            id=d.id,
            name=d.name,
            filename=d.filename,
            upload_time=d.upload_time,
            n_series=d.n_series,
            n_observations=d.n_observations,
            schema=json.loads(d.schema_json)
        )
        for d in datasets
    ]

@app.get("/datasets/{dataset_id}/series")
async def get_dataset_series(dataset_id: int, db: Session = Depends(get_db)):
    """Get list of unique series IDs in a dataset"""
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    file_path = f"uploads/{dataset.filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")
    
    try:
        df = pd.read_csv(file_path)
        series_list = df['series_id'].unique().tolist() if 'series_id' in df.columns else []
        return {"series": series_list}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading dataset: {str(e)}")

@app.get("/datasets/{dataset_id}/series/{series_id}/history")
async def get_series_history(dataset_id: int, series_id: str, db: Session = Depends(get_db)):
    """Get historical data for a specific series"""
    dataset = db.query(models.Dataset).filter(models.Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    file_path = f"uploads/{dataset.filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")
    
    try:
        df = pd.read_csv(file_path)
        
        # Filter for the specific series
        if 'series_id' not in df.columns:
            raise HTTPException(status_code=400, detail="series_id column not found")
        
        series_data = df[df['series_id'] == series_id].copy()
        
        if len(series_data) == 0:
            raise HTTPException(status_code=404, detail=f"No data found for series: {series_id}")
        
        # Prepare data in the format expected by StatsForecast
        series_data['timestamp'] = pd.to_datetime(series_data['timestamp'])
        series_data = series_data.rename(columns={'timestamp': 'ds', 'series_id': 'unique_id'})
        series_data = series_data.sort_values('ds')
        
        # Return the last 60 data points to avoid huge responses
        series_data = series_data.tail(60)
        
        return series_data[['ds', 'unique_id', 'y']].to_dict('records')
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading series data: {str(e)}")

@app.post("/models/backtest", response_model=schemas.BacktestResult)
async def run_backtest(
    request: schemas.BacktestRequest,
    db: Session = Depends(get_db)
):
    """Run backtest on a dataset"""
    
    # Get dataset
    dataset = db.query(models.Dataset).filter(models.Dataset.id == request.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Load data
    file_path = f"uploads/{dataset.filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")
    
    try:
        df = pd.read_csv(file_path)
        
        # Run backtest
        backtest_result = forecasting_engine.run_backtest(
            df=df,
            models=request.models,
            horizon=request.horizon,
            quantiles=request.quantiles,
            n_folds=request.n_folds
        )
        
        # Find best model based on WAPE
        best_model = min(backtest_result['metrics'].items(), 
                        key=lambda x: x[1]['wape'])
        
        # Save model config
        model_config = models.ModelConfig(
            dataset_id=request.dataset_id,
            track="baseline",
            models=json.dumps(request.models),
            horizon=request.horizon,
            quantiles=json.dumps(request.quantiles),
            winner_model=best_model[0],
            wape=best_model[1]['wape'],
            capacity_breach_rate=best_model[1].get('capacity_breach_rate', 0.0)
        )
        
        db.add(model_config)
        db.commit()
        db.refresh(model_config)
        
        return schemas.BacktestResult(
            model_config_id=model_config.id,
            winner_model=best_model[0],
            wape=best_model[1]['wape'],
            capacity_breach_rate=best_model[1].get('capacity_breach_rate', 0.0),
            model_results=[
                {"model": model, **metrics} 
                for model, metrics in backtest_result['metrics'].items()
            ]
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Backtest failed: {str(e)}")

@app.post("/forecasts/generate")
async def generate_forecast(
    request: schemas.ForecastRequest,
    db: Session = Depends(get_db)
):
    """Generate forecasts using trained model"""
    
    # Get model config
    model_config = db.query(models.ModelConfig).filter(
        models.ModelConfig.id == request.model_config_id
    ).first()
    
    if not model_config:
        raise HTTPException(status_code=404, detail="Model config not found")
    
    # Get dataset
    dataset = db.query(models.Dataset).filter(
        models.Dataset.id == model_config.dataset_id
    ).first()
    
    try:
        df = pd.read_csv(f"uploads/{dataset.filename}")
        models_list = json.loads(model_config.models)
        
        # Generate forecasts
        forecasts = forecasting_engine.generate_forecast(
            df=df,
            models=models_list,
            horizon=model_config.horizon
        )
        
        # Save forecasts to database (simplified)
        # In production, you'd want to save each forecast point
        
        return {
            "forecast_id": f"fc_{model_config.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "model_config_id": model_config.id,
            "n_series": len(forecasts['unique_id'].unique()) if 'unique_id' in forecasts.columns else 0,
            "horizon": model_config.horizon,
            "forecasts": forecasts.to_dict('records')[:100]  # Limit response size
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Forecast generation failed: {str(e)}")

@app.post("/alerts/create", response_model=schemas.AlertResponse)
async def create_alert(
    request: schemas.AlertRequest,
    db: Session = Depends(get_db)
):
    """Create a capacity alert configuration"""
    
    alert = models.Alert(
        model_config_id=request.model_config_id,
        alert_type=request.alert_type,
        threshold=request.threshold,
        series_filter=json.dumps(request.series_filter or {}),
        is_active=True
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    return schemas.AlertResponse(
        id=alert.id,
        alert_type=alert.alert_type,
        threshold=alert.threshold,
        is_active=alert.is_active,
        created_at=alert.created_at
    )

@app.post("/alerts/check/{alert_id}")
async def check_alerts(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Check for capacity alerts and log to console"""
    
    alert = db.query(models.Alert).filter(models.Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Get model config and dataset
    model_config = db.query(models.ModelConfig).filter(
        models.ModelConfig.id == alert.model_config_id
    ).first()
    
    dataset = db.query(models.Dataset).filter(
        models.Dataset.id == model_config.dataset_id
    ).first()
    
    try:
        df = pd.read_csv(f"uploads/{dataset.filename}")
        models_list = json.loads(model_config.models)
        
        # Generate fresh forecasts
        forecasts = forecasting_engine.generate_forecast(
            df=df,
            models=models_list,
            horizon=model_config.horizon
        )
        
        # Check for alerts
        capacity_df = df[['series_id', 'capacity']] if 'capacity' in df.columns else pd.DataFrame()
        alerts_triggered = forecasting_engine.check_capacity_alerts(
            forecasts=forecasts,
            capacity_df=capacity_df,
            threshold=alert.threshold
        )
        
        # Log alerts to console
        if alerts_triggered:
            print(f"\n🚨 CAPACITY ALERTS TRIGGERED ({len(alerts_triggered)} alerts)")
            print("=" * 60)
            for alert_item in alerts_triggered:
                print(f"Series: {alert_item['series_id']}")
                print(f"Date: {alert_item['date']}")
                print(f"Message: {alert_item['message']}")
                print("-" * 40)
        else:
            print(f"\n✅ No capacity alerts triggered for alert {alert_id}")
        
        return {
            "alert_id": alert_id,
            "alerts_triggered": len(alerts_triggered),
            "alerts": alerts_triggered
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Alert check failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
