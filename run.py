#!/usr/bin/env python3
"""
Simple script to run both backend and frontend locally
"""
import subprocess
import sys
import time
import signal
import os

def run_services():
    """Run both FastAPI backend and Streamlit frontend"""
    
    # Start backend
    print("🚀 Starting FastAPI backend on http://localhost:8000")
    backend_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "backend.main:app", 
        "--reload", 
        "--port", "8000"
    ])
    
    # Wait a moment for backend to start
    time.sleep(3)
    
    # Start frontend
    print("🎨 Starting Streamlit frontend on http://localhost:8501")
    frontend_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", 
        "run", "frontend/app.py",
        "--server.port", "8501"
    ])
    
    print("\n✅ Both services are running!")
    print("📊 Open http://localhost:8501 in your browser")
    print("🔧 API docs available at http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop both services")
    
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down services...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print("✅ Services stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Wait for processes
    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_services()
