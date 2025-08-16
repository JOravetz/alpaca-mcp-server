#!/usr/bin/env python3
"""
Report generation hook - creates final analysis report
"""
import json
import sys
from datetime import datetime

def main():
    # Read analysis from stdin
    analysis = json.loads(sys.stdin.read())
    
    timestamp = analysis.get("timestamp", datetime.now().isoformat())
    symbols_count = analysis.get("symbols_count", 0)
    
    print(f"📄 Generating report for {symbols_count} symbols")
    
    # Create markdown report
    report = f"""# MOMENTUM ANALYSIS REPORT
Generated: {timestamp}
Symbols: {symbols_count}

## TRADING SIGNALS

### 🟢 BUY SIGNALS
"""
    
    # Add buy signals
    buy_signals = analysis.get("signals", {}).get("buy", [])
    for signal in buy_signals[:10]:
        report += f"- {signal}\n"
    
    report += "\n### 🔴 SELL SIGNALS\n"
    
    # Add sell signals
    sell_signals = analysis.get("signals", {}).get("sell", [])
    for signal in sell_signals[:10]:
        report += f"- {signal}\n"
    
    # Write report
    report_path = f"/tmp/analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"✅ Report saved: {report_path}")
    
    # Also create JSON summary
    summary = {
        "timestamp": timestamp,
        "symbols_analyzed": symbols_count,
        "buy_signals": len(buy_signals),
        "sell_signals": len(sell_signals),
        "report_path": report_path
    }
    
    with open("/tmp/analysis_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())