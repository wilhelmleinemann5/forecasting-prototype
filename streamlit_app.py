#!/usr/bin/env python3
"""
Streamlit-only entry point for Railway deployment.
This serves just the frontend, with API calls going to the backend service.
"""
import os
import sys
import subprocess

if __name__ == "__main__":
    print("🚀 Starting Streamlit Frontend on Railway...")
    
    # Get Railway's assigned port
    port = os.environ.get("PORT", "8501")
    
    # Set API URL to the backend service
    os.environ["API_BASE_URL"] = "https://forecasting-prototype-production.up.railway.app"
    
    print(f"🎨 Starting Streamlit on port {port}...")
    
    # Start Streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run", 
        "frontend/app.py",
        "--server.port", port,
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--server.fileWatcherType", "none"
    ]
    
    subprocess.run(cmd)
