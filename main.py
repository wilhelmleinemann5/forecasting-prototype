#!/usr/bin/env python3
"""
Railway deployment entry point - Simple FastAPI backend only.
"""
import os
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Forecasting Prototype API on Railway...")
    
    port = int(os.environ.get("PORT", 8000))
    print(f"🔧 Starting FastAPI backend on port {port}...")
    
    # Start the FastAPI backend directly
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
