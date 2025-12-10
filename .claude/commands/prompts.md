# MCP Prompts - Guided Trading Workflows (Highest Level)

List all available MCP prompts - the highest level guided workflows in the Alpaca MCP Server architecture.

**Architecture:** Prompts → Resources → Tools

## Available Prompts (5 total)

### 🎯 **Core Trading Prompts**

#### **1. `list_trading_capabilities()`**
**Complete Alpaca trading capabilities with guided workflows**
- Overview of all trading features and capabilities
- Guided workflows for different trading strategies
- Integration examples and best practices
- **Use when:** Starting with the platform or need complete overview

---

#### **2. `account_analysis()`**
**Complete portfolio health check with actionable insights**
- Account balance and buying power analysis
- Position performance review
- Risk assessment and recommendations
- Portfolio optimization suggestions
- **Use when:** Daily account review or portfolio health check

---

#### **3. `position_management(symbol=None)`**
**Strategic position review and optimization**
- Individual position analysis
- Exit strategy recommendations
- Risk/reward optimization
- Performance tracking
- **Parameters:** `symbol` (optional) - specific symbol to analyze
- **Use when:** Managing existing positions or planning exits

---

#### **4. `market_analysis(symbols=None, timeframe="1Day", analysis_type="comprehensive")`**
**Real-time market analysis with trading opportunities**
- Market sentiment and conditions
- Sector analysis and trends
- Trading opportunity identification
- Technical and fundamental insights
- **Parameters:**
  - `symbols` (list, optional) - specific symbols to analyze
  - `timeframe` (str) - "1Day", "1Hour", "15Min", etc.
  - `analysis_type` (str) - "comprehensive", "technical", "fundamental"
- **Use when:** Pre-market analysis or identifying opportunities

---

### 🛠 **Utility Prompt**

#### **5. `list_all_tools()`**
**List all available MCP tools with descriptions and usage examples**
- Complete tools reference
- Organized by category
- Usage examples and workflows
- **Use when:** Need to discover available tools

---

## Prompt Usage Patterns

### **Daily Trading Workflow:**
1. **Morning Setup:** `account_analysis()` → `market_analysis()`
2. **Opportunity Identification:** `market_analysis(symbols=["CGTL", "HCTI"], timeframe="1Min")`
3. **Position Management:** `position_management("AAPL")` → `position_management()`
4. **Discovery:** `list_all_tools()` when needed

### **Strategic Analysis:**
```
# Comprehensive market overview
market_analysis(analysis_type="comprehensive")

# Account health check  
account_analysis()

# Position optimization
position_management()
```

### **Quick References:**
```
# Trading capabilities overview
list_trading_capabilities()

# Available tools
list_all_tools()
```

---

## Architecture Integration

**Prompts (Highest Level):**
- Guided workflows and comprehensive analysis
- Strategic decision support
- Multi-tool orchestration

**↓ Use Resources for:**
- Real-time data monitoring
- System health checks
- Performance tracking

**↓ Use Tools for:**
- Individual actions
- Data retrieval
- Order execution

Show examples with: $ARGUMENTS