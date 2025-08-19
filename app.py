"""
Unified FastAPI + Streamlit application for Railway deployment.
FastAPI serves the API and also hosts the Streamlit frontend.
"""
import os
import subprocess
import threading
import time
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import the existing FastAPI app
from backend.main import app as api_app

# Create the main app
app = FastAPI(title="Forecasting Prototype", version="1.0.0")

# Mount the API routes
app.mount("/api", api_app)

# Redirect root to Streamlit (will be running on a different port internally)
@app.get("/")
async def root():
    return {"message": "Forecasting Prototype", "frontend": "Access the Streamlit frontend", "api": "API available at /api"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "forecasting-prototype"}

def start_streamlit():
    """Start Streamlit in the background"""
    time.sleep(3)  # Give FastAPI time to start
    
    # Start Streamlit on internal port
    subprocess.run([
        "python", "-m", "streamlit", "run", 
        "frontend/app.py",
        "--server.port", "8501",
        "--server.address", "127.0.0.1",
        "--server.headless", "true"
    ])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    # Set API URL for internal communication
    os.environ["API_BASE_URL"] = f"http://127.0.0.1:{port}/api"
    
    # Start Streamlit in background thread
    streamlit_thread = threading.Thread(target=start_streamlit, daemon=True)
    streamlit_thread.start()
    
    # Start FastAPI on Railway's port
    uvicorn.run(app, host="0.0.0.0", port=port)
