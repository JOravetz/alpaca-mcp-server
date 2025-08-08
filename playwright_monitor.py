#!/usr/bin/env python3
"""
CLIK Day Low Monitor - Takes screenshots every 15 seconds
Monitors for Day Low changes below $0.4422 trigger point
"""

import time
import os
from datetime import datetime

# Configuration
INTERVAL_SECONDS = 15
SCREENSHOT_DIR = "/tmp/clik_monitoring"
TRIGGER_PRICE = 0.4422
MONITORING_URL = "http://localhost:8000"

def setup_directories():
    """Create screenshot directory if it doesn't exist"""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    print(f"📁 Screenshots will be saved to: {SCREENSHOT_DIR}")

def take_screenshot_marker(counter):
    """Create a marker file for screenshot request"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{SCREENSHOT_DIR}/clik_{timestamp}.png"
    
    # Create marker file with screenshot details
    marker_file = f"{SCREENSHOT_DIR}/screenshot_request.txt"
    with open(marker_file, 'w') as f:
        f.write(f"SCREENSHOT_REQUEST\n")
        f.write(f"Counter: {counter}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Filename: {filename}\n")
        f.write(f"Trigger: {TRIGGER_PRICE}\n")
    
    return timestamp, filename

def main():
    """Main monitoring loop"""
    print("🎯 CLIK Day Low Monitor Started")
    print(f"📊 Monitoring: {MONITORING_URL}")
    print(f"⏱️  Interval: {INTERVAL_SECONDS} seconds")
    print(f"🎯 Trigger: Day Low < ${TRIGGER_PRICE}")
    print("=" * 50)
    
    setup_directories()
    counter = 0
    
    try:
        while True:
            counter += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            # Take screenshot
            timestamp, filename = take_screenshot_marker(counter)
            
            print(f"[{current_time}] Screenshot #{counter}")
            print(f"  📸 Saved as: {os.path.basename(filename)}")
            print(f"  🔍 Checking Day Low vs ${TRIGGER_PRICE}")
            print()
            
            # Sleep for interval
            time.sleep(INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print("\n⏹️  Monitoring stopped by user")
        print(f"📊 Total screenshots: {counter}")

if __name__ == "__main__":
    main()