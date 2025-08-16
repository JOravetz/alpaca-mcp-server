#!/usr/bin/env python3
"""
Signal detection hook - triggered when trading signals are detected
Can send alerts, place orders, or log signals
"""
import json
import sys
from datetime import datetime

def main():
    # Read signals from stdin
    signals = json.loads(sys.stdin.read())
    
    strong_buy_count = len(signals.get("strong_buy", []))
    buy_count = len(signals.get("buy", []))
    sell_count = len(signals.get("sell", []))
    
    print(f"🎯 Signals detected: {strong_buy_count} strong buys, {buy_count} buys, {sell_count} sells")
    
    # Process strong buy signals
    if strong_buy_count > 0:
        print("🔥 STRONG BUY SIGNALS:")
        for symbol in signals["strong_buy"][:5]:  # Top 5
            print(f"   • {symbol}")
    
    # Could send alerts here
    if strong_buy_count > 0:
        # Send to monitoring service
        try:
            import requests
            requests.post("http://localhost:8000/alerts", json={
                "type": "strong_buy",
                "symbols": signals["strong_buy"],
                "timestamp": datetime.now().isoformat()
            }, timeout=1)
        except:
            pass
    
    # Log signals
    with open("/tmp/signals.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "signals": signals
        }, f)
    
    print("✅ Signal processing complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())