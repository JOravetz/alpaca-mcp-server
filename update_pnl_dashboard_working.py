#!/usr/bin/env python3
"""
Fast P&L Dashboard Updater
Fetches daily P&L data and generates an interactive HTML dashboard
"""

import json
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
import sys
import asyncio

# Add the alpaca_mcp_server to path for direct imports
sys.path.insert(0, str(Path(__file__).parent))

from alpaca_mcp_server.tools.single_day_pnl import get_single_day_pnl


async def fetch_pnl_data(date=None):
    """Fetch P&L data for specified date (default: today)"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📊 Fetching P&L data for {date}...")
    
    # Call the MCP tool directly
    result = await get_single_day_pnl(date)
    
    # Parse the text output to extract data
    lines = result.split('\n')
    data = {
        'date': date,
        'total_pnl': 0,
        'total_volume': 0,
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'win_rate': 0,
        'symbols': []
    }
    
    # Extract summary data
    for line in lines:
        if 'TOTAL P&L:' in line:
            data['total_pnl'] = float(line.split('$')[1].replace(',', ''))
        elif 'Total Volume:' in line:
            vol_str = line.split('$')[1].replace(',', '')
            data['total_volume'] = float(vol_str)
        elif 'Total Trades:' in line:
            data['total_trades'] = int(line.split(':')[1].strip())
        elif 'Winning Trades:' in line:
            data['winning_trades'] = int(line.split(':')[1].strip())
        elif 'Losing Trades:' in line:
            data['losing_trades'] = int(line.split(':')[1].strip())
        elif 'Win Rate:' in line:
            data['win_rate'] = float(line.split(':')[1].strip().replace('%', ''))
        elif '|' in line and 'P&L:' in line:
            # Parse symbol data
            parts = line.split('|')
            if len(parts) >= 4:
                symbol = parts[0].strip().replace('✅', '').strip()
                pnl_str = parts[1].split('$')[1].strip()
                trades = int(parts[2].split(':')[1].strip())
                volume_str = parts[3].split('$')[1].strip()
                
                data['symbols'].append({
                    'symbol': symbol,
                    'pnl': float(pnl_str.replace(',', '')),
                    'trades': trades,
                    'volume': float(volume_str.replace(',', ''))
                })
    
    # Sort symbols by P&L
    data['symbols'].sort(key=lambda x: x['pnl'], reverse=True)
    
    return data


def generate_dashboard_html(data):
    """Generate HTML dashboard with P&L data"""
    
    # Format timestamp
    now = datetime.now()
    timestamp = now.strftime("%A, %B %d, %Y | %I:%M %p EDT")
    session = "Pre-Market" if now.hour < 9 or (now.hour == 9 and now.minute < 30) else "Market Hours"
    
    # Generate symbol rows for table
    symbol_rows = ""
    for sym in data['symbols']:
        symbol_rows += f"""
                    <tr>
                        <td><strong>{sym['symbol']}</strong></td>
                        <td class="positive">+${sym['pnl']:,.2f}</td>
                        <td>{sym['trades']}</td>
                        <td>${sym['volume']:,.0f}</td>
                        <td><span class="badge badge-success">WINNER</span></td>
                    </tr>"""
    
    # Prepare chart data
    chart_labels = [s['symbol'] for s in data['symbols']]
    chart_pnl_data = [s['pnl'] for s in data['symbols']]
    chart_volume_data = [s['volume'] for s in data['symbols']]
    
    # Calculate average win
    avg_win = data['total_pnl'] / data['winning_trades'] if data['winning_trades'] > 0 else 0
    
    # Find best trade
    best_trade = data['symbols'][0] if data['symbols'] else {'symbol': 'N/A', 'pnl': 0}
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trading Dashboard - {data['date']}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
            color: #ffffff;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #00ff88 0%, #00d4ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        
        .timestamp {{
            color: #888;
            font-size: 0.9rem;
        }}
        
        .live-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            background: rgba(34, 197, 94, 0.2);
            border-radius: 20px;
            margin-top: 10px;
        }}
        
        .live-dot {{
            width: 8px;
            height: 8px;
            background: #00ff88;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 255, 136, 0.2);
        }}
        
        .metric-card.profit {{
            background: linear-gradient(135deg, rgba(0, 255, 136, 0.1), rgba(0, 255, 136, 0.05));
            border-color: #00ff88;
        }}
        
        .metric-label {{
            font-size: 0.85rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}
        
        .metric-value {{
            font-size: 2rem;
            font-weight: 700;
        }}
        
        .positive {{
            color: #00ff88;
        }}
        
        .win-rate-100 {{
            background: linear-gradient(135deg, #00ff88, #00d4ff);
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 30px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0, 255, 136, 0.3);
        }}
        
        .win-rate-100::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.1), transparent);
            animation: shine 3s infinite;
        }}
        
        @keyframes shine {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .perfect-score {{
            font-size: 4rem;
            font-weight: 900;
            color: #0a0a0f;
            text-shadow: 
                2px 2px 4px rgba(255, 255, 255, 0.8),
                -1px -1px 2px rgba(255, 255, 255, 0.4),
                0 0 30px rgba(255, 255, 255, 0.6);
            position: relative;
            z-index: 1;
        }}
        
        .perfect-label {{
            font-size: 1.2rem;
            color: #0a0a0f;
            margin-top: 10px;
            font-weight: 600;
            text-shadow: 
                1px 1px 2px rgba(255, 255, 255, 0.7),
                -1px -1px 1px rgba(255, 255, 255, 0.3);
            position: relative;
            z-index: 1;
            letter-spacing: 0.5px;
        }}
        
        .charts-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .chart-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .chart-title {{
            font-size: 1.2rem;
            margin-bottom: 15px;
            color: #fff;
        }}
        
        .trades-table {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            background: rgba(255, 255, 255, 0.1);
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #00d4ff;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        tr:hover {{
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        
        .badge-success {{
            background: rgba(0, 255, 136, 0.2);
            color: #00ff88;
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>Trading P&L Dashboard</h1>
            <div class="timestamp">{timestamp} | {session}</div>
            <div class="live-indicator">
                <div class="live-dot"></div>
                <span>LIVE DATA</span>
            </div>
        </div>
        
        {"<div class='win-rate-100'><div class='perfect-score'>" + str(int(data['win_rate'])) + "%</div><div class='perfect-label'>PERFECT WIN RATE - " + str(data['winning_trades']) + " WINS / " + str(data['losing_trades']) + " LOSSES</div></div>" if data['win_rate'] == 100 else ""}
        
        <div class="metrics-grid">
            <div class="metric-card profit">
                <div class="metric-label">Total P&L</div>
                <div class="metric-value positive">+${data['total_pnl']:,.2f}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value positive">{data['win_rate']:.0f}%</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Total Trades</div>
                <div class="metric-value">{data['total_trades']}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Total Volume</div>
                <div class="metric-value">${data['total_volume']/1000000:.2f}M</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Winning Trades</div>
                <div class="metric-value positive">{data['winning_trades']}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Average Win</div>
                <div class="metric-value positive">${avg_win:,.2f}</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Best Trade</div>
                <div class="metric-value positive">{best_trade['symbol']} +${best_trade['pnl']:,.0f}</div>
            </div>
        </div>
        
        <div class="charts-container">
            <div class="chart-card">
                <h3 class="chart-title">P&L by Symbol</h3>
                <canvas id="pnlChart"></canvas>
            </div>
            
            <div class="chart-card">
                <h3 class="chart-title">Volume Distribution</h3>
                <canvas id="volumeChart"></canvas>
            </div>
        </div>
        
        <div class="trades-table">
            <h3 class="chart-title">Symbol Performance</h3>
            <table>
                <thead>
                    <tr>
                        <th>Symbol</th>
                        <th>P&L</th>
                        <th>Trades</th>
                        <th>Volume</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {symbol_rows}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // Color palette
        const colors = [
            'rgba(0, 255, 136, 0.6)',
            'rgba(0, 212, 255, 0.6)',
            'rgba(255, 87, 51, 0.6)',
            'rgba(255, 206, 86, 0.6)',
            'rgba(153, 102, 255, 0.6)',
            'rgba(255, 159, 64, 0.6)',
            'rgba(75, 192, 192, 0.6)',
            'rgba(255, 99, 132, 0.6)',
            'rgba(54, 162, 235, 0.6)',
            'rgba(255, 144, 0, 0.6)'
        ];
        
        const borderColors = colors.map(c => c.replace('0.6', '1'));
        
        // P&L Chart
        const pnlCtx = document.getElementById('pnlChart').getContext('2d');
        new Chart(pnlCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(chart_labels)},
                datasets: [{{
                    label: 'Profit & Loss',
                    data: {json.dumps(chart_pnl_data)},
                    backgroundColor: colors.slice(0, {len(chart_labels)}),
                    borderColor: borderColors.slice(0, {len(chart_labels)}),
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return '$' + context.parsed.y.toLocaleString('en-US', {{minimumFractionDigits: 2}});
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: function(value) {{
                                return '$' + value.toLocaleString();
                            }},
                            color: '#888'
                        }},
                        grid: {{
                            color: 'rgba(255, 255, 255, 0.1)'
                        }}
                    }},
                    x: {{
                        ticks: {{
                            color: '#888'
                        }},
                        grid: {{
                            display: false
                        }}
                    }}
                }}
            }}
        }});
        
        // Volume Chart
        const volumeCtx = document.getElementById('volumeChart').getContext('2d');
        new Chart(volumeCtx, {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(chart_labels)},
                datasets: [{{
                    data: {json.dumps(chart_volume_data)},
                    backgroundColor: colors.slice(0, {len(chart_labels)}),
                    borderColor: borderColors.slice(0, {len(chart_labels)}),
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            color: '#888',
                            padding: 20
                        }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                const label = context.label || '';
                                const value = '$' + (context.parsed / 1000000).toFixed(2) + 'M';
                                return label + ': ' + value;
                            }}
                        }}
                    }}
                }}
            }}
        }});
        
        // Add animation on load
        document.addEventListener('DOMContentLoaded', function() {{
            const cards = document.querySelectorAll('.metric-card');
            cards.forEach((card, index) => {{
                card.style.opacity = '0';
                card.style.transform = 'translateY(20px)';
                setTimeout(() => {{
                    card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }}, index * 50);
            }});
        }});
    </script>
</body>
</html>"""
    
    return html_content


async def main():
    """Main function to update P&L dashboard"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Update P&L Dashboard')
    parser.add_argument('--date', help='Date in YYYY-MM-DD format (default: today)')
    parser.add_argument('--output', default='trading_dashboard.html', help='Output HTML file')
    parser.add_argument('--no-browser', action='store_true', help='Do not open browser')
    
    args = parser.parse_args()
    
    try:
        # Fetch P&L data
        data = await fetch_pnl_data(args.date)
        print(f"✅ P&L data fetched: ${data['total_pnl']:,.2f} profit")
        
        # Generate HTML
        html = generate_dashboard_html(data)
        
        # Save to file
        output_path = Path(args.output)
        output_path.write_text(html)
        print(f"✅ Dashboard saved to {output_path}")
        
        # Open in browser
        if not args.no_browser:
            file_url = f"file://{output_path.absolute()}"
            webbrowser.open(file_url)
            print("✅ Dashboard opened in browser")
        
        print(f"\n📊 Dashboard Update Complete!")
        print(f"   Total P&L: ${data['total_pnl']:,.2f}")
        print(f"   Win Rate: {data['win_rate']:.0f}%")
        print(f"   Symbols: {len(data['symbols'])}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))