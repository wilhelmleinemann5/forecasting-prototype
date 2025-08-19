#!/usr/bin/env python3
"""
Unified application entry point for Railway deployment.
Serves both FastAPI backend and Streamlit frontend on a single port.
"""
import os
import subprocess
import threading
import time
import sys
from pathlib import Path

def start_backend():
    """Start the FastAPI backend server"""
    os.chdir(Path(__file__).parent)
    subprocess.run([
        sys.executable, "-m", "uvicorn", 
        "backend.main:app", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ])

def start_frontend():
    """Start the Streamlit frontend server"""
    os.chdir(Path(__file__).parent)
    # Wait a bit for backend to start
    time.sleep(5)
    
    port = os.environ.get("PORT", "8501")
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "frontend/app.py",
        "--server.port", port,
        "--server.address", "0.0.0.0",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--server.headless", "true"
    ])

if __name__ == "__main__":
    print("🚀 Starting Forecasting Prototype...")
    
    # Set environment variables for production
    if "RAILWAY_ENVIRONMENT" in os.environ:
        railway_url = os.environ.get("RAILWAY_STATIC_URL", "https://forecasting-prototype-production.up.railway.app")
        os.environ["API_BASE_URL"] = railway_url
        print(f"📡 API_BASE_URL set to: {railway_url}")
    
    # Start backend in background thread
    print("🔧 Starting backend server...")
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Start frontend on main thread
    print("🎨 Starting frontend server...")
    start_frontend()
