"""
P&L Bling Dashboard Prompt - Full celebration experience with Kokoro TTS
Command: /pnl-bling
"""

from datetime import datetime
from typing import Any

import pytz


def get_pnl_bling_prompt() -> dict[str, Any]:
    """
    Generate the P&L Bling dashboard with full celebrations.

    This prompt:
    1. Fetches current day P&L data
    2. Generates interactive HTML dashboard with animations
    3. Plays Kokoro TTS victory messages (Jessica's voice)
    4. Shows tiered celebration effects based on profit level

    Returns:
        Dictionary with prompt name, description and arguments
    """

    et_tz = pytz.timezone("America/New_York")
    datetime.now(et_tz)

    prompt = {
        "name": "pnl-bling",
        "description": "💰 Generate P&L Dashboard with full bling-bling celebrations and Kokoro TTS",
        "arguments": [
            {
                "name": "date",
                "description": "Date for P&L (YYYY-MM-DD format, default: today)",
                "required": False,
            },
            {
                "name": "sound",
                "description": "Enable Kokoro TTS victory messages (default: true)",
                "required": False,
            },
        ],
    }

    return prompt


def generate_pnl_bling_prompt_text(date: str | None = None, sound: bool = True) -> str:
    """
    Generate the actual prompt text for the P&L Bling dashboard.

    Args:
        date: Optional date override (YYYY-MM-DD)
        sound: Whether to enable TTS (default: True)

    Returns:
        The formatted prompt text
    """

    et_tz = pytz.timezone("America/New_York")
    current_time = datetime.now(et_tz)
    # Ensure we have a valid date string
    date_str = current_time.strftime("%Y-%m-%d") if not date or date.strip() == "" else date.strip()
    sound_flag = "" if sound else "--no-sound"

    return f"""
🎉 P&L BLING DASHBOARD - FULL CELEBRATION MODE! 🎉
==================================================

I'll generate your P&L dashboard with all the bling-bling effects!

📊 DASHBOARD FEATURES:
• Kokoro TTS with Jessica's sultry voice
• Tiered celebration animations
• Real-time P&L data from Alpaca
• Interactive charts and visualizations

🎯 CELEBRATION TIERS:
• LEGENDARY ($10k+): Full effects, 150 confetti, trophy, fireworks
• EPIC ($5k-$10k): 100 confetti, money rain, pulse effects
• GREAT ($2.5k-$5k): 50 confetti, sparkles
• GOOD ($1k-$2.5k): Basic animations
• ANY PROFIT: Victory message

EXECUTING WORKFLOW:
1. Fetching P&L data for {date_str}
2. Generating HTML dashboard with animations
3. Playing Kokoro TTS celebration (if profit > $0)
4. Opening dashboard in browser

Please run this command:

```bash
# Run the P&L Bling Dashboard (assumes API credentials are already in environment)
uv run python update_pnl_dashboard.py --date {date_str} {sound_flag}
```

The dashboard will:
✨ Display your P&L with visual effects
🔊 Play Jessica's congratulatory message
🎊 Show animations scaled to your profit level
📈 Include interactive charts and metrics

Let's see those gains and celebrate in style! 🚀
"""


def register_pnl_bling_prompt():
    """Register the P&L Bling prompt with the MCP server."""
    return {
        "pnl-bling": {
            "description": "💰 P&L Dashboard with full celebrations and Kokoro TTS",
            "function": generate_pnl_bling_prompt_text,
            "metadata": get_pnl_bling_prompt(),
        }
    }
