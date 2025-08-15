#!/bin/bash
# Test a real hook execution

echo "=== SIMULATING CLAUDE CODE HOOK TRIGGER ==="
echo ""

# Set environment variables that Claude Code would set
export CLAUDE_TOOL_NAME="get_option_contracts"
export CLAUDE_TOOL_INPUT='{"underlying_symbol": "SPY", "type": "call"}'

echo "Tool triggered: $CLAUDE_TOOL_NAME"
echo "With input: $CLAUDE_TOOL_INPUT"
echo ""

# Check if this matches our hook pattern
if [[ "$CLAUDE_TOOL_NAME" =~ "option" ]]; then
    echo "🎯 HOOK MATCH! Pattern detected: options trading"
    echo ""
    echo "Executing learned automation..."
    echo "-----------------------------------"
    
    # Actually run the bull call spread
    python3 bull_call_spread_cli.py --dry_run -s SPY --buy 3 --sell 5 --weeks 2
    
    echo "-----------------------------------"
    echo "✅ Hook execution complete!"
else
    echo "No matching hook for this tool"
fi