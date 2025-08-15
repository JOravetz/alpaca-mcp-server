#!/bin/bash
"""
Setup Script for MCP Intelligent Hooks System
Installs all components and configures Claude Code for intelligent trading automation
"""

echo "🚀 Setting up MCP Intelligent Hooks System"
echo "=========================================="

# Create directory structure
echo "📁 Creating directories..."
mkdir -p ~/.claude/evolution
mkdir -p ~/.claude/hooks
mkdir -p ~/.claude/commands
mkdir -p .claude/evolution
mkdir -p .claude/hooks
mkdir -p .claude/commands

# Make scripts executable
echo "🔧 Setting permissions..."
chmod +x mcp_intelligent_hooks.py
chmod +x .claude/evolution/pattern_detector.py
chmod +x .claude/evolution/log_mcp_action.py

# Install Python dependencies
echo "📦 Installing dependencies..."
uv add toml

# Initialize the system
echo "🧠 Initializing intelligent hooks..."
uv run python mcp_intelligent_hooks.py

# Generate initial settings.toml
echo "⚙️ Configuring Claude Code hooks..."
cat > .claude/settings.toml << 'EOF'
[[hooks.PostToolUse]]
name = "mcp_logger"
matcher = "mcp__alpaca-trading__.*"
[[hooks.PostToolUse.hooks]]
type = "command"
command = "python3 $HOME/.claude/evolution/log_mcp_action.py"
async = true

[[hooks.PostToolUse]]
name = "peak_trough_auto"
matcher = "analyze_peaks_troughs_fast"
[[hooks.PostToolUse.hooks]]
type = "command"
command = '''
SYMBOL=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.symbols // empty')
if [ ! -z "$SYMBOL" ]; then
    echo "🎯 Detected peak/trough analysis for $SYMBOL"
    echo "💡 Run: /auto_trade_setup $SYMBOL"
fi
'''

[[hooks.PostToolUse]]
name = "order_monitor"
matcher = "place.*order"
[[hooks.PostToolUse.hooks]]
type = "command"
command = '''
echo "📊 Order placed - starting position monitor"
bash ~/.claude/hooks/position_monitor.sh &
'''
async = true

[[hooks.OnError]]
name = "market_hours_handler"
matcher = ".*market.*hours.*"
[[hooks.OnError.hooks]]
type = "command"
command = '''
echo "⏰ Market hours error - scheduling for next session"
echo "💡 Tip: Add extended_hours=true to trade now"
'''
EOF

# Create position monitor script
echo "📊 Creating position monitor..."
cat > ~/.claude/hooks/position_monitor.sh << 'EOF'
#!/bin/bash
# Position monitor with profit alerts

INTERVAL=5
for i in {1..60}; do
    POSITIONS=$(mcp call mcp__alpaca-trading__get_positions 2>/dev/null)
    if [ ! -z "$POSITIONS" ]; then
        PNL=$(echo "$POSITIONS" | jq -r '.[0].unrealized_pl // 0')
        if (( $(echo "$PNL > 100" | bc -l) )); then
            echo "🚀 PROFIT SPIKE: $PNL - Consider taking profit!"
        fi
    fi
    sleep $INTERVAL
done
EOF
chmod +x ~/.claude/hooks/position_monitor.sh

# Test MCP connection
echo "🔌 Testing MCP server connection..."
if mcp call mcp__alpaca-trading__health_check > /dev/null 2>&1; then
    echo "✅ MCP server connected successfully"
else
    echo "⚠️ MCP server not responding - make sure it's running"
fi

# Create quick test script
echo "🧪 Creating test script..."
cat > test_hooks.py << 'EOF'
#!/usr/bin/env python3
"""Test the intelligent hooks system"""

import json
from pathlib import Path
from mcp_intelligent_hooks import MCPIntelligentHooks

# Create test session
system = MCPIntelligentHooks()

# Log some test actions
test_actions = [
    ('mcp__alpaca-trading__analyze_peaks_troughs_fast', {'symbols': 'AAPL', 'timeframe': '5Min'}),
    ('mcp__alpaca-trading__get_stock_quote', {'symbol': 'AAPL'}),
    ('mcp__alpaca-trading__place_stock_order', {'symbol': 'AAPL', 'side': 'buy', 'quantity': 100}),
    ('mcp__alpaca-trading__get_option_contracts', {'underlying_symbol': 'SPY', 'type': 'call'}),
]

for tool, params in test_actions:
    system.log_mcp_action(tool, params, "Test result")

print("✅ Test actions logged")
print("📊 Detecting patterns...")
system.detect_patterns()
print("🪝 Generating hooks...")
system.generate_hooks()

# Show report
report = system.generate_report()
print(report)
EOF
chmod +x test_hooks.py

echo ""
echo "✨ Setup Complete!"
echo "=================="
echo ""
echo "📋 What's been installed:"
echo "  • MCP Intelligent Hooks System"
echo "  • Pattern detector for options trading"
echo "  • Auto-trade commands with ARGUMENTS"
echo "  • Position monitoring with profit alerts"
echo "  • Market hours error handling"
echo ""
echo "🎯 Available Commands:"
echo "  • /auto_trade_setup SYMBOL [strategy] [width] [expiration]"
echo "  • /debit_spread SYMBOL [width] [expiration] [contracts]"
echo ""
echo "🚀 How to use:"
echo "1. Start trading normally with your MCP tools"
echo "2. The system learns your patterns after 5-10 trades"
echo "3. Hooks activate automatically based on your workflow"
echo "4. Check ~/.claude/evolution/detected_patterns.json for insights"
echo ""
echo "🧪 To test: uv run python test_hooks.py"
echo ""
echo "📊 The system is now actively:"
echo "  • Logging your MCP tool usage"
echo "  • Learning your trading patterns"
echo "  • Generating automations"
echo "  • Ready for options trading!"