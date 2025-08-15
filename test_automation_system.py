#!/usr/bin/env python3
"""
Test the complete automation system by simulating the hook environment
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

def simulate_hook_trigger(tool_name, tool_input):
    """Simulate how Claude Code triggers hooks"""
    
    # Set up environment variables that Claude Code would set
    env = os.environ.copy()
    env['CLAUDE_TOOL_NAME'] = tool_name
    env['CLAUDE_TOOL_INPUT'] = json.dumps(tool_input)
    
    # Create stdin data
    stdin_data = {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "session_id": "test_session_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    }
    
    # Run the tracking hook
    track_script = Path.home() / '.claude' / 'evolution' / 'track_trading_action.py'
    if track_script.exists():
        result = subprocess.run(
            ['python3', str(track_script)],
            input=json.dumps(stdin_data),
            text=True,
            capture_output=True,
            env=env
        )
        if result.stdout:
            print(f"  Hook output: {result.stdout.strip()}")
    
    return stdin_data

def main():
    print("=" * 60)
    print("Testing Trading Automation System")
    print("=" * 60)
    print()
    
    # Test 1: Simulate a series of trading actions
    print("📊 TEST 1: Simulating trading workflow...")
    print("-" * 40)
    
    actions = [
        ("get_stock_quote", {"symbol": "SPY"}),
        ("get_option_contracts", {"underlying_symbol": "SPY", "type": "call"}),
        ("bull_call_spread", {"symbol": "SPY", "buy": 3, "sell": 5}),
        ("get_positions", {}),
        ("get_stock_quote", {"symbol": "SPY"}),
        ("get_option_contracts", {"underlying_symbol": "SPY", "type": "call"}),
        ("bull_call_spread", {"symbol": "SPY", "buy": 3, "sell": 5}),
        ("get_positions", {}),
        ("get_stock_quote", {"symbol": "SPY"}),
        ("get_option_contracts", {"underlying_symbol": "SPY", "type": "call"}),
        ("bull_call_spread", {"symbol": "SPY", "buy": 3, "sell": 5}),
        ("get_positions", {}),
    ]
    
    for i, (tool, input_data) in enumerate(actions, 1):
        print(f"  Action {i}: {tool}")
        simulate_hook_trigger(tool, input_data)
    
    print()
    
    # Test 2: Check if actions were tracked
    print("📝 TEST 2: Checking tracked actions...")
    print("-" * 40)
    
    log_file = Path.home() / '.claude' / 'evolution' / 'trading_actions.jsonl'
    if log_file.exists():
        with open(log_file, 'r') as f:
            lines = f.readlines()
        print(f"  ✓ {len(lines)} actions tracked")
        
        # Show last few actions
        if lines:
            print("  Last 3 tracked actions:")
            for line in lines[-3:]:
                try:
                    action = json.loads(line)
                    print(f"    - {action.get('action_type', 'unknown')}: {action.get('tool', 'unknown')}")
                except:
                    pass
    else:
        print("  ✗ No tracking file found")
    
    print()
    
    # Test 3: Run pattern analyzer
    print("🔍 TEST 3: Running pattern analysis...")
    print("-" * 40)
    
    analyze_script = Path.home() / '.claude' / 'evolution' / 'analyze_trading_patterns.py'
    if analyze_script.exists():
        result = subprocess.run(
            ['python3', str(analyze_script)],
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(f"  {result.stdout.strip()}")
        if result.returncode == 0:
            print("  ✓ Pattern analysis completed")
    
    # Check patterns file
    patterns_file = Path.home() / '.claude' / 'evolution' / 'trading_patterns.json'
    if patterns_file.exists():
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
        print(f"  ✓ {len(patterns)} patterns detected")
        for p in patterns[:3]:
            print(f"    - Pattern: {' → '.join(p['sequence'])} (confidence: {p['confidence']*100:.0f}%)")
    
    print()
    
    # Test 4: Check if hooks were generated
    print("🪝 TEST 4: Checking for auto-generated hooks...")
    print("-" * 40)
    
    settings_file = Path.cwd() / '.claude' / 'settings.toml'
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            content = f.read()
        
        # Count hooks
        hook_count = content.count('[[hooks.')
        auto_generated = 'auto_trade_' in content
        
        print(f"  ✓ {hook_count} total hooks in settings.toml")
        if auto_generated:
            print("  ✓ Auto-generated trading hooks found!")
        else:
            print("  ⚠️ No auto-generated hooks yet (need higher confidence patterns)")
    
    print()
    
    # Test 5: Generate analysis report
    print("📈 TEST 5: Generating intelligence report...")
    print("-" * 40)
    
    analyzer_script = Path.home() / '.claude' / 'evolution' / 'intelligent_trade_analyzer.py'
    if analyzer_script.exists():
        result = subprocess.run(
            ['python3', str(analyzer_script)],
            capture_output=True,
            text=True
        )
        if result.stdout:
            # Show just the summary
            lines = result.stdout.split('\n')
            for line in lines[:20]:  # First 20 lines
                if line.strip():
                    print(f"  {line}")
    
    print()
    print("=" * 60)
    print("✅ Automation System Test Complete!")
    print("=" * 60)
    print()
    print("The system is now learning from your actions.")
    print("After more repetitions, it will auto-generate hooks.")
    print()

if __name__ == "__main__":
    main()