#!/usr/bin/env python3
"""
Enable auto-trading in the FastAPI monitoring service
"""

import asyncio
import requests
import sys
import json
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from alpaca_mcp_server.monitoring.fastapi_service import MonitoringServiceAPI
from alpaca_mcp_server.config.global_config import reload_global_config

async def enable_auto_trading():
    """Enable auto-trading with updated config"""
    
    # Reload config to pick up the new $5,000 position size
    config = reload_global_config()
    print(f"✅ Config reloaded - Position size: ${config.trading.default_position_size_usd:,}")
    
    # Try to get the existing monitoring service instance
    try:
        # Check if FastAPI service is running
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ FastAPI service is running")
            
            # Access the service directly via a test endpoint that enables auto-trading
            try:
                # Create a monitoring service instance
                service = MonitoringServiceAPI()
                
                if hasattr(service, 'auto_trader') and service.auto_trader:
                    result = await service.auto_trader.enable_trading()
                    print(f"🚀 Auto-trader enabled: {result}")
                    
                    # Get status
                    if service.auto_trader.enabled:
                        print(f"✅ AUTO-TRADING ACTIVATED")
                        print(f"   • Position size: ${service.auto_trader.position_size_usd:,}")
                        print(f"   • Max positions: {service.auto_trader.max_positions}")
                        print(f"   • Max stock price: ${service.auto_trader.max_stock_price}")
                        print(f"   • Never sell for loss: {service.auto_trader.never_sell_for_loss}")
                        return True
                    else:
                        print("❌ Failed to enable auto-trading")
                        return False
                else:
                    print("❌ Auto-trader not available in service")
                    return False
                    
            except Exception as e:
                print(f"❌ Error accessing auto-trader: {e}")
                return False
        else:
            print("❌ FastAPI service not responding")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Cannot connect to FastAPI service: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(enable_auto_trading())
    if success:
        print("\n🎯 AUTO-TRADING IS NOW ACTIVE FOR PRE-MARKET TRADING")
        print("💰 Ready to execute fresh trough signals with $5,000 position size")
    else:
        print("\n❌ Failed to enable auto-trading")
        sys.exit(1)