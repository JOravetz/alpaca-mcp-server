from alpaca.trading.models import Position
"""Position management prompt implementation."""

from ..config.settings import get_trading_client


async def position_management(symbol: str | None = None) -> str:
    """Strategic position review and optimization with actionable guidance."""

    try:
        client = get_trading_client()

        if symbol:
            # Analyze specific position
            try:
                position = client.get_open_position(symbol)

                # Calculate position metrics
                current_value = float(position.market_value)  # type: ignore[arg-type,union-attr]
                unrealized_pnl = float(position.unrealized_pl)  # type: ignore[arg-type,union-attr]
                unrealized_pnl_pct = float(position.unrealized_plpc) * 100  # type: ignore[arg-type,union-attr]
                entry_price = float(position.avg_entry_price)  # type: ignore[union-attr]
                current_price = float(position.current_price)  # type: ignore[arg-type,union-attr]
                quantity = float(position.qty)  # type: ignore[union-attr]

                # Determine position analysis
                if unrealized_pnl_pct > 20:
                    performance = "Strong Winner"
                    action = "Consider taking partial profits"
                elif unrealized_pnl_pct > 10:
                    performance = "Good Performer"
                    action = "Monitor for continuation"
                elif unrealized_pnl_pct > -5:
                    performance = "Neutral"
                    action = "Hold and monitor"
                elif unrealized_pnl_pct > -15:
                    performance = "Underperforming"
                    action = "Review thesis, consider stop loss"
                else:
                    performance = "Significant Loss"
                    action = "Urgent review - consider cutting losses"

                base_analysis = f"""# Position Analysis: {symbol}

## Position Details
Quantity: {quantity:,.0f} shares
Entry Price: ${entry_price:.2f}
Current Price: ${current_price:.2f}
Market Value: ${current_value:,.2f}
Unrealized P&L: ${unrealized_pnl:,.2f} ({unrealized_pnl_pct:+.2f}%)

## Performance Assessment
Status: {performance}
Recommendation: {action}

## Action Options
Take Profits (25%): close_position('{symbol}', percentage='25')
Take Profits (50%): close_position('{symbol}', percentage='50')
Close Full Position: close_position('{symbol}')

## Analysis Points"""

                # Add specific analysis based on performance
                if unrealized_pnl_pct > 15:
                    return (
                        base_analysis
                        + """
• Strong position - consider scaling out to lock profits
• Monitor for potential reversal signals
• Consider setting trailing stop"""
                    )
                elif unrealized_pnl_pct < -10:
                    return (
                        base_analysis
                        + """
• Position under pressure - review original thesis
• Check for company news or sector weakness
• Consider stop loss to limit downside"""
                    )
                else:
                    return (
                        base_analysis
                        + """
• Position within normal range
• Monitor for breakout or breakdown signals
• Maintain current allocation unless fundamentals change"""
                    )

            except Exception as e:
                return f"Could not analyze position for {symbol}: {str(e)}"

        else:
            # Analyze entire portfolio
            positions = client.get_all_positions()

            if not positions:
                return """# Position Management

## Portfolio Status
No open positions found

## Getting Started
• Use market_analysis() to find trading opportunities
• Use account_analysis() to review available capital

Popular starting strategies:
• Index ETFs (SPY, QQQ, IWM) for broad exposure
• Blue chip stocks (AAPL, MSFT, GOOGL) for stability
"""

            # Categorize positions by performance
            winners = []
            losers = []
            neutral = []

            for pos in positions:
                pnl_pct = float(pos.unrealized_plpc) * 100  # type: ignore[arg-type,union-attr]
                if pnl_pct > 5:
                    winners.append((pos, pnl_pct))
                elif pnl_pct < -5:
                    losers.append((pos, pnl_pct))
                else:
                    neutral.append((pos, pnl_pct))

            # Sort by performance
            winners.sort(key=lambda x: x[1], reverse=True)
            losers.sort(key=lambda x: x[1])

            result = f"""# Portfolio Position Management

## Position Summary
Total Positions: {len(positions)}
Winners: {len(winners)} positions (>5% gain)
Neutral: {len(neutral)} positions (-5% to +5%)
Losers: {len(losers)} positions (>5% loss)

"""

            # Analyze winners
            if winners:
                result += "## Top Performers\n"
                for pos, pnl_pct in winners[:5]:
                    result += (
                        f"• {pos.symbol}: {pnl_pct:+.1f}% (${float(pos.unrealized_pl):,.2f})\n"  # type: ignore[arg-type,union-attr]
                    )
                result += "\n"

            # Analyze losers
            if losers:
                result += "## Underperformers\n"
                for pos, pnl_pct in losers[:5]:
                    result += (
                        f"• {pos.symbol}: {pnl_pct:+.1f}% (${float(pos.unrealized_pl):,.2f})\n"  # type: ignore[arg-type,union-attr]
                    )
                result += "\n"

            # Strategic recommendations
            result += """## Portfolio Management Strategy

Immediate Actions:"""

            if len(winners) > 0:
                best_winner = winners[0]
                result += f"\n• Review top winner {best_winner[0].symbol} for profit-taking"  # type: ignore[union-attr]

            if len(losers) > 0:
                worst_loser = losers[0]
                result += f"\n• Analyze worst performer {worst_loser[0].symbol} for stop loss"  # type: ignore[union-attr]

            result += """

Next Steps:
• Analyze individual positions: position_management('SYMBOL')
• Find new opportunities: market_analysis()
• Review overall strategy: account_analysis()
"""

            return result

    except Exception as e:
        return f"""Error in position management: {str(e)}

Troubleshooting:
• Check API connectivity and credentials
• Try get_positions() for basic position data
"""
