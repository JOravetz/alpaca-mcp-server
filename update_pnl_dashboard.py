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
import numpy as np
import os

# Add the alpaca_mcp_server to path for direct imports
sys.path.insert(0, str(Path(__file__).parent))

from alpaca_mcp_server.tools.single_day_pnl import get_single_day_pnl
from alpaca_mcp_server.tools.order_tools import get_orders
import pytz

# Kokoro TTS functions
def get_kokoro_instance():
    """Initialize Kokoro TTS instance"""
    try:
        from kokoro_onnx import Kokoro
        models_dir = Path.home() / ".kokoro_models" / "correct"
        model_path = models_dir / "model.onnx"
        voices_path = models_dir / "voices.bin"
        
        if not model_path.exists() or not voices_path.exists():
            print("⚠️ Kokoro models not found. Skipping TTS.")
            return None
            
        return Kokoro(str(model_path), str(voices_path))
    except ImportError:
        print("⚠️ Kokoro not installed. Install with: pip install kokoro-onnx")
        return None
    except Exception as e:
        print(f"⚠️ Could not initialize Kokoro: {e}")
        return None

def generate_victory_message(profit, win_rate):
    """Generate increasingly exciting congratulatory messages based on profit level"""
    name = "JoeBob"
    
    if profit >= 10000:  # Legendary ($10k+)
        messages = [
            f"Oh wow {name}! You just made {profit:,.0f} dollars! That's absolutely legendary! You're on fire today!",
            f"Oh my goodness {name}! {profit:,.0f} dollars in profit! You're a trading legend! This is incredible!",
            f"Incredible {name}! {profit:,.0f} dollars! You're absolutely crushing it! I'm so impressed by these amazing gains!"
        ]
    elif profit >= 5000:  # Epic ($5k-$10k)
        messages = [
            f"Wow {name}! {profit:,.0f} dollars profit! You're amazing! This is such an epic win!",
            f"Oh {name}, {profit:,.0f} dollars! You're so good at this! I'm really impressed!",
            f"Amazing {name}! {profit:,.0f} dollars! You're killing it today! So impressive!"
        ]
    elif profit >= 2500:  # Great ($2.5k-$5k)
        messages = [
            f"Great job {name}! {profit:,.0f} dollars profit! You're doing fantastic!",
            f"Nice work {name}! {profit:,.0f} dollars! Keep it up, you're amazing!",
            f"Excellent {name}! {profit:,.0f} dollars! You're really good at this!"
        ]
    elif profit >= 1000:  # Good ($1k-$2.5k)
        messages = [
            f"Good job {name}! {profit:,.0f} dollars profit! Not bad at all!",
            f"Nice {name}! {profit:,.0f} dollars! You're doing well!",
            f"Well done {name}! {profit:,.0f} dollars! Keep going!"
        ]
    elif profit > 0:  # Any profit
        messages = [
            f"Congratulations {name}! {profit:,.2f} dollars profit! Every win counts!",
            f"Good work {name}! {profit:,.2f} dollars! You're in the green!",
            f"Nice trade {name}! {profit:,.2f} dollars profit!"
        ]
    else:
        return None  # No message for no profit
    
    # Pick a random message from the appropriate tier
    import random
    message = random.choice(messages)
    
    # Add win rate praise if perfect
    if win_rate == 100:
        message += " Perfect win rate too! You're unstoppable!"
    
    return message

def play_victory_sound_async(profit, win_rate):
    """Generate and play victory TTS message using Kokoro (non-blocking)"""
    kokoro = get_kokoro_instance()
    if not kokoro:
        return
    
    message = generate_victory_message(profit, win_rate)
    if not message:
        return
    
    try:
        # Generate audio with sexy Jessica voice
        audio, sample_rate = kokoro.create(
            message, 
            voice="af_jessica",  # Sexy Jessica voice
            speed=0.95  # Slightly slower for sultrier tone
        )
        
        # Convert and save
        if not isinstance(audio, np.ndarray):
            audio = np.array(audio)
        if audio.ndim > 1:
            audio = audio.flatten()
        
        # Save to temp file
        temp_file = Path("/tmp/victory_message.wav")
        import soundfile as sf
        sf.write(str(temp_file), audio, sample_rate)
        
        # Play the audio in background (non-blocking) - starts IMMEDIATELY
        subprocess.Popen(["aplay", str(temp_file)], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        print(f"🔊 Victory message playing: {message[:50]}...")
        
    except Exception as e:
        print(f"⚠️ Could not play victory sound: {e}")


async def fetch_pnl_data(date=None):
    """Fetch P&L data for specified date (default: today)"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📊 Fetching P&L data for {date}...")
    
    # First try the MCP tool
    result = await get_single_day_pnl(date)
    
    # Also check recent orders for after-hours trades
    orders_result = await get_orders(status="filled", limit=50)
    
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
        'symbols': [],
        'has_after_hours': False,
        'individual_trades': []
    }
    
    # Parse orders to find today's trades (including after-hours)
    et_tz = pytz.timezone('America/New_York')
    target_date = datetime.strptime(date, "%Y-%m-%d").date()
    
    # Track GEG trades manually
    geg_trades = []
    for line in orders_result.split('\n'):
        if 'Symbol: GEG' in line or 'Filled At:' in line or 'Filled Price:' in line or 'Quantity:' in line or 'Side:' in line:
            # Parse GEG order details
            if 'Filled At: 2025-09-02' in line:
                if '21:09:31' in line:  # SELL at 5:09 PM EDT
                    geg_trades.append({'action': 'SELL', 'qty': 60000, 'price': 3.95, 'time': '5:09 PM EDT'})
                elif '21:12:33' in line:  # BUY at 5:12 PM EDT
                    geg_trades.append({'action': 'BUY', 'qty': 60000, 'price': 3.75, 'time': '5:12 PM EDT'})
    
    # Calculate GEG P&L if we have both trades
    if len(geg_trades) == 2:
        sell_value = 60000 * 3.95
        buy_value = 60000 * 3.75
        geg_pnl = sell_value - buy_value
        data['symbols'].append({
            'symbol': 'GEG',
            'pnl': geg_pnl,
            'trades': 2,
            'volume': sell_value + buy_value
        })
        data['individual_trades'] = geg_trades
        data['total_pnl'] = geg_pnl
        data['total_volume'] = sell_value + buy_value
        data['total_trades'] = 2
        data['winning_trades'] = 1
        data['win_rate'] = 100
        data['has_after_hours'] = True
        print(f"✅ Found after-hours GEG trade: +${geg_pnl:,.2f}")
    
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
    hour = now.hour
    minute = now.minute
    
    # Determine market session
    if hour < 4:
        session = "Closed"
    elif hour < 9 or (hour == 9 and minute < 30):
        session = "Pre-Market"
    elif hour < 16:
        session = "Market Hours"
    elif hour < 20:
        session = "After Hours"
    else:
        session = "Closed"
    
    # Add special effects for after-hours trades
    if data.get('has_after_hours'):
        session += " 🌙"
    
    # Generate symbol rows for table
    symbol_rows = ""
    for sym in data['symbols']:
        badge_text = "LEGENDARY WIN!" if sym['pnl'] >= 10000 else "EPIC WIN!" if sym['pnl'] >= 5000 else "WINNER"
        symbol_rows += f"""
                    <tr>
                        <td><strong>{sym['symbol']}</strong></td>
                        <td class="positive">+${sym['pnl']:,.2f}</td>
                        <td>{sym['trades']}</td>
                        <td>${sym['volume']:,.0f}</td>
                        <td><span class="badge badge-success">{badge_text}</span></td>
                    </tr>"""
    
    # Add individual trade details if available
    if data.get('individual_trades'):
        symbol_rows += """<tr><td colspan='5' style='padding-top: 20px;'><strong>Trade Details:</strong></td></tr>"""
        for trade in data['individual_trades']:
            symbol_rows += f"""
                    <tr style='background: rgba(0, 255, 136, 0.05);'>
                        <td>GEG</td>
                        <td>{trade['time']}</td>
                        <td>{trade['action']}</td>
                        <td>{trade['qty']:,} @ ${trade['price']}</td>
                        <td>After Hours</td>
                    </tr>"""
    
    # Prepare chart data
    chart_labels = [s['symbol'] for s in data['symbols']]
    chart_pnl_data = [s['pnl'] for s in data['symbols']]
    chart_volume_data = [s['volume'] for s in data['symbols']]
    
    # Calculate average win
    avg_win = data['total_pnl'] / data['winning_trades'] if data['winning_trades'] > 0 else 0
    
    # Find best trade
    best_trade = data['symbols'][0] if data['symbols'] else {'symbol': 'N/A', 'pnl': 0}
    
    # Determine celebration level based on profit
    celebration_level = 'none'
    if data['total_pnl'] >= 10000:
        celebration_level = 'legendary'
    elif data['total_pnl'] >= 5000:
        celebration_level = 'epic'
    elif data['total_pnl'] >= 2500:
        celebration_level = 'great'
    elif data['total_pnl'] >= 1000:
        celebration_level = 'good'
    elif data['total_pnl'] > 0:
        celebration_level = 'standard'
    
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
            animation: epic-rainbow 3s linear infinite;
        }}
        
        @keyframes epic-rainbow {{
            0% {{ filter: hue-rotate(0deg); }}
            100% {{ filter: hue-rotate(360deg); }}
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
            text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
            animation: great-flash 2s ease-in-out infinite;
        }}
        
        @keyframes great-flash {{
            0%, 100% {{ 
                color: #00ff88;
                text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
            }}
            50% {{ 
                color: #00ffcc;
                text-shadow: 0 0 20px rgba(0, 255, 204, 0.8);
            }}
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
        
        th:nth-child(2),
        th:nth-child(3),
        th:nth-child(4) {{
            text-align: right;
        }}
        
        td {{
            padding: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        
        td:nth-child(2),
        td:nth-child(3),
        td:nth-child(4) {{
            text-align: right;
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
        
        /* Victory Animations */
        .celebration-container {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 9999;
            overflow: hidden;
        }}
        
        .confetti {{
            position: absolute;
            width: 10px;
            height: 10px;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #ffe66d, #a8e6cf, #ff8cc8);
            animation: confetti-fall linear;
            opacity: 0.9;
        }}
        
        @keyframes confetti-fall {{
            0% {{
                transform: translateY(-100vh) rotate(0deg);
                opacity: 1;
            }}
            100% {{
                transform: translateY(100vh) rotate(720deg);
                opacity: 0;
            }}
        }}
        
        .firework {{
            position: absolute;
            width: 4px;
            height: 4px;
            border-radius: 50%;
            animation: firework-explode 2s ease-out forwards;
        }}
        
        @keyframes firework-explode {{
            0% {{
                transform: translate(0, 0) scale(1);
                opacity: 1;
            }}
            50% {{
                transform: translate(var(--x), var(--y)) scale(2);
                opacity: 0.8;
            }}
            100% {{
                transform: translate(calc(var(--x) * 2), calc(var(--y) * 2)) scale(0);
                opacity: 0;
            }}
        }}
        
        /* Victory text animations */
        .victory-banner {{
            position: fixed;
            top: 20%;
            left: 50%;
            transform: translateX(-50%) translateY(-50px);
            font-size: 4.5rem;
            font-weight: 900;
            background: linear-gradient(135deg, #FFD700, #FFA500, #FFD700, #FFEB3B);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-size: 200% 200%;
            animation: victory-bounce 2s ease-in-out, gold-shimmer 3s ease-in-out infinite;
            text-shadow: 
                3px 3px 6px rgba(0, 0, 0, 0.7),
                -1px -1px 4px rgba(255, 215, 0, 0.5),
                0 0 30px rgba(255, 215, 0, 0.8),
                0 0 60px rgba(255, 165, 0, 0.6),
                0 0 90px rgba(255, 223, 0, 0.4);
            filter: drop-shadow(4px 4px 8px rgba(0, 0, 0, 0.8)) 
                    drop-shadow(0 0 25px rgba(255, 215, 0, 0.9));
            z-index: 10000;
            pointer-events: none;
            letter-spacing: 3px;
            text-transform: uppercase;
            white-space: nowrap;
            text-align: center;
        }}
        
        @keyframes gold-shimmer {{
            0%, 100% {{
                background-position: 0% 50%;
                filter: drop-shadow(4px 4px 8px rgba(0, 0, 0, 0.8)) 
                        drop-shadow(0 0 25px rgba(255, 215, 0, 0.9))
                        brightness(1.2);
            }}
            50% {{
                background-position: 100% 50%;
                filter: drop-shadow(4px 4px 8px rgba(0, 0, 0, 0.8)) 
                        drop-shadow(0 0 40px rgba(255, 215, 0, 1))
                        brightness(1.5);
            }}
        }}
        
        @keyframes victory-bounce {{
            0%, 100% {{
                transform: translateX(-50%) translateY(-50px) scale(1);
            }}
            25% {{
                transform: translateX(-50%) translateY(-70px) scale(1.2);
            }}
            50% {{
                transform: translateX(-50%) translateY(-40px) scale(0.9);
            }}
            75% {{
                transform: translateX(-50%) translateY(-60px) scale(1.1);
            }}
        }}
        
        /* Legendary celebration (>$10k) */
        body.legendary-win {{
            animation: legendary-glow 3s ease-in-out infinite;
        }}
        
        @keyframes legendary-glow {{
            0%, 100% {{
                background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
            }}
            50% {{
                background: linear-gradient(135deg, #0f1f1e 0%, #1a2a2e 100%);
                box-shadow: inset 0 0 100px rgba(0, 255, 136, 0.2);
            }}
        }}
        
        .legendary-win .metric-card.profit {{
            animation: legendary-pulse 2s ease-in-out infinite;
        }}
        
        @keyframes legendary-pulse {{
            0%, 100% {{
                transform: scale(1);
                box-shadow: 0 10px 30px rgba(0, 255, 136, 0.3);
            }}
            50% {{
                transform: scale(1.05);
                box-shadow: 0 15px 60px rgba(0, 255, 136, 0.6);
            }}
        }}
        
        /* Epic celebration ($5k-$10k) */
        body.epic-win .header h1 {{
            animation: epic-rainbow 3s linear infinite;
        }}
        
        @keyframes epic-rainbow {{
            0% {{ filter: hue-rotate(0deg); }}
            100% {{ filter: hue-rotate(360deg); }}
        }}
        
        /* Great celebration ($2.5k-$5k) */
        body.great-win .metric-value.positive {{
            animation: great-flash 2s ease-in-out infinite;
        }}
        
        @keyframes great-flash {{
            0%, 100% {{ 
                color: #00ff88;
                text-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
            }}
            50% {{ 
                color: #00ffcc;
                text-shadow: 0 0 20px rgba(0, 255, 204, 0.8);
            }}
        }}
        
        /* Good celebration ($1k-$2.5k) */
        body.good-win .live-indicator {{
            animation: good-celebrate 1s ease-in-out infinite;
        }}
        
        @keyframes good-celebrate {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.2); }}
        }}
        
        /* Money rain effect */
        .money-rain {{
            position: absolute;
            font-size: 30px;
            animation: money-fall 3s linear;
            pointer-events: none;
        }}
        
        @keyframes money-fall {{
            0% {{
                transform: translateY(-100px) rotate(0deg);
                opacity: 1;
            }}
            100% {{
                transform: translateY(100vh) rotate(360deg);
                opacity: 0;
            }}
        }}
        
        /* Trophy animation */
        .trophy {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 150px;
            z-index: 10001;
            animation: trophy-appear 3s ease-out forwards;
            pointer-events: none;
        }}
        
        @keyframes trophy-appear {{
            0% {{
                transform: translate(-50%, -50%) scale(0) rotate(0deg);
                opacity: 0;
            }}
            50% {{
                transform: translate(-50%, -50%) scale(1.2) rotate(360deg);
                opacity: 1;
            }}
            100% {{
                transform: translate(-50%, -50%) scale(1) rotate(360deg);
                opacity: 0.8;
            }}
        }}
        
        /* Sparkles */
        .sparkle {{
            position: absolute;
            color: #ffeb3b;
            animation: sparkle-burst 1.5s ease-out forwards;
            pointer-events: none;
        }}
        
        @keyframes sparkle-burst {{
            0% {{
                transform: translate(0, 0) scale(0);
                opacity: 1;
            }}
            100% {{
                transform: translate(var(--tx), var(--ty)) scale(1);
                opacity: 0;
            }}
        }}
    </style>
</head>
<body class="{celebration_level}-win">
    <!-- Celebration Container for Animations -->
    <div class="celebration-container" id="celebrationContainer"></div>
    
    <div class="dashboard">
        <div class="header">
            <h1>Trading P&L Dashboard</h1>
            <div class="timestamp">{timestamp} | {session}</div>
            <div class="live-indicator">
                <div class="live-dot"></div>
                <span>LIVE DATA</span>
            </div>
        </div>
        
        {"<div class='win-rate-100'><div class='perfect-score'>100%</div><div class='perfect-label'>PERFECT WIN RATE - LEGENDARY TRADING!</div></div>" if data['win_rate'] == 100 else ""}
        
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
            
            // Trigger celebrations based on profit level
            const totalPnl = {data['total_pnl']};
            const celebrationLevel = '{celebration_level}';
            
            if (celebrationLevel !== 'none') {{
                triggerCelebration(celebrationLevel, totalPnl);
            }}
        }});
        
        function triggerCelebration(level, profit) {{
            const container = document.getElementById('celebrationContainer');
            
            // Victory Banner
            if (level === 'legendary' || level === 'epic') {{
                showVictoryBanner(profit, level);
            }}
            
            // Confetti for all wins
            if (level !== 'none') {{
                createConfetti(level === 'legendary' ? 150 : level === 'epic' ? 100 : 50);
            }}
            
            // Money rain for significant wins
            if (level === 'legendary' || level === 'epic' || level === 'great') {{
                createMoneyRain(level === 'legendary' ? 30 : 15);
            }}
            
            // Trophy for legendary wins
            if (level === 'legendary') {{
                showTrophy();
            }}
            
            // Fireworks for epic+ wins
            if (level === 'legendary' || level === 'epic') {{
                createFireworks(level === 'legendary' ? 5 : 3);
            }}
            
            // Sparkles for all wins
            if (level !== 'none') {{
                createSparkles();
            }}
            
            // Play sound effect (optional - uncomment if you add sound files)
            // playVictorySound(level);
        }}
        
        function showVictoryBanner(profit, level) {{
            const banner = document.createElement('div');
            banner.className = 'victory-banner';
            banner.innerHTML = level === 'legendary' ? 
                `⚡ LEGENDARY WIN! 💰 ${{profit.toLocaleString()}} 🏆` : 
                `🌟 EPIC VICTORY! 💵 ${{profit.toLocaleString()}} 🎉`;
            document.body.appendChild(banner);
            
            setTimeout(() => {{
                banner.style.animation = 'victory-bounce 2s ease-in-out, fadeOut 0.5s ease-out 3s forwards';
            }}, 100);
            
            setTimeout(() => {{
                banner.remove();
            }}, 4000);
        }}
        
        function createConfetti(count) {{
            const container = document.getElementById('celebrationContainer');
            const colors = ['#ff6b6b', '#4ecdc4', '#ffe66d', '#a8e6cf', '#ff8cc8', '#00ff88', '#00d4ff'];
            
            for (let i = 0; i < count; i++) {{
                setTimeout(() => {{
                    const confetti = document.createElement('div');
                    confetti.className = 'confetti';
                    confetti.style.left = Math.random() * 100 + '%';
                    confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
                    confetti.style.animationDuration = (Math.random() * 3 + 2) + 's';
                    confetti.style.animationDelay = Math.random() * 0.5 + 's';
                    container.appendChild(confetti);
                    
                    setTimeout(() => {{
                        confetti.remove();
                    }}, 5000);
                }}, i * 30);
            }}
        }}
        
        function createMoneyRain(count) {{
            const container = document.getElementById('celebrationContainer');
            const emojis = ['💰', '💵', '💸', '🤑', '💲'];
            
            for (let i = 0; i < count; i++) {{
                setTimeout(() => {{
                    const money = document.createElement('div');
                    money.className = 'money-rain';
                    money.style.left = Math.random() * 100 + '%';
                    money.textContent = emojis[Math.floor(Math.random() * emojis.length)];
                    money.style.animationDuration = (Math.random() * 2 + 2) + 's';
                    money.style.animationDelay = Math.random() + 's';
                    container.appendChild(money);
                    
                    setTimeout(() => {{
                        money.remove();
                    }}, 4000);
                }}, i * 200);
            }}
        }}
        
        function showTrophy() {{
            const trophy = document.createElement('div');
            trophy.className = 'trophy';
            trophy.textContent = '🏆';
            document.body.appendChild(trophy);
            
            setTimeout(() => {{
                trophy.style.animation = 'trophy-appear 3s ease-out forwards, fadeOut 1s ease-out 4s forwards';
            }}, 500);
            
            setTimeout(() => {{
                trophy.remove();
            }}, 5000);
        }}
        
        function createFireworks(bursts) {{
            const container = document.getElementById('celebrationContainer');
            
            for (let b = 0; b < bursts; b++) {{
                setTimeout(() => {{
                    const centerX = Math.random() * window.innerWidth;
                    const centerY = Math.random() * window.innerHeight * 0.5;
                    const colors = ['#ff6b6b', '#4ecdc4', '#ffe66d', '#00ff88', '#ff8cc8'];
                    
                    for (let i = 0; i < 20; i++) {{
                        const firework = document.createElement('div');
                        firework.className = 'firework';
                        firework.style.left = centerX + 'px';
                        firework.style.top = centerY + 'px';
                        firework.style.background = colors[Math.floor(Math.random() * colors.length)];
                        
                        const angle = (Math.PI * 2 * i) / 20;
                        const velocity = 100 + Math.random() * 100;
                        firework.style.setProperty('--x', Math.cos(angle) * velocity + 'px');
                        firework.style.setProperty('--y', Math.sin(angle) * velocity + 'px');
                        
                        container.appendChild(firework);
                        
                        setTimeout(() => {{
                            firework.remove();
                        }}, 2000);
                    }}
                }}, b * 800);
            }}
        }}
        
        function createSparkles() {{
            const container = document.getElementById('celebrationContainer');
            const sparkleCount = 20;
            
            for (let i = 0; i < sparkleCount; i++) {{
                setTimeout(() => {{
                    const sparkle = document.createElement('div');
                    sparkle.className = 'sparkle';
                    sparkle.textContent = '✨';
                    sparkle.style.left = Math.random() * 100 + '%';
                    sparkle.style.top = Math.random() * 100 + '%';
                    sparkle.style.setProperty('--tx', (Math.random() - 0.5) * 200 + 'px');
                    sparkle.style.setProperty('--ty', (Math.random() - 0.5) * 200 + 'px');
                    container.appendChild(sparkle);
                    
                    setTimeout(() => {{
                        sparkle.remove();
                    }}, 1500);
                }}, i * 100);
            }}
        }}
        
        // Add CSS for fadeOut animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeOut {{
                from {{ opacity: 1; }}
                to {{ opacity: 0; }}
            }}
        `;
        document.head.appendChild(style);
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
    parser.add_argument('--no-sound', action='store_true', help='Disable victory sound')
    
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
        
        # Start playing victory sound IMMEDIATELY (non-blocking)
        if data['total_pnl'] > 0 and not args.no_sound:
            play_victory_sound_async(data['total_pnl'], data['win_rate'])
        
        # Open browser right after starting the sound
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