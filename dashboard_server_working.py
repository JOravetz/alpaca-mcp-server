#!/usr/bin/env python3
"""
Working Dashboard Server - Uses analyze_peaks.py to generate real charts
Saves charts to /tmp directory for easy cleanup
Auto-cleans ports and launches browser
"""

import json
import subprocess
import asyncio
import base64
import os
import signal
import time
import webbrowser
import socket
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Working Dashboard API - Real Charts from analyze_peaks.py")

# Enable CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).parent
ANALYZE_PEAKS_SCRIPT = BASE_DIR / "analyze_peaks.py"

@app.get("/")
async def serve_dashboard():
    """Serve the dashboard HTML"""
    dashboard_file = BASE_DIR / "ultimate_4day_dashboard.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    else:
        # Return a simple test page if dashboard doesn't exist
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Chart Test</title>
            <style>
                body { background: #0f0f0f; color: white; font-family: monospace; padding: 20px; }
                button { background: #00D9FF; color: black; padding: 10px; margin: 5px; cursor: pointer; }
                #chart { margin-top: 20px; }
                img { max-width: 100%; }
            </style>
        </head>
        <body>
            <h1>Real Chart Generator Test</h1>
            <button onclick="generateChart('AAPL')">Generate AAPL Chart</button>
            <button onclick="generateChart('NEON')">Generate NEON Chart</button>
            <button onclick="generateChart('TSLA')">Generate TSLA Chart</button>
            <div id="chart"></div>
            <script>
                async function generateChart(symbol) {
                    const chartDiv = document.getElementById('chart');
                    chartDiv.innerHTML = '<p>Generating chart for ' + symbol + '...</p>';
                    
                    try {
                        const response = await fetch('/api/chart/' + symbol);
                        const data = await response.json();
                        
                        if (data.chart_data) {
                            chartDiv.innerHTML = '<img src="' + data.chart_data + '" alt="' + symbol + ' chart">';
                        } else {
                            chartDiv.innerHTML = '<p>Error: ' + (data.error || 'No chart data') + '</p>';
                        }
                    } catch (error) {
                        chartDiv.innerHTML = '<p>Error: ' + error + '</p>';
                    }
                }
            </script>
        </body>
        </html>
        """)

@app.get("/api/chart/{symbol}")
async def generate_chart(
    symbol: str,
    timeframe: str = "1Day",
    days: int = 30,
    window: int = 11
):
    """
    Generate peak/trough analysis chart using analyze_peaks.py
    
    Args:
        symbol: Stock symbol
        timeframe: Time interval (1Min, 5Min, 15Min, 30Min, 1Hour, 1Day)
        days: Number of days to analyze
        window: Hanning filter window size
    """
    try:
        # Build command to run analyze_peaks.py with save-plot option
        cmd = [
            "python3", str(ANALYZE_PEAKS_SCRIPT),
            "-s", symbol,
            "-t", timeframe,
            "-n", str(days),
            "-w", str(window),
            "--save-plot"  # This will save to /tmp with auto-generated name
        ]
        
        logger.info(f"Executing: {' '.join(cmd)}")
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=BASE_DIR
        )
        
        if result.returncode != 0:
            logger.error(f"Chart generation failed: {result.stderr}")
            return JSONResponse({
                "status": "error",
                "error": f"Failed to generate chart: {result.stderr}"
            })
        
        # Parse output to find the saved file path
        output_lines = result.stdout.split('\n')
        saved_path = None
        
        for line in output_lines:
            if "Chart saved to:" in line or "successfully saved to:" in line:
                # Extract the path from the output
                parts = line.split(":")
                if len(parts) > 1:
                    saved_path = parts[-1].strip()
                    break
        
        if not saved_path:
            # Try to find the file in /tmp
            import glob
            pattern = f"/tmp/{symbol}_{timeframe}_*.png"
            files = sorted(glob.glob(pattern), key=lambda x: Path(x).stat().st_mtime, reverse=True)
            if files:
                saved_path = files[0]
                logger.info(f"Found chart file: {saved_path}")
        
        if saved_path and Path(saved_path).exists():
            # Read the image and convert to base64
            with open(saved_path, 'rb') as f:
                image_data = f.read()
            
            base64_image = base64.b64encode(image_data).decode('utf-8')
            chart_data = f"data:image/png;base64,{base64_image}"
            
            # Clean up the file after reading (optional, since it's in /tmp)
            # Path(saved_path).unlink()
            
            return JSONResponse({
                "status": "success",
                "chart_data": chart_data,
                "symbol": symbol,
                "parameters": {
                    "timeframe": timeframe,
                    "days": days,
                    "window": window
                },
                "file_path": saved_path,
                "timestamp": datetime.now().isoformat()
            })
        else:
            # If we can't find the file, include the full output for debugging
            return JSONResponse({
                "status": "error",
                "error": "Chart file not found",
                "output": result.stdout,
                "stderr": result.stderr
            })
        
    except subprocess.TimeoutExpired:
        return JSONResponse({
            "status": "error",
            "error": "Chart generation timed out"
        })
    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        })

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify server is working"""
    return JSONResponse({
        "status": "ok",
        "message": "Server is running",
        "analyze_peaks_exists": ANALYZE_PEAKS_SCRIPT.exists(),
        "timestamp": datetime.now().isoformat()
    })

def kill_process_on_port(port):
    """Kill any process using the specified port"""
    try:
        # Try using fuser command first (Linux)
        result = subprocess.run(
            f"fuser -k {port}/tcp",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info(f"Killed existing process on port {port}")
            time.sleep(1)  # Give it a moment to clean up
            return True
    except:
        pass
    
    try:
        # Alternative method using lsof
        result = subprocess.run(
            f"lsof -ti:{port} | xargs kill -9",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info(f"Killed existing process on port {port} using lsof")
            time.sleep(1)
            return True
    except:
        pass
    
    return False

def is_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('', port))
            return False
        except:
            return True

def open_browser(url, delay=2):
    """Open browser after a delay to ensure server is ready"""
    def _open():
        time.sleep(delay)
        logger.info(f"Opening browser at {url}")
        
        # Try different methods to open browser
        try:
            # First try webbrowser module
            webbrowser.open(url)
        except:
            # Fallback to xdg-open on Linux
            try:
                subprocess.run(["xdg-open", url], check=False)
            except:
                # Final fallback to common browsers
                for browser in ["chromium", "google-chrome", "firefox"]:
                    try:
                        subprocess.run([browser, url], check=False)
                        break
                    except:
                        continue
    
    # Start browser opening in background thread
    import threading
    thread = threading.Thread(target=_open, daemon=True)
    thread.start()

def main():
    """Run the dashboard server with auto-cleanup and browser launch"""
    PORT = 8003
    HOST = "0.0.0.0"
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     WORKING Dashboard Server with Auto-Cleanup & Launch     ║
    ║               Uses analyze_peaks.py for charts              ║
    ║                  Saves charts to /tmp                       ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Clean up any existing process on the port
    if is_port_in_use(PORT):
        print(f"🔧 Port {PORT} is in use. Cleaning up...")
        if kill_process_on_port(PORT):
            print(f"✅ Successfully cleaned up port {PORT}")
        else:
            print(f"⚠️  Could not automatically clean port {PORT}")
            print(f"    You may need to manually kill the process using:")
            print(f"    fuser -k {PORT}/tcp")
            
    # Prepare dashboard URL - Use momentum_stocks_dashboard_dark.html
    dashboard_file = Path(__file__).parent / "momentum_stocks_dashboard_dark.html"
    if dashboard_file.exists():
        dashboard_url = f"file://{dashboard_file.absolute()}"
        print(f"📊 Dashboard found at: {dashboard_file}")
    else:
        # Fallback to other dashboards if preferred one doesn't exist
        dashboard_file = Path(__file__).parent / "ultimate_4day_dashboard.html"
        if dashboard_file.exists():
            dashboard_url = f"file://{dashboard_file.absolute()}"
            print(f"📊 Using fallback dashboard: {dashboard_file}")
        else:
            dashboard_url = f"http://localhost:{PORT}/"
            print(f"📊 Using server test page")
    
    print(f"""
    Starting server on http://localhost:{PORT}
    
    Features:
    ✅ Auto-cleanup of existing processes
    ✅ Auto-launch browser on startup
    ✅ REAL charts from analyze_peaks.py
    ✅ Saves PNG files to /tmp for easy cleanup
    ✅ No mockups - actual technical analysis!
    
    API Endpoints:
    - http://localhost:{PORT}/           - Test page
    - http://localhost:{PORT}/api/test   - Server status
    - http://localhost:{PORT}/api/chart/SYMBOL - Generate chart
    
    🚀 Launching browser in 2 seconds...
    
    Press Ctrl+C to stop the server
    """)
    
    # Launch browser automatically
    open_browser(dashboard_url, delay=2)
    
    # Start the server
    try:
        uvicorn.run(
            "dashboard_server_working:app",
            host=HOST,
            port=PORT,
            reload=False,  # Disable reload to prevent multiple browser opens
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        if is_port_in_use(PORT):
            print(f"   Port {PORT} is still in use. Try running:")
            print(f"   fuser -k {PORT}/tcp")

if __name__ == "__main__":
    main()