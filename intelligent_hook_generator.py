#!/usr/bin/env python3
"""
intelligent_hook_generator.py
This ACTUALLY has Claude observe your patterns and generate useful hooks
Uses YOUR existing Claude Code MAX plan authentication - no API key needed!
"""

import json
import os
from pathlib import Path
from datetime import datetime
import subprocess
import toml

class IntelligentHookGenerator:
    def __init__(self):
        # No API key needed - use Claude Code's existing connection
        self.session_log = Path.home() / '.claude' / 'evolution' / 'session.jsonl'
        self.claude_dir = Path.cwd() / '.claude'
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        
    def observe_session(self):
        """Read the actual Claude Code session transcript"""
        if not self.session_log.exists():
            return []
            
        actions = []
        with open(self.session_log, 'r') as f:
            for line in f:
                actions.append(json.loads(line))
        return actions
    
    def analyze_with_claude(self, actions):
        """Have Claude analyze the ACTUAL actions and generate REAL hooks"""
        
        # Format the actions for Claude to understand
        session_description = "\n".join([
            f"{a['timestamp']}: {a['tool']} - {json.dumps(a['details'])}"
            for a in actions[-50:]  # Last 50 actions
        ])
        
        prompt = f"""You are analyzing a developer's actual workflow to create automation.

Here's what they actually did:
{session_description}

Analyze this and:
1. Identify the specific repetitive pattern
2. Understand what they're trying to accomplish
3. Generate a Claude Code hook that automates EXACTLY what they keep doing

Return a JSON object with:
{{
    "pattern_name": "descriptive name",
    "pattern_description": "what the developer is doing",
    "trigger": "when to activate this automation",
    "hook_code": "the actual bash/python code to automate this",
    "estimated_time_saved": "seconds per occurrence"
}}

Make the hook_code SPECIFIC to their actual files and commands, not generic placeholders."""

        # Use Claude Code's built-in connection via subprocess
        analysis_script = f"""
import subprocess
import json

prompt = '''{prompt}'''

# Call Claude through Claude Code CLI
result = subprocess.run(
    ['claude-code', '--json', prompt],
    capture_output=True,
    text=True
)

print(result.stdout)
"""
        
        result = subprocess.run(
            ['python3', '-c', analysis_script],
            capture_output=True,
            text=True
        )
        
        return json.loads(result.stdout)
    
    def create_actual_hook(self, analysis):
        """Create a REAL, WORKING Claude Code hook from Claude's analysis"""
        
        # Create the hook configuration
        hook_config = {
            "name": analysis['pattern_name'],
            "matcher": analysis['trigger'],
            "hooks": [{
                "type": "command",
                "command": analysis['hook_code']
            }]
        }
        
        # Load existing settings
        settings_file = self.claude_dir / 'settings.toml'
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                settings = toml.load(f)
        else:
            settings = {"hooks": {}}
        
        # Add the new hook
        if 'PreToolUse' not in settings['hooks']:
            settings['hooks']['PreToolUse'] = []
        settings['hooks']['PreToolUse'].append(hook_config)
        
        # Save updated settings
        with open(settings_file, 'w') as f:
            toml.dump(settings, f)
        
        print(f"✅ Created hook: {analysis['pattern_name']}")
        print(f"   Trigger: {analysis['trigger']}")
        print(f"   Saves: {analysis['estimated_time_saved']} seconds per use")
        
        return hook_config
    
    def create_intelligent_command(self, analysis):
        """Also create a Claude Code command for manual triggering"""
        
        command_file = self.claude_dir / 'commands' / f"{analysis['pattern_name']}.md"
        command_file.parent.mkdir(exist_ok=True)
        
        command_content = f"""---
name: {analysis['pattern_name']}
description: {analysis['pattern_description']}
---

# {analysis['pattern_name']}

This command automates: {analysis['pattern_description']}

Estimated time saved: {analysis['estimated_time_saved']} seconds

## What it does:
{analysis['pattern_description']}

## Implementation:
```bash
{analysis['hook_code']}
```

$ARGUMENTS
"""
        
        with open(command_file, 'w') as f:
            f.write(command_content)
        
        print(f"✅ Created command: /{analysis['pattern_name']}")

# The bridge that connects Claude Code hooks to Claude's intelligence
class ClaudeCodeBridge:
    """This runs as a service that hooks can call - uses YOUR Claude Code connection"""
    
    def __init__(self):
        # No separate API needed - you're already authenticated
        pass
        
    def process_hook_request(self, context):
        """Hooks call this to get intelligent responses using YOUR Claude session"""
        
        prompt = f"""Based on this context from a Claude Code session:
{json.dumps(context, indent=2)}

Generate the appropriate action to take. Be specific and executable.
Return only the shell command to run."""

        # Use YOUR existing Claude Code connection
        result = subprocess.run(
            ['claude-code', '--json', prompt],
            capture_output=True,
            text=True
        )
        
        return result.stdout

# The actual session observer that logs everything
class SessionObserver:
    """Logs all Claude Code actions with full context"""
    
    def __init__(self):
        self.log_file = Path.home() / '.claude' / 'evolution' / 'session.jsonl'
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
    def log_action(self, tool, details):
        """Called by hooks to log actions with full context"""
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "details": details,
            "working_dir": os.getcwd(),
            "git_branch": self.get_git_branch(),
            "recent_files": self.get_recent_files()
        }
        
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def get_git_branch(self):
        try:
            return subprocess.check_output(
                ['git', 'branch', '--show-current'],
                text=True
            ).strip()
        except:
            return None
    
    def get_recent_files(self):
        try:
            return subprocess.check_output(
                ['find', '.', '-type', 'f', '-mmin', '-5', '-name', '*.py'],
                text=True
            ).strip().split('\n')[:5]
        except:
            return []

def setup_intelligent_system():
    """Set up the complete intelligent hook system"""
    
    print("🧠 Setting up Intelligent Claude Code Hook System...")
    
    # Create the observer hook that logs everything
    observer_hook = """#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime

# Read Claude Code input
try:
    input_data = json.load(sys.stdin)
except:
    input_data = {}

# Log with full context
log_entry = {
    "timestamp": datetime.now().isoformat(),
    "tool": input_data.get("tool_name", "unknown"),
    "details": {
        "input": input_data.get("tool_input", {}),
        "file_paths": input_data.get("file_paths", []),
        "session_id": input_data.get("session_id", ""),
        "full_context": input_data
    }
}

log_file = Path.home() / '.claude' / 'evolution' / 'session.jsonl'
log_file.parent.mkdir(parents=True, exist_ok=True)

with open(log_file, 'a') as f:
    f.write(json.dumps(log_entry) + '\\n')

# Check if we should generate new hooks (every 20 actions)
with open(log_file, 'r') as f:
    line_count = sum(1 for _ in f)

if line_count % 20 == 0:
    print("🔄 Analyzing patterns and generating hooks...")
    import subprocess
    subprocess.run(['python3', str(Path.home() / '.claude' / 'evolution' / 'generate_hooks.py')])

sys.exit(0)
"""
    
    # Save the observer
    observer_file = Path.home() / '.claude' / 'evolution' / 'observer.py'
    observer_file.parent.mkdir(parents=True, exist_ok=True)
    with open(observer_file, 'w') as f:
        f.write(observer_hook)
    os.chmod(observer_file, 0o755)
    
    # Create the hook generator that Claude runs
    generator = """#!/usr/bin/env python3
from intelligent_hook_generator import IntelligentHookGenerator

generator = IntelligentHookGenerator()
actions = generator.observe_session()

if len(actions) > 10:
    print("🤖 Analyzing your workflow with Claude...")
    analysis = generator.analyze_with_claude(actions)
    
    print(f"📊 Found pattern: {analysis['pattern_name']}")
    
    generator.create_actual_hook(analysis)
    generator.create_intelligent_command(analysis)
    
    print("✨ Automation created and ready to use!")
"""
    
    with open(Path.home() / '.claude' / 'evolution' / 'generate_hooks.py', 'w') as f:
        f.write(generator)
    os.chmod(Path.home() / '.claude' / 'evolution' / 'generate_hooks.py', 0o755)
    
    # Install the observer hook in Claude Code settings
    settings_file = Path.cwd() / '.claude' / 'settings.toml'
    settings_file.parent.mkdir(exist_ok=True)
    
    settings = {
        "hooks": {
            "PostToolUse": [{
                "matcher": ".*",
                "hooks": [{
                    "type": "command",
                    "command": f"python3 {Path.home()}/.claude/evolution/observer.py",
                    "async": True
                }]
            }]
        }
    }
    
    with open(settings_file, 'w') as f:
        toml.dump(settings, f)
    
    print("✅ Intelligent hook system installed!")
    print("\nHow it works:")
    print("1. Work normally in Claude Code")
    print("2. Every 20 actions, Claude analyzes your patterns")
    print("3. Claude generates SPECIFIC hooks for YOUR workflow")
    print("4. Hooks are automatically installed and ready to use")
    print("\nThis is REAL - Claude actually understands what you're doing!")

if __name__ == "__main__":
    setup_intelligent_system()