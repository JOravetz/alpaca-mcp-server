# mypy: disable-error-code="union-attr, arg-type"


"""Account analysis prompt implementation."""

from datetime import datetime

from ..config.settings import get_trading_client
from ..tools.account_tools import get_account_info, get_positions


async def account_analysis() -> str:
    """Complete portfolio health check with actionable insights."""

    try:
        # 1. Get core account data (for tool registration)
        await get_account_info()
        await get_positions()

        # 2. Parse account data for analysis
        client = get_trading_client()
        account = client.get_account()
        positions = client.get_all_positions()

        # 3. Calculate key metrics
        total_portfolio_value = float(account.portfolio_value)  # type: ignore[union-attr]
        cash_balance = float(account.cash)  # type: ignore[union-attr]
        buying_power = float(account.buying_power)  # type: ignore[union-attr]
        equity = float(account.equity)  # type: ignore[union-attr]

        # Calculate position metrics
        position_count = len(positions)
        if positions:
            total_unrealized_pnl = sum(float(pos.unrealized_pl) for pos in positions)  # type: ignore[misc]
            total_market_value = sum(float(pos.market_value) for pos in positions)  # type: ignore[misc]

            # Calculate concentration risk
            largest_position = max(positions, key=lambda p: float(p.market_value))
            largest_position_pct = (
                float(largest_position.market_value) / total_portfolio_value * 100  # type: ignore[attr-defined]
            )
        else:
            total_unrealized_pnl = 0
            total_market_value = 0
            largest_position_pct = 0

        # 4. Risk Assessment
        risk_level = "Low"
        risk_factors = []

        if largest_position_pct > 25:
            risk_level = "High"
            risk_factors.append("High concentration risk detected")
        elif largest_position_pct > 15:
            risk_level = "Moderate"
            risk_factors.append("Moderate concentration risk")

        if cash_balance < total_portfolio_value * 0.05:
            risk_factors.append("Low cash reserves")

        # 5. Generate strategic recommendations
        recommendations = []

        if largest_position_pct > 20:
            recommendations.append("Consider reducing largest position concentration")

        if cash_balance > total_portfolio_value * 0.20:
            recommendations.append("High cash - consider deploying capital")
        elif cash_balance < total_portfolio_value * 0.05:
            recommendations.append("Consider maintaining 5-10% cash reserve")

        if position_count > 20:
            recommendations.append("Consider consolidating positions")
        elif position_count < 5 and total_portfolio_value > 10000:
            recommendations.append("Consider adding positions for diversification")

        # 6. Format comprehensive response
        result = f"""# Portfolio Health Check

## Account Overview
Portfolio Value: ${total_portfolio_value:,.2f}
Cash Available: ${cash_balance:,.2f} ({cash_balance / total_portfolio_value * 100:.1f}%)
Buying Power: ${buying_power:,.2f}
Equity: ${equity:,.2f}

## Position Summary
Total Positions: {position_count}
Market Value: ${total_market_value:,.2f}
Unrealized P&L: ${total_unrealized_pnl:,.2f}

## Risk Assessment
Risk Level: {risk_level}
Risk Factors:"""

        if risk_factors:
            for factor in risk_factors:
                result += f"\n• {factor}"
        else:
            result += "\n• No significant risk factors identified"

        result += """

## Strategic Recommendations"""

        if recommendations:
            for rec in recommendations:
                result += f"\n• {rec}"
        else:
            result += "\n• Portfolio appears well-balanced"

        result += f"""

## Next Steps
• Use position_management() to review individual holdings
• Use market_analysis() to identify new opportunities

Analysis Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        return result

    except Exception as e:
        return f"""Error during account analysis: {str(e)}

Troubleshooting:
• Verify API credentials are valid
• Check market connectivity
• Try get_account_info() for basic data
"""
