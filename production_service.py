#!/usr/bin/env python3
"""
Production Service - Continuous Operation with Monitoring
"""

import json
import time
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess

class ProductionService:
    """Continuous monitoring service with auto-recovery"""
    
    def __init__(self):
        self.running = False
        self.start_time = datetime.now()
        self.execution_count = 0
        self.error_count = 0
        self.last_check = None
        self.pid_file = Path.home() / '.claude' / 'evolution' / 'service.pid'
        self.log_file = Path.home() / '.claude' / 'evolution' / 'production.log'
        self.error_log = Path.home() / '.claude' / 'evolution' / 'error.log'
        
    def start(self):
        """Start the production service"""
        # Check if already running
        if self.pid_file.exists():
            with open(self.pid_file, 'r') as f:
                old_pid = int(f.read())
            
            # Check if process is alive
            try:
                import os
                os.kill(old_pid, 0)
                print(f"Service already running with PID {old_pid}")
                return
            except ProcessLookupError:
                print(f"Removing stale PID file")
                self.pid_file.unlink()
        
        # Write PID
        import os
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
        
        self.running = True
        self.log("Service started")
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Start metrics server
        metrics_thread = threading.Thread(target=self.start_metrics_server)
        metrics_thread.daemon = True
        metrics_thread.start()
        
        # Main loop
        while self.running:
            try:
                self.check_patterns()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                self.log_error(f"Main loop error: {e}")
                self.error_count += 1
                
                # Auto-recovery
                if self.error_count > 5:
                    self.log("Too many errors, restarting...")
                    self.restart()
    
    def monitor_loop(self):
        """Background monitoring loop"""
        while self.running:
            try:
                # Check for new actions
                actions_file = Path.home() / '.claude' / 'evolution' / 'trading_actions.jsonl'
                if actions_file.exists():
                    with open(actions_file, 'r') as f:
                        action_count = sum(1 for _ in f)
                    
                    # Trigger pattern detection every 10 new actions
                    if action_count % 10 == 0 and action_count > 0:
                        self.log(f"Triggering pattern detection at {action_count} actions")
                        subprocess.run(['python3', 'production_hook_system.py', 'detect'])
                
                time.sleep(5)
            except Exception as e:
                self.log_error(f"Monitor error: {e}")
    
    def check_patterns(self):
        """Check and execute high-confidence patterns"""
        patterns_file = Path.home() / '.claude' / 'evolution' / 'patterns.json'
        
        if not patterns_file.exists():
            return
        
        with open(patterns_file, 'r') as f:
            patterns = json.load(f)
        
        for pattern in patterns:
            if pattern['confidence'] >= 0.9:  # High confidence only
                # Check if we should execute
                self.last_check = datetime.now()
                self.execution_count += 1
                
                # Log the check
                self.log(f"Checked pattern: {' → '.join(pattern['sequence'])} ({pattern['confidence']*100:.0f}%)")
    
    def start_metrics_server(self):
        """Start HTTP metrics server"""
        class MetricsHandler(BaseHTTPRequestHandler):
            def do_GET(handler_self):
                if handler_self.path == '/metrics':
                    metrics = {
                        "status": "running" if self.running else "stopped",
                        "uptime": str(datetime.now() - self.start_time),
                        "execution_count": self.execution_count,
                        "error_count": self.error_count,
                        "last_check": self.last_check.isoformat() if self.last_check else None
                    }
                    
                    handler_self.send_response(200)
                    handler_self.send_header('Content-Type', 'application/json')
                    handler_self.end_headers()
                    handler_self.wfile.write(json.dumps(metrics).encode())
                else:
                    handler_self.send_response(404)
                    handler_self.end_headers()
            
            def log_message(self, format, *args):
                pass  # Suppress logs
        
        try:
            server = HTTPServer(('localhost', 8765), MetricsHandler)
            self.log("Metrics server started on http://localhost:8765/metrics")
            server.serve_forever()
        except Exception as e:
            self.log_error(f"Metrics server error: {e}")
    
    def log(self, message):
        """Log message"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}\n"
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
        
        print(log_entry.strip())
    
    def log_error(self, message):
        """Log error"""
        timestamp = datetime.now().isoformat()
        error_entry = f"[{timestamp}] ERROR: {message}\n"
        
        with open(self.error_log, 'a') as f:
            f.write(error_entry)
        
        print(error_entry.strip(), file=sys.stderr)
    
    def shutdown(self, signum, frame):
        """Graceful shutdown"""
        self.log("Shutting down...")
        self.running = False
        
        if self.pid_file.exists():
            self.pid_file.unlink()
        
        sys.exit(0)
    
    def restart(self):
        """Restart the service"""
        self.log("Restarting service...")
        self.running = False
        time.sleep(2)
        
        # Start new instance
        import os
        os.execv(sys.executable, [sys.executable] + sys.argv)


class ServiceManager:
    """Manage the production service"""
    
    @staticmethod
    def start():
        """Start service in background"""
        subprocess.Popen(
            ['python3', 'production_service.py', 'run'],
            stdout=open('/tmp/production_service.log', 'a'),
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        print("✓ Service started in background")
    
    @staticmethod
    def stop():
        """Stop the service"""
        pid_file = Path.home() / '.claude' / 'evolution' / 'service.pid'
        
        if not pid_file.exists():
            print("Service not running")
            return
        
        with open(pid_file, 'r') as f:
            pid = int(f.read())
        
        try:
            import os
            os.kill(pid, signal.SIGTERM)
            print(f"✓ Stopped service (PID {pid})")
        except ProcessLookupError:
            print("Service already stopped")
            pid_file.unlink()
    
    @staticmethod
    def status():
        """Check service status"""
        pid_file = Path.home() / '.claude' / 'evolution' / 'service.pid'
        
        if not pid_file.exists():
            print("Service not running")
            return False
        
        with open(pid_file, 'r') as f:
            pid = int(f.read())
        
        try:
            import os
            os.kill(pid, 0)
            print(f"✓ Service running (PID {pid})")
            
            # Get metrics
            try:
                import urllib.request
                with urllib.request.urlopen('http://localhost:8765/metrics') as response:
                    metrics = json.loads(response.read())
                    print(f"  Uptime: {metrics['uptime']}")
                    print(f"  Executions: {metrics['execution_count']}")
                    print(f"  Errors: {metrics['error_count']}")
            except:
                pass
            
            return True
        except ProcessLookupError:
            print("Service not running (stale PID)")
            pid_file.unlink()
            return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: production_service.py [start|stop|status|run]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "start":
        ServiceManager.start()
    elif command == "stop":
        ServiceManager.stop()
    elif command == "status":
        ServiceManager.status()
    elif command == "run":
        # Direct run (for background process)
        service = ProductionService()
        service.start()
    else:
        print(f"Unknown command: {command}")