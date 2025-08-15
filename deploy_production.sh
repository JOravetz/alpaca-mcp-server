#!/bin/bash
################################################################################
# PRODUCTION DEPLOYMENT SCRIPT - Trading Hook System
# Deploy Date: TODAY
################################################################################

set -e

echo "🚀 DEPLOYING PRODUCTION HOOK SYSTEM"
echo "===================================="
echo "Deployment Time: $(date)"
echo ""

# Step 1: Backup existing data
echo "📦 Step 1: Backing up existing data..."
BACKUP_DIR="$HOME/.claude/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -d "$HOME/.claude/evolution" ]; then
    cp -r "$HOME/.claude/evolution" "$BACKUP_DIR/" 2>/dev/null || true
    echo "  ✓ Backed up to $BACKUP_DIR"
else
    echo "  → No existing data to backup"
fi

# Step 2: Install production system
echo ""
echo "🔧 Step 2: Installing production system..."
chmod +x production_hook_system.py
cp production_hook_system.py "$HOME/.claude/evolution/" 2>/dev/null || mkdir -p "$HOME/.claude/evolution" && cp production_hook_system.py "$HOME/.claude/evolution/"

# Step 3: Migrate existing data to production format
echo ""
echo "📊 Step 3: Migrating existing data..."
python3 << 'EOF'
import json
from pathlib import Path

# Migrate patterns
old_patterns = Path.home() / '.claude' / 'evolution' / 'trading_patterns.json'
new_patterns = Path.home() / '.claude' / 'evolution' / 'patterns.json'

if old_patterns.exists() and not new_patterns.exists():
    with open(old_patterns, 'r') as f:
        data = json.load(f)
    with open(new_patterns, 'w') as f:
        json.dump(data, f, indent=2)
    print("  ✓ Migrated patterns")
else:
    print("  → Patterns already migrated or don't exist")

print("  ✓ Migration complete")
EOF

# Step 4: Initialize production system
echo ""
echo "🎯 Step 4: Initializing production system..."
python3 production_hook_system.py detect
python3 production_hook_system.py status

# Step 5: Create Claude Code integration
echo ""
echo "🔌 Step 5: Setting up Claude Code integration..."
cat > "$HOME/.claude/claude_integration.sh" << 'INTEGRATION'
#!/bin/bash
# Claude Code Integration Layer

# This script bridges Claude Code hooks with our production system
# It should be called from Claude Code's PostToolUse hooks

TOOL_NAME="$1"
TOOL_INPUT="$2"
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"

# Track the action
python3 "$HOME/.claude/evolution/production_hook_system.py" track "$TOOL_NAME" "$TOOL_INPUT"

# Check if we should execute any hooks
# This is where Claude Code would trigger our patterns
INTEGRATION

chmod +x "$HOME/.claude/claude_integration.sh"
echo "  ✓ Integration script created"

# Step 6: Create monitoring dashboard
echo ""
echo "📈 Step 6: Creating monitoring dashboard..."
cat > "$HOME/.claude/evolution/dashboard.py" << 'DASHBOARD'
#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timedelta

metrics_file = Path.home() / '.claude' / 'evolution' / 'metrics.jsonl'
patterns_file = Path.home() / '.claude' / 'evolution' / 'patterns.json'
hooks_file = Path.cwd() / '.claude' / 'hooks.json'

print("=" * 60)
print("TRADING HOOK SYSTEM DASHBOARD")
print("=" * 60)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Load patterns
if patterns_file.exists():
    with open(patterns_file, 'r') as f:
        patterns = json.load(f)
    
    print(f"📊 PATTERNS: {len(patterns)} detected")
    for p in patterns[:5]:
        conf = p['confidence'] * 100
        print(f"  • {' → '.join(p['sequence'])}: {conf:.0f}% confidence ({p['count']} times)")
    print()

# Load hooks
if hooks_file.exists():
    with open(hooks_file, 'r') as f:
        hooks = json.load(f)
    
    print(f"🪝 HOOKS: {len(hooks.get('hooks', []))} generated")
    for h in hooks.get('hooks', [])[:5]:
        print(f"  • {h['name']}: {h['confidence']*100:.0f}% confidence")
    print()

# Load metrics
if metrics_file.exists():
    with open(metrics_file, 'r') as f:
        metrics = [json.loads(line) for line in f]
    
    if metrics:
        recent = [m for m in metrics if 'hook_execution' in m.get('type', '')]
        if recent:
            print(f"⚡ RECENT EXECUTIONS: {len(recent)}")
            success_rate = sum(1 for m in recent if m['data'].get('success')) / len(recent) * 100
            avg_duration = sum(m['data'].get('duration', 0) for m in recent) / len(recent)
            print(f"  • Success rate: {success_rate:.1f}%")
            print(f"  • Avg duration: {avg_duration:.2f}s")
        print()

print("✅ System operational and learning from your patterns!")
DASHBOARD

chmod +x "$HOME/.claude/evolution/dashboard.py"
python3 "$HOME/.claude/evolution/dashboard.py"

# Step 7: Final verification
echo ""
echo "✅ Step 7: Final verification..."
echo ""

# Test the complete pipeline
echo "Testing complete pipeline..."
python3 << 'TEST'
import sys
sys.path.insert(0, '.')
from production_hook_system import ProductionHookSystem

system = ProductionHookSystem()

# Test tracking
system.track_action("get_stock_quote", {"symbol": "SPY"}, "deployment_test")
system.track_action("get_option_contracts", {"symbol": "SPY"}, "deployment_test")
system.track_action("bull_call_spread", {"symbol": "SPY", "buy": 3, "sell": 5}, "deployment_test")

# Get status
status = system.get_status()
print(f"✓ Actions tracked: {status['actions_tracked']}")
print(f"✓ Patterns detected: {status['patterns_detected']}")
print(f"✓ Hooks generated: {status['hooks_generated']}")
print(f"✓ System ready: {status['ready']}")
TEST

echo ""
echo "===================================="
echo "🎉 PRODUCTION DEPLOYMENT COMPLETE!"
echo "===================================="
echo ""
echo "USAGE:"
echo "------"
echo "1. Track actions:    python3 production_hook_system.py track <tool> <input>"
echo "2. View dashboard:   python3 ~/.claude/evolution/dashboard.py"
echo "3. Execute hook:     python3 production_hook_system.py execute <hook_name>"
echo "4. Check status:     python3 production_hook_system.py status"
echo ""
echo "INTEGRATION:"
echo "------------"
echo "Add to Claude Code settings:"
echo '  [[hooks.PostToolUse]]'
echo '  name = "production_tracker"'
echo '  matcher = ".*"'
echo '  hooks = ['
echo '    { type = "command", command = "~/.claude/claude_integration.sh $CLAUDE_TOOL_NAME $CLAUDE_TOOL_INPUT" }'
echo '  ]'
echo ""
echo "📊 Dashboard: python3 ~/.claude/evolution/dashboard.py"
echo "===================================="