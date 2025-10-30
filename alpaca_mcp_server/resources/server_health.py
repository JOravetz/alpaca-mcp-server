"""Server health monitoring resource."""

import os
import time
from datetime import datetime

import psutil

from ..config.settings import get_stock_historical_client, get_trading_client


async def get_server_health() -> dict:
    """Comprehensive server health monitoring with real system metrics."""
    try:
        process = psutil.Process(os.getpid())

        # Memory usage - actual process memory
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024

        # CPU usage - actual process CPU
        cpu_percent = process.cpu_percent(interval=0.1)

        # Process uptime
        create_time = process.create_time()
        uptime_seconds = int(time.time() - create_time)

        # System resources
        system_memory = psutil.virtual_memory()
        system_cpu = psutil.cpu_percent(interval=0.1)

        # Connection health tests
        connection_status = {}

        # Test trading API with timing
        try:
            start_time = time.time()
            client = get_trading_client()
            account = client.get_account()
            trading_latency = (time.time() - start_time) * 1000

            connection_status["trading_api"] = {
                "status": "connected",
                "account_id": account.id,  # type: ignore[union-attr]
                "account_status": account.status.value,  # type: ignore[union-attr]
                "response_time_ms": round(trading_latency, 1),
                "buying_power": float(account.buying_power or 0),  # type: ignore[union-attr]
                "cash": float(account.cash or 0),  # type: ignore[union-attr]
            }
        except Exception as e:
            connection_status["trading_api"] = {
                "status": "error",
                "error": str(e),
                "response_time_ms": None,
            }

        # Test market data API with timing
        try:
            start_time = time.time()
            data_client = get_stock_historical_client()
            from alpaca.data.requests import StockLatestQuoteRequest

            quote_request = StockLatestQuoteRequest(symbol_or_symbols="SPY")
            quotes = data_client.get_stock_latest_quote(quote_request)
            data_latency = (time.time() - start_time) * 1000

            if "SPY" in quotes:
                quote_data = quotes["SPY"]
                quote_age = datetime.now() - quote_data.timestamp.replace(tzinfo=None)

                connection_status["market_data_api"] = {
                    "status": "connected",
                    "response_time_ms": round(data_latency, 1),
                    "quote_age_seconds": round(quote_age.total_seconds(), 1),
                    "last_quote_time": quote_data.timestamp.isoformat(),
                    "last_price": float(quote_data.ask_price),
                }
            else:
                connection_status["market_data_api"] = {
                    "status": "no_data",
                    "response_time_ms": round(data_latency, 1),
                    "error": "No SPY quote data received",
                }
        except Exception as e:
            connection_status["market_data_api"] = {
                "status": "error",
                "error": str(e),
                "response_time_ms": None,
            }

        # Health assessment
        healthy_connections = sum(
            1 for conn in connection_status.values() if conn.get("status") == "connected"
        )
        total_connections = len(connection_status)

        # Overall health determination
        if healthy_connections == total_connections and memory_mb < 1000 and cpu_percent < 80:
            overall_status = "healthy"
        elif healthy_connections > 0 and memory_mb < 2000 and cpu_percent < 95:
            overall_status = "degraded"
        else:
            overall_status = "critical"

        # Performance recommendations
        recommendations = []
        if memory_mb > 1000:
            recommendations.append("High memory usage detected")
        if cpu_percent > 80:
            recommendations.append("High CPU usage detected")
        if healthy_connections < total_connections:
            recommendations.append("API connection issues detected")

        if not recommendations:
            recommendations.append("All systems operating normally")

        return {
            "server_status": overall_status,
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m",
            "process_metrics": {
                "memory_usage_mb": round(memory_mb, 1),
                "cpu_usage_percent": round(cpu_percent, 1),
                "pid": process.pid,
            },
            "system_metrics": {
                "system_memory_percent": round(system_memory.percent, 1),
                "system_cpu_percent": round(system_cpu, 1),
                "available_memory_gb": round(system_memory.available / 1024 / 1024 / 1024, 1),
            },
            "connection_health": {
                "healthy_connections": healthy_connections,
                "total_connections": total_connections,
                "connection_rate_percent": round(
                    (healthy_connections / total_connections) * 100, 1
                ),
                "details": connection_status,
            },
            "capabilities": {
                "tools": 41,  # Current count
                "resources": 11,  # Current count
                "prompts": 4,
            },
            "recommendations": recommendations,
            "last_check": datetime.now().isoformat(),
        }

    except Exception as e:
        return {
            "server_status": "error",
            "error": str(e),
            "last_check": datetime.now().isoformat(),
        }
