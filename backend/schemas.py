from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class DatasetUpload(BaseModel):
    name: str
    
class DatasetResponse(BaseModel):
    id: int
    name: str
    filename: str
    upload_time: datetime
    n_series: int
    n_observations: int
    schema: Dict[str, str]
    
    class Config:
        from_attributes = True

class BacktestRequest(BaseModel):
    dataset_id: int
    models: List[str] = ["AutoARIMA", "ETS", "Theta"]
    horizon: int = 14
    quantiles: List[float] = [0.1, 0.5, 0.9]
    n_folds: int = 3

class BacktestResult(BaseModel):
    model_config_id: int
    winner_model: str
    wape: float
    capacity_breach_rate: float
    model_results: List[Dict[str, Any]]

class ForecastRequest(BaseModel):
    model_config_id: int
    origin_date: Optional[str] = None

class AlertRequest(BaseModel):
    model_config_id: int
    alert_type: str = "capacity_breach"
    threshold: float = 0.9  # P90 threshold
    series_filter: Optional[Dict[str, Any]] = None

class AlertResponse(BaseModel):
    id: int
    alert_type: str
    threshold: float
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
