# MCP Execution Service

A comprehensive FastAPI backend service for executing MCP tools, resources, and prompts with live connections to the actual MCP server implementation.

## 🚀 Features

- **101+ MCP Tools**: Execute all trading tools with parameter validation
- **16+ MCP Resources**: Access all read-only data endpoints  
- **14+ MCP Prompts**: Run all workflow prompts with arguments
- **Real Execution**: Uses actual MCP server functions, not mocks
- **REST API**: Complete REST interface with JSON responses
- **WebSocket Support**: Streaming results and real-time execution
- **Error Handling**: Comprehensive error handling and result formatting
- **Performance Metrics**: Execution time tracking and analysis
- **CORS Enabled**: Browser-accessible from any origin

## 🌐 Service Information

- **Port**: 8002 (different from monitoring service on 8001)
- **Base URL**: `http://localhost:8002`
- **API Docs**: `http://localhost:8002/docs`
- **WebSocket**: `ws://localhost:8002/ws/stream`

## 🔧 Starting the Service

### Option 1: Using Makefile
```bash
make web-service
```

### Option 2: Using script
```bash
./scripts/start_mcp_execution_service.sh
```

### Option 3: Direct Python
```bash
uv run python -m alpaca_mcp_server.web.mcp_execution_service
```

## 📊 API Endpoints

### Discovery Endpoints
- `GET /api/tools/list` - List all available MCP tools with schemas
- `GET /api/resources/list` - List all available MCP resources  
- `GET /api/prompts/list` - List all available MCP prompts

### Execution Endpoints
- `POST /api/execute/tool/{tool_name}` - Execute any MCP tool with parameters
- `GET /api/execute/resource/{resource_uri}` - Get data from any MCP resource
- `POST /api/execute/prompt/{prompt_name}` - Run any MCP prompt with arguments

### Status Endpoints
- `GET /api/status` - Comprehensive service status and metrics
- `GET /health` - Simple health check
- `GET /` - Service homepage with endpoint documentation

### WebSocket
- `WS /ws/stream` - Real-time streaming interface for all operations

## 🛠 Request/Response Format

### Tool Execution Request
```json
{
  "parameters": {
    "symbol": "AAPL",
    "days": 5
  }
}
```

### Resource Request  
```json
{
  "parameters": {
    "symbol_filter": "AAPL",
    "min_trade_value": 1000
  }
}
```

### Prompt Execution Request
```json
{
  "arguments": {
    "symbols": ["AAPL", "MSFT"],
    "timeframe": "1Day",
    "analysis_type": "comprehensive"
  }
}
```

### Response Format
```json
{
  "success": true,
  "result": "Execution results here...",
  "error": null,
  "execution_time": 0.245,
  "timestamp": "2025-08-24T09:43:18Z",
  "metadata": {
    "function_name": "get_stock_quote",
    "module": "alpaca_mcp_server.tools.market_data_tools",
    "filtered_parameters": {"symbol": "AAPL"},
    "parameter_count": 1
  }
}
```

## 📡 WebSocket Usage

### Connect to WebSocket
```javascript
const ws = new WebSocket('ws://localhost:8002/ws/stream');
```

### Execute Tool via WebSocket
```javascript
ws.send(JSON.stringify({
  "type": "execute_tool",
  "tool_name": "get_stock_quote",
  "parameters": {"symbol": "AAPL"}
}));
```

### Get Resource via WebSocket
```javascript
ws.send(JSON.stringify({
  "type": "get_resource", 
  "resource_uri": "market://conditions",
  "parameters": {}
}));
```

### Execute Prompt via WebSocket
```javascript
ws.send(JSON.stringify({
  "type": "execute_prompt",
  "prompt_name": "market_analysis", 
  "arguments": {"symbols": ["AAPL"]}
}));
```

## 🔍 Available Tools (101+)

### Account & Position Management
- `get_account_info` - Account information and balances
- `get_positions` - All current positions
- `get_open_position` - Specific position details
- `close_position` - Close specific position
- `close_all_positions` - Close all positions

### Market Data & Analysis
- `get_stock_quote` - Latest stock quote
- `get_stock_snapshots` - Market snapshots
- `get_stock_bars` - Historical price bars
- `get_stock_bars_intraday` - Intraday bars with analysis
- `get_stock_trades` - Recent trades
- `get_stock_latest_trade` - Latest trade
- `get_stock_latest_bar` - Latest minute bar

### Technical Analysis
- `get_stock_peak_trough_analysis` - Peak/trough analysis for day trading
- `analyze_peaks_troughs_fast` - Ultra-fast C implementation
- `compare_peak_trough_implementations` - Performance comparison

### Day Trading Scanners
- `scan_day_trading_opportunities` - Explosive day-trading opportunities
- `scan_explosive_momentum` - Quick explosive momentum scanner
- `scan_after_hours_opportunities` - After-hours trading opportunities
- `analyze_market_activity_fast` - Ultra-fast market activity analysis
- `scan_explosive_stocks_fast` - Lightning-fast explosive stock scanner

### Volume Bar Analysis
- `get_volume_bars_from_history` - Generate volume bars from history
- `compare_bar_types` - Compare time bars vs volume bars
- `start_volume_bar_streaming` - Real-time volume bar aggregation
- `get_volume_bar_stats` - Volume bar statistics

### Real-time Streaming
- `start_global_stock_stream` - Start global stock data stream
- `stop_global_stock_stream` - Stop stock streaming
- `add_symbols_to_stock_stream` - Add symbols to stream
- `get_stock_stream_data` - Get streaming data
- `get_enhanced_streaming_analytics` - Enhanced streaming analytics

### Order Management
- `place_stock_order` - Place any type of stock order
- `get_orders` - Get orders with status filter
- `cancel_order_by_id` - Cancel specific order
- `cancel_all_orders` - Cancel all open orders
- `place_option_market_order` - Place options orders

### Monitoring & Alerts
- `start_hybrid_monitoring` - Start monitoring service
- `get_hybrid_monitoring_status` - Monitoring status
- `get_current_trading_signals` - Current trading signals
- `get_profit_spike_alerts` - Profit spike alerts
- `ping_monitoring_service` - Health check monitoring

### Extended Hours Trading
- `get_extended_market_clock` - Enhanced market clock
- `validate_extended_hours_order` - Validate extended hours orders
- `place_extended_hours_order` - Place extended hours orders
- `get_extended_hours_info` - Extended hours information

### Advanced Plotting
- `generate_advanced_technical_plots` - Professional technical plots
- `generate_stock_plot` - Stock analysis plots with plot.py

### P&L Analysis
- `get_single_day_pnl` - Calculate P&L for specific trading day

And many more...

## 📋 Available Resources (16+)

- `account://status` - Real-time account health
- `positions://current` - Live position data with P&L
- `positions://intraday_pnl` - Today's intraday P&L
- `market://conditions` - Current market status
- `market://momentum` - Market momentum analysis
- `data://quality` - Data quality and latency metrics
- `server://health` - Server health and performance
- `server://session` - Current session information
- `server://apis` - API connectivity status
- `streaming://status` - Real-time streaming status
- `streaming://buffers` - Streaming buffer statistics
- `streaming://activity` - Recent streaming activity
- `portfolio://summary` - Portfolio summary
- `portfolio://risk` - Portfolio risk analysis

## 🔄 Available Prompts (14+)

### Core Trading Workflows
- `startup` - Comprehensive day trading startup checks
- `account_analysis` - Complete portfolio health check
- `position_management` - Strategic position review
- `market_analysis` - Real-time market analysis
- `day_trading_workflow` - Complete day trading workflow
- `master_scanning_workflow` - Master scanning for opportunities

### Specialized Workflows  
- `options_strategy` - Options trading strategy analysis
- `order_strategy` - Order placement strategy optimization
- `portfolio_review` - Comprehensive portfolio review
- `risk_management` - Risk management analysis
- `stream_centric_trading` - Stream-centric trading workflow
- `stock_news_analysis` - Stock news analysis and impact
- `pro_technical_workflow` - Professional technical analysis

### Reference & Tools
- `list_trading_capabilities` - List all trading capabilities
- `tools_reference` - Complete tools reference guide

## 🔧 Error Handling

The service provides comprehensive error handling:

- **Parameter Validation**: Automatic filtering of parameters based on function signatures
- **Exception Handling**: All exceptions caught and returned in structured format
- **Execution Tracking**: Performance metrics for all operations
- **Detailed Metadata**: Function names, modules, parameters, and execution context
- **Traceback Information**: Full error tracebacks for debugging

## 🏗 Architecture

The service directly imports and executes the actual MCP server functions:

```python
# Real imports from MCP server modules
from ..tools import market_data_tools, day_trading_scanner, streaming_tools
from ..resources import account_resources, market_resources  
from ..prompts import startup_prompt, market_analysis_prompt

# Direct function execution
result = await market_data_tools.get_stock_quote(symbol="AAPL")
```

This ensures:
- ✅ **Real Execution**: No mocks or simulators
- ✅ **Live Data**: Actual market data and trading operations
- ✅ **Full Functionality**: All MCP capabilities accessible via REST
- ✅ **Performance**: Direct function calls without overhead
- ✅ **Consistency**: Same results as MCP server

## 🔒 Security & Configuration

The service inherits all security and configuration from the main MCP server:
- Environment variables from `.env` file
- API credentials for Alpaca trading
- Global configuration from `config/global_config.json`
- Same trading rules and risk management

## 📈 Performance & Monitoring

- **Execution Timing**: All operations timed and reported
- **Connection Tracking**: Active WebSocket connections monitored  
- **Request Counting**: Total executions tracked
- **Memory Management**: Efficient handling of streaming data
- **Error Reporting**: Comprehensive error logging and reporting

## 🎯 Use Cases

### Web Applications
- Build trading dashboards and interfaces
- Create real-time market monitoring apps
- Develop automated trading systems

### API Integration
- Integrate with existing trading platforms
- Connect to external analytics systems
- Build microservices architectures

### Real-time Applications
- Stream market data to web clients
- Provide live trading signals
- Real-time portfolio monitoring

### Development & Testing
- Test MCP functionality via REST
- Debug trading strategies
- Prototype new trading applications

## 🚀 Getting Started Example

```bash
# 1. Start the service
make web-service

# 2. Test basic functionality
curl http://localhost:8002/health

# 3. List available tools
curl http://localhost:8002/api/tools/list

# 4. Execute a tool
curl -X POST http://localhost:8002/api/execute/tool/get_stock_quote \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"symbol": "AAPL"}}'

# 5. Get resource data  
curl http://localhost:8002/api/execute/resource/market://conditions

# 6. View interactive docs
open http://localhost:8002/docs
```

The MCP Execution Service provides a complete REST interface to the powerful Alpaca MCP Server, enabling web applications and external systems to access all trading capabilities through standard HTTP protocols.