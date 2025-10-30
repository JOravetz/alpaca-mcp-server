"""API connection monitoring resource."""

import time
from datetime import datetime

from ..config.settings import get_stock_historical_client, get_trading_client


async def get_api_status() -> dict:
    """Monitor API connections and performance with detailed metrics."""
    try:
        results = {}

        # Test trading API with comprehensive metrics
        start_time = time.time()
        try:
            client = get_trading_client()
            account = client.get_account()
            trading_latency = (time.time() - start_time) * 1000

            # Get additional trading API metrics
            try:
                positions = client.get_all_positions()
                positions_count = len(positions)
            except Exception:
                positions_count = None

            results["trading_api"] = {
                "status": "connected",
                "latency_ms": round(trading_latency, 1),
                "account_id": account.id,  # type: ignore[union-attr]
                "account_status": account.status.value,  # type: ignore[union-attr]
                "buying_power": float(account.buying_power),  # type: ignore[arg-type,union-attr]
                "cash": float(account.cash),  # type: ignore[arg-type,union-attr]
                "portfolio_value": float(account.portfolio_value),  # type: ignore[arg-type,union-attr]
                "positions_count": positions_count,
                "pattern_day_trader": account.pattern_day_trader,  # type: ignore[union-attr]
                "last_test": datetime.now().isoformat(),
            }
        except Exception as e:
            results["trading_api"] = {
                "status": "error",
                "error": str(e),
                "latency_ms": None,
                "last_test": datetime.now().isoformat(),
            }

        # Test market data API with multiple symbols
        test_symbols = ["SPY", "QQQ", "AAPL"]
        market_data_results = {}

        for symbol in test_symbols:
            start_time = time.time()
            try:
                data_client = get_stock_historical_client()
                from alpaca.data.requests import StockLatestQuoteRequest

                quote_request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
                quotes = data_client.get_stock_latest_quote(quote_request)
                data_latency = (time.time() - start_time) * 1000

                if symbol in quotes:
                    quote_data = quotes[symbol]
                    quote_age = datetime.now() - quote_data.timestamp.replace(tzinfo=None)

                    # Calculate bid-ask spread
                    bid_price = float(quote_data.bid_price)
                    ask_price = float(quote_data.ask_price)
                    spread = ask_price - bid_price
                    mid_price = (bid_price + ask_price) / 2
                    spread_pct = (spread / mid_price * 100) if mid_price > 0 else 0

                    market_data_results[symbol] = {
                        "status": "connected",
                        "latency_ms": round(data_latency, 1),
                        "quote_age_seconds": round(quote_age.total_seconds(), 1),
                        "last_quote_time": quote_data.timestamp.isoformat(),
                        "bid_price": bid_price,
                        "ask_price": ask_price,
                        "spread": round(spread, 4),
                        "spread_pct": round(spread_pct, 4),
                        "bid_size": int(quote_data.bid_size),
                        "ask_size": int(quote_data.ask_size),
                    }
                else:
                    market_data_results[symbol] = {
                        "status": "no_data",
                        "latency_ms": round(data_latency, 1),
                        "error": "No quote data received",
                    }

            except Exception as e:
                market_data_results[symbol] = {
                    "status": "error",
                    "error": str(e),
                    "latency_ms": None,
                }

        # Aggregate market data API status
        successful_symbols = sum(
            1 for result in market_data_results.values() if result.get("status") == "connected"
        )
        total_symbols = len(test_symbols)

        if successful_symbols == total_symbols:
            market_data_status = "connected"
            avg_latency = (
                sum(result.get("latency_ms", 0) for result in market_data_results.values())  # type: ignore[misc]
                / total_symbols
            )
        elif successful_symbols > 0:
            market_data_status = "partial"
            successful_latencies = [
                result.get("latency_ms", 0)
                for result in market_data_results.values()
                if result.get("status") == "connected"
            ]
            avg_latency = (
                sum(successful_latencies) / len(successful_latencies) if successful_latencies else 0  # type: ignore[arg-type]
            )
        else:
            market_data_status = "error"
            avg_latency = 0

        results["market_data_api"] = {
            "status": market_data_status,
            "average_latency_ms": round(avg_latency, 1),
            "successful_symbols": successful_symbols,
            "total_symbols": total_symbols,
            "success_rate_pct": round((successful_symbols / total_symbols) * 100, 1),
            "symbol_details": market_data_results,
            "last_test": datetime.now().isoformat(),
        }

        # Overall health assessment
        trading_healthy = results["trading_api"].get("status") == "connected"
        market_data_healthy = market_data_status in ["connected", "partial"]

        if trading_healthy and market_data_healthy:
            overall_status = "healthy"
        elif trading_healthy or market_data_healthy:
            overall_status = "degraded"
        else:
            overall_status = "failed"

        # Performance assessment
        performance_issues = []
        if results["trading_api"].get("latency_ms", 0) > 1000:
            performance_issues.append("High trading API latency")
        if avg_latency > 500:
            performance_issues.append("High market data API latency")
        if successful_symbols < total_symbols:
            performance_issues.append("Market data feed inconsistency")

        # Recommendations
        recommendations = []
        if not trading_healthy:
            recommendations.append("Check trading API credentials and permissions")
        if not market_data_healthy:
            recommendations.append("Verify market data feed subscription")
        if performance_issues:
            recommendations.extend(performance_issues)

        if not recommendations:
            recommendations.append("All API connections operating normally")

        return {
            "overall_status": overall_status,
            "healthy_apis": sum([trading_healthy, market_data_healthy]),
            "total_apis": 2,
            "performance_issues": performance_issues,
            "recommendations": recommendations,
            "api_details": results,
            "test_summary": {
                "trading_api_latency_ms": results["trading_api"].get("latency_ms"),
                "market_data_avg_latency_ms": round(avg_latency, 1),
                "market_data_success_rate": round((successful_symbols / total_symbols) * 100, 1),
            },
            "last_check": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "error": str(e),
            "overall_status": "error",
            "healthy_apis": 0,
            "total_apis": 2,
            "last_check": datetime.now().isoformat(),
        }
