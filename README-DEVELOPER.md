# Alpaca MCP Server - Developer Documentation

**Comprehensive Technical Guide for Developers**

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Environment Setup](#development-environment-setup)
3. [Project Structure](#project-structure)
4. [Core Components Deep Dive](#core-components-deep-dive)
5. [Development Workflow](#development-workflow)
6. [Testing Framework](#testing-framework)
7. [Performance Guidelines](#performance-guidelines)
8. [Contributing Guidelines](#contributing-guidelines)
9. [Deployment & Operations](#deployment--operations)
10. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### 🏗️ Three-Tier Intelligence Hierarchy

The Alpaca MCP Server follows a sophisticated three-tier architecture designed for maximum intelligence and composability:

```
PROMPTS (🥇 Highest Value) > TOOLS (🥈 Action Layer) > RESOURCES (🥉 Data Layer)
```

#### Design Philosophy: Intelligence Over Integration

Instead of simple API passthrough, this system provides an **intelligent trading assistant** that:
- Interprets market conditions using advanced prompts
- Combines multiple data sources for comprehensive analysis  
- Provides actionable insights rather than raw data
- Scales to institutional requirements with professional-grade tools

### 📊 Component Architecture

```
alpaca_mcp_server/
├── prompts/           # 🥇 HIGHEST: Intelligent orchestration
├── tools/            # 🥈 MIDDLE: Action execution (90+ tools)
├── resources/        # 🥉 LOWEST: Data context providers
├── config/           # Configuration management
├── models/           # Type-safe data structures
├── monitoring/       # Real-time monitoring services
├── utils/           # Shared utilities
└── tests/           # Comprehensive test suite
```

#### 1. Prompts Layer (Highest Value)
**Purpose**: Transform raw API data into intelligent trading workflows

```python
# Example: Intelligent workflow orchestration
@mcp.prompt()
async def account_analysis_workflow() -> str:
    """Multi-source analysis combining account, positions, and market data"""
    account_data = await get_account_info()
    positions = await get_positions() 
    market_status = await get_market_clock()
    
    # Generate contextual analysis
    return generate_intelligent_analysis(account_data, positions, market_status)
```

**Key Features:**
- Multi-source data fusion
- Contextual market analysis
- Risk assessment workflows
- Strategy recommendations

#### 2. Tools Layer (Action Execution)
**Purpose**: Atomic operations that prompts compose

```python
# Example: Composable trading tool
@mcp.tool()
async def place_stock_order(
    symbol: str,
    side: str,
    quantity: int,
    order_type: str = "limit",
    limit_price: Optional[float] = None
) -> OrderResponse:
    """Execute trade with comprehensive validation"""
    # Input validation
    # Order execution
    # Response formatting
```

**Categories:**
- **Account Management**: Portfolio tracking, P&L monitoring
- **Order Management**: Trading operations with validation
- **Market Data**: Real-time and historical data access
- **Technical Analysis**: Peak/trough detection, filtering
- **Monitoring**: Real-time position tracking
- **System Maintenance**: Health checks, cleanup

#### 3. Resources Layer (Data Foundation)
**Purpose**: Real-time data and state information

```python
# Example: Dynamic resource provider
@mcp.resource("account://status")
async def account_status() -> dict:
    """Real-time account metrics"""
    return {
        "buying_power": await get_buying_power(),
        "positions_count": await get_positions_count(),
        "day_trades_remaining": await get_day_trades_remaining()
    }
```

**Resource Types:**
- `account://status` - Live account metrics
- `positions://current` - Real-time P&L data
- `market://conditions` - Market status and momentum
- `server://health` - System performance metrics

---

## Development Environment Setup

### Prerequisites

- **Python 3.12+** (Required for latest type hints and performance)
- **UV Package Manager** (Recommended for fast dependency management)
- **Alpaca Markets Account** with API credentials
- **Git** for version control

### Quick Setup

```bash
# 1. Clone repository
git clone https://github.com/your-org/alpaca-mcp-server-enhanced.git
cd alpaca-mcp-server-enhanced

# 2. Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh
# Or: pip install uv

# 3. Create development environment
uv sync --dev

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your Alpaca API credentials

# 5. Verify installation
uv run python -m alpaca_mcp_server --version
```

### Environment Configuration

Create `.env` file with:
```env
# Alpaca API Configuration
APCA_API_KEY_ID=your_alpaca_api_key
APCA_API_SECRET_KEY=your_alpaca_secret_key
APCA_API_BASE_URL=https://paper-api.alpaca.markets

# Development Settings
MCP_DEBUG=1
CLAUDE_CODE_TOOL_DISCOVERY=1
PYTHONPATH=/path/to/alpaca-mcp-server-enhanced
```

### Development Tools

```bash
# Code formatting
uv run black alpaca_mcp_server/
uv run isort alpaca_mcp_server/

# Type checking
uv run mypy alpaca_mcp_server/

# Linting
uv run ruff check alpaca_mcp_server/

# Testing
uv run python -m pytest alpaca_mcp_server/tests/
```

---

## Project Structure

### 📁 Directory Organization

```
alpaca_mcp_server/
├── __init__.py              # Package initialization
├── __main__.py              # Entry point for module execution
├── main.py                  # Alternative entry point
├── server.py                # Main MCP server implementation
├── compatibility.py         # Claude Code compatibility layer
│
├── config/                  # Configuration Management
│   ├── __init__.py
│   ├── clients.py          # API client configuration
│   ├── global_config.py    # Global configuration system
│   └── settings.py         # Application settings
│
├── models/                  # Data Models & Type Safety
│   ├── __init__.py
│   ├── data_models.py      # Core trading data structures
│   ├── response_models.py  # API response models
│   └── schemas.py          # Pydantic validation schemas
│
├── prompts/                 # 🥇 Intelligent Workflows
│   ├── __init__.py
│   ├── account_analysis_prompt.py     # Portfolio analysis
│   ├── market_analysis_prompt.py      # Market condition analysis
│   ├── position_management_prompt.py  # Position management workflows
│   ├── pro_technical_workflow.py      # Professional technical analysis
│   ├── master_scanning_workflow.py    # Market scanning workflows
│   ├── day_trading_workflow.py        # Day trading procedures
│   └── stream_centric_trading_prompt.py # Real-time trading workflows
│
├── tools/                   # 🥈 Action Execution Layer
│   ├── __init__.py
│   ├── account_tools.py               # Account operations
│   ├── order_tools.py                 # Order management
│   ├── position_tools.py              # Position tracking
│   ├── market_data_tools.py           # Market data access
│   ├── streaming_tools.py             # Real-time streaming
│   ├── day_trading_scanner.py         # Market scanners
│   ├── peak_trough_analysis_tool.py   # Technical analysis
│   ├── advanced_plotting_tool.py      # Chart generation
│   ├── options_tools.py               # Options trading
│   ├── watchlist_tools.py             # Watchlist management
│   ├── monitoring_tools.py            # System monitoring
│   └── cleanup_tool.py                # System maintenance
│
├── resources/               # 🥉 Data Context Layer
│   ├── __init__.py
│   ├── account_resources.py          # Account data providers
│   ├── position_resources.py         # Position data providers
│   ├── market_resources.py           # Market data providers
│   ├── server_health.py              # Health monitoring
│   ├── api_monitor.py                # API monitoring
│   └── streaming_resources.py        # Streaming data resources
│
├── monitoring/              # Real-time Monitoring Services
│   ├── __init__.py
│   ├── fastapi_service.py            # FastAPI monitoring server
│   ├── hybrid_service.py             # Hybrid trading service
│   ├── streaming_integration.py      # Stream processing
│   ├── position_tracker.py           # Position monitoring
│   ├── signal_detector.py            # Signal detection
│   ├── alert_system.py               # Alert management
│   ├── desktop_notifications.py      # Desktop alerts
│   └── trade_confirmation.py         # Trade verification
│
├── utils/                   # Shared Utilities
│   ├── __init__.py
│   ├── alpaca_stream.py              # Streaming utilities
│   ├── tickers.py                    # Symbol utilities
│   ├── snapshot.py                   # Market snapshot tools
│   └── stock_analyzer.py             # Analysis utilities
│
└── tests/                   # Comprehensive Test Suite
    ├── __init__.py
    ├── conftest.py                   # Test configuration
    ├── run_tests.py                  # Test runner
    │
    ├── unit/                         # Unit Tests
    │   ├── test_workflows.py
    │   ├── test_error_handling.py
    │   ├── test_global_config_simple.py
    │   ├── test_streaming_real.py
    │   └── test_buffer_timestamp_parsing.py
    │
    ├── integration/                  # Integration Tests
    │   ├── test_mcp_server.py
    │   ├── test_fastapi_server.py
    │   └── test_production_scenarios.py
    │
    └── performance/                  # Performance Tests
        └── test_performance.py
```

### 🔑 Key Files

#### Core Server Files
- **`server.py`** - Main MCP server with tool registration
- **`main.py`** - Application entry point
- **`compatibility.py`** - Claude Code integration layer

#### Configuration
- **`config/global_config.py`** - Centralized configuration system
- **`config/settings.py`** - Application settings and defaults

#### Models & Type Safety
- **`models/data_models.py`** - Core trading data structures
- **`models/schemas.py`** - Pydantic validation schemas

---

## Core Components Deep Dive

### 1. MCP Server Implementation (`server.py`)

The main server implements the Model Context Protocol with 90+ tools:

```python
from mcp.server import FastMCP
from alpaca_mcp_server.tools import *
from alpaca_mcp_server.resources import *
from alpaca_mcp_server.prompts import *

class AlpacaMCPServer:
    def __init__(self):
        self.app = FastMCP("Alpaca Trading MCP Server", "1.0.0")
        self._register_tools()
        self._register_resources()
        self._register_prompts()
    
    def _register_tools(self):
        # Register 90+ trading tools
        self.app.add_tool(place_stock_order)
        self.app.add_tool(get_positions)
        # ... etc
    
    def run(self):
        self.app.run()
```

### 2. Global Configuration System (`config/global_config.py`)

Centralized configuration for consistent behavior:

```python
{
  "trading": {
    "trades_per_minute_threshold": 1000,
    "min_percent_change_threshold": 10.0,
    "default_position_size_usd": 50000,
    "max_concurrent_positions": 5,
    "never_sell_for_loss": true
  },
  "technical_analysis": {
    "hanning_window_samples": 11,
    "peak_trough_min_distance": 3,
    "peak_trough_lookahead": 1
  },
  "monitoring": {
    "alert_threshold_percent": 5.0,
    "notification_enabled": true,
    "log_level": "INFO"
  }
}
```

### 3. Type Safety & Data Models (`models/`)

Enhanced Pydantic v2 schemas for robust data validation:

```python
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional

class TradingPosition(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    quantity: Decimal = Field(..., gt=0, description="Position quantity") 
    entry_price: Decimal = Field(..., gt=0, description="Entry price")
    current_price: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    
    class Config:
        validate_assignment = True
        use_enum_values = True
```

### 4. Real-Time Monitoring (`monitoring/`)

Production-grade monitoring with FastAPI service:

```python
# FastAPI monitoring service
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/positions")
async def get_positions():
    return await position_tracker.get_current_positions()

@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    # Real-time data streaming
    pass
```

---

## Development Workflow

### 1. Adding New Tools

```python
# tools/my_new_tool.py
from mcp import tool
from alpaca_mcp_server.models import OrderResponse

@tool()
async def my_trading_function(
    symbol: str,
    action: str,
    quantity: int
) -> OrderResponse:
    """
    Execute trading operation with validation.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        action: 'buy' or 'sell'
        quantity: Number of shares
        
    Returns:
        OrderResponse with execution details
    """
    # Implement functionality
    pass

# Register in server.py
from alpaca_mcp_server.tools.my_new_tool import my_trading_function
self.app.add_tool(my_trading_function)
```

### 2. Creating New Prompts

```python
# prompts/my_workflow.py
from mcp import prompt

@prompt()
async def trading_workflow(context: str) -> str:
    """
    Intelligent trading workflow that orchestrates multiple tools.
    
    Args:
        context: Trading context or user request
        
    Returns:
        Formatted workflow guidance
    """
    # Analyze context
    analysis = await analyze_market_conditions()
    
    # Generate workflow
    workflow = f"""
    # Trading Workflow for {context}
    
    ## Market Analysis
    {analysis}
    
    ## Recommended Actions
    1. Check account status: get_account_info()
    2. Scan opportunities: scan_day_trading_opportunities()
    3. Analyze targets: get_stock_peak_trough_analysis()
    """
    
    return workflow
```

### 3. Adding Resources

```python
# resources/my_resource.py
from mcp import resource

@resource("trading://my_data")
async def my_trading_resource() -> dict:
    """
    Provide real-time trading data.
    
    Returns:
        Dictionary with trading metrics
    """
    return {
        "active_positions": await get_position_count(),
        "daily_pnl": await calculate_daily_pnl(),
        "market_status": await get_market_status()
    }
```

### 4. Code Quality Standards

#### Type Hints (Required)
```python
# Good
async def place_order(
    symbol: str, 
    quantity: int, 
    price: Optional[Decimal] = None
) -> OrderResponse:
    pass

# Bad  
async def place_order(symbol, quantity, price=None):
    pass
```

#### Error Handling (Required)
```python
# Good
try:
    result = await execute_trade(symbol, quantity)
    return {
        "success": True,
        "result": result
    }
except ValidationError as e:
    return {
        "success": False,
        "error": "Invalid input",
        "details": str(e),
        "suggestions": ["Check symbol format", "Verify quantity"]
    }
except Exception as e:
    logger.error(f"Trade execution failed: {e}")
    return {
        "success": False,
        "error": "Trade execution failed",
        "details": str(e)
    }
```

#### Async/Await (Required)
```python
# Good
async def get_market_data(symbol: str) -> MarketData:
    async with aiohttp.ClientSession() as session:
        response = await session.get(f"/api/data/{symbol}")
        return MarketData.parse_obj(await response.json())

# Bad
def get_market_data(symbol: str) -> MarketData:
    response = requests.get(f"/api/data/{symbol}")
    return MarketData.parse_obj(response.json())
```

---

## Testing Framework

### Test Categories

#### 1. Unit Tests (`tests/unit/`)
Test individual components in isolation:

```python
# tests/unit/test_trading_tools.py
import pytest
from alpaca_mcp_server.tools.order_tools import place_stock_order

@pytest.mark.asyncio
async def test_place_stock_order_validation():
    """Test order validation"""
    with pytest.raises(ValidationError):
        await place_stock_order("", "buy", 0)  # Invalid inputs

@pytest.mark.asyncio 
async def test_place_stock_order_success():
    """Test successful order placement"""
    result = await place_stock_order("AAPL", "buy", 100)
    assert result["success"] is True
    assert "order_id" in result
```

#### 2. Integration Tests (`tests/integration/`)
Test component interactions:

```python
# tests/integration/test_mcp_server.py
@pytest.mark.asyncio
async def test_server_startup():
    """Test MCP server initialization"""
    server = AlpacaMCPServer()
    assert len(server.tools) >= 90
    assert len(server.resources) >= 10
    assert len(server.prompts) >= 5

@pytest.mark.asyncio
async def test_trading_workflow():
    """Test complete trading workflow"""
    # Test account access
    account = await get_account_info()
    assert account["status"] == "ACTIVE"
    
    # Test market data
    quote = await get_stock_quote("SPY")
    assert "price" in quote
    
    # Test order placement
    order = await place_stock_order("SPY", "buy", 1)
    assert order["success"] is True
```

#### 3. Performance Tests (`tests/performance/`)
Validate performance requirements:

```python
# tests/performance/test_performance.py
@pytest.mark.asyncio
async def test_response_times():
    """Test API response times meet requirements"""
    import time
    
    start = time.time()
    await get_stock_quote("SPY")
    response_time = (time.time() - start) * 1000  # Convert to ms
    
    assert response_time < 500  # 95th percentile requirement
```

### Running Tests

```bash
# Run all tests
uv run python alpaca_mcp_server/tests/run_tests.py

# Run specific test categories
uv run python -m pytest alpaca_mcp_server/tests/unit/ -v
uv run python -m pytest alpaca_mcp_server/tests/integration/ -v
uv run python -m pytest alpaca_mcp_server/tests/performance/ -v

# Run with coverage
uv run python -m pytest --cov=alpaca_mcp_server alpaca_mcp_server/tests/

# Quick system verification
uv run python comprehensive_test_summary.py
```

### Test Configuration

```ini
# pytest.ini
[tool:pytest]
testpaths = alpaca_mcp_server/tests
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
timeout = 30
addopts = --strict-markers --tb=short --timeout=30
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    performance: marks tests as performance tests
```

---

## Performance Guidelines

### Response Time Requirements

- **95th percentile**: <500ms for market data queries
- **99th percentile**: <1000ms for complex operations
- **Order execution**: Sub-second placement and confirmation
- **Memory usage**: <200MB baseline consumption

### Optimization Techniques

#### 1. Async/Await Throughout
```python
# Good: Non-blocking operations
async def get_multiple_quotes(symbols: List[str]) -> List[Quote]:
    tasks = [get_stock_quote(symbol) for symbol in symbols]
    return await asyncio.gather(*tasks)

# Bad: Blocking operations
def get_multiple_quotes(symbols: List[str]) -> List[Quote]:
    quotes = []
    for symbol in symbols:
        quotes.append(get_stock_quote(symbol))  # Blocks each call
    return quotes
```

#### 2. Connection Pooling
```python
# Shared HTTP session for connection reuse
import aiohttp

class MarketDataClient:
    def __init__(self):
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=100),
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def close(self):
        await self.session.close()
```

#### 3. Caching Strategies
```python
from functools import lru_cache
import asyncio

# Cache market status (changes infrequently)
@lru_cache(maxsize=1)
def get_market_hours() -> dict:
    return calculate_market_hours()

# Cache with TTL for real-time data
class DataCache:
    def __init__(self, ttl_seconds: int = 60):
        self.cache = {}
        self.ttl = ttl_seconds
    
    async def get_cached_data(self, key: str, fetch_func):
        now = time.time()
        if key in self.cache:
            data, timestamp = self.cache[key]
            if now - timestamp < self.ttl:
                return data
        
        # Cache miss or expired
        data = await fetch_func()
        self.cache[key] = (data, now)
        return data
```

#### 4. Memory Management
```python
# Use generators for large datasets
def process_large_dataset(data_stream):
    for chunk in data_stream:
        yield process_chunk(chunk)  # Process one chunk at a time

# Clean up resources
async def cleanup_streaming_buffers():
    """Regular cleanup of streaming data buffers"""
    for buffer in active_buffers:
        if buffer.age() > max_buffer_age:
            buffer.clear()
```

---

## Contributing Guidelines

### 1. Development Process

#### Branch Strategy
```bash
# Create feature branch
git checkout -b feature/new-trading-tool

# Make changes with atomic commits
git add alpaca_mcp_server/tools/new_tool.py
git commit -m "Add new trading tool with validation"

# Update tests
git add alpaca_mcp_server/tests/unit/test_new_tool.py
git commit -m "Add comprehensive tests for new trading tool"

# Create pull request
git push origin feature/new-trading-tool
```

#### Code Review Checklist
- [ ] Type hints for all function signatures
- [ ] Comprehensive error handling
- [ ] Async/await for all I/O operations
- [ ] Unit tests with >80% coverage
- [ ] Integration tests for workflows
- [ ] Performance impact assessment
- [ ] Documentation updates

### 2. Commit Message Format

```
type(scope): description

feat(tools): add options trading capabilities
fix(streaming): resolve connection timeout issues
docs(readme): update installation instructions
test(unit): add tests for market data tools
perf(cache): optimize quote data caching
refactor(config): simplify configuration loading
```

### 3. Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature  
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Performance tests pass
- [ ] Manual testing completed

## Performance Impact
Describe any performance implications

## Documentation
- [ ] README updated
- [ ] API documentation updated
- [ ] Developer documentation updated
```

---

## Deployment & Operations

### 1. Container Deployment

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install UV
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY alpaca_mcp_server/ ./alpaca_mcp_server/

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
  CMD uv run python -c "from alpaca_mcp_server.tools.health_tools import health_check; print(health_check())"

# Run server
CMD ["uv", "run", "python", "-m", "alpaca_mcp_server"]
```

### 2. Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alpaca-mcp-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: alpaca-mcp-server
  template:
    metadata:
      labels:
        app: alpaca-mcp-server
    spec:
      containers:
      - name: alpaca-mcp-server
        image: alpaca-mcp-server:latest
        ports:
        - containerPort: 8080
        env:
        - name: APCA_API_KEY_ID
          valueFrom:
            secretKeyRef:
              name: alpaca-credentials
              key: api-key-id
        - name: APCA_API_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: alpaca-credentials
              key: api-secret-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 3. Monitoring & Observability

```python
# Prometheus metrics integration
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_count = Counter('mcp_requests_total', 'Total MCP requests', ['tool', 'status'])
request_duration = Histogram('mcp_request_duration_seconds', 'Request duration', ['tool'])
active_positions = Gauge('mcp_active_positions', 'Active trading positions')

# Instrument tools
def instrument_tool(tool_func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_name = tool_func.__name__
        
        try:
            result = await tool_func(*args, **kwargs)
            request_count.labels(tool=tool_name, status='success').inc()
            return result
        except Exception as e:
            request_count.labels(tool=tool_name, status='error').inc()
            raise
        finally:
            duration = time.time() - start_time
            request_duration.labels(tool=tool_name).observe(duration)
    
    return wrapper
```

### 4. Configuration Management

```python
# Environment-specific configuration
class Config:
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.load_config()
    
    def load_config(self):
        if self.environment == "production":
            self.api_base_url = "https://api.alpaca.markets"
            self.log_level = "INFO"
            self.enable_debug = False
        elif self.environment == "staging":
            self.api_base_url = "https://paper-api.alpaca.markets"
            self.log_level = "DEBUG"
            self.enable_debug = True
        else:  # development
            self.api_base_url = "https://paper-api.alpaca.markets"
            self.log_level = "DEBUG"
            self.enable_debug = True
```

---

## Troubleshooting

### Common Issues & Solutions

#### 1. Connection Issues

**Problem**: API connection failures
```python
# Diagnosis
await health_check()                    # Check overall health
await resource_api_status()             # Check API connectivity
await get_stock_quote("SPY")           # Test basic functionality
```

**Solutions**:
```bash
# Check credentials
echo $APCA_API_KEY_ID
echo $APCA_API_SECRET_KEY

# Verify network connectivity
curl -I https://paper-api.alpaca.markets

# Check UV environment
uv run python -c "import alpaca_mcp_server; print('OK')"
```

#### 2. Performance Issues

**Problem**: Slow response times
```python
# Diagnosis
await resource_data_quality()          # Check data feed quality
await get_stock_stream_buffer_stats()  # Check streaming performance
```

**Solutions**:
```bash
# Clear streaming buffers
await clear_stock_stream_buffers()

# System cleanup
await cleanup()

# Check memory usage
import psutil
print(f"Memory usage: {psutil.virtual_memory().percent}%")
```

#### 3. Tool Registration Issues

**Problem**: Tools not appearing in Claude
```python
# Diagnosis
tools_count = len(get_all_tools_help())
print(f"Registered tools: {tools_count}")

# Check specific tool
search_tools("place_order")
```

**Solutions**:
```bash
# Restart MCP server
./start_mcp_server_debug.sh

# Check logs
tail -f /tmp/alpaca_mcp_server_debug.log

# Verify tool registration
uv run python -c "from alpaca_mcp_server.server import get_tool_count; print(f'Tools: {get_tool_count()}')"
```

### Debug Mode

Enable comprehensive debugging:

```bash
# Start in debug mode
./start_mcp_server_debug.sh

# Monitor logs
tail -f /tmp/alpaca_mcp_server_debug.log

# Check specific components
uv run python -c "
from alpaca_mcp_server.tools.account_tools import get_account_info
import asyncio
result = asyncio.run(get_account_info())
print(result)
"
```

### Log Analysis

```bash
# Error patterns
grep "ERROR" /tmp/alpaca_mcp_server_debug.log | tail -10

# Performance issues
grep "slow" /tmp/alpaca_mcp_server_debug.log

# Connection issues
grep -i "connection\|timeout\|failed" /tmp/alpaca_mcp_server_debug.log
```

---

## Advanced Topics

### 1. Custom Tool Development

```python
# Advanced tool with configuration integration
from alpaca_mcp_server.config.global_config import get_global_config

@tool()
async def advanced_trading_tool(
    symbol: str,
    strategy: str = "default"
) -> dict:
    """Advanced trading tool with configuration integration"""
    config = get_global_config()
    
    # Use global configuration
    position_size = config["trading"]["default_position_size_usd"]
    risk_threshold = config["trading"]["max_risk_percent"]
    
    # Implement advanced logic
    analysis = await perform_technical_analysis(symbol)
    risk_assessment = await calculate_risk(symbol, position_size)
    
    if risk_assessment["risk_percent"] > risk_threshold:
        return {
            "success": False,
            "reason": "Risk exceeds threshold",
            "max_risk": risk_threshold,
            "calculated_risk": risk_assessment["risk_percent"]
        }
    
    return await execute_strategy(symbol, strategy, position_size)
```

### 2. Real-Time Stream Processing

```python
# High-performance streaming with asyncio
import asyncio
from collections import deque

class StreamProcessor:
    def __init__(self, max_buffer_size: int = 10000):
        self.buffer = deque(maxlen=max_buffer_size)
        self.subscribers = []
        self.running = False
    
    async def start_processing(self):
        """Start real-time stream processing"""
        self.running = True
        
        # Start multiple coroutines
        await asyncio.gather(
            self.data_ingestion(),
            self.signal_detection(),
            self.notification_dispatch(),
            return_exceptions=True
        )
    
    async def data_ingestion(self):
        """Ingest real-time market data"""
        while self.running:
            try:
                data = await receive_market_data()
                self.buffer.append(data)
                await asyncio.sleep(0.001)  # High frequency processing
            except Exception as e:
                logger.error(f"Data ingestion error: {e}")
    
    async def signal_detection(self):
        """Detect trading signals from buffer"""
        while self.running:
            if len(self.buffer) >= 100:  # Minimum data points
                signals = await analyze_buffer(list(self.buffer)[-100:])
                for signal in signals:
                    await self.notify_subscribers(signal)
            await asyncio.sleep(0.1)
```

### 3. Error Recovery Patterns

```python
# Robust error handling with automatic recovery
import asyncio
from functools import wraps

def with_retry(max_retries: int = 3, delay: float = 1.0):
    """Decorator for automatic retry with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")
            
            raise last_exception
        return wrapper
    return decorator

# Usage
@with_retry(max_retries=3, delay=1.0)
async def reliable_api_call(symbol: str) -> dict:
    """API call with automatic retry"""
    return await alpaca_client.get_quote(symbol)
```

---

This comprehensive developer documentation provides everything needed to understand, extend, and maintain the Alpaca MCP Server. The three-tier architecture, comprehensive testing, and production-ready patterns ensure scalable, maintainable trading system development.

For additional information, refer to the consolidated documentation in the `/docs` directory and the extensive test suite for practical examples.
