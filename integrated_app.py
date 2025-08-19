"""
Integrated FastAPI application that serves both API and Streamlit frontend.
This approach works best with Railway's single-port requirement.
"""
import os
import asyncio
import subprocess
import threading
import time
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import requests

# Import the existing FastAPI backend
from backend.main import app as backend_app

# Create the main integrated app
app = FastAPI(title="Forecasting Prototype", version="1.0.0")

# Global variable to track Streamlit process
streamlit_process = None

def start_streamlit():
    """Start Streamlit in the background on internal port"""
    global streamlit_process
    try:
        print("🎨 Starting Streamlit frontend...")
        streamlit_process = subprocess.Popen([
            "python", "-m", "streamlit", "run", 
            "frontend/app.py",
            "--server.port", "8501",
            "--server.address", "127.0.0.1",
            "--server.headless", "true",
            "--server.enableCORS", "false",
            "--server.enableXsrfProtection", "false"
        ])
        print("✅ Streamlit started on internal port 8501")
    except Exception as e:
        print(f"❌ Failed to start Streamlit: {e}")

# Mount the backend API under /api prefix
app.mount("/api", backend_app)

@app.on_event("startup")
async def startup_event():
    """Start Streamlit when the app starts"""
    # Set API URL for internal communication
    os.environ["API_BASE_URL"] = "http://127.0.0.1:" + os.environ.get("PORT", "8000") + "/api"
    
    # Start Streamlit in background thread
    streamlit_thread = threading.Thread(target=start_streamlit, daemon=True)
    streamlit_thread.start()
    
    # Wait a moment for Streamlit to start
    await asyncio.sleep(3)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown"""
    global streamlit_process
    if streamlit_process:
        streamlit_process.terminate()

@app.get("/")
async def root():
    """Proxy to Streamlit frontend"""
    try:
        # Try to proxy the request to Streamlit
        response = requests.get("http://127.0.0.1:8501", timeout=5)
        return HTMLResponse(content=response.content, status_code=response.status_code)
    except:
        # Fallback if Streamlit isn't ready
        return HTMLResponse(content="""
        <html>
            <head><title>Forecasting Prototype</title></head>
            <body>
                <h1>🚀 Forecasting Prototype</h1>
                <p>Starting up... Please refresh in a few seconds.</p>
                <p><a href="/api">API Documentation</a></p>
                <script>setTimeout(() => location.reload(), 3000);</script>
            </body>
        </html>
        """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    streamlit_status = "unknown"
    try:
        response = requests.get("http://127.0.0.1:8501/_stcore/health", timeout=2)
        streamlit_status = "healthy" if response.status_code == 200 else "unhealthy"
    except:
        streamlit_status = "down"
    
    return {
        "status": "healthy",
        "services": {
            "api": "healthy",
            "frontend": streamlit_status
        }
    }

# Proxy other requests to Streamlit
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_to_streamlit(request: Request, path: str):
    """Proxy requests to Streamlit"""
    # Skip API routes
    if path.startswith("api/"):
        return {"error": "API route not found"}
    
    try:
        # Forward the request to Streamlit
        url = f"http://127.0.0.1:8501/{path}"
        
        if request.method == "GET":
            response = requests.get(url, params=request.query_params, timeout=10)
        else:
            # For POST requests, forward the body
            body = await request.body()
            response = requests.request(
                method=request.method,
                url=url,
                data=body,
                headers=dict(request.headers),
                timeout=10
            )
        
        return HTMLResponse(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>Could not connect to frontend: {e}</p></body></html>",
            status_code=502
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting integrated app on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
