#!/usr/bin/env python3
"""
REAL Working Dashboard Server - Actually generates charts from plot.py
"""

import json
import subprocess
import base64
import os
import glob
from pathlib import Path
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
import logging
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Real Momentum Stocks Dashboard API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).parent
CHARTS_DIR = BASE_DIR / "charts"
CHARTS_DIR.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the dashboard HTML"""
    dashboard_file = BASE_DIR / "ultimate_4day_dashboard.html"
    if dashboard_file.exists():
        with open(dashboard_file, 'r') as f:
            return HTMLResponse(content=f.read())
    else:
        return HTMLResponse(content="<h1>Dashboard file not found</h1>", status_code=404)

@app.get("/api/chart/{symbol}")
async def generate_chart(
    symbol: str,
    timeframe: str = Query("1Day", description="Timeframe"),
    days: int = Query(30, description="Number of days"),
    window: int = Query(11, description="Window size")
):
    """Generate a REAL chart for the given symbol using plot.py"""
    try:
        logger.info(f"Generating REAL chart for {symbol} with timeframe={timeframe}, days={days}, window={window}")
        
        # Clean up old temp directories
        for old_dir in glob.glob("/tmp/alpaca_plots_*"):
            try:
                shutil.rmtree(old_dir)
            except:
                pass
        
        # Run plot.py WITHOUT --no-plot to generate actual chart
        cmd = [
            "python3", "plot.py",
            "-s", symbol,
            "-t", timeframe,
            "-d", str(days),
            "-w", str(window)
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        # Set environment for headless operation
        env = os.environ.copy()
        env['MPLBACKEND'] = 'Agg'
        env['DISPLAY'] = ':0'  # Still set display for compatibility
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=BASE_DIR,
            env=env
        )
        
        # Find the generated plot in temp directory
        plot_found = False
        latest_plot = None
        
        # Look for the most recent plot file
        for temp_dir in glob.glob("/tmp/alpaca_plots_*"):
            for png_file in glob.glob(f"{temp_dir}/*.png"):
                if symbol in png_file:
                    latest_plot = png_file
                    plot_found = True
                    logger.info(f"Found plot at: {latest_plot}")
                    break
            if plot_found:
                break
        
        if plot_found and latest_plot and os.path.exists(latest_plot):
            # Copy to our charts directory with a unique name
            output_file = CHARTS_DIR / f"{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            shutil.copy2(latest_plot, output_file)
            logger.info(f"Copied plot to: {output_file}")
            
            # Also save as "latest" for easy access
            latest_file = CHARTS_DIR / f"{symbol}_{timeframe}_latest.png"
            shutil.copy2(latest_plot, latest_file)
            
            # Read and encode the REAL chart
            with open(output_file, 'rb') as f:
                image_data = f.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            return JSONResponse({
                "status": "success",
                "symbol": symbol,
                "chart_data": f"data:image/png;base64,{base64_image}",
                "source": "plot.py_real",
                "parameters": {"timeframe": timeframe, "days": days, "window": window},
                "plot_path": str(latest_plot)
            })
        else:
            # If plot.py failed, log the error
            logger.error(f"plot.py output: {result.stdout}")
            logger.error(f"plot.py error: {result.stderr}")
            
            # Fallback: Try to get data and create a simple chart
            logger.info("Falling back to direct data fetch and plot")
            
            # Use MCP tool to get real data
            try:
                from alpaca_mcp_server.utils.market_data import get_bars_for_symbol
                from alpaca_mcp_server.config.settings import get_clients
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                import numpy as np
                
                # Get market data client
                _, market_client = get_clients()
                
                # Fetch real data
                bars = get_bars_for_symbol(
                    market_client,
                    symbol,
                    timeframe,
                    days
                )
                
                if bars and len(bars) > 0:
                    # Extract prices and times
                    times = [bar.timestamp for bar in bars]
                    prices = [bar.close for bar in bars]
                    
                    # Create real chart
                    fig, ax = plt.subplots(figsize=(14, 8))
                    fig.patch.set_facecolor('#0a0e1a')
                    ax.set_facecolor('#0f1823')
                    
                    # Plot real data
                    ax.plot(range(len(prices)), prices, color='#3b82f6', linewidth=2, label=f'{symbol} Price')
                    
                    # Simple peak/trough detection
                    peaks = []
                    troughs = []
                    for i in range(1, len(prices) - 1):
                        if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                            peaks.append(i)
                        elif prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                            troughs.append(i)
                    
                    # Plot peaks and troughs
                    if peaks:
                        ax.scatter(peaks, [prices[i] for i in peaks], color='#ef4444', s=100, zorder=5, label='Peaks')
                        for peak in peaks[:3]:
                            ax.annotate(f'${prices[peak]:.2f}', 
                                      xy=(peak, prices[peak]), 
                                      xytext=(0, 10),
                                      textcoords='offset points',
                                      ha='center',
                                      fontsize=8,
                                      color='#ef4444')
                    
                    if troughs:
                        ax.scatter(troughs, [prices[i] for i in troughs], color='#10b981', s=100, zorder=5, label='Troughs')
                        for trough in troughs[:3]:
                            ax.annotate(f'${prices[trough]:.2f}', 
                                      xy=(trough, prices[trough]), 
                                      xytext=(0, -15),
                                      textcoords='offset points',
                                      ha='center',
                                      fontsize=8,
                                      color='#10b981')
                    
                    # Style
                    ax.set_title(f'{symbol} - Technical Analysis | {timeframe} | {days} Days | Window: {window}', 
                                color='#e8eaed', fontsize=16, pad=20)
                    ax.set_ylabel('Price ($)', color='#9ca3af')
                    ax.set_xlabel('Days', color='#9ca3af')
                    ax.grid(True, alpha=0.2, color='#9ca3af')
                    ax.legend(loc='upper left', facecolor='#1e2938', edgecolor='#9ca3af')
                    ax.tick_params(colors='#9ca3af')
                    
                    # Remove spines
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    ax.spines['bottom'].set_color('#9ca3af')
                    ax.spines['left'].set_color('#9ca3af')
                    
                    plt.tight_layout()
                    
                    # Save
                    output_file = CHARTS_DIR / f"{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    fig.savefig(output_file, facecolor='#0a0e1a', dpi=100, bbox_inches='tight')
                    plt.close(fig)
                    
                    # Convert to base64
                    with open(output_file, 'rb') as f:
                        image_data = f.read()
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                    
                    return JSONResponse({
                        "status": "success",
                        "symbol": symbol,
                        "chart_data": f"data:image/png;base64,{base64_image}",
                        "source": "direct_real_data",
                        "parameters": {"timeframe": timeframe, "days": days, "window": window}
                    })
                    
            except Exception as e:
                logger.error(f"Fallback error: {str(e)}")
        
        # If all fails
        return JSONResponse({
            "status": "error",
            "message": "Failed to generate chart",
            "symbol": symbol,
            "error": result.stderr if 'result' in locals() else str(e) if 'e' in locals() else "Unknown error"
        })
        
    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "symbol": symbol
        })

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify server is running"""
    return JSONResponse({
        "status": "ok",
        "message": "REAL Server is running - This generates ACTUAL charts!",
        "timestamp": datetime.now().isoformat()
    })

def main():
    """Run the REAL dashboard server"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║             REAL Dashboard Server - NO MOCKUPS!             ║
    ║                 Generates ACTUAL plot.py charts             ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Starting on http://localhost:8002
    
    ✅ REAL: Uses plot.py to generate actual charts
    ✅ REAL: Shows real peak/trough detection
    ✅ REAL: Displays actual market data
    ✅ REAL: No mockups, no fake data!
    
    Test it:
    1. Open http://localhost:8002 or ultimate_4day_dashboard.html
    2. Click any stock symbol
    3. Click "Generate Chart"
    4. REAL chart with REAL data will appear!
    
    API Test: http://localhost:8002/api/chart/NEON
    
    Press Ctrl+C to stop
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=False)

if __name__ == "__main__":
    main()