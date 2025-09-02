#!/usr/bin/env python3
"""
Interactive Dashboard Server for Momentum Stocks Analysis
Handles chart generation and news/filing requests
"""

import json
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Momentum Stocks Dashboard API")

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
DASHBOARD_FILE = BASE_DIR / "momentum_stocks_dashboard_dark.html"
PLOT_OUTPUT_DIR = BASE_DIR / "static" / "charts"
NEWS_SCRAPER = BASE_DIR / "external_tools" / "news_scrapers" / "yf_rss.py"

# Create output directories
PLOT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/")
async def serve_dashboard():
    """Serve the main dashboard HTML"""
    if not DASHBOARD_FILE.exists():
        raise HTTPException(status_code=404, detail="Dashboard file not found")
    return FileResponse(DASHBOARD_FILE)

@app.get("/api/chart/{symbol}")
async def generate_chart(
    symbol: str,
    timeframe: str = "1Day",
    days: int = 504,
    window: int = 11
):
    """
    Generate peak/trough analysis chart for a symbol
    
    Args:
        symbol: Stock symbol
        timeframe: Time interval (1Min, 5Min, 15Min, 30Min, 1Hour, 1Day)
        days: Number of days to analyze
        window: Hanning filter window size
    """
    try:
        # Prepare output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = PLOT_OUTPUT_DIR / f"{symbol}_{timeframe}_{timestamp}.png"
        
        # Build command
        cmd = [
            "uv", "run", "python", "plot.py",
            "-s", symbol,
            "-t", timeframe,
            "-n", str(days),
            "-w", str(window),
            "--output", str(output_file)
        ]
        
        logger.info(f"Executing: {' '.join(cmd)}")
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=BASE_DIR
        )
        
        if result.returncode != 0:
            logger.error(f"Chart generation failed: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Chart generation failed: {result.stderr}"
            )
        
        # Return the chart file path
        return JSONResponse({
            "status": "success",
            "chart_url": f"/static/charts/{output_file.name}",
            "symbol": symbol,
            "parameters": {
                "timeframe": timeframe,
                "days": days,
                "window": window
            },
            "timestamp": timestamp
        })
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Chart generation timed out")
    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/news/{symbol}")
async def get_news(symbol: str):
    """
    Fetch recent news for a symbol using Yahoo Finance RSS
    
    Args:
        symbol: Stock symbol
    """
    try:
        if not NEWS_SCRAPER.exists():
            # Fallback to mock data if scraper not available
            return JSONResponse({
                "status": "success",
                "symbol": symbol,
                "news": [
                    {
                        "title": f"{symbol} Shows Strong Trading Activity",
                        "summary": f"Latest analysis shows {symbol} with significant momentum",
                        "date": datetime.now().isoformat(),
                        "source": "Market Analysis",
                        "sentiment": "neutral"
                    }
                ],
                "source": "mock_data"
            })
        
        # Run the news scraper
        cmd = ["python3", str(NEWS_SCRAPER), symbol]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Parse the output (assuming JSON format)
            try:
                news_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                # If not JSON, return raw text
                news_data = {"raw_output": result.stdout}
            
            return JSONResponse({
                "status": "success",
                "symbol": symbol,
                "news": news_data,
                "source": "yf_rss"
            })
        else:
            logger.error(f"News fetch failed: {result.stderr}")
            raise HTTPException(status_code=500, detail="News fetch failed")
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="News fetch timed out")
    except Exception as e:
        logger.error(f"Error fetching news: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/filings/{symbol}")
async def get_sec_filings(symbol: str, limit: int = 10):
    """
    Fetch SEC filings for a symbol
    
    Args:
        symbol: Stock symbol
        limit: Maximum number of filings to return
    """
    try:
        # Use MCP SEC-EDGAR tools
        from alpaca_mcp_server.tools.sec_tools import get_recent_filings_for_symbol
        
        filings = await get_recent_filings_for_symbol(symbol, limit)
        
        return JSONResponse({
            "status": "success",
            "symbol": symbol,
            "filings": filings,
            "source": "sec_edgar"
        })
        
    except ImportError:
        # Fallback to mock data
        return JSONResponse({
            "status": "success",
            "symbol": symbol,
            "filings": [
                {
                    "form_type": "10-Q",
                    "filing_date": "2025-08-15",
                    "description": "Quarterly Report",
                    "url": f"https://www.sec.gov/edgar/browse/?CIK={symbol}"
                },
                {
                    "form_type": "8-K",
                    "filing_date": "2025-08-10",
                    "description": "Current Report",
                    "url": f"https://www.sec.gov/edgar/browse/?CIK={symbol}"
                }
            ],
            "source": "mock_data"
        })
    except Exception as e:
        logger.error(f"Error fetching SEC filings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analysis/{symbol}")
async def get_comprehensive_analysis(symbol: str):
    """
    Get comprehensive analysis for a symbol including technical, news, and filings
    
    Args:
        symbol: Stock symbol
    """
    try:
        # Gather all data in parallel
        chart_task = generate_chart(symbol, "1Day", 30, 11)
        news_task = get_news(symbol)
        filings_task = get_sec_filings(symbol, 5)
        
        # Wait for all tasks
        results = await asyncio.gather(
            chart_task,
            news_task,
            filings_task,
            return_exceptions=True
        )
        
        analysis = {
            "status": "success",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "technical": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
            "news": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
            "filings": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])}
        }
        
        return JSONResponse(analysis)
        
    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/portfolio/summary")
async def get_portfolio_summary():
    """Get summary statistics for the momentum portfolio"""
    try:
        # Load the analysis data
        analysis_file = BASE_DIR / "momentum_analysis_52_stocks.json"
        
        if analysis_file.exists():
            with open(analysis_file, 'r') as f:
                data = json.load(f)
            
            return JSONResponse({
                "status": "success",
                "summary": data.get("analysis_summary", {}),
                "key_findings": data.get("key_findings", {}),
                "recommendations": data.get("trading_recommendations", {}),
                "timestamp": data.get("analysis_timestamp", "")
            })
        else:
            raise HTTPException(status_code=404, detail="Analysis data not found")
            
    except Exception as e:
        logger.error(f"Error loading portfolio summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files directory for serving charts
app.mount("/static", StaticFiles(directory=BASE_DIR / "static", html=True), name="static")

def main():
    """Run the dashboard server"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║     Momentum Stocks Dashboard Server                        ║
    ║     Professional Dark Theme with Interactive Charts         ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Starting server on http://localhost:8002
    
    Features:
    - Interactive chart generation on symbol click
    - Real-time news fetching via Yahoo Finance RSS
    - SEC filing retrieval from EDGAR
    - Professional dark theme UI
    - Advanced filtering and sorting
    
    API Endpoints:
    - GET /                           - Main dashboard
    - GET /api/chart/{symbol}         - Generate technical chart
    - GET /api/news/{symbol}          - Fetch latest news
    - GET /api/filings/{symbol}       - Get SEC filings
    - GET /api/analysis/{symbol}      - Comprehensive analysis
    - GET /api/portfolio/summary      - Portfolio statistics
    
    Press Ctrl+C to stop the server
    """)
    
    uvicorn.run(
        "dashboard_server:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()