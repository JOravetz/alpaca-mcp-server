# Dashboard Chart Fix Session Documentation

## Date: 2025-09-09

## Problem Statement
The Momentum Stocks Analysis dashboard at http://localhost:8003 was not displaying charts when clicking on stock symbols. Instead, it showed an error message "Failed to generate chart - Unknown error occurred" even though the backend was successfully generating the charts.

## Issue Identification

### Initial Symptoms
1. User reported seeing the wrong dashboard ("Ultimate 4-Day Trading Dashboard" instead of "Momentum Stocks Analysis")
2. Chart generation failing with generic error message when clicking on stocks
3. Multiple server instances running on port 8003

### Root Causes Found

#### Issue 1: Browser Caching
- Browser was showing cached version of a different dashboard
- Multiple attempts to start servers created confusion

#### Issue 2: Backend Command Arguments (Fixed Previously)
- The `dashboard_server_stocks.py` was using incorrect arguments for `analyze_peaks.py`:
  - Was using `-o` instead of `--save-plot` for output file
  - Was using `-d` instead of `-n` for number of days

#### Issue 3: Frontend/Backend API Mismatch (Primary Fix)
- **Backend API** returned chart data as `data.chart_base64`
- **Frontend HTML** was checking for `data.chart_data`
- This mismatch caused the success condition to always fail

## Solution Implementation

### Step 1: Clean Server Restart
```bash
# Kill all existing servers on port 8003
pkill -f "dashboard_server_stocks.*8003"

# Start fresh server instance
uv run python dashboard_server_stocks.py ~/autotrade/momentum.lis --port 8003 &
```

### Step 2: Fix Frontend/Backend Mismatch
Changed line 1822 in `momentum_stocks_dashboard_dark.html`:

**Before:**
```javascript
if (data.status === 'success' && data.chart_data) {
```

**After:**
```javascript
if (data.status === 'success' && data.chart_base64) {
```

### Step 3: Verification
- Tested API directly: `curl "http://localhost:8003/api/chart/HOOD?timeframe=1Day&days=30&window=11"`
- Confirmed API returns `chart_base64` field with base64-encoded PNG data
- Refreshed browser and confirmed charts display correctly

## Technical Details

### File Structure
- **Backend Server**: `/home/jjoravet/alpaca-mcp-server-enhanced/dashboard_server_stocks.py`
- **Frontend HTML**: `/home/jjoravet/alpaca-mcp-server-enhanced/momentum_stocks_dashboard_dark.html`
- **Chart Generator**: `/home/jjoravet/alpaca-mcp-server-enhanced/analyze_peaks.py`
- **Stock List**: `~/autotrade/momentum.lis` (52 stocks)

### API Endpoint
- **URL**: `http://localhost:8003/api/chart/{symbol}`
- **Parameters**: 
  - `timeframe`: Chart timeframe (e.g., "1Day", "1Min")
  - `days`: Number of days to analyze (1-504)
  - `window`: Hanning filter window size (3-101, odd numbers)
- **Response**: JSON with `status`, `symbol`, `chart_base64`, and metadata

### Chart Generation Process
1. Frontend makes GET request to `/api/chart/{symbol}`
2. Backend executes `analyze_peaks.py` with parameters
3. Python script generates PNG chart with peak/trough analysis
4. Backend reads PNG file, converts to base64
5. Returns JSON response with base64-encoded image
6. Frontend displays image using data URI: `data:image/png;base64,{data}`

## Features Working
- ✅ Momentum Stocks Analysis dashboard displays correctly
- ✅ 52 stocks loaded from momentum.lis file
- ✅ Click on any stock symbol to generate technical analysis chart
- ✅ Charts show:
  - Close price (blue line)
  - Filtered price using Hanning window (red line)
  - VWAP (Volume Weighted Average Price)
  - Peak indicators with price labels (green triangles)
  - Trough indicators with price labels (red triangles)
  - Volume and trade count analysis
- ✅ Interactive controls to adjust timeframe, days, and window parameters
- ✅ "Regenerate Chart" button for updating with new parameters

## Lessons Learned
1. Always verify the exact field names between backend API responses and frontend expectations
2. Browser caching can mask the real issue - use hard refresh (Ctrl+Shift+R) when debugging
3. Check server logs to confirm backend is working before debugging frontend
4. Use curl or API testing tools to verify backend responses independently
5. Multiple server instances on the same port can cause confusion - always clean up before restarting

## Future Improvements
1. Add better error handling with specific error messages
2. Implement WebSocket for real-time chart updates
3. Add chart caching to improve performance
4. Include more technical indicators in the analysis
5. Add export functionality for charts

## Commands for Quick Reference
```bash
# Start the dashboard server
uv run python dashboard_server_stocks.py ~/autotrade/momentum.lis --port 8003

# Test chart generation manually
python3 analyze_peaks.py -s HOOD -t 1Day -n 30 -w 11 -l 5 --save-plot /tmp/test.png

# Test API endpoint
curl "http://localhost:8003/api/chart/HOOD?timeframe=1Day&days=30&window=11" | python3 -m json.tool

# Check running servers
ps aux | grep -E "dashboard.*8003"
```

## Status: ✅ RESOLVED
The dashboard is now fully functional with chart generation working correctly for all stocks.