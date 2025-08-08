#!/usr/bin/env python3
"""
/scan-analyze command - Combined scanner + peak/trough analysis for optimal entry timing.

This command:
1. Scans for day trading opportunities
2. Runs peak/trough analysis on all qualified stocks
3. Filters for fresh TROUGH signals (buy zones)
4. Provides clear BUY/WAIT/AVOID recommendations
"""

import asyncio
import sys
from datetime import datetime
import pytz

# Add the project root to path
sys.path.insert(0, '/home/jjoravet/alpaca-mcp-server-enhanced')

from alpaca_mcp_server.tools.day_trading_scanner import scan_day_trading_opportunities
from alpaca_mcp_server.tools.peak_trough_analysis_tool import analyze_peaks_and_troughs


async def scan_and_analyze(
    min_trades_per_minute: int = 500,  # Lower threshold for broader coverage
    min_percent_change: float = 10.0,
    max_symbols: int = 10,
    fresh_signal_bars: int = 10  # Consider signals within last 10 bars as "fresh"
):
    """
    Perform combined scan and technical analysis.
    
    Returns stocks with entry recommendations based on peak/trough signals.
    """
    eastern = pytz.timezone('America/New_York')
    current_time = datetime.now(eastern).strftime('%H:%M:%S EDT')
    
    print(f"\n{'='*80}")
    print(f"🎯 SCAN-ANALYZE COMMAND - {current_time}")
    print(f"{'='*80}\n")
    
    # Step 1: Scan for opportunities
    print("📡 STEP 1: Scanning for active stocks...")
    print(f"   Filters: {min_trades_per_minute}+ trades/min, {min_percent_change}%+ change\n")
    
    scan_result = await scan_day_trading_opportunities(
        symbols="ALL",
        min_trades_per_minute=min_trades_per_minute,
        min_percent_change=min_percent_change,
        max_symbols=max_symbols,
        sort_by="trades"
    )
    
    # Parse scan results to extract symbols
    if "No opportunities found" in scan_result:
        print("❌ No stocks meeting criteria. Try lowering thresholds.")
        return
    
    # Extract symbols from the scan result
    lines = scan_result.split('\n')
    symbols = []
    trades_data = {}
    
    for line in lines:
        if line.strip() and not line.startswith('*') and not line.startswith('=') and not line.startswith('Rank'):
            parts = line.split()
            if len(parts) >= 4 and parts[0].isdigit():
                symbol = parts[1]
                trades_min = parts[2].replace('+', '').strip()
                change_pct = parts[3].replace('%', '').replace('+', '').strip()
                price = parts[4].replace('$', '').strip()
                
                symbols.append(symbol)
                trades_data[symbol] = {
                    'trades_per_min': trades_min,
                    'change_pct': float(change_pct),
                    'price': float(price)
                }
    
    if not symbols:
        print("❌ Could not parse scan results")
        return
    
    print(f"✅ Found {len(symbols)} active stocks: {', '.join(symbols)}\n")
    
    # Step 2: Run peak/trough analysis
    print("📊 STEP 2: Analyzing peak/trough signals...")
    print(f"   Looking for fresh signals (within {fresh_signal_bars} bars)\n")
    
    symbols_str = ','.join(symbols[:5])  # Analyze top 5 for speed
    
    try:
        analysis_result = await analyze_peaks_and_troughs(
            symbols=symbols_str,
            timeframe="1Min",
            days=1,
            limit=100
        )
        
        # Parse peak/trough results
        recommendations = []
        
        if "LATEST PEAK/TROUGH SIGNALS" in analysis_result:
            lines = analysis_result.split('\n')
            
            for line in lines:
                if line.strip() and ('vT' in line or '^P' in line):
                    parts = line.split()
                    if len(parts) >= 7:
                        symbol = parts[0]
                        signal_type = parts[1]  # vT or ^P
                        bars_ago = int(parts[2])
                        signal_price = float(parts[3])
                        current_price = float(parts[4])
                        
                        # Get scan data
                        scan_info = trades_data.get(symbol, {})
                        
                        # Determine recommendation
                        if signal_type == 'vT':  # Trough signal
                            if bars_ago <= fresh_signal_bars:
                                if bars_ago <= 3:
                                    status = "🔥 BUY NOW"
                                    priority = 1
                                elif bars_ago <= 6:
                                    status = "✅ BUY ZONE"
                                    priority = 2
                                else:
                                    status = "⚠️ AGING BUY"
                                    priority = 3
                            else:
                                status = "🕐 STALE TROUGH"
                                priority = 5
                        else:  # Peak signal
                            if bars_ago <= fresh_signal_bars:
                                status = "❌ AVOID (PEAK)"
                                priority = 4
                            else:
                                status = "⚪ OLD PEAK"
                                priority = 6
                        
                        recommendations.append({
                            'symbol': symbol,
                            'status': status,
                            'priority': priority,
                            'signal_type': 'TROUGH' if signal_type == 'vT' else 'PEAK',
                            'bars_ago': bars_ago,
                            'signal_price': signal_price,
                            'current_price': current_price,
                            'trades_per_min': scan_info.get('trades_per_min', 'N/A'),
                            'change_pct': scan_info.get('change_pct', 0)
                        })
        
        # Sort by priority (lower = better)
        recommendations.sort(key=lambda x: x['priority'])
        
        # Step 3: Display recommendations
        print("🎯 STEP 3: TRADING RECOMMENDATIONS")
        print("="*80)
        print(f"{'Symbol':<8} {'Status':<20} {'Signal':<8} {'Ago':<5} {'Entry':<10} {'Current':<10} {'Trades/Min':<12} {'Change%':<10}")
        print("-"*80)
        
        for rec in recommendations:
            print(f"{rec['symbol']:<8} {rec['status']:<20} {rec['signal_type']:<8} {rec['bars_ago']:<5} "
                  f"${rec['signal_price']:<9.4f} ${rec['current_price']:<9.4f} "
                  f"{rec['trades_per_min']:<12} {rec['change_pct']:>+9.2f}%")
        
        print("\n" + "="*80)
        print("📋 LEGEND:")
        print("  🔥 BUY NOW     = Fresh trough (1-3 bars), immediate entry opportunity")
        print("  ✅ BUY ZONE    = Recent trough (4-6 bars), good entry zone")
        print("  ⚠️ AGING BUY   = Older trough (7-10 bars), consider with caution")
        print("  ❌ AVOID       = At/near peak resistance, do not buy")
        print("  🕐 STALE       = Signal too old (>10 bars), wait for fresh signal")
        print("="*80)
        
        # Summary
        buy_now = [r for r in recommendations if '🔥' in r['status']]
        buy_zone = [r for r in recommendations if '✅' in r['status']]
        
        print(f"\n✨ SUMMARY:")
        print(f"  • Immediate buys: {len(buy_now)} stocks")
        print(f"  • Good buy zones: {len(buy_zone)} stocks")
        
        if buy_now:
            print(f"\n🚀 TOP PICK: {buy_now[0]['symbol']} - {buy_now[0]['status']}")
            print(f"   Entry: ${buy_now[0]['signal_price']:.4f}, Current: ${buy_now[0]['current_price']:.4f}")
            print(f"   Liquidity: {buy_now[0]['trades_per_min']} trades/min")
        
    except Exception as e:
        print(f"❌ Error in analysis: {str(e)}")
        return


async def main():
    """Main entry point for the command."""
    # Parse command line arguments if needed
    import argparse
    
    parser = argparse.ArgumentParser(description='Scan and analyze stocks for optimal entry')
    parser.add_argument('-t', '--trades', type=int, default=500, 
                        help='Minimum trades per minute threshold')
    parser.add_argument('-p', '--percent', type=float, default=10.0,
                        help='Minimum percent change threshold')
    parser.add_argument('-m', '--max', type=int, default=10,
                        help='Maximum symbols to analyze')
    parser.add_argument('-f', '--fresh', type=int, default=10,
                        help='Fresh signal threshold in bars')
    
    args = parser.parse_args()
    
    await scan_and_analyze(
        min_trades_per_minute=args.trades,
        min_percent_change=args.percent,
        max_symbols=args.max,
        fresh_signal_bars=args.fresh
    )


if __name__ == "__main__":
    asyncio.run(main())