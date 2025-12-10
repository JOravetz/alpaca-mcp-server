# MCP Resources - Real-time Trading Context

List all available MCP resources - the middle layer providing dynamic trading context in the Alpaca MCP Server architecture.

**Architecture:** Prompts → **Resources** → Tools

## Available Resources (14 total)

### 💼 **Account & Portfolio Resources**

#### **1. `account://status`**
**Real-time account health and trading capacity**
- Account balance and buying power
- Account status and restrictions
- Trading permissions and capabilities
- **Use when:** Checking trading capacity before placing orders

---

#### **2. `positions://current`**
**Live position data with P&L updates**
- Current positions with real-time P&L
- Position sizes and market values
- Unrealized gains/losses
- **Use when:** Monitoring active positions during trading

---

#### **3. `portfolio://performance`**
**Real-time portfolio performance metrics and P&L analysis**
- Total portfolio value and performance
- Daily P&L tracking
- Performance metrics and ratios
- **Use when:** Evaluating overall portfolio health

---

#### **4. `portfolio://allocation`**
**Asset allocation breakdown with winners/losers analysis**
- Sector and asset class allocation
- Top winners and losers
- Concentration risk analysis
- **Use when:** Portfolio rebalancing decisions

---

#### **5. `portfolio://risk`**
**Portfolio risk metrics and exposure analysis**
- Risk exposure by position
- Correlation analysis
- Volatility metrics
- **Use when:** Risk management and position sizing

---

### 📊 **Market & Data Resources**

#### **6. `market://conditions`**
**Current market status and conditions**
- Market open/closed status
- Market sentiment indicators
- Trading session information
- **Use when:** Before starting trading sessions

---

#### **7. `market://momentum`**
**Real-time market momentum for SPY with default parameters**
- SPY momentum analysis
- Moving average crossovers
- Trend strength indicators
- **Use when:** Understanding overall market direction

---

#### **8. `data://quality`**
**Monitor data feed quality with default parameters**
- Data latency monitoring
- Quote freshness checks
- Feed reliability metrics
- **Use when:** Troubleshooting data issues

---

### 🌊 **Streaming Resources**

#### **9. `streams://status`**
**Real-time streaming status and buffer statistics**
- Active stream subscriptions
- Buffer utilization
- Connection health
- **Use when:** Managing streaming data feeds

---

#### **10. `streams://performance`**
**Streaming performance metrics and health indicators**
- Throughput statistics
- Latency measurements
- Error rates
- **Use when:** Optimizing streaming performance

---

### 💰 **Trading Performance Resources**

#### **11. `positions://intraday_pnl`**
**Track today's intraday P&L with default parameters**
- Today's realized P&L
- Intraday performance tracking
- Trade-by-trade analysis
- **Use when:** Monitoring daily trading performance

---

### 🔧 **System Health Resources**

#### **12. `server://health`**
**Comprehensive server health monitoring**
- Server status and uptime
- Memory and CPU usage
- Connection health
- **Use when:** System diagnostics and monitoring

---

#### **13. `server://session`**
**Trading session and market status**
- Current session phase
- Extended hours status
- Next market events
- **Use when:** Planning trading activities

---

#### **14. `server://apis`**
**Monitor API connections and performance**
- API endpoint status
- Response times
- Rate limiting status
- **Use when:** Troubleshooting API issues

---

## Resource Usage Patterns

### **Pre-Trading Setup:**
1. **Market Check:** `market://conditions` → `server://session`
2. **Account Review:** `account://status` → `portfolio://performance`
3. **System Health:** `server://health` → `data://quality`

### **Active Trading:**
1. **Position Monitoring:** `positions://current` → `positions://intraday_pnl`
2. **Market Context:** `market://momentum` → `market://conditions`
3. **Data Quality:** `streams://status` → `streams://performance`

### **Post-Trading Analysis:**
1. **Performance Review:** `portfolio://performance` → `positions://intraday_pnl`
2. **Risk Assessment:** `portfolio://risk` → `portfolio://allocation`

---

## Architecture Integration

**Prompts (Highest Level):**
- Use multiple resources for comprehensive analysis
- Orchestrate resource data for trading decisions
- Provide strategic insights

**↓ Resources (Real-time Context):**
- Dynamic data monitoring
- Performance tracking
- System health validation

**↓ Tools (Individual Actions):**
- Execute specific operations
- Retrieve point-in-time data
- Place orders and manage positions

---

## Resource vs Tool Mirror Functions

Many resources also have corresponding **tool mirror functions** for Claude Code compatibility:

| Resource | Tool Mirror |
|----------|-------------|
| `account://status` | `resource_account_status()` |
| `positions://current` | `resource_current_positions()` |
| `market://conditions` | `resource_market_conditions()` |
| `market://momentum` | `resource_market_momentum()` |
| `positions://intraday_pnl` | `resource_intraday_pnl()` |
| `data://quality` | `resource_data_quality()` |
| `server://health` | `resource_server_health()` |
| `server://session` | `resource_session_status()` |
| `server://apis` | `resource_api_status()` |

**Note:** Tool mirrors allow parameter customization while resources use optimized defaults for real-time monitoring.

Show resource data for: $ARGUMENTS