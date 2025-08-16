#!/usr/bin/env python3
"""
Post-fetch hook - process raw data after fetching
"""
import json
import sys
from datetime import datetime

def main():
    # Read JSON from stdin
    data = json.loads(sys.stdin.read())
    
    results_count = data.get("results", 0)
    
    print(f"📊 Post-fetch: Processing {results_count} results")
    
    # Log metrics
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "results_processed": results_count,
        "status": "success"
    }
    
    # Could write to metrics file
    with open("/tmp/analyze_metrics.json", "w") as f:
        json.dump(metrics, f)
    
    print("✅ Post-fetch complete")
    
    # Return processed data
    return 0

if __name__ == "__main__":
    sys.exit(main())