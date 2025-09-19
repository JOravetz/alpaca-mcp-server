# 🚀 Alpaca Trading Dashboard - Complete Guide

## Overview
A full-stack web application providing a visual interface for all Alpaca MCP trading tools. Execute trades, monitor positions, scan for opportunities, and manage your portfolio through an intuitive browser-based dashboard.

---

## 🎯 Quick Start

### 1. Start the Backend Server
```bash
# Navigate to project directory
cd /home/jjoravet/alpaca-mcp-server-enhanced

# Start the MCP backend server (port 8002)
uv run python start_mcp_backend.py
```

### 2. Open the Dashboard
```bash
# Open in default browser
xdg-open comprehensive_dashboard.html

# Or navigate directly to:
file:///home/jjoravet/alpaca-mcp-server-enhanced/comprehensive_dashboard.html
```

### 3. Verify Connection
- Check for green "Connected" indicator in dashboard
- Or verify backend health:
```bash
curl http://localhost:8002/health
```

---

## 📋 System Architecture

### Frontend: `comprehensive_dashboard.html`
- **Technology:** Pure HTML/CSS/JavaScript (no frameworks)
- **Location:** `/home/jjoravet/alpaca-mcp-server-enhanced/comprehensive_dashboard.html`
- **Features:**
  - Interactive tool execution
  - Real-time result display
  - Modal-based parameter input
  - Professional trading interface

### Backend: `start_mcp_backend.py`
- **Technology:** FastAPI with async Python
- **Port:** 8002
- **Location:** `/home/jjoravet/alpaca-mcp-server-enhanced/start_mcp_backend.py`
- **Capabilities:**
  - 51+ MCP trading tools
  - CORS-enabled for browser access
  - Weekend-aware date handling
  - Async execution for performance

---

## 🛠️ Complete Startup Procedure

### Step-by-Step Instructions

1. **Ensure Dependencies are Installed**
   ```bash
   cd /home/jjoravet/alpaca-mcp-server-enhanced
   uv sync
   ```

2. **Set Environment Variables** (if not already set)
   ```bash
   # Check if .env exists
   cat .env
   
   # If not, copy from example
   cp .env.example .env
   # Edit .env and add your Alpaca API credentials
   ```

3. **Start the Backend Server**
   ```bash
   # Foreground (see logs)
   uv run python start_mcp_backend.py
   
   # OR Background (production)
   uv run python start_mcp_backend.py > logs/mcp_backend.log 2>&1 &
   ```

4. **Verify Backend is Running**
   ```bash
   # Check health endpoint
   curl http://localhost:8002/health
   
   # Expected response:
   # {"status": "healthy", "timestamp": "...", "tools_count": 51}
   ```

5. **Open the Dashboard**
   ```bash
   # Linux
   xdg-open comprehensive_dashboard.html
   
   # macOS
   open comprehensive_dashboard.html
   
   # Windows
   start comprehensive_dashboard.html
   ```

---

## 🎮 User Guide

### Dashboard Layout

#### Header Section
- **Mission Statement:** Your trading philosophy
- **Market Status:** Current market conditions
- **Quick Stats:** Account balance, positions, P&L

#### Navigation Tabs
1. **📊 Overview** - System status and quick actions
2. **🔧 MCP Tools** - Interactive tool execution (main feature)
3. **📈 Resources** - Read-only data endpoints
4. **🎯 Prompts** - Pre-configured workflows
5. **📚 Reference** - Complete documentation

### How to Use MCP Tools

1. **Navigate to MCP Tools Tab**
   - Click "🔧 MCP Tools" in the navigation

2. **Select a Tool Category**
   - Market Data Tools
   - Trading Execution
   - Scanning Tools
   - Account Management
   - Technical Analysis
   - Monitoring Tools

3. **Execute a Tool**
   - Click on any tool name (they're all interactive)
   - A modal will appear with parameter fields
   - Default values are pre-filled
   - Modify parameters as needed
   - Click "Execute Tool"

4. **View Results**
   - Results appear in a formatted modal
   - Click "Copy Result" to copy to clipboard
   - Click "Close" to dismiss

### Common Workflows

#### 🔍 Scan for Trading Opportunities
```javascript
Tool: scan_day_trading_opportunities
Parameters:
  - min_percent_change: 10
  - max_symbols: 20
  - sort_by: "percent_change"
```

#### 📊 Check Account Status
```javascript
Tool: get_account_info
Parameters: (none required)
```

#### 📈 Get Stock Quote
```javascript
Tool: get_stock_quote
Parameters:
  - symbol: "AAPL"
```

#### 🎯 Place an Order
```javascript
Tool: place_stock_order
Parameters:
  - symbol: "AAPL"
  - side: "buy"
  - quantity: 100
  - order_type: "limit"
  - limit_price: 150.00
```

---

## 🔧 Backend Management

### Start Backend
```bash
# Foreground (with logs)
uv run python start_mcp_backend.py

# Background (daemon mode)
nohup uv run python start_mcp_backend.py > logs/mcp_backend.log 2>&1 &

# With specific port (default is 8002)
uvicorn start_mcp_backend:app --port 8002 --host 0.0.0.0
```

### Stop Backend
```bash
# Find process
ps aux | grep start_mcp_backend

# Kill by name
pkill -f "start_mcp_backend.py"

# Or kill by PID
kill <PID>
```

### Monitor Logs
```bash
# Real-time logs
tail -f logs/mcp_backend.log

# Last 100 lines
tail -100 logs/mcp_backend.log

# Search logs
grep ERROR logs/mcp_backend.log
```

### Check Status
```bash
# Health check
curl http://localhost:8002/health

# List available tools
curl http://localhost:8002/tools

# API documentation (when backend is running)
open http://localhost:8002/docs
```

---

## 📊 Available Tools (51+)

### Market Data Tools
- `get_stock_quote` - Latest quote for a stock
- `get_stock_bars` - Historical price bars
- `get_stock_bars_intraday` - Intraday bars with analysis
- `get_stock_trades` - Recent trades
- `get_stock_latest_trade` - Most recent trade
- `get_stock_latest_bar` - Latest minute bar
- `get_stock_snapshots` - Comprehensive market snapshots

### Scanning Tools
- `scan_day_trading_opportunities` - Find explosive movers
- `scan_explosive_momentum` - Quick momentum scanner
- `scan_after_hours_opportunities` - After-hours scanner
- `scan_explosive_stocks_fast` - C-optimized scanner

### Trading Execution
- `place_stock_order` - Place any order type
- `place_extended_hours_order` - Extended hours orders
- `get_orders` - View orders
- `cancel_order_by_id` - Cancel specific order
- `cancel_all_orders` - Cancel all open orders

### Account Management
- `get_account_info` - Account details
- `get_positions` - Current positions
- `get_open_position` - Specific position details
- `close_position` - Close a position
- `close_all_positions` - Close all positions

### Technical Analysis
- `get_stock_peak_trough_analysis` - Peak/trough detection
- `generate_advanced_technical_plots` - Technical charts
- `analyze_peaks_troughs_fast` - Fast C implementation

### Streaming Tools
- `start_global_stock_stream` - Start WebSocket stream
- `stop_global_stock_stream` - Stop streaming
- `get_stock_stream_data` - Get buffered data
- `list_active_stock_streams` - Active subscriptions
- `clear_stock_stream_buffers` - Clear buffers

---

## 🚨 Troubleshooting

### Backend Won't Start
```bash
# Check if port 8002 is in use
lsof -i :8002

# Kill any existing process
kill -9 <PID>

# Try alternative port
uvicorn start_mcp_backend:app --port 8003
# Then update comprehensive_dashboard.html API_URL to match
```

### Dashboard Shows "Disconnected"
```bash
# Verify backend is running
curl http://localhost:8002/health

# Check browser console for errors
# Press F12 in browser → Console tab

# Ensure CORS is enabled (should be by default)
```

### Tools Return Errors
```bash
# Check API credentials
cat .env | grep ALPACA

# Verify paper trading mode
cat .env | grep PAPER

# Check backend logs
tail -50 logs/mcp_backend.log
```

### Weekend Data Issues
- The backend automatically adjusts dates for weekends
- Market data tools will use the last trading day
- This is handled in the wrapper functions

---

## 🔒 Security Notes

1. **API Credentials**
   - Never commit `.env` file
   - Keep credentials in environment variables
   - Use paper trading for testing

2. **Network Access**
   - Backend binds to 0.0.0.0:8002 (accessible from network)
   - For local-only: change to 127.0.0.1:8002
   - Consider firewall rules for production

3. **CORS Settings**
   - Currently allows all origins (*)
   - Restrict in production to specific domains

---

## 📁 File Structure

```
alpaca-mcp-server-enhanced/
├── comprehensive_dashboard.html    # Frontend dashboard
├── start_mcp_backend.py           # Backend server
├── .env                           # API credentials (git-ignored)
├── logs/
│   └── mcp_backend.log           # Backend logs
└── alpaca_mcp_server/
    └── tools/                     # MCP tool implementations
```

---

## 🎯 Quick Commands Reference

```bash
# Start everything
uv run python start_mcp_backend.py & xdg-open comprehensive_dashboard.html

# Stop everything
pkill -f "start_mcp_backend.py"

# Check status
curl http://localhost:8002/health

# View logs
tail -f logs/mcp_backend.log

# Restart backend
pkill -f "start_mcp_backend.py" && uv run python start_mcp_backend.py
```

---

## 🚀 Advanced Features

### API Documentation
When backend is running, visit:
- http://localhost:8002/docs - Swagger UI
- http://localhost:8002/redoc - ReDoc documentation

### Direct API Calls
```bash
# Execute tool via curl
curl -X POST http://localhost:8002/api/execute/tool/get_stock_quote \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

### Custom Tool Integration
Add new tools to `start_mcp_backend.py`:
1. Import the tool function
2. Add to TOOL_REGISTRY dictionary
3. Restart backend

---

## 📝 Notes

- Dashboard works best in Chrome/Firefox/Edge
- All times displayed in ET (America/New_York)
- Paper trading mode recommended for testing
- Backend auto-handles weekend dates for market data
- 51+ tools available with more being added

---

## 🆘 Support

1. Check this guide first
2. Review backend logs: `tail -100 logs/mcp_backend.log`
3. Verify API credentials are set correctly
4. Ensure you're using paper trading for testing
5. Check browser console for frontend errors

---

---

## 🎉 Celebration Dashboards

### P&L Victory Dashboards
Special dashboards for celebrating profitable trading days with maximum visual and audio intensity!

#### Files Created Today (September 19, 2025)

1. **`TODAYS_8K_INSANE_CELEBRATION.html`**
   - Giant $8,040.15 profit display with rainbow gradient
   - 100% win rate celebration (26 wins, 0 losses)
   - Money rain and confetti effects
   - Lightning effects
   - Auto-celebration every 10 seconds
   - Click anywhere for instant fireworks

2. **`MAXIMUM_ULTRA_8K_CELEBRATION.html`**
   - Enhanced version with 60-second intervals for Jessica's voice
   - Animated particle canvas with 200+ particles
   - Floating stat boxes showing 56 trades, $1.2M volume
   - Rainbow gradient animations
   - Background flashing effects
   - Integrated Jessica's victory audio

3. **`ULTIMATE_GIPHY_8K_INSANITY.html`**
   - 28+ animated GIFs from Giphy
   - Categories: money rain, celebrations, victory, mind-blown
   - 12 GIF display grid with 2 floating GIFs
   - Auto-refresh every 60 seconds (updated for Jessica's voice)
   - Scrooge McDuck money swimming overlay
   - Wolf of Wall Street, SpongeBob, and more GIFs

4. **`ULTIMATE_3D_GIPHY_8K_INSANITY.html`** (Most Advanced)
   - **Three.js 3D Graphics**:
     - 500+ colored 3D particles floating in space
     - 20 golden money cubes rotating in 3D
     - Giant 3D trophy spinning and bouncing
     - Moving camera orbiting the scene
     - 3D fog effects with color transitions
   - **3D CSS Transforms**:
     - Rotating stat cubes showing data on all 6 faces
     - 3D perspective on $8,040.15 profit text
     - 3D hover effects on GIF boxes
   - **Giphy Integration**: 8 animated celebration GIFs
   - **90-second intervals** to allow Jessica's voice to complete

### Audio Integration

#### Kokoro TTS System
- Uses Jessica's voice (`af_jessica`) for epic celebrations
- Generated audio files:
  - `jessica_todays_epic_victory.wav` - Today's $8,040.15 celebration
  - Custom messages for different profit levels

#### Voice Generation Scripts
- `generate_todays_victory.py` - Creates custom celebration messages
- `jessica_todays_victory.py` - Generates voice files
- `kokoro_voices.py` - Main Kokoro TTS integration

### Today's Epic Performance (September 19, 2025)
- **Total P&L**: $8,040.15
- **Win Rate**: 100% (26 wins, 0 losses)
- **Total Trades**: 56 across 5 symbols
- **Volume Traded**: $1,202,436.86
- **Biggest Win**: $2,600 (CDLX short position)
- **Top Performer**: AGMH with $3,557.43 profit

### Launching Celebration Dashboards
```bash
# Open any celebration dashboard
chromium ULTIMATE_3D_GIPHY_8K_INSANITY.html

# Generate Jessica's voice celebration
uv run python generate_todays_victory.py

# Play celebration audio
aplay jessica_todays_epic_victory.wav
```

---

*Last Updated: September 19, 2025*
*Version: 2.0.0 - Added Epic Celebration Dashboards*