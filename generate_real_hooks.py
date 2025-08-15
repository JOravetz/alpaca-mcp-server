#!/usr/bin/env python3
"""
Generate REAL working hooks for Claude Code based on detected patterns
"""
import json
from pathlib import Path
from datetime import datetime

def generate_hook_command(pattern_sequence, pattern_data):
    """Generate the actual command that will execute when pattern is detected"""
    
    # Map pattern sequences to actual commands
    if pattern_sequence == ["analysis", "options_trade", "bull_call_spread"]:
        return f"""echo '🎯 Auto-executing learned pattern: {' → '.join(pattern_sequence)}' && \\
python3 bull_call_spread_cli.py --dry_run -s SPY --buy 3 --sell 5"""
    
    elif pattern_sequence == ["analysis", "bull_call_spread", "monitor"]:
        return f"""echo '📊 Bull spread workflow detected' && \\
echo 'Next: Monitor positions for profit spikes'"""
    
    else:
        # Generic pattern execution
        return f"""echo '🔄 Pattern detected: {' → '.join(pattern_sequence)}' && \\
python3 ~/.claude/evolution/execute_trade_pattern.py '{json.dumps(pattern_data)}'"""

def main():
    patterns_file = Path.home() / '.claude' / 'evolution' / 'trading_patterns.json'
    settings_file = Path.cwd() / '.claude' / 'settings.toml'
    evolution_log = Path.home() / '.claude' / 'evolution' / 'trading_evolution.log'
    
    if not patterns_file.exists():
        print("No patterns file found")
        return
    
    with open(patterns_file, 'r') as f:
        patterns = json.load(f)
    
    print(f"Found {len(patterns)} patterns")
    
    # Generate hook entries for high-confidence patterns
    generated_hooks = []
    
    for pattern in patterns:
        if pattern['confidence'] >= 0.8:  # Only high confidence
            # Fix: Don't truncate the sequence before joining
            hook_name = f"auto_{'_'.join(pattern['sequence'])}"[:50]  # Truncate AFTER joining
            hook_entry = f"""
# Auto-generated from pattern: {' → '.join(pattern['sequence'])}
# Confidence: {pattern['confidence']*100:.0f}%, Occurrences: {pattern['count']}
[[hooks.PostToolUse]]
name = "{hook_name}"
matcher = "{'|'.join(pattern['sequence'])}"
hooks = [
    {{ type = "command", command = "{generate_hook_command(pattern['sequence'], pattern)}" }}
]
"""
            generated_hooks.append(hook_entry)
            
            # Log the generation
            evolution_log.parent.mkdir(parents=True, exist_ok=True)
            with open(evolution_log, 'a') as f:
                f.write(f"{datetime.now().isoformat()} - Generated hook: {hook_name}\n")
                f.write(f"  Pattern: {' → '.join(pattern['sequence'])}\n")
                f.write(f"  Confidence: {pattern['confidence']*100:.0f}%\n\n")
    
    if generated_hooks:
        print(f"\n✅ Generated {len(generated_hooks)} hooks")
        print("\nAdd these to your .claude/settings.toml file:")
        print("=" * 60)
        for hook in generated_hooks:
            print(hook)
        
        # Save to a file for easy copying
        output_file = Path.cwd() / '.claude' / 'generated_hooks.toml'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            f.write("# Auto-generated hooks from pattern detection\n")
            f.write(f"# Generated at: {datetime.now().isoformat()}\n\n")
            for hook in generated_hooks:
                f.write(hook)
        
        print(f"\n📝 Hooks saved to: {output_file}")
    else:
        print("No high-confidence patterns found (need >= 80% confidence)")
        print("\nCurrent patterns:")
        for p in patterns:
            print(f"  - {' → '.join(p['sequence'])}: {p['confidence']*100:.0f}% confidence")

if __name__ == "__main__":
    main()