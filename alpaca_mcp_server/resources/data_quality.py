"""Data feed quality monitoring resource with configurable parameters."""

import time
from datetime import datetime

from alpaca.data.requests import StockLatestQuoteRequest

from ..config.settings import get_stock_historical_client


async def get_data_quality(
    test_symbols: list = None,
    latency_threshold_ms: float = 500.0,
    quote_age_threshold_seconds: float = 60.0,
    spread_threshold_pct: float = 1.0,
) -> dict:
    """Monitor actual data feed quality and latency with configurable parameters.

    Args:
        test_symbols: List of symbols to test (default: ["SPY", "QQQ", "AAPL"])
        latency_threshold_ms: Latency threshold in milliseconds for quality rating (default: 500.0)
        quote_age_threshold_seconds: Quote age threshold in seconds for freshness (default: 60.0)
        spread_threshold_pct: Bid-ask spread threshold as % of price for quality (default: 1.0)
    """
    try:
        data_client = get_stock_historical_client()

        # Use default symbols if none provided
        if test_symbols is None:
            test_symbols = ["SPY", "QQQ", "AAPL"]

        feed_status = {}
        latency_tests = []

        for symbol in test_symbols:
            start_time = time.time()

            try:
                request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
                quote = data_client.get_stock_latest_quote(request)

                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                latency_tests.append(latency_ms)

                if symbol in quote:
                    quote_data = quote[symbol]
                    quote_age = datetime.now() - quote_data.timestamp.replace(tzinfo=None)
                    quote_age_seconds = quote_age.total_seconds()

                    # Calculate bid-ask spread
                    bid_price = float(quote_data.bid_price)
                    ask_price = float(quote_data.ask_price)
                    spread = ask_price - bid_price
                    mid_price = (bid_price + ask_price) / 2
                    spread_pct = (spread / mid_price * 100) if mid_price > 0 else 0

                    # Determine quality metrics
                    latency_quality = (
                        "excellent"
                        if latency_ms < latency_threshold_ms * 0.2
                        else (
                            "good"
                            if latency_ms < latency_threshold_ms * 0.5
                            else "fair" if latency_ms < latency_threshold_ms else "poor"
                        )
                    )

                    freshness_quality = (
                        "excellent"
                        if quote_age_seconds < quote_age_threshold_seconds * 0.1
                        else (
                            "good"
                            if quote_age_seconds < quote_age_threshold_seconds * 0.5
                            else (
                                "fair"
                                if quote_age_seconds < quote_age_threshold_seconds
                                else "poor"
                            )
                        )
                    )

                    spread_quality = (
                        "excellent"
                        if spread_pct < spread_threshold_pct * 0.1
                        else (
                            "good"
                            if spread_pct < spread_threshold_pct * 0.5
                            else "fair" if spread_pct < spread_threshold_pct else "poor"
                        )
                    )

                    # Overall quality score (0-100)
                    quality_scores = {
                        "excellent": 100,
                        "good": 75,
                        "fair": 50,
                        "poor": 25,
                    }

                    overall_score = (
                        quality_scores[latency_quality]
                        + quality_scores[freshness_quality]
                        + quality_scores[spread_quality]
                    ) / 3

                    overall_quality = (
                        "excellent"
                        if overall_score >= 90
                        else (
                            "good"
                            if overall_score >= 70
                            else "fair" if overall_score >= 50 else "poor"
                        )
                    )

                    feed_status[symbol] = {
                        "status": "connected",
                        "overall_quality": overall_quality,
                        "overall_score": round(overall_score, 1),
                        "latency_ms": round(latency_ms, 1),
                        "latency_quality": latency_quality,
                        "quote_age_seconds": round(quote_age_seconds, 1),
                        "freshness_quality": freshness_quality,
                        "last_quote_time": quote_data.timestamp.isoformat(),
                        "bid_price": bid_price,
                        "ask_price": ask_price,
                        "bid_ask_spread": round(spread, 4),
                        "spread_pct": round(spread_pct, 4),
                        "spread_quality": spread_quality,
                        "bid_size": int(quote_data.bid_size),
                        "ask_size": int(quote_data.ask_size),
                    }
                else:
                    feed_status[symbol] = {
                        "status": "no_data",
                        "overall_quality": "poor",
                        "overall_score": 0,
                        "latency_ms": round(latency_ms, 1),
                        "error": "No quote data received",
                    }

            except Exception as e:
                feed_status[symbol] = {
                    "status": "error",
                    "overall_quality": "poor",
                    "overall_score": 0,
                    "error": str(e),
                }

        # Calculate aggregate metrics
        connected_feeds = sum(
            1 for status in feed_status.values() if status.get("status") == "connected"
        )
        total_feeds = len(test_symbols)
        connection_rate = (connected_feeds / total_feeds * 100) if total_feeds > 0 else 0

        if latency_tests:
            avg_latency = sum(latency_tests) / len(latency_tests)
            max_latency = max(latency_tests)
            min_latency = min(latency_tests)
        else:
            avg_latency = max_latency = min_latency = 0

        # Calculate overall feed health
        connected_qualities = [
            status.get("overall_score", 0)
            for status in feed_status.values()
            if status.get("status") == "connected"
        ]

        if connected_qualities:
            avg_quality_score = sum(connected_qualities) / len(connected_qualities)
        else:
            avg_quality_score = 0

        # Determine overall system quality
        if connection_rate >= 95 and avg_quality_score >= 90:
            system_quality = "excellent"
        elif connection_rate >= 90 and avg_quality_score >= 70:
            system_quality = "good"
        elif connection_rate >= 70 and avg_quality_score >= 50:
            system_quality = "fair"
        else:
            system_quality = "poor"

        # Generate recommendations
        recommendations = []
        if avg_latency > latency_threshold_ms:
            recommendations.append("High latency detected - check network connection")
        if connection_rate < 90:
            recommendations.append("Feed connection issues - verify API credentials")
        if avg_quality_score < 70:
            recommendations.append("Data quality degraded - consider using alternative feeds")

        if not recommendations:
            recommendations.append("All systems operating normally")

        return {
            "system_quality": system_quality,
            "overall_score": round(avg_quality_score, 1),
            "connection_rate_pct": round(connection_rate, 1),
            "connected_feeds": connected_feeds,
            "total_feeds": total_feeds,
            "latency_stats": {
                "average_ms": round(avg_latency, 1),
                "minimum_ms": round(min_latency, 1),
                "maximum_ms": round(max_latency, 1),
            },
            "feed_details": feed_status,
            "recommendations": recommendations,
            "thresholds": {
                "latency_threshold_ms": latency_threshold_ms,
                "quote_age_threshold_seconds": quote_age_threshold_seconds,
                "spread_threshold_pct": spread_threshold_pct,
            },
            "parameters": {
                "test_symbols": test_symbols,
                "latency_threshold_ms": latency_threshold_ms,
                "quote_age_threshold_seconds": quote_age_threshold_seconds,
                "spread_threshold_pct": spread_threshold_pct,
            },
            "last_check": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "error": str(e),
            "system_quality": "error",
            "overall_score": 0,
            "parameters": {
                "test_symbols": test_symbols or ["SPY", "QQQ", "AAPL"],
                "latency_threshold_ms": latency_threshold_ms,
                "quote_age_threshold_seconds": quote_age_threshold_seconds,
                "spread_threshold_pct": spread_threshold_pct,
            },
            "last_check": datetime.now().isoformat(),
        }
