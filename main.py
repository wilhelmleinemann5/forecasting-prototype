#!/usr/bin/env python3
"""
Unified application entry point for Railway deployment.
Serves both FastAPI backend and Streamlit frontend on a single port.
"""
import os
import subprocess
import threading
import time
from pathlib import Path

def start_backend():
    """Start the FastAPI backend server"""
    os.chdir(Path(__file__).parent)
    subprocess.run([
        "python", "-m", "uvicorn", 
        "backend.main:app", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ])

def start_frontend():
    """Start the Streamlit frontend server"""
    os.chdir(Path(__file__).parent)
    # Wait a bit for backend to start
    time.sleep(3)
    subprocess.run([
        "python", "-m", "streamlit", "run", 
        "frontend/app.py",
        "--server.port", os.environ.get("PORT", "8501"),
        "--server.address", "0.0.0.0",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false"
    ])

if __name__ == "__main__":
    # Railway provides PORT environment variable
    port = os.environ.get("PORT", "8501")
    
    if port == "8501":
        # Development mode - run both services
        backend_thread = threading.Thread(target=start_backend, daemon=True)
        backend_thread.start()
        start_frontend()
    else:
        # Production mode - Railway deployment
        # Update frontend to use Railway's port
        os.environ["PORT"] = port
        
        # Start backend in background
        backend_thread = threading.Thread(target=start_backend, daemon=True)
        backend_thread.start()
        
        # Start frontend on Railway's port
        start_frontend()
