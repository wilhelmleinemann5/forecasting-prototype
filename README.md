# Forecasting Prototype

A thin wrapper around StatsForecast for business-focused forecasting and decision-making.

## 🚀 Quick Start

### Option 1: Simple Python Script
```bash
# Clone the repository
git clone <repository-url>
cd forecasting-prototype

# Install dependencies
pip install -r requirements.txt

# Run both services with one command
python run.py
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Terminal 1 - Start backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 - Start frontend
streamlit run frontend/app.py --server.port 8501
```

### Option 3: Docker
```bash
# Build and run with Docker Compose
docker-compose up --build
```

Then open **http://localhost:8501** in your browser! 🎉

## Features

- CSV data upload and validation
- Automated backtesting with StatsForecast (AutoARIMA, ETS, Theta)
- Business KPI calculation (WAPE, Capacity Breach Rate)
- Simple capacity alert configuration
- Console logging for alerts

## Data Format

Expected CSV columns:
- `timestamp`: Date/datetime column
- `series_id`: Identifier for each time series
- `y`: Target variable to forecast
- `capacity` (optional): Capacity constraint for alerts

## 📊 How to Use

1. **Upload Data**: Upload a CSV with columns `timestamp`, `series_id`, `y`, and optionally `capacity`
2. **Run Backtest**: Test AutoARIMA, ETS, and Theta models with rolling cross-validation
3. **Generate Forecast**: Create forecasts using the best-performing model
4. **Configure Alerts**: Set up capacity breach alerts that log to console

## 🚀 Deployment Options

### GitHub Codespaces / Gitpod
This project is ready for one-click deployment to cloud development environments.

### Railway / Render
1. Connect your GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python run.py`
4. Expose ports 8000 and 8501

### Docker
```bash
docker build -t forecasting-prototype .
docker run -p 8501:8501 -p 8000:8000 forecasting-prototype
```

## 🧪 Example Data Format

```csv
timestamp,series_id,y,capacity
2024-01-01,route_A,150,200
2024-01-02,route_A,165,200
2024-01-03,route_A,142,200
2024-01-01,route_B,89,120
2024-01-02,route_B,95,120
```
