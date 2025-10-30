"""Extended hours order validation and placement tools."""

from datetime import time

from ..utils.timezone_utils import get_eastern_time


async def validate_extended_hours_order(
    symbol: str, order_type: str, extended_hours: bool | None = None
) -> dict:
    """Validate if order can be placed in current market session."""
    try:
        now_et, tz_name = get_eastern_time()
        current_time = now_et.time()

        # Session detection
        premarket_start = time(4, 0)
        market_open = time(9, 30)
        market_close = time(16, 0)
        postmarket_end = time(20, 0)

        if premarket_start <= current_time < market_open:
            current_session = "pre_market"
            in_extended_hours = True
        elif market_open <= current_time < market_close:
            current_session = "regular_market"
            in_extended_hours = False
        elif market_close <= current_time < postmarket_end:
            current_session = "post_market"
            in_extended_hours = True
        else:
            current_session = "closed"
            in_extended_hours = False

        # Order validation logic
        can_place_order = True
        warnings = []
        recommendations = []

        if current_session == "closed":
            can_place_order = False
            warnings.append("Markets are closed - no trading sessions active")
            recommendations.append("Orders will be queued for next trading session")

        elif in_extended_hours:
            if order_type.upper() == "MARKET":
                warnings.append("Market orders may have poor execution in extended hours")
                recommendations.append("Consider using LIMIT orders for better fills")

            if extended_hours is False:
                warnings.append("extended_hours=False but currently in extended hours session")
                recommendations.append("Set extended_hours=True to trade in current session")
                can_place_order = False

            # Additional extended hours warnings
            warnings.append("Extended hours trading has increased risks")
            recommendations.extend(
                [
                    "Lower liquidity - expect wider spreads",
                    "Use conservative position sizing",
                    "Monitor news that could cause gaps",
                ]
            )

        # Symbol-specific validation (simplified)
        major_symbols = [
            "SPY",
            "QQQ",
            "AAPL",
            "MSFT",
            "TSLA",
            "NVDA",
            "AMZN",
            "GOOGL",
            "META",
            "AMD",
            "NFLX",
        ]
        if symbol.upper() not in major_symbols:
            warnings.append(f"{symbol} may have very limited extended hours liquidity")
            recommendations.append("Check recent volume before placing extended hours orders")

        # Order type recommendations
        order_type_recommendations = {
            "MARKET": "Not recommended for extended hours - use LIMIT instead",
            "LIMIT": "Good choice for extended hours trading",
            "STOP": "May not execute properly in extended hours",
            "STOP_LIMIT": "Acceptable but monitor carefully",
        }

        if order_type.upper() in order_type_recommendations:
            recommendations.append(order_type_recommendations[order_type.upper()])

        return {
            "can_place_order": can_place_order,
            "current_session": current_session,
            "in_extended_hours": in_extended_hours,
            "recommended_extended_hours_flag": in_extended_hours,
            "order_type_assessment": order_type_recommendations.get(
                order_type.upper(), "Unknown order type"
            ),
            "warnings": warnings,
            "recommendations": recommendations,
            "session_info": {
                "session": current_session,
                "time_et": now_et.strftime("%H:%M:%S ET"),
                "extended_hours_active": in_extended_hours,
                "date": now_et.strftime("%Y-%m-%d"),
            },
            "risk_factors": {
                "liquidity": "Low" if in_extended_hours else "Normal",
                "spread_width": "Wide" if in_extended_hours else "Normal",
                "volatility": "High" if in_extended_hours else "Normal",
                "news_sensitivity": "Very High" if in_extended_hours else "Normal",
            },
        }

    except Exception as e:
        return {"error": str(e)}


async def place_extended_hours_order(  # type: ignore[no-untyped-def]
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "limit",
    limit_price: float | None = None,
    extended_hours: bool | None = None,
    time_in_force: str = "day",
    **kwargs,
) -> str:
    """Place order with automatic extended hours detection and validation."""

    try:
        # Validate the order first
        validation = await validate_extended_hours_order(symbol, order_type, extended_hours)

        # Auto-detect extended hours if not specified
        if extended_hours is None:
            extended_hours = validation.get("recommended_extended_hours_flag", False)

        # Check if order can be placed
        if not validation.get("can_place_order", False):
            return f"""
❌ Order Validation Failed:
Symbol: {symbol}
Reason: {", ".join(validation.get("warnings", ["Unknown error"]))}

Recommendations:
{chr(10).join(f"• {rec}" for rec in validation.get("recommendations", []))}

Current Session: {validation.get("session_info", {}).get("session", "unknown")}
            """

        # Import the original order placement function
        from ..tools.order_tools import (
            format_price_for_alpaca,
            get_current_stock_price,
            place_stock_order,
        )

        # Format limit price properly for penny stocks
        if limit_price is not None:
            current_price = await get_current_stock_price(symbol)
            limit_price = format_price_for_alpaca(limit_price, current_price)

        # Place the order with extended hours flag
        result = await place_stock_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            extended_hours=extended_hours,
            time_in_force=time_in_force,
            **kwargs,
        )

        # Format warnings and recommendations
        warning_text = ""
        if validation.get("warnings"):
            warning_text = "⚠️ Warnings:\n" + "\n".join(f"• {w}" for w in validation["warnings"])

        rec_text = ""
        if validation.get("recommendations"):
            rec_text = "💡 Recommendations:\n" + "\n".join(
                f"• {r}" for r in validation["recommendations"]
            )

        # Risk assessment
        risk_info = validation.get("risk_factors", {})
        risk_text = f"""
📊 Risk Assessment:
• Liquidity: {risk_info.get("liquidity", "Unknown")}
• Spread Width: {risk_info.get("spread_width", "Unknown")}
• Volatility: {risk_info.get("volatility", "Unknown")}
• News Sensitivity: {risk_info.get("news_sensitivity", "Unknown")}
        """

        # Enhanced result with session info
        enhanced_result = f"""
Extended Hours Order Placement:
==============================
{result}

Session Information:
• Extended Hours: {"Yes" if extended_hours else "No"}
• Current Session: {validation.get("session_info", {}).get("session", "unknown")}
• Time: {validation.get("session_info", {}).get("time_et", "unknown")}

{warning_text}

{rec_text}

{risk_text}
        """

        return enhanced_result.strip()

    except Exception as e:
        return f"Error placing extended hours order: {str(e)}"


async def get_extended_hours_info() -> str:
    """Get comprehensive information about extended hours trading."""

    now_et, tz_name = get_eastern_time()

    return f"""
Extended Hours Trading Information
=================================
Current Time: {now_et.strftime("%Y-%m-%d %H:%M:%S")} {tz_name}

Trading Sessions:
• Pre-market:  4:00 AM - 9:30 AM ET
• Regular:     9:30 AM - 4:00 PM ET
• After-hours: 4:00 PM - 8:00 PM ET
• Closed:      8:00 PM - 4:00 AM ET

Extended Hours Characteristics:
• Volume: 5-10% of regular session
• Spreads: 2-5x wider than regular hours
• Liquidity: Limited, especially for smaller stocks
• Volatility: Higher due to news reactions
• Order Types: Limit orders strongly recommended

Risks and Considerations:
• Price Gaps: Stocks can gap significantly at market open
• Limited Participants: Mainly institutional traders
• News Impact: Earnings and announcements cause volatility
• Execution: May take longer to fill orders
• Slippage: Higher likelihood of unfavorable fills

Best Practices:
• Use limit orders exclusively
• Start with small position sizes
• Monitor news and earnings calendars
• Set conservative price targets
• Avoid market orders completely
• Check recent volume before trading

Recommended Stocks for Extended Hours:
• High Volume: SPY, QQQ, AAPL, MSFT, TSLA
• ETFs: Generally better liquidity than individual stocks
• Large Cap: Better than small cap for extended hours
• Avoid: Penny stocks, low volume stocks, options

Order Flags:
• Set extended_hours=True for pre/post market
• Use time_in_force="day" (orders expire at market close)
• Consider "ioc" (immediate-or-cancel) for fast fills
    """
