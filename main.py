#!/usr/bin/env python3
"""
Railway deployment entry point.
Runs the integrated FastAPI + Streamlit application.
"""
import os
import sys

if __name__ == "__main__":
    print("🚀 Starting Forecasting Prototype on Railway...")
    
    # Import and run the integrated app
    from integrated_app import app
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    print(f"🔧 Starting integrated app on port {port}...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
