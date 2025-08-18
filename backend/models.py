from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class Dataset(Base):
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    filename = Column(String)
    upload_time = Column(DateTime, default=datetime.utcnow)
    schema_json = Column(Text)
    n_series = Column(Integer)
    n_observations = Column(Integer)
    
class ModelConfig(Base):
    __tablename__ = "model_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer)
    track = Column(String, default="baseline")
    models = Column(Text)  # JSON list of model names
    horizon = Column(Integer, default=14)
    quantiles = Column(Text)  # JSON list of quantiles
    created_at = Column(DateTime, default=datetime.utcnow)
    winner_model = Column(String)
    wape = Column(Float)
    capacity_breach_rate = Column(Float)

class Forecast(Base):
    __tablename__ = "forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    model_config_id = Column(Integer)
    series_id = Column(String)
    origin_ts = Column(DateTime)
    horizon_step = Column(Integer)
    forecast_ts = Column(DateTime)
    y_pred = Column(Float)
    quantile = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    model_config_id = Column(Integer)
    alert_type = Column(String, default="capacity_breach")
    threshold = Column(Float)
    series_filter = Column(Text)  # JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Database setup
DATABASE_URL = "sqlite:///./forecasting.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
