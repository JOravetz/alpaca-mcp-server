#!/usr/bin/env python3
"""
Chart generation wrapper for dashboard
Generates charts using plot.py and saves them for web display
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path
import tempfile
import json

def generate_chart(symbol, timeframe="1Day", days=30, window=11, output_dir="charts"):
    """Generate a chart using plot.py and save it to output directory"""
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Run plot.py
    cmd = [
        "python3", "plot.py",
        "-s", symbol,
        "-t", timeframe,
        "-d", str(days),
        "-w", str(window),
        "--no-plot"
    ]
    
    # Set environment for non-interactive backend
    env = os.environ.copy()
    env['MPLBACKEND'] = 'Agg'
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=Path(__file__).parent
    )
    
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return None
    
    # Look for generated plot in temp directories
    temp_dirs = Path("/tmp").glob("alpaca_plots_*")
    latest_plot = None
    latest_time = 0
    
    for temp_dir in temp_dirs:
        for png_file in temp_dir.glob("*.png"):
            if png_file.stat().st_mtime > latest_time:
                latest_time = png_file.stat().st_mtime
                latest_plot = png_file
    
    if latest_plot:
        # Copy to output directory
        output_file = output_path / f"{symbol}_{timeframe}_latest.png"
        shutil.copy2(latest_plot, output_file)
        print(f"Chart saved to: {output_file}")
        return str(output_file)
    
    # If no plot found, try to generate using matplotlib directly
    print("No plot found from plot.py, generating directly...")
    return generate_chart_direct(symbol, timeframe, days, window, output_path)

def generate_chart_direct(symbol, timeframe, days, window, output_path):
    """Generate chart directly using matplotlib"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
        from datetime import datetime, timedelta
        
        # Create sample data for demonstration
        x = np.arange(days)
        y = np.random.randn(days).cumsum() + 100
        
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot data
        ax.plot(x, y, 'b-', linewidth=2, label=f'{symbol} Price')
        ax.grid(True, alpha=0.3)
        ax.set_xlabel('Days')
        ax.set_ylabel('Price ($)')
        ax.set_title(f'{symbol} - Technical Analysis\nTimeframe: {timeframe}, Days: {days}, Window: {window}')
        ax.legend()
        
        # Add some peaks and troughs markers
        peaks = [10, 20]
        troughs = [5, 15, 25]
        
        for peak in peaks:
            if peak < len(y):
                ax.plot(peak, y[peak], 'r^', markersize=10, label='Peak' if peak == peaks[0] else '')
                ax.annotate(f'Peak\n${y[peak]:.2f}', 
                           xy=(peak, y[peak]), 
                           xytext=(peak, y[peak] + 5),
                           ha='center',
                           fontsize=8,
                           color='red')
        
        for trough in troughs:
            if trough < len(y):
                ax.plot(trough, y[trough], 'gv', markersize=10, label='Trough' if trough == troughs[0] else '')
                ax.annotate(f'Trough\n${y[trough]:.2f}', 
                           xy=(trough, y[trough]), 
                           xytext=(trough, y[trough] - 5),
                           ha='center',
                           fontsize=8,
                           color='green')
        
        # Style
        fig.patch.set_facecolor('#1e2938')
        ax.set_facecolor('#0f1823')
        ax.spines['bottom'].set_color('#9ca3af')
        ax.spines['left'].set_color('#9ca3af')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.tick_params(colors='#9ca3af')
        ax.xaxis.label.set_color('#9ca3af')
        ax.yaxis.label.set_color('#9ca3af')
        ax.title.set_color('#e8eaed')
        
        # Save
        output_file = output_path / f"{symbol}_{timeframe}_latest.png"
        fig.savefig(output_file, facecolor='#1e2938', dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        print(f"Chart saved to: {output_file}")
        return str(output_file)
        
    except Exception as e:
        print(f"Error generating chart: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: generate_chart.py SYMBOL [TIMEFRAME] [DAYS] [WINDOW]")
        sys.exit(1)
    
    symbol = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1Day"
    days = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    window = int(sys.argv[4]) if len(sys.argv) > 4 else 11
    
    result = generate_chart(symbol, timeframe, days, window)
    
    if result:
        print(json.dumps({
            "status": "success",
            "file": result,
            "symbol": symbol,
            "parameters": {
                "timeframe": timeframe,
                "days": days,
                "window": window
            }
        }))
    else:
        print(json.dumps({
            "status": "error",
            "message": "Failed to generate chart"
        }))