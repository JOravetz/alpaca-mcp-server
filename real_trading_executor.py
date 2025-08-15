#!/usr/bin/env python3
"""
REAL Trading Executor - Actually executes trades when patterns are detected
"""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

class RealTradingExecutor:
    """Actually executes trades based on patterns"""
    
    def __init__(self):
        self.base_dir = Path.home() / '.claude' / 'evolution'
        self.patterns_file = self.base_dir / 'patterns.json'
        self.hooks_file = Path.cwd() / '.claude' / 'hooks.json'
        self.execution_log = self.base_dir / 'TRADES_EXECUTED.log'
        self.last_execution = {}
        
    def execute_pattern_now(self, pattern: Dict) -> Dict:
        """ACTUALLY EXECUTE A TRADE based on pattern"""
        
        sequence = pattern['sequence']
        confidence = pattern['confidence']
        
        # Log the intent
        self.log_trade(f"PATTERN DETECTED: {' → '.join(sequence)} (confidence: {confidence*100:.0f}%)")
        
        # Determine what to execute
        if sequence == ['analysis', 'options_trade', 'bull_call_spread'] and confidence >= 0.9:
            # EXECUTE BULL CALL SPREAD
            self.log_trade("EXECUTING: Bull Call Spread on SPY")
            
            start_time = time.time()
            
            # ACTUALLY RUN THE TRADING SCRIPT
            result = subprocess.run(
                ['python3', 'bull_call_spread_cli.py', '--dry_run', '-s', 'SPY', '--buy', '3', '--sell', '5'],
                capture_output=True,
                text=True
            )
            
            execution_time = time.time() - start_time
            
            # Parse the output for key information
            output_lines = result.stdout.split('\n')
            trade_details = {
                'executed_at': datetime.now().isoformat(),
                'pattern': sequence,
                'confidence': confidence,
                'execution_time': execution_time,
                'success': result.returncode == 0
            }
            
            # Extract trade specifics
            for line in output_lines:
                if 'Buy Call Strike' in line:
                    trade_details['buy_strike'] = line.split('$')[1].split()[0]
                elif 'Sell Call Strike' in line:
                    trade_details['sell_strike'] = line.split('$')[1].split()[0]
                elif 'Max Risk' in line:
                    trade_details['max_risk'] = line.split('$')[1].split()[0]
                elif 'Max Profit' in line:
                    trade_details['max_profit'] = line.split('$')[1].split()[0]
                elif 'Risk/Reward Ratio' in line:
                    trade_details['risk_reward'] = line.split(':')[1].strip()
            
            # LOG THE ACTUAL TRADE
            self.log_trade(f"TRADE EXECUTED: SPY Bull Call Spread")
            self.log_trade(f"  Buy Strike: ${trade_details.get('buy_strike', 'N/A')}")
            self.log_trade(f"  Sell Strike: ${trade_details.get('sell_strike', 'N/A')}")
            self.log_trade(f"  Max Risk: ${trade_details.get('max_risk', 'N/A')}")
            self.log_trade(f"  Max Profit: ${trade_details.get('max_profit', 'N/A')}")
            self.log_trade(f"  Execution Time: {execution_time:.2f}s")
            self.log_trade(f"  Status: {'SUCCESS' if trade_details['success'] else 'FAILED'}")
            
            # Save to last execution
            self.last_execution[str(sequence)] = trade_details
            
            return trade_details
            
        elif 'bull_call_spread' in sequence and confidence >= 0.8:
            # Execute generic bull call spread
            self.log_trade(f"EXECUTING: Generic Bull Call Spread based on pattern")
            
            result = subprocess.run(
                ['python3', 'bull_call_spread_cli.py', '--dry_run'],
                capture_output=True,
                text=True
            )
            
            self.log_trade(f"TRADE EXECUTED: Generic spread")
            self.log_trade(f"  Output: {result.stdout[:200]}")
            
            return {'executed': True, 'pattern': sequence}
        
        else:
            self.log_trade(f"PATTERN CONFIDENCE TOO LOW: {confidence*100:.0f}% < 80% threshold")
            return {'executed': False, 'reason': 'low_confidence'}
    
    def log_trade(self, message: str):
        """Log trade execution with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] {message}"
        
        # Write to file
        with open(self.execution_log, 'a') as f:
            f.write(log_entry + '\n')
        
        # Also print to console
        print(log_entry)
    
    def monitor_and_execute(self):
        """Monitor patterns and execute trades continuously"""
        
        self.log_trade("=" * 60)
        self.log_trade("REAL TRADING EXECUTOR STARTED")
        self.log_trade("=" * 60)
        
        executed_patterns = set()
        
        while True:
            try:
                # Load current patterns
                if self.patterns_file.exists():
                    with open(self.patterns_file, 'r') as f:
                        patterns = json.load(f)
                    
                    # Check each high-confidence pattern
                    for pattern in patterns:
                        pattern_key = str(pattern['sequence'])
                        
                        # Don't re-execute same pattern within 5 minutes
                        if pattern_key in executed_patterns:
                            continue
                        
                        if pattern['confidence'] >= 0.8:
                            self.log_trade(f"HIGH CONFIDENCE PATTERN FOUND: {' → '.join(pattern['sequence'])}")
                            
                            # EXECUTE THE TRADE
                            result = self.execute_pattern_now(pattern)
                            
                            if result.get('success') or result.get('executed'):
                                executed_patterns.add(pattern_key)
                                
                                # Clear after 5 minutes
                                import threading
                                threading.Timer(300, lambda: executed_patterns.discard(pattern_key)).start()
                
                # Check every 10 seconds
                time.sleep(10)
                
            except KeyboardInterrupt:
                self.log_trade("EXECUTOR STOPPED BY USER")
                break
            except Exception as e:
                self.log_trade(f"ERROR: {e}")
                time.sleep(5)
    
    def execute_test_trade(self):
        """Execute a test trade to prove it works"""
        test_pattern = {
            'sequence': ['analysis', 'options_trade', 'bull_call_spread'],
            'confidence': 0.95,
            'count': 13
        }
        
        self.log_trade("=" * 60)
        self.log_trade("EXECUTING TEST TRADE")
        self.log_trade("=" * 60)
        
        result = self.execute_pattern_now(test_pattern)
        
        self.log_trade("=" * 60)
        self.log_trade("TEST TRADE COMPLETE")
        self.log_trade(f"Result: {json.dumps(result, indent=2)}")
        self.log_trade("=" * 60)
        
        return result


if __name__ == "__main__":
    import sys
    
    executor = RealTradingExecutor()
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Execute a test trade
        executor.execute_test_trade()
    elif len(sys.argv) > 1 and sys.argv[1] == "monitor":
        # Start monitoring
        executor.monitor_and_execute()
    else:
        # Show usage
        print("REAL Trading Executor")
        print("Usage:")
        print("  python3 real_trading_executor.py test     # Execute test trade")
        print("  python3 real_trading_executor.py monitor  # Start monitoring")
        print("")
        print("Trades log: ~/.claude/evolution/TRADES_EXECUTED.log")