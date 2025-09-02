#!/usr/bin/env python3
"""
Test the animated dashboard with sample victory data
"""

import asyncio
from pathlib import Path
from update_pnl_dashboard import generate_dashboard_html
import webbrowser

async def main():
    """Generate test dashboards with different profit levels"""
    
    # Test data for EPIC win ($5,059.28 as shown in screenshot)
    epic_data = {
        'date': '2025-08-26',
        'total_pnl': 5059.28,
        'total_volume': 1110000,
        'total_trades': 37,
        'winning_trades': 19,
        'losing_trades': 0,
        'win_rate': 100,
        'symbols': [
            {'symbol': 'PFSA', 'pnl': 1794, 'trades': 8, 'volume': 280000},
            {'symbol': 'AAPL', 'pnl': 1650, 'trades': 7, 'volume': 320000},
            {'symbol': 'TSLA', 'pnl': 980, 'trades': 6, 'volume': 200000},
            {'symbol': 'NVDA', 'pnl': 450, 'trades': 5, 'volume': 150000},
            {'symbol': 'SPY', 'pnl': 185.28, 'trades': 11, 'volume': 160000}
        ]
    }
    
    # Generate EPIC dashboard
    print("🎉 Generating EPIC WIN dashboard ($5,059.28)...")
    epic_html = generate_dashboard_html(epic_data)
    Path('trading_dashboard_epic.html').write_text(epic_html)
    print("✅ Saved to trading_dashboard_epic.html")
    
    # Test data for LEGENDARY win ($12,500+)
    legendary_data = {
        'date': '2025-08-26',
        'total_pnl': 12500.50,
        'total_volume': 2500000,
        'total_trades': 45,
        'winning_trades': 30,
        'losing_trades': 0,
        'win_rate': 100,
        'symbols': [
            {'symbol': 'NVDA', 'pnl': 4500, 'trades': 10, 'volume': 800000},
            {'symbol': 'TSLA', 'pnl': 3200, 'trades': 8, 'volume': 600000},
            {'symbol': 'AAPL', 'pnl': 2800, 'trades': 9, 'volume': 500000},
            {'symbol': 'META', 'pnl': 1500, 'trades': 10, 'volume': 400000},
            {'symbol': 'AMZN', 'pnl': 500.50, 'trades': 8, 'volume': 200000}
        ]
    }
    
    # Generate LEGENDARY dashboard
    print("🏆 Generating LEGENDARY WIN dashboard ($12,500+)...")
    legendary_html = generate_dashboard_html(legendary_data)
    Path('trading_dashboard_legendary.html').write_text(legendary_html)
    print("✅ Saved to trading_dashboard_legendary.html")
    
    # Test data for GREAT win ($3,000)
    great_data = {
        'date': '2025-08-26',
        'total_pnl': 3000.00,
        'total_volume': 750000,
        'total_trades': 25,
        'winning_trades': 15,
        'losing_trades': 0,
        'win_rate': 100,
        'symbols': [
            {'symbol': 'SPY', 'pnl': 1200, 'trades': 8, 'volume': 300000},
            {'symbol': 'QQQ', 'pnl': 900, 'trades': 7, 'volume': 250000},
            {'symbol': 'IWM', 'pnl': 600, 'trades': 5, 'volume': 100000},
            {'symbol': 'DIA', 'pnl': 300, 'trades': 5, 'volume': 100000}
        ]
    }
    
    # Generate GREAT dashboard
    print("💪 Generating GREAT WIN dashboard ($3,000)...")
    great_html = generate_dashboard_html(great_data)
    Path('trading_dashboard_great.html').write_text(great_html)
    print("✅ Saved to trading_dashboard_great.html")
    
    print("\n🚀 All test dashboards generated!")
    print("Open these files in your browser to see the animations:")
    print("  - trading_dashboard_epic.html (Epic win - $5k+)")
    print("  - trading_dashboard_legendary.html (Legendary win - $10k+)")
    print("  - trading_dashboard_great.html (Great win - $2.5k+)")
    
    # Open the epic one (matching the screenshot)
    file_url = f"file://{Path('trading_dashboard_epic.html').absolute()}"
    webbrowser.open(file_url)
    print(f"\n✨ Opening EPIC dashboard in browser...")

if __name__ == "__main__":
    asyncio.run(main())