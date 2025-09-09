#!/usr/bin/env python3
"""
Enhanced Dashboard Server with Stock List File Support
Default: ~/autotrade/momentum.lis
Accepts custom stock list files via command line argument
"""

import json
import subprocess
import asyncio
import base64
import os
import sys
import signal
import time
import webbrowser
import socket
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Dashboard API with Custom Stock Lists")

# Enable CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to store stock list
STOCK_LIST = []
STOCK_FILE_PATH = None

# Paths
BASE_DIR = Path(__file__).parent
ANALYZE_PEAKS_SCRIPT = BASE_DIR / "analyze_peaks.py"
DEFAULT_STOCK_FILE = Path.home() / "autotrade" / "momentum.lis"

def load_stock_list(file_path: Path) -> List[str]:
    """Load stock symbols from a file"""
    stocks = []
    if file_path.exists():
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    symbol = line.strip().upper()
                    if symbol and not symbol.startswith('#'):  # Skip comments
                        stocks.append(symbol)
            logger.info(f"✅ Loaded {len(stocks)} stocks from {file_path}")
        except Exception as e:
            logger.error(f"❌ Error loading stock file: {e}")
    else:
        logger.warning(f"⚠️  Stock file not found: {file_path}")
    return stocks

def generate_stock_analysis_json(stocks: List[str]) -> Dict:
    """Generate the momentum analysis JSON structure with real market data"""
    from alpaca.data import StockHistoricalDataClient
    from alpaca.data.requests import StockSnapshotRequest
    import os
    
    analysis = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "total_stocks": len(stocks),
            "source_file": str(STOCK_FILE_PATH) if STOCK_FILE_PATH else "manual",
            "scan_type": "custom_list"
        },
        "stocks": []
    }
    
    # Initialize Alpaca client
    try:
        api_key = os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")
        
        if not api_key or not api_secret:
            logger.warning("Alpaca API credentials not found, using placeholder data")
            # Fall back to placeholder data
            for i, symbol in enumerate(stocks):
                stock_entry = {
                    "symbol": symbol,
                    "rank": i + 1,
                    "metrics": {
                        "percent_change": 0,
                        "volume": 0,
                        "trades": 0,
                        "price": 0,
                        "spread": 0
                    },
                    "signals": {
                        "momentum": "pending",
                        "trend": "pending"
                    }
                }
                analysis["stocks"].append(stock_entry)
            return analysis
        
        # Create data client
        data_client = StockHistoricalDataClient(api_key, api_secret, raw_data=False)
        
        # Fetch snapshots for all stocks
        logger.info(f"📊 Fetching market data for {len(stocks)} stocks...")
        
        # Process in batches to avoid rate limits
        batch_size = 20
        all_snapshots = {}
        
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i+batch_size]
            try:
                request = StockSnapshotRequest(symbol_or_symbols=batch, feed="sip")
                snapshots = data_client.get_stock_snapshot(request)
                
                # Handle both dict and object responses
                if hasattr(snapshots, '__dict__'):
                    all_snapshots.update(snapshots.__dict__)
                else:
                    all_snapshots.update(snapshots)
                    
                logger.info(f"✅ Fetched data for batch {i//batch_size + 1}")
            except Exception as e:
                logger.warning(f"Failed to fetch batch {i//batch_size + 1}: {e}")
        
        # Process each stock with real data
        for i, symbol in enumerate(stocks):
            stock_entry = {
                "symbol": symbol,
                "rank": i + 1,
                "metrics": {
                    "percent_change": 0,
                    "volume": 0,
                    "trades": 0,
                    "price": 0,
                    "spread": 0,
                    "support": 0,
                    "resistance": 0
                },
                "signals": {
                    "momentum": "neutral",
                    "trend": "neutral",
                    "risk": "medium"
                }
            }
            
            # Extract data from snapshot
            if symbol in all_snapshots:
                snapshot = all_snapshots[symbol]
                
                try:
                    # Extract latest trade
                    if hasattr(snapshot, 'latest_trade') and snapshot.latest_trade:
                        stock_entry["metrics"]["price"] = float(snapshot.latest_trade.price)
                    
                    # Extract daily bar for change calculation
                    if hasattr(snapshot, 'daily_bar') and snapshot.daily_bar:
                        bar = snapshot.daily_bar
                        close = float(bar.close)
                        open_price = float(bar.open)
                        high = float(bar.high)
                        low = float(bar.low)
                        volume = int(bar.volume)
                        
                        stock_entry["metrics"]["price"] = close
                        stock_entry["metrics"]["volume"] = volume
                        stock_entry["metrics"]["support"] = low
                        stock_entry["metrics"]["resistance"] = high
                        
                        # Calculate percent change
                        if open_price > 0:
                            percent_change = ((close - open_price) / open_price) * 100
                            stock_entry["metrics"]["percent_change"] = round(percent_change, 2)
                        
                        # Determine momentum signal
                        if percent_change > 5:
                            stock_entry["signals"]["momentum"] = "bullish"
                            stock_entry["signals"]["risk"] = "high"
                        elif percent_change > 2:
                            stock_entry["signals"]["momentum"] = "bullish"
                            stock_entry["signals"]["risk"] = "medium"
                        elif percent_change < -5:
                            stock_entry["signals"]["momentum"] = "bearish"
                            stock_entry["signals"]["risk"] = "high"
                        elif percent_change < -2:
                            stock_entry["signals"]["momentum"] = "bearish"
                            stock_entry["signals"]["risk"] = "medium"
                        else:
                            stock_entry["signals"]["momentum"] = "neutral"
                            stock_entry["signals"]["risk"] = "low"
                    
                    # Extract quote for spread
                    if hasattr(snapshot, 'latest_quote') and snapshot.latest_quote:
                        quote = snapshot.latest_quote
                        bid = float(quote.bid_price) if quote.bid_price else 0
                        ask = float(quote.ask_price) if quote.ask_price else 0
                        
                        if bid > 0 and ask > 0:
                            spread = ((ask - bid) / bid) * 100
                            stock_entry["metrics"]["spread"] = round(spread, 2)
                    
                    # Extract trade count
                    if hasattr(snapshot, 'minute_bar') and snapshot.minute_bar:
                        stock_entry["metrics"]["trades"] = int(snapshot.minute_bar.trade_count) if hasattr(snapshot.minute_bar, 'trade_count') else 0
                        
                except Exception as e:
                    logger.warning(f"Error processing snapshot for {symbol}: {e}")
            
            analysis["stocks"].append(stock_entry)
        
        # Sort by percent change (highest first)
        analysis["stocks"].sort(key=lambda x: x["metrics"]["percent_change"], reverse=True)
        
        # Update ranks after sorting
        for i, stock in enumerate(analysis["stocks"]):
            stock["rank"] = i + 1
        
        analysis["metadata"]["has_live_data"] = True
        logger.info(f"✅ Generated analysis with live data for {len(stocks)} stocks")
        
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        # Fall back to placeholder data
        for i, symbol in enumerate(stocks):
            stock_entry = {
                "symbol": symbol,
                "rank": i + 1,
                "metrics": {
                    "percent_change": 0,
                    "volume": 0,
                    "trades": 0,
                    "price": 0,
                    "spread": 0
                },
                "signals": {
                    "momentum": "pending",
                    "trend": "pending"
                }
            }
            analysis["stocks"].append(stock_entry)
    
    return analysis

@app.get("/")
async def serve_dashboard():
    """Serve the dashboard HTML"""
    dashboard_file = BASE_DIR / "momentum_stocks_dashboard_dark.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    else:
        # Fallback dashboards
        dashboard_file = BASE_DIR / "ultimate_4day_dashboard.html"
        if dashboard_file.exists():
            return FileResponse(dashboard_file)
        else:
            # Return a simple test page
            stock_divs = ''.join([f'<div class="stock" onclick="generateChart(\'{s}\')">{s}</div>' for s in STOCK_LIST])
            return HTMLResponse(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Stock Dashboard Server</title>
                <style>
                    body {{ background: #0f0f0f; color: #00ff00; font-family: monospace; padding: 20px; }}
                    .stock {{ margin: 10px; padding: 10px; border: 1px solid #00ff00; cursor: pointer; }}
                    .stock:hover {{ background: #1a1a1a; }}
                </style>
            </head>
            <body>
                <h1>Stock Dashboard Server</h1>
                <p>Loaded {len(STOCK_LIST)} stocks from {STOCK_FILE_PATH}</p>
                <h2>Stock List:</h2>
                <div id="stocks">
                    {stock_divs}
                </div>
                <script>
                    function generateChart(symbol) {{
                        fetch(`/api/chart/${{symbol}}`)
                            .then(r => r.json())
                            .then(data => {{
                                if (data.chart_base64) {{
                                    window.open('data:image/png;base64,' + data.chart_base64);
                                }}
                            }});
                    }}
                </script>
            </body>
            </html>
            """)

@app.get("/api/stocks")
async def get_stock_list():
    """Return the current stock analysis data"""
    # Try to load latest analysis if available
    latest_file = Path("latest_analysis.json")
    if latest_file.exists():
        try:
            with open(latest_file, 'r') as f:
                analysis = json.load(f)
            # Return the stocks array from the analysis
            if 'stocks' in analysis and isinstance(analysis['stocks'], list):
                return JSONResponse({
                    "stocks": analysis['stocks'],
                    "count": len(analysis['stocks']),
                    "source": str(STOCK_FILE_PATH) if STOCK_FILE_PATH else "analysis",
                    "metadata": analysis.get('metadata', {}),
                    "summary": analysis.get('summary', {})
                })
        except Exception as e:
            logger.warning(f"Could not load latest_analysis.json: {e}")
    
    # Fallback to simple stock list
    return JSONResponse({
        "stocks": STOCK_LIST,
        "count": len(STOCK_LIST),
        "source": str(STOCK_FILE_PATH) if STOCK_FILE_PATH else "manual"
    })

@app.get("/momentum_analysis_52_stocks.json")
async def get_momentum_analysis():
    """Serve the momentum analysis JSON for the dashboard"""
    if not STOCK_LIST:
        return JSONResponse(
            {"error": "No stocks loaded"},
            status_code=404
        )
    
    analysis = generate_stock_analysis_json(STOCK_LIST)
    return JSONResponse(analysis)

class LoadStocksRequest(BaseModel):
    file_path: str

@app.get("/api/analysis")
async def get_latest_analysis():
    """
    Get the latest analysis JSON from the /analyze command
    Returns saved analysis or generates new one if not available
    """
    try:
        # Check if latest_analysis.json exists
        analysis_file = Path("latest_analysis.json")
        if analysis_file.exists():
            with open(analysis_file, 'r') as f:
                data = json.load(f)
            
            logger.info(f"✅ Serving latest analysis with {len(data.get('stocks', []))} stocks")
            return JSONResponse(data)
        else:
            # Fallback to generating new analysis
            logger.info("No latest_analysis.json found, generating new analysis")
            analysis = generate_stock_analysis_json(STOCK_LIST)
            return JSONResponse(analysis)
    except Exception as e:
        logger.error(f"Error loading analysis: {str(e)}")
        return JSONResponse(
            {"error": f"Failed to load analysis: {str(e)}"},
            status_code=500
        )

@app.get("/api/analysis/live")
async def get_live_analysis():
    """Get real-time analysis with live market data"""
    import subprocess
    
    try:
        # Generate base analysis
        analysis = generate_stock_analysis_json(STOCK_LIST)
        
        # Fetch live quotes for all stocks using Alpaca MCP
        if STOCK_LIST:
            symbols_str = ','.join(STOCK_LIST[:20])  # Limit to first 20 for performance
            
            try:
                # Use the MCP tool to get stock quotes
                cmd = [
                    "uv", "run", "python", "-c",
                    f"""
import json
from alpaca_mcp_server.tools.market_data_tools import get_stock_snapshots
result = get_stock_snapshots('{symbols_str}')
# Extract percent changes from the formatted output
lines = result.split('\\n')
data = {{}}
for line in lines:
    if '│' in line and any(s in line for s in {STOCK_LIST}):
        parts = line.split('│')
        for i, part in enumerate(parts):
            part = part.strip()
            if part in {STOCK_LIST}:
                # Look for change percentage in the same or next parts
                for j in range(i, min(i+3, len(parts))):
                    if '%' in parts[j]:
                        try:
                            pct = float(parts[j].replace('%', '').strip())
                            data[part] = pct
                            break
                        except:
                            pass
print(json.dumps(data))
"""
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    # Try to parse the output
                    output_lines = result.stdout.strip().split('\n')
                    for line in output_lines:
                        if line.startswith('{') and line.endswith('}'):
                            try:
                                live_data = json.loads(line)
                                # Update analysis with live data
                                for stock in analysis["stocks"]:
                                    if stock["symbol"] in live_data:
                                        stock["metrics"]["percent_change"] = live_data[stock["symbol"]]
                                        stock["signals"]["momentum"] = "bullish" if live_data[stock["symbol"]] > 5 else "bearish" if live_data[stock["symbol"]] < -5 else "neutral"
                                
                                analysis["metadata"]["has_live_data"] = True
                                logger.info(f"✅ Updated {len(live_data)} stocks with live data")
                                break
                            except json.JSONDecodeError:
                                pass
                
            except Exception as e:
                logger.warning(f"Could not fetch live data: {e}")
        
        analysis["metadata"]["last_updated"] = datetime.now().isoformat()
        return JSONResponse(analysis)
        
    except Exception as e:
        logger.error(f"Error in live analysis: {e}")
        return JSONResponse(generate_stock_analysis_json(STOCK_LIST))

@app.post("/api/load-stocks")
async def load_stocks_from_file(request: LoadStocksRequest):
    """
    Load stocks from a file, run full /analyze command workflow, 
    save results to JSON, and return for dashboard update
    """
    global STOCK_LIST, STOCK_FILE_PATH
    
    path = Path(request.file_path).expanduser()
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
    
    STOCK_LIST = load_stock_list(path)
    STOCK_FILE_PATH = path
    
    # Generate the analysis for the new stock list
    analysis = generate_stock_analysis_json(STOCK_LIST)
    
    # Save the analysis JSON files
    analysis_file = BASE_DIR / f"momentum_analysis_{len(STOCK_LIST)}_stocks.json"
    with open(analysis_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    # Also save as latest_analysis.json for the /analyze command integration
    latest_file = BASE_DIR / "latest_analysis.json"
    with open(latest_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    # Optionally run the full /analyze command for technical analysis
    # This can be done asynchronously in the background
    try:
        import subprocess
        cmd = [
            "uv", "run", "python", 
            str(BASE_DIR / "analyze_and_save_json.py"),
            str(path)
        ]
        # Run in background, don't wait for completion
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("🔄 Started background technical analysis")
    except Exception as e:
        logger.warning(f"Could not start background analysis: {e}")
    
    logger.info(f"✅ Generated analysis for {len(STOCK_LIST)} stocks")
    logger.info(f"📊 Analysis saved to {analysis_file} and latest_analysis.json")
    
    # Return both the status and the full analysis data
    return JSONResponse({
        "status": "success",
        "stocks_loaded": len(STOCK_LIST),
        "file": str(path),
        "stocks": STOCK_LIST,
        "analysis_file": str(analysis_file),
        "analysis_generated": True,
        "analysis": analysis  # Include the full analysis data for immediate dashboard update
    })

@app.get("/api/chart/{symbol}")
async def generate_chart(
    symbol: str,
    timeframe: str = "1Day",
    days: int = 504,
    window: int = 11,
    lookahead: int = 5
):
    """Generate a chart using analyze_peaks.py"""
    try:
        symbol = symbol.upper()
        
        # Validate that analyze_peaks.py exists
        if not ANALYZE_PEAKS_SCRIPT.exists():
            return JSONResponse({
                "status": "error",
                "error": f"analyze_peaks.py not found at {ANALYZE_PEAKS_SCRIPT}"
            })
        
        # Generate unique filename in /tmp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"/tmp/chart_{symbol}_{timestamp}.png"
        
        # Build the command
        cmd = [
            "python3", str(ANALYZE_PEAKS_SCRIPT),
            "-s", symbol,
            "-t", timeframe,
            "-n", str(days),  # Changed from -d to -n (number of days)
            "-w", str(window),
            "-l", str(lookahead),
            "--save-plot", output_file  # Changed from -o to --save-plot
        ]
        
        logger.info(f"Executing: {' '.join(cmd)}")
        
        # Execute the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"Command failed: {result.stderr}")
            return JSONResponse({
                "status": "error",
                "error": result.stderr or "Failed to generate chart"
            })
        
        # Check if the file was created
        if not Path(output_file).exists():
            return JSONResponse({
                "status": "error",
                "error": "Chart file was not created"
            })
        
        # Read the generated image
        with open(output_file, "rb") as f:
            image_data = f.read()
        
        # Clean up the file
        os.remove(output_file)
        
        # Convert to base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        return JSONResponse({
            "status": "success",
            "symbol": symbol,
            "chart_base64": image_base64,
            "timeframe": timeframe,
            "days": days,
            "window": window,
            "timestamp": datetime.now().isoformat()
        })
        
    except subprocess.TimeoutExpired:
        return JSONResponse({
            "status": "error",
            "error": "Chart generation timed out"
        })
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return JSONResponse({
            "status": "error",
            "error": str(e)
        })

@app.get("/api/market-clock")
async def get_market_clock():
    """Get current market status from Alpaca"""
    try:
        # Import Alpaca tools
        from alpaca_mcp_server.tools.market_info_tools import get_market_clock as alpaca_market_clock
        
        # Get market clock data
        clock_data = await alpaca_market_clock()
        
        # Parse the response to extract the data
        lines = clock_data.strip().split('\n')
        market_info = {}
        
        for line in lines:
            if 'Current Time:' in line:
                market_info['current_time'] = line.split('Current Time:')[1].strip()
            elif 'Is Open:' in line:
                market_info['is_open'] = line.split('Is Open:')[1].strip().lower() == 'yes'
            elif 'Next Open:' in line:
                market_info['next_open'] = line.split('Next Open:')[1].strip()
            elif 'Next Close:' in line:
                market_info['next_close'] = line.split('Next Close:')[1].strip()
        
        # Format the response for the dashboard
        if market_info.get('is_open'):
            status_text = "Markets Open"
            next_event = f"Closes at {market_info.get('next_close', 'N/A')}"
            status_class = "open"
        else:
            status_text = "Markets Closed"
            # Parse next open time for display
            if market_info.get('next_open'):
                try:
                    # Parse the datetime string
                    from datetime import datetime as dt
                    import pytz
                    
                    # The format from Alpaca is like "2025-09-09 09:30:00-04:00"
                    next_open_str = market_info['next_open']
                    
                    # Parse the datetime to get day of week
                    # Remove timezone part for parsing
                    date_part = next_open_str.split('-04:00')[0].strip()
                    next_open_dt = dt.strptime(date_part, "%Y-%m-%d %H:%M:%S")
                    
                    # Get day of week
                    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    day_of_week = day_names[next_open_dt.weekday()]
                    
                    # Format time
                    time_str = next_open_dt.strftime("%-I:%M %p")
                    
                    next_event = f"Next: {day_of_week} {time_str} EDT"
                except Exception as e:
                    # Fallback format
                    next_event = f"Next: {market_info.get('next_open', 'N/A')}"
            else:
                next_event = "Next: N/A"
            status_class = "closed"
        
        return JSONResponse({
            "status": "success",
            "market_status": {
                "is_open": market_info.get('is_open', False),
                "status_text": status_text,
                "next_event": next_event,
                "status_class": status_class,
                "current_time": market_info.get('current_time', ''),
                "next_open": market_info.get('next_open', ''),
                "next_close": market_info.get('next_close', '')
            }
        })
    except Exception as e:
        logger.error(f"Error getting market clock: {e}")
        # Fallback response
        return JSONResponse({
            "status": "error",
            "market_status": {
                "is_open": False,
                "status_text": "Market Status Unknown",
                "next_event": "Unable to fetch market hours",
                "status_class": "closed"
            },
            "error": str(e)
        })

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify server is working"""
    return JSONResponse({
        "status": "ok",
        "message": "Server is running",
        "stocks_loaded": len(STOCK_LIST),
        "stock_file": str(STOCK_FILE_PATH) if STOCK_FILE_PATH else None,
        "analyze_peaks_exists": ANALYZE_PEAKS_SCRIPT.exists(),
        "timestamp": datetime.now().isoformat()
    })

# Mount static files for any additional resources
if (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

def kill_process_on_port(port):
    """Kill any process using the specified port"""
    try:
        result = subprocess.run(
            f"fuser -k {port}/tcp",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info(f"Killed existing process on port {port}")
            time.sleep(1)
            return True
    except:
        pass
    
    try:
        result = subprocess.run(
            f"lsof -ti:{port} | xargs kill -9",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            time.sleep(1)
            return True
    except:
        pass
    
    return False

def is_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

async def main():
    """Main entry point with CLI argument parsing"""
    global STOCK_LIST, STOCK_FILE_PATH
    
    parser = argparse.ArgumentParser(
        description='Stock Dashboard Server with Custom Stock Lists',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default file (~/autotrade/momentum.lis)
  python dashboard_server_stocks.py
  
  # Use custom stock file
  python dashboard_server_stocks.py stocks.txt
  
  # Use specific path
  python dashboard_server_stocks.py /path/to/my/stocks.lis
  
  # Specify port
  python dashboard_server_stocks.py --port 8004
        """
    )
    
    parser.add_argument(
        'stock_file',
        nargs='?',
        default=str(DEFAULT_STOCK_FILE),
        help=f'Stock list file (default: {DEFAULT_STOCK_FILE})'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8003,
        help='Port to run server on (default: 8003)'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help="Don't auto-launch browser"
    )
    
    args = parser.parse_args()
    
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║        Enhanced Dashboard Server with Stock Lists           ║
    ║            Customizable Stock Analysis Dashboard            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Load stock list
    stock_file = Path(args.stock_file).expanduser()
    if stock_file.exists():
        STOCK_LIST = load_stock_list(stock_file)
        STOCK_FILE_PATH = stock_file
        print(f"📊 Loaded {len(STOCK_LIST)} stocks from: {stock_file}")
        if STOCK_LIST[:5]:  # Show first 5 stocks
            print(f"   First stocks: {', '.join(STOCK_LIST[:5])}")
            if len(STOCK_LIST) > 5:
                print(f"   ... and {len(STOCK_LIST) - 5} more")
    else:
        print(f"⚠️  Stock file not found: {stock_file}")
        print(f"   Creating example file...")
        
        # Create example file with some default stocks
        stock_file.parent.mkdir(parents=True, exist_ok=True)
        with open(stock_file, 'w') as f:
            f.write("# Momentum stocks list\n")
            f.write("# One symbol per line\n")
            f.write("AAPL\n")
            f.write("MSFT\n")
            f.write("NVDA\n")
            f.write("TSLA\n")
            f.write("META\n")
            f.write("GOOGL\n")
            f.write("AMZN\n")
            f.write("AMD\n")
            f.write("SPY\n")
            f.write("QQQ\n")
        
        STOCK_LIST = load_stock_list(stock_file)
        STOCK_FILE_PATH = stock_file
        print(f"   Created example file with {len(STOCK_LIST)} stocks")
    
    PORT = args.port
    
    # Check if port is in use
    if is_port_in_use(PORT):
        print(f"🔧 Port {PORT} is in use. Cleaning up...")
        if kill_process_on_port(PORT):
            print(f"✅ Successfully cleaned up port {PORT}")
        else:
            print(f"⚠️  Could not automatically clean port {PORT}")
            print(f"    Try using a different port with --port")
            sys.exit(1)
    
    # Prepare dashboard URL
    dashboard_file = BASE_DIR / "momentum_stocks_dashboard_dark.html"
    if dashboard_file.exists():
        dashboard_url = f"file://{dashboard_file.absolute()}"
        print(f"📊 Dashboard found at: {dashboard_file}")
    else:
        dashboard_url = f"http://localhost:{PORT}/"
        print(f"📊 Using server dashboard page")
    
    print(f"""
    Starting server on http://localhost:{PORT}
    
    Stock File: {STOCK_FILE_PATH}
    Stocks Loaded: {len(STOCK_LIST)}
    
    API Endpoints:
    - http://localhost:{PORT}/                           - Dashboard
    - http://localhost:{PORT}/api/stocks                 - List loaded stocks
    - http://localhost:{PORT}/api/chart/SYMBOL           - Generate chart
    - http://localhost:{PORT}/momentum_analysis_52_stocks.json - Dashboard data
    - http://localhost:{PORT}/api/test                   - Server status
    
    POST Endpoints:
    - http://localhost:{PORT}/api/load-stocks            - Load new stock file
    """)
    
    if not args.no_browser:
        print(f"🚀 Launching browser in 2 seconds...")
        await asyncio.sleep(2)
        
        def launch_browser():
            logger.info(f"Opening browser at {dashboard_url}")
            webbrowser.open(dashboard_url)
        
        asyncio.create_task(asyncio.to_thread(launch_browser))
    
    print("\nPress Ctrl+C to stop the server\n")
    
    # Start the server
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped gracefully")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)