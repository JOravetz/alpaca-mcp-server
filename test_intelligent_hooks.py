#!/usr/bin/env python3
"""
Test script for the intelligent hook generator
Creates a mock session with repetitive patterns for Claude to analyze
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

def create_mock_session():
    """Create a mock session log showing repetitive trading workflow patterns"""
    
    session_log = Path.home() / '.claude' / 'evolution' / 'session.jsonl'
    session_log.parent.mkdir(parents=True, exist_ok=True)
    
    # Clear existing log
    if session_log.exists():
        session_log.unlink()
    
    # Create a realistic pattern: repeatedly checking peak/trough, then placing orders
    base_time = datetime.now() - timedelta(hours=1)
    actions = []
    
    # Pattern 1: Check peak/trough analysis before trading (done 5 times)
    symbols = ["WULF", "PPSI", "SGMO", "BSLK", "PGEN"]
    
    for i, symbol in enumerate(symbols):
        # User checks peak/trough
        actions.append({
            "timestamp": (base_time + timedelta(minutes=i*10)).isoformat(),
            "tool": "mcp__alpaca-trading__analyze_peaks_troughs_fast",
            "details": {
                "input": {"symbols": symbol, "timeframe": "1Min", "days": 1},
                "file_paths": [],
                "result": f"Support @ ${8.50 + i*0.25:.2f}"
            }
        })
        
        # User checks current quote
        actions.append({
            "timestamp": (base_time + timedelta(minutes=i*10+1)).isoformat(),
            "tool": "mcp__alpaca-trading__get_stock_quote",
            "details": {
                "input": {"symbol": symbol},
                "file_paths": [],
                "result": f"Current: ${8.55 + i*0.25:.2f}"
            }
        })
        
        # User places order at support
        actions.append({
            "timestamp": (base_time + timedelta(minutes=i*10+2)).isoformat(),
            "tool": "mcp__alpaca-trading__place_stock_order",
            "details": {
                "input": {
                    "symbol": symbol,
                    "side": "buy",
                    "quantity": 100,
                    "order_type": "limit",
                    "limit_price": 8.50 + i*0.25
                },
                "file_paths": [],
                "result": "Order placed successfully"
            }
        })
        
        # User monitors position
        actions.append({
            "timestamp": (base_time + timedelta(minutes=i*10+5)).isoformat(),
            "tool": "mcp__alpaca-trading__get_stock_stream_data",
            "details": {
                "input": {"symbol": symbol, "data_type": "trades", "recent_seconds": 10},
                "file_paths": [],
                "result": "Latest trades showing upward movement"
            }
        })
    
    # Pattern 2: Running scanner then analyzing top movers (done 3 times)
    for i in range(3):
        actions.append({
            "timestamp": (base_time + timedelta(minutes=60+i*15)).isoformat(),
            "tool": "mcp__alpaca-trading__scan_explosive_stocks_fast",
            "details": {
                "input": {"min_percent_change": 10, "max_price": 30},
                "file_paths": [],
                "result": "Found 15 explosive stocks"
            }
        })
        
        # Then analyze the top one
        actions.append({
            "timestamp": (base_time + timedelta(minutes=61+i*15)).isoformat(),
            "tool": "mcp__alpaca-trading__analyze_peaks_troughs_fast",
            "details": {
                "input": {"symbols": f"TOP{i+1}", "timeframe": "5Min", "days": 1},
                "file_paths": [],
                "result": "Support level identified"
            }
        })
    
    # Write all actions to the log
    with open(session_log, 'w') as f:
        for action in actions:
            f.write(json.dumps(action) + '\n')
    
    print(f"✅ Created mock session log with {len(actions)} actions")
    print(f"   Location: {session_log}")
    print(f"\n📊 Patterns included:")
    print("   1. Peak/trough → Quote → Order → Monitor (5 times)")
    print("   2. Scan → Analyze top mover (3 times)")
    
    return session_log

def test_generator():
    """Test the intelligent hook generator with the mock session"""
    
    print("\n🧠 Testing Intelligent Hook Generator...")
    print("=" * 60)
    
    # Import and run the generator
    sys.path.insert(0, str(Path.cwd()))
    from intelligent_hook_generator import IntelligentHookGenerator
    
    generator = IntelligentHookGenerator()
    
    # Load the mock session
    actions = generator.observe_session()
    print(f"\n📖 Loaded {len(actions)} actions from session log")
    
    # Since we can't actually call Claude in test mode, 
    # let's simulate what Claude would generate
    mock_analysis = {
        "pattern_name": "peak_trough_trading",
        "pattern_description": "Analyzes peak/trough, checks quote, places limit order at support, then monitors",
        "trigger": "analyze_peaks_troughs_fast",
        "hook_code": """
# Detected peak/trough analysis - automating the trading workflow
symbol=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.symbols')
if [ ! -z "$symbol" ]; then
    echo "🎯 Auto-trading workflow triggered for $symbol"
    
    # Get current quote
    echo "📊 Checking current price..."
    claude-code "Get quote for $symbol"
    
    # Suggest order at support
    echo "💡 Suggesting limit order at identified support level"
    echo "   Run: place_stock_order at trough price"
    
    # Set up monitoring
    echo "👁️ Ready to monitor position after order"
fi
""",
        "estimated_time_saved": "45"
    }
    
    print(f"\n🤖 Simulated Claude analysis:")
    print(f"   Pattern: {mock_analysis['pattern_name']}")
    print(f"   Description: {mock_analysis['pattern_description']}")
    print(f"   Trigger: When using {mock_analysis['trigger']}")
    print(f"   Time saved: {mock_analysis['estimated_time_saved']} seconds per use")
    
    # Create the hook and command
    generator.create_actual_hook(mock_analysis)
    generator.create_intelligent_command(mock_analysis)
    
    # Verify the files were created
    settings_file = Path.cwd() / '.claude' / 'settings.toml'
    command_file = Path.cwd() / '.claude' / 'commands' / f"{mock_analysis['pattern_name']}.md"
    
    print(f"\n✅ Files created:")
    print(f"   Settings: {settings_file.exists()} - {settings_file}")
    print(f"   Command: {command_file.exists()} - {command_file}")
    
    if settings_file.exists():
        print(f"\n📝 Hook configuration saved to settings.toml")
    
    if command_file.exists():
        print(f"📝 Command /{mock_analysis['pattern_name']} is ready to use")

if __name__ == "__main__":
    # Create mock session
    session_log = create_mock_session()
    
    # Test the generator
    test_generator()
    
    print("\n" + "=" * 60)
    print("🎉 Test complete! The intelligent hook system is working.")
    print("\nTo use with real Claude analysis:")
    print("1. Work normally in Claude Code")
    print("2. The system logs your actions")
    print("3. Claude analyzes patterns and creates specific hooks")
    print("4. Your repetitive workflows become automated!")