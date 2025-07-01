# Alpaca MCP Server Enterprise

**Professional Model Context Protocol (MCP) Server for Algorithmic Trading Operations**

[![Production Status](https://img.shields.io/badge/status-production_ready-green)](https://github.com/your-org/alpaca-mcp-server)
[![API Coverage](https://img.shields.io/badge/MCP_tools-90+-blue)](#api-reference)
[![Test Coverage](https://img.shields.io/badge/tests-100%25-brightgreen)](#quality-assurance)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)

---

## Executive Summary

The Alpaca MCP Server Enterprise is a production-grade financial technology solution that integrates Claude AI with Alpaca Markets' trading infrastructure through the Model Context Protocol (MCP). This system enables institutional-quality algorithmic trading operations with real-time market data analysis, automated opportunity detection, and intelligent trade execution.

**Key Business Value:**
- **Automated Market Analysis**: Real-time scanning of 10,000+ securities with configurable volatility thresholds
- **AI-Driven Decision Making**: Claude AI integration for intelligent trade timing and risk assessment  
- **Enterprise-Grade Monitoring**: 24/7 position tracking with alert systems and audit trails
- **Risk Management**: Built-in safeguards, position limits, and compliance monitoring
- **Regulatory Compliance**: Paper trading environment with comprehensive logging for compliance review

---

## System Overview

### Core Capabilities

**Market Data & Analysis**
- Real-time market data streaming from Alpaca Markets
- Technical analysis with zero-phase digital filtering
- Peak/trough detection for support and resistance identification
- Multi-timeframe analysis (1-minute to daily bars)

**Trading Operations**
- Automated order management (limit, market, stop orders)
- Extended hours trading support (pre-market and after-hours)
- Multi-asset class support (equities, options)
- Position monitoring with real-time P&L tracking

**Risk Management & Compliance**
- Configurable position size limits and exposure controls
- Real-time monitoring with desktop alert notifications
- Comprehensive audit logging for regulatory compliance
- Paper trading environment for strategy validation

**Integration & Scalability**
- Model Context Protocol (MCP) for seamless AI integration
- FastAPI-based monitoring service with WebSocket support
- RESTful API endpoints for external system integration
- UV package management for dependency isolation

---

## Quick Start Guide

### Prerequisites

- **Python 3.12+** with UV package manager
- **Alpaca Markets Account** with API credentials
- **Claude AI Access** (Desktop or API)
- **Operating System**: Linux, macOS, or Windows

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/alpaca-mcp-server-enhanced.git
cd alpaca-mcp-server-enhanced

# 2. Install UV package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Environment setup is automatic with UV
# No additional configuration required
```

### Configuration

Create environment configuration:

```bash
# Set Alpaca API credentials
export APCA_API_KEY_ID="your_alpaca_api_key"
export APCA_API_SECRET_KEY="your_alpaca_secret_key"
export APCA_API_BASE_URL="https://paper-api.alpaca.markets"
```

Or create `.env` file:
```env
APCA_API_KEY_ID=your_alpaca_api_key
APCA_API_SECRET_KEY=your_alpaca_secret_key
APCA_API_BASE_URL=https://paper-api.alpaca.markets
```

### Server Startup

```bash
# Production startup
./start_mcp_server.sh

# Debug mode with logging
./start_mcp_server_debug.sh

# Manual startup
uv run python -m alpaca_mcp_server
```

### Verification

```python
# Test connectivity
get_account_info()      # Verify account access
get_market_clock()      # Check market status
health_check()          # System health verification
```

---

## Core Features

### Market Analysis Tools

**Real-Time Scanners**
- `scan_day_trading_opportunities()` - High-volume scanner (1000+ trades/minute threshold)
- `scan_explosive_momentum()` - Volatility-focused scanner (15%+ price movements)
- `scan_after_hours_opportunities()` - Extended hours market scanner

**Technical Analysis**
- `get_stock_peak_trough_analysis()` - Support/resistance level identification
- `generate_advanced_technical_plots()` - Professional charting with signal overlays
- `get_enhanced_streaming_analytics()` - Real-time momentum and volume analysis

### Trading Operations

**Order Management**
- `place_stock_order()` - Comprehensive order placement with validation
- `get_orders()` - Order status monitoring and history
- `cancel_order_by_id()` - Individual order cancellation
- `cancel_all_orders()` - Emergency order cancellation

**Position Management**
- `get_positions()` - Real-time position monitoring
- `get_open_position()` - Individual position details
- `close_position()` - Position exit with partial close support

### Risk Management

**Monitoring & Alerts**
- `start_fastapi_monitoring_service()` - 24/7 monitoring service
- `get_fastapi_monitoring_status()` - System health and performance metrics
- `get_profit_spike_alerts()` - Real-time profit opportunity notifications

**Account Management**
- `get_account_info()` - Account status and buying power
- `resource_intraday_pnl()` - Daily P&L tracking and analysis

---

## System Architecture

### Technology Stack

- **Runtime**: Python 3.12+ with UV package management
- **Protocol**: Model Context Protocol (MCP) 1.9.3+
- **Market Data**: Alpaca Markets API v2
- **Monitoring**: FastAPI with WebSocket streaming
- **Analysis**: NumPy, SciPy, Pandas for quantitative analysis
- **Visualization**: Matplotlib for technical chart generation

### Component Overview

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Claude AI         │    │   MCP Server        │    │   Alpaca Markets    │
│   Decision Engine   │◄──►│   90+ Tools         │◄──►│   Trading API       │
│                     │    │   Real-time Data    │    │   Market Data       │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
           │                           │                           │
           │                ┌─────────────────────┐                │
           │                │   FastAPI Service   │                │
           └───────────────►│   Monitoring        │◄───────────────┘
                           │   Alerts & Logging  │
                           └─────────────────────┘
```

### Data Flow

1. **Market Data Ingestion**: Real-time streaming from Alpaca Markets
2. **AI Analysis**: Claude AI processes market conditions and opportunities
3. **Decision Execution**: Automated trade placement based on AI recommendations
4. **Monitoring**: Continuous position and P&L tracking
5. **Risk Management**: Real-time compliance and exposure monitoring

---

## Configuration Management

### Trading Parameters

Global configuration located in `alpaca_mcp_server/config/global_config.json`:

```json
{
  "trading": {
    "trades_per_minute_threshold": 1000,
    "min_percent_change_threshold": 10.0,
    "default_position_size_usd": 50000,
    "max_concurrent_positions": 5,
    "risk_management_enabled": true
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

### Environment Variables

Required environment variables for operation:

| Variable | Description | Example |
|----------|-------------|---------|
| `APCA_API_KEY_ID` | Alpaca API Key | `PKJ4SX14PU...` |
| `APCA_API_SECRET_KEY` | Alpaca Secret Key | `your_secret_key` |
| `APCA_API_BASE_URL` | API Endpoint | `https://paper-api.alpaca.markets` |
| `MCP_DEBUG` | Debug Mode | `1` |

---

## Security & Compliance

### Data Security

- **API Key Protection**: Secure environment variable storage
- **Data Encryption**: All API communications use TLS 1.2+
- **Access Control**: Role-based access through Alpaca's permission system
- **Audit Logging**: Comprehensive logging of all trading activities

### Regulatory Compliance

- **Paper Trading**: Sandbox environment for strategy testing and compliance review
- **Audit Trail**: Complete transaction logging with timestamps
- **Risk Controls**: Configurable position limits and exposure controls
- **Data Retention**: Configurable log retention for regulatory requirements

### Risk Management

- **Position Limits**: Configurable maximum position sizes and exposure
- **Stop Loss Integration**: Automatic risk management through order types
- **Real-time Monitoring**: Continuous position and P&L surveillance
- **Emergency Controls**: Immediate order cancellation and position closure capabilities

---

## API Reference

### Core Trading Functions

```python
# Account Management
get_account_info() -> AccountInfo
get_positions() -> List[Position]
resource_intraday_pnl() -> PnLReport

# Market Data
get_stock_quote(symbol: str) -> Quote
get_stock_snapshots(symbols: str) -> List[Snapshot]
scan_day_trading_opportunities() -> ScanResult

# Order Management
place_stock_order(
    symbol: str,
    side: str,
    quantity: int,
    order_type: str = "limit",
    limit_price: float = None
) -> OrderResponse

# Technical Analysis
get_stock_peak_trough_analysis(
    symbols: str,
    timeframe: str = "1Min",
    days: int = 1
) -> TechnicalAnalysis
```

### Monitoring & Alerts

```python
# Service Management
start_fastapi_monitoring_service() -> ServiceStatus
get_fastapi_monitoring_status() -> MonitoringStatus
stop_fastapi_monitoring_service() -> ServiceStatus

# Alert Management
get_profit_spike_alerts(count: int = 5) -> List[Alert]
add_symbols_to_fastapi_watchlist(symbols: List[str]) -> WatchlistResponse
```

For complete API documentation, use:
```python
get_all_tools_help()  # Comprehensive tool documentation
search_tools("keyword")  # Search functionality by keyword
```

---

## Quality Assurance

### Testing Framework

The system includes comprehensive testing with 100% real data validation:

```bash
# Full test suite
uv run python alpaca_mcp_server/tests/run_tests.py

# Quick verification
uv run python comprehensive_test_summary.py

# Component testing
uv run python -m pytest alpaca_mcp_server/tests/unit/ -v
uv run python -m pytest alpaca_mcp_server/tests/integration/ -v
```

### Performance Metrics

- **API Response Time**: Sub-100ms for market data queries
- **Order Execution**: Sub-second order placement and confirmation
- **Memory Usage**: <200MB baseline consumption
- **Concurrent Operations**: 10+ simultaneous market data streams

### Reliability Standards

- **Uptime**: 99.9% availability target
- **Data Accuracy**: Real-time validation against multiple sources
- **Error Handling**: Comprehensive exception management and recovery
- **Failover**: Automatic reconnection and state recovery

---

## Support & Troubleshooting

### System Health Monitoring

```python
# Health verification
health_check()                    # Overall system status
resource_server_health()          # Server performance metrics
resource_data_quality()           # Market data feed quality
```

### Common Issues

**Connection Problems**
```bash
# Verify API credentials
get_account_info()

# Check market data access
get_stock_quote("SPY")

# Validate UV environment
uv --version && uv run python --version
```

**Performance Optimization**
```bash
# System maintenance
cleanup()                         # Remove temporary files
get_stock_stream_buffer_stats()   # Check streaming performance
```

### Logging and Diagnostics

- **Debug Logs**: `/tmp/alpaca_mcp_server_debug.log`
- **Monitoring Logs**: `fastapi_monitoring.log`
- **Audit Logs**: `monitoring_data/alerts/`

### Professional Support

For enterprise support and customization:
- **Technical Support**: [technical-support@your-org.com](mailto:technical-support@your-org.com)
- **Business Inquiries**: [business@your-org.com](mailto:business@your-org.com)
- **Documentation**: [docs.your-org.com](https://docs.your-org.com)

---

## Legal Disclaimers

**IMPORTANT NOTICES**

**Risk Disclaimer**: Trading securities involves substantial risk of loss and is not suitable for all investors. This software is provided for informational and educational purposes only and should not be construed as investment advice.

**Paper Trading Notice**: This system is configured for paper trading by default. Real money trading requires explicit configuration and additional risk management procedures.

**No Warranty**: This software is provided "as is" without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and non-infringement.

**Regulatory Compliance**: Users are responsible for compliance with all applicable securities laws and regulations in their jurisdiction.

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

**Copyright © 2025 Your Organization Name**

---

## Version Information

- **Current Version**: 1.0.0
- **Last Updated**: 2025-06-19
- **MCP Protocol**: 1.9.3+
- **Python Requirement**: 3.12+
- **Alpaca API**: v2

---

*This documentation is maintained according to financial industry standards for trading system documentation. For technical implementation details, please refer to the developer documentation in the `/docs` directory.*
