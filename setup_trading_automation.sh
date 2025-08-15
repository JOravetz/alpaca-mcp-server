#!/bin/bash
#############################################################
# Trading Automation Setup Script
# Sets up bull call spread algorithm + intelligent hooks
#############################################################

set -e

echo "🚀 Setting up Trading Automation System"
echo "======================================="

# Create directory structure
echo "📁 Creating evolution directories..."
mkdir -p ~/.claude/evolution

# Make all Python scripts executable
echo "🔧 Making scripts executable..."
chmod +x bull_call_spread_cli.py 2>/dev/null || true
chmod +x ~/.claude/evolution/*.py 2>/dev/null || true

# Initialize log files
echo "📝 Initializing log files..."
touch ~/.claude/evolution/trading_actions.jsonl
touch ~/.claude/evolution/trading_evolution.log

# Create initial settings.toml if not exists
if [ ! -f ".claude/settings.toml" ]; then
    echo "⚙️ Creating settings.toml with trading hooks..."
    mkdir -p .claude
    cat > .claude/settings.toml << 'EOF'
[hooks]
# Trading Pattern Learning System
# These hooks track your trading actions and learn from patterns

[[hooks.PostToolUse]]
name = "track_trading_patterns"
matcher = "alpaca|option|spread|peak|trough|order|position"
hooks = [
    { type = "command", command = "python3 ~/.claude/evolution/track_trading_action.py" }
]

[[hooks.PostToolUse]]
name = "analyze_patterns_periodically"
matcher = ".*"
hooks = [
    { type = "command", command = "python3 ~/.claude/evolution/analyze_trading_patterns.py" }
]

# Auto-generated hooks will appear here after pattern detection
EOF
    echo "✅ Settings.toml created"
else
    echo "⚠️ Settings.toml already exists, skipping..."
fi

# Test bull call spread script
echo ""
echo "🧪 Testing bull call spread algorithm..."
if python3 bull_call_spread_cli.py --help > /dev/null 2>&1; then
    echo "✅ Bull call spread script working"
else
    echo "❌ Bull call spread script not found or has errors"
fi

# Display usage instructions
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ SETUP COMPLETE! Here's how to use the system:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1️⃣ Bull Call Spread Algorithm:"
echo "   # Dry run (recommended first)"
echo "   python3 bull_call_spread_cli.py --dry_run"
echo ""
echo "   # Execute with defaults (SPY, 3% below, 5% above)"
echo "   python3 bull_call_spread_cli.py"
echo ""
echo "   # Custom parameters"
echo "   python3 bull_call_spread_cli.py -s AAPL --buy 2 --sell 4 --weeks 3"
echo ""
echo "2️⃣ Pattern Learning System:"
echo "   The system automatically learns from your trading actions!"
echo "   - After 3+ repetitions: Pattern detected"
echo "   - After 5+ repetitions: Auto-hook generated"
echo "   - Check patterns: python3 ~/.claude/evolution/intelligent_trade_analyzer.py"
echo ""
echo "3️⃣ Manual Analysis:"
echo "   # View trading patterns report"
echo "   python3 ~/.claude/evolution/intelligent_trade_analyzer.py"
echo ""
echo "   # Check evolution log"
echo "   cat ~/.claude/evolution/trading_evolution.log"
echo ""
echo "4️⃣ How It Works:"
echo "   - Every trading action is tracked automatically"
echo "   - Patterns are analyzed every 10 actions"
echo "   - Hooks are generated for high-confidence patterns"
echo "   - Your common parameters are learned and suggested"
echo ""
echo "📊 The system will learn YOUR trading style and automate it!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"