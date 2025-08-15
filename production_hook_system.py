#!/usr/bin/env python3
"""
Production-Ready Trading Pattern Hook System
Designed for immediate deployment - TODAY
"""

import json
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any

class ProductionHookSystem:
    """Complete production-ready hook system with metrics and integration"""
    
    def __init__(self):
        self.base_dir = Path.home() / '.claude' / 'evolution'
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Use JSON consistently
        self.actions_file = self.base_dir / 'trading_actions.jsonl'
        self.patterns_file = self.base_dir / 'patterns.json'
        self.hooks_file = Path.cwd() / '.claude' / 'hooks.json'
        self.metrics_file = self.base_dir / 'metrics.jsonl'
        self.config_file = self.base_dir / 'config.json'
        
        # Load or create config
        self.config = self.load_config()
        
    def load_config(self) -> Dict:
        """Load or create configuration"""
        default_config = {
            "min_pattern_occurrences": 3,
            "min_confidence_for_hook": 0.6,
            "max_hook_name_length": 50,
            "pattern_window_size": 3,
            "auto_execute_threshold": 0.8,
            "metrics_enabled": True
        }
        
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            with open(self.config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def track_action(self, tool_name: str, tool_input: Dict, session_id: str = None) -> None:
        """Track a trading action with proper structure"""
        # Determine action type intelligently
        action_type = self.classify_action(tool_name, tool_input)
        
        action = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "input": tool_input,
            "session_id": session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "trading_related": self.is_trading_related(tool_name, tool_input),
            "action_type": action_type
        }
        
        # Append to actions file
        with open(self.actions_file, 'a') as f:
            f.write(json.dumps(action) + '\n')
        
        # Check if we should analyze patterns
        with open(self.actions_file, 'r') as f:
            line_count = sum(1 for _ in f)
        
        if line_count % 10 == 0:
            self.detect_patterns()
    
    def classify_action(self, tool_name: str, tool_input: Dict) -> str:
        """Classify action type based on tool and input"""
        tool_lower = tool_name.lower()
        
        if 'quote' in tool_lower or 'peak' in tool_lower or 'trough' in tool_lower:
            return 'analysis'
        elif 'option' in tool_lower or 'contract' in tool_lower:
            return 'options_trade'
        elif 'bull_call' in tool_lower or 'spread' in tool_lower:
            return 'bull_call_spread'
        elif 'position' in tool_lower or 'monitor' in tool_lower:
            return 'monitor'
        elif 'order' in tool_lower or 'place' in tool_lower:
            return 'order'
        else:
            return 'other'
    
    def is_trading_related(self, tool_name: str, tool_input: Dict) -> bool:
        """Check if action is trading related"""
        keywords = ['spread', 'call', 'put', 'strike', 'option', 'order', 
                   'position', 'peak', 'trough', 'quote', 'alpaca']
        
        tool_str = f"{tool_name} {json.dumps(tool_input)}".lower()
        return any(keyword in tool_str for keyword in keywords)
    
    def detect_patterns(self) -> List[Dict]:
        """Detect patterns with proper sliding window"""
        if not self.actions_file.exists():
            return []
        
        # Load all actions
        actions = []
        with open(self.actions_file, 'r') as f:
            for line in f:
                try:
                    actions.append(json.loads(line))
                except:
                    continue
        
        if len(actions) < self.config['pattern_window_size']:
            return []
        
        # Extract sequences using sliding window
        sequences = []
        window_size = self.config['pattern_window_size']
        
        for i in range(len(actions) - window_size + 1):
            window = actions[i:i + window_size]
            if all(a.get('trading_related') for a in window):
                seq = tuple(a['action_type'] for a in window)
                sequences.append(seq)
        
        # Count patterns
        seq_counts = Counter(sequences)
        
        # Build patterns with metadata
        patterns = []
        for seq, count in seq_counts.items():
            if count >= self.config['min_pattern_occurrences']:
                confidence = min(0.95, count / 10.0)
                
                pattern = {
                    "sequence": list(seq),
                    "count": count,
                    "confidence": confidence,
                    "type": self.classify_pattern_type(seq),
                    "hash": hashlib.md5(str(seq).encode()).hexdigest()[:8],
                    "first_seen": datetime.now().isoformat(),
                    "last_seen": datetime.now().isoformat()
                }
                patterns.append(pattern)
        
        # Save patterns
        with open(self.patterns_file, 'w') as f:
            json.dump(patterns, f, indent=2)
        
        # Generate hooks for high-confidence patterns
        if patterns:
            self.generate_hooks(patterns)
        
        return patterns
    
    def classify_pattern_type(self, sequence: Tuple[str, ...]) -> str:
        """Classify the type of pattern"""
        seq_str = ' '.join(sequence)
        
        if 'bull_call_spread' in seq_str:
            return 'bull_spread_workflow'
        elif 'options_trade' in seq_str:
            return 'options_workflow'
        elif 'analysis' in seq_str and 'monitor' in seq_str:
            return 'analysis_monitoring'
        else:
            return 'trading_workflow'
    
    def generate_hooks(self, patterns: List[Dict]) -> None:
        """Generate production-ready hooks"""
        hooks = {
            "version": "1.0",
            "generated": datetime.now().isoformat(),
            "hooks": []
        }
        
        for pattern in patterns:
            if pattern['confidence'] >= self.config['min_confidence_for_hook']:
                hook = self.create_hook(pattern)
                hooks['hooks'].append(hook)
                
                # Track metrics
                self.track_metric('hook_generated', {
                    'pattern': pattern['sequence'],
                    'confidence': pattern['confidence']
                })
        
        # Save hooks
        self.hooks_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.hooks_file, 'w') as f:
            json.dump(hooks, f, indent=2)
        
        # Also generate TOML for Claude Code compatibility
        self.generate_toml_hooks(hooks)
    
    def create_hook(self, pattern: Dict) -> Dict:
        """Create a single hook from pattern"""
        # Generate proper hook name (no truncation bug)
        sequence_str = '_'.join(pattern['sequence'][:3])
        hook_name = f"auto_{sequence_str}_{pattern['hash']}"
        
        # Determine execution command
        if pattern['confidence'] >= self.config['auto_execute_threshold']:
            command = self.get_execution_command(pattern)
        else:
            command = f"echo 'Pattern detected: {' → '.join(pattern['sequence'])}'"
        
        hook = {
            "name": hook_name,
            "pattern": pattern['sequence'],
            "matcher": '|'.join(pattern['sequence']),
            "confidence": pattern['confidence'],
            "type": "PostToolUse",
            "command": command,
            "enabled": True,
            "metadata": {
                "count": pattern['count'],
                "pattern_type": pattern['type'],
                "created": datetime.now().isoformat()
            }
        }
        
        return hook
    
    def get_execution_command(self, pattern: Dict) -> str:
        """Get the execution command for a pattern"""
        seq = pattern['sequence']
        
        if seq == ['analysis', 'options_trade', 'bull_call_spread']:
            return "python3 bull_call_spread_cli.py --dry_run -s SPY --buy 3 --sell 5"
        elif seq == ['analysis', 'bull_call_spread', 'monitor']:
            return "python3 ~/.claude/evolution/monitor_positions.py"
        elif 'bull_call_spread' in seq:
            return "python3 bull_call_spread_cli.py --dry_run"
        else:
            return f"python3 ~/.claude/evolution/execute_pattern.py '{json.dumps(pattern)}'"
    
    def generate_toml_hooks(self, hooks: Dict) -> None:
        """Generate TOML format for Claude Code"""
        toml_file = Path.cwd() / '.claude' / 'settings.toml'
        
        with open(toml_file, 'w') as f:
            f.write("# Auto-generated Trading Hooks\n")
            f.write(f"# Generated: {hooks['generated']}\n\n")
            f.write("[hooks]\n\n")
            
            for hook in hooks['hooks']:
                f.write(f"# Pattern: {' → '.join(hook['pattern'])}\n")
                f.write(f"# Confidence: {hook['confidence']*100:.0f}%\n")
                f.write(f"[[hooks.{hook['type']}]]\n")
                f.write(f'name = "{hook["name"]}"\n')
                f.write(f'matcher = "{hook["matcher"]}"\n')
                f.write('hooks = [\n')
                f.write(f'    {{ type = "command", command = "{hook["command"]}" }}\n')
                f.write(']\n\n')
    
    def track_metric(self, metric_type: str, data: Dict) -> None:
        """Track metrics for monitoring"""
        if not self.config.get('metrics_enabled'):
            return
        
        metric = {
            "timestamp": datetime.now().isoformat(),
            "type": metric_type,
            "data": data
        }
        
        with open(self.metrics_file, 'a') as f:
            f.write(json.dumps(metric) + '\n')
    
    def execute_hook(self, hook_name: str) -> Dict:
        """Execute a specific hook and track results"""
        start_time = datetime.now()
        
        # Load hooks
        if not self.hooks_file.exists():
            return {"success": False, "error": "No hooks file"}
        
        with open(self.hooks_file, 'r') as f:
            hooks_data = json.load(f)
        
        # Find hook
        hook = None
        for h in hooks_data['hooks']:
            if h['name'] == hook_name:
                hook = h
                break
        
        if not hook:
            return {"success": False, "error": f"Hook {hook_name} not found"}
        
        # Execute command
        try:
            result = subprocess.run(
                hook['command'],
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
        except subprocess.TimeoutExpired:
            success = False
            output = "Command timed out"
        except Exception as e:
            success = False
            output = str(e)
        
        # Track metrics
        duration = (datetime.now() - start_time).total_seconds()
        self.track_metric('hook_execution', {
            'hook': hook_name,
            'success': success,
            'duration': duration
        })
        
        return {
            "success": success,
            "output": output,
            "duration": duration,
            "hook": hook
        }
    
    def get_status(self) -> Dict:
        """Get complete system status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "actions_tracked": 0,
            "patterns_detected": 0,
            "hooks_generated": 0,
            "metrics_count": 0,
            "ready": False
        }
        
        # Count actions
        if self.actions_file.exists():
            with open(self.actions_file, 'r') as f:
                status['actions_tracked'] = sum(1 for _ in f)
        
        # Count patterns
        if self.patterns_file.exists():
            with open(self.patterns_file, 'r') as f:
                patterns = json.load(f)
                status['patterns_detected'] = len(patterns)
        
        # Count hooks
        if self.hooks_file.exists():
            with open(self.hooks_file, 'r') as f:
                hooks = json.load(f)
                status['hooks_generated'] = len(hooks.get('hooks', []))
        
        # Count metrics
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                status['metrics_count'] = sum(1 for _ in f)
        
        status['ready'] = (
            status['actions_tracked'] > 0 and
            status['patterns_detected'] > 0 and
            status['hooks_generated'] > 0
        )
        
        return status


# CLI Interface
if __name__ == "__main__":
    import sys
    
    system = ProductionHookSystem()
    
    if len(sys.argv) < 2:
        print("Production Hook System Status:")
        print(json.dumps(system.get_status(), indent=2))
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "track":
        # Track an action
        if len(sys.argv) < 4:
            print("Usage: track <tool_name> <tool_input_json>")
            sys.exit(1)
        
        tool_name = sys.argv[2]
        tool_input = json.loads(sys.argv[3])
        system.track_action(tool_name, tool_input)
        print(f"✓ Action tracked: {tool_name}")
    
    elif command == "detect":
        # Detect patterns
        patterns = system.detect_patterns()
        print(f"✓ Detected {len(patterns)} patterns")
        for p in patterns:
            print(f"  - {' → '.join(p['sequence'])}: {p['confidence']*100:.0f}% confidence")
    
    elif command == "execute":
        # Execute a hook
        if len(sys.argv) < 3:
            print("Usage: execute <hook_name>")
            sys.exit(1)
        
        hook_name = sys.argv[2]
        result = system.execute_hook(hook_name)
        print(f"Hook execution: {'✓' if result['success'] else '✗'}")
        print(f"Duration: {result.get('duration', 0):.2f}s")
        print(f"Output: {result.get('output', '')[:200]}")
    
    elif command == "status":
        # Get status
        status = system.get_status()
        print("System Status:")
        print(json.dumps(status, indent=2))
    
    else:
        print(f"Unknown command: {command}")
        print("Commands: track, detect, execute, status")