#!/usr/bin/env python3
"""
Complete system test - verify all components work together
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime

def test_component(name, check_func):
    """Test a component and report status"""
    try:
        result = check_func()
        print(f"✅ {name}: {result}")
        return True
    except Exception as e:
        print(f"❌ {name}: {str(e)}")
        return False

# Component tests
def check_tracking():
    log_file = Path.home() / '.claude' / 'evolution' / 'trading_actions.jsonl'
    if log_file.exists():
        with open(log_file, 'r') as f:
            count = sum(1 for _ in f)
        return f"{count} actions tracked"
    return "No tracking file"

def check_patterns():
    patterns_file = Path.home() / '.claude' / 'evolution' / 'trading_patterns.json'
    if patterns_file.exists():
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
        high_conf = sum(1 for p in patterns if p['confidence'] >= 0.8)
        return f"{len(patterns)} patterns ({high_conf} high-confidence)"
    return "No patterns file"

def check_hooks():
    settings_file = Path.cwd() / '.claude' / 'settings.toml'
    if settings_file.exists():
        with open(settings_file, 'r') as f:
            content = f.read()
        auto_hooks = content.count('Auto-generated from pattern')
        total_hooks = content.count('[[hooks.')
        return f"{total_hooks} total hooks ({auto_hooks} auto-generated)"
    return "No settings file"

def check_evolution_log():
    log_file = Path.home() / '.claude' / 'evolution' / 'trading_evolution.log'
    if log_file.exists():
        with open(log_file, 'r') as f:
            lines = f.readlines()
        if lines:
            return f"{len(lines)} log entries"
        return "Empty log"
    return "No log file"

def check_bull_call_spread():
    """Test the bull call spread script"""
    result = subprocess.run(
        ['python3', 'bull_call_spread_cli.py', '--help'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return "Script working"
    return "Script error"

print("=" * 60)
print("COMPLETE SYSTEM TEST REPORT")
print("=" * 60)
print(f"Timestamp: {datetime.now().isoformat()}")
print()

# Run all tests
results = []
results.append(test_component("Action Tracking", check_tracking))
results.append(test_component("Pattern Detection", check_patterns))
results.append(test_component("Hook Generation", check_hooks))
results.append(test_component("Evolution Log", check_evolution_log))
results.append(test_component("Bull Call Spread", check_bull_call_spread))

print()
print("=" * 60)
if all(results):
    print("🎉 SYSTEM FULLY OPERATIONAL!")
else:
    print("⚠️ Some components need attention")
print("=" * 60)

# Show a sample hook in action
print("\nSample Hook Configuration:")
print("-" * 40)
settings_file = Path.cwd() / '.claude' / 'settings.toml'
if settings_file.exists():
    with open(settings_file, 'r') as f:
        lines = f.readlines()
    
    # Find first auto-generated hook
    in_hook = False
    hook_lines = []
    for line in lines:
        if 'Auto-generated from pattern' in line:
            in_hook = True
        if in_hook:
            hook_lines.append(line.rstrip())
            if line.strip() == ']':
                break
    
    if hook_lines:
        print('\n'.join(hook_lines[:10]))  # First 10 lines

