"""Streaming resources implementation."""

import sys
from datetime import datetime
from typing import Any

# Get the actual module from sys.modules to avoid the Settings instance shadowing
_settings_module = sys.modules["alpaca_mcp_server.config.settings"]


async def get_stream_status() -> dict:
    """Real-time streaming status and buffer statistics."""
    try:
        # Check if streaming is active
        if not _settings_module._stock_stream_active:
            return {
                "status": "inactive",
                "streams_active": 0,
                "buffer_stats": {},
                "last_updated": datetime.now().isoformat(),
            }

        # Get all subscribed symbols
        all_symbols = set()
        for symbol_set in _settings_module._stock_stream_subscriptions.values():
            all_symbols.update(symbol_set)

        # Get buffer statistics
        buffer_stats = {}
        total_messages = 0

        # Group buffers by symbol
        symbol_buffers: dict[str, dict[str, Any]] = {}
        for buffer_key, buffer in _settings_module._stock_data_buffers.items():
            symbol, data_type = buffer_key.rsplit("_", 1)
            if symbol not in symbol_buffers:
                symbol_buffers[symbol] = {}
            symbol_buffers[symbol][data_type] = buffer

        for symbol, buffers in symbol_buffers.items():
            symbol_stats = {}
            symbol_total = 0

            for data_type, buffer in buffers.items():
                buffer_size = len(buffer.get_all())
                stats = buffer.get_stats()
                symbol_stats[data_type] = {
                    "buffer_size": buffer_size,
                    "last_update": (
                        datetime.fromtimestamp(stats["last_update"]).isoformat()
                        if stats["last_update"]
                        else None
                    ),
                }
                symbol_total += buffer_size

            buffer_stats[symbol] = {
                "data_types": symbol_stats,
                "total_messages": symbol_total,
            }
            total_messages += symbol_total

        # Calculate runtime
        runtime_seconds = (
            datetime.now().timestamp() - _settings_module._stock_stream_start_time
            if _settings_module._stock_stream_start_time
            else 0
        )

        return {
            "status": "active",
            "streams_active": len(all_symbols),
            "subscribed_symbols": list(all_symbols),
            "total_messages_buffered": total_messages,
            "buffer_stats": buffer_stats,
            "stream_duration_seconds": runtime_seconds,
            "feed_type": _settings_module._stock_stream_config.get("feed", "unknown"),
            "configured_duration": _settings_module._stock_stream_config.get("duration_seconds"),
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error",
            "streams_active": 0,
            "last_updated": datetime.now().isoformat(),
        }


async def get_stream_health_monitor() -> dict:
    """Enhanced stream health monitoring for single-stream architecture reliability."""
    try:
        if not _settings_module._stock_stream_active:
            return {
                "health_status": "inactive",
                "stream_reliability": "standby",
                "critical_alerts": [],
                "recommendations": ["Start streaming with start_global_stock_stream()"],
                "last_updated": datetime.now().isoformat(),
            }

        # Critical health metrics for single stream
        current_time = datetime.now().timestamp()
        stream_age = current_time - _settings_module._stock_stream_start_time

        # Check for data staleness (critical for trading)
        freshest_data_time = 0
        stale_symbols = []
        healthy_symbols = []

        for buffer_key, buffer in _settings_module._stock_data_buffers.items():
            symbol, data_type = buffer_key.rsplit("_", 1)
            stats = buffer.get_stats()

            if stats["last_update"]:
                data_age = current_time - stats["last_update"]
                freshest_data_time = max(freshest_data_time, stats["last_update"])

                if data_age > 30:  # Stale if >30 seconds old
                    stale_symbols.append(f"{symbol}_{data_type}")
                else:
                    healthy_symbols.append(f"{symbol}_{data_type}")

        # Overall stream latency
        overall_latency = (
            current_time - freshest_data_time if freshest_data_time > 0 else float("inf")
        )

        # Health assessment
        critical_alerts = []
        health_status = "healthy"

        if overall_latency > 60:
            critical_alerts.append("CRITICAL: No data received in 60+ seconds")
            health_status = "critical"
        elif overall_latency > 30:
            critical_alerts.append("WARNING: Data latency >30 seconds")
            health_status = "degraded"
        elif len(stale_symbols) > len(healthy_symbols):
            critical_alerts.append("WARNING: More stale buffers than fresh")
            health_status = "degraded"

        # Event rate analysis
        total_events = sum(_settings_module._stock_stream_stats.values())
        events_per_second = total_events / stream_age if stream_age > 0 else 0

        if events_per_second < 0.1:  # Very low activity
            critical_alerts.append("Low activity: <0.1 events/second")

        # Recommendations
        recommendations = []
        if health_status == "critical":
            recommendations.extend(
                [
                    "IMMEDIATE: Restart stream with start_global_stock_stream()",
                    "Check network connectivity",
                    "Verify API credentials",
                ]
            )
        elif health_status == "degraded":
            recommendations.extend(
                [
                    "Monitor stream performance closely",
                    "Consider restarting if issues persist",
                    "Check symbol liquidity during market hours",
                ]
            )
        else:
            recommendations.append("Stream operating normally")

        return {
            "health_status": health_status,
            "stream_reliability": "excellent" if health_status == "healthy" else "compromised",
            "overall_latency_seconds": round(overall_latency, 2),
            "stream_age_minutes": round(stream_age / 60, 2),
            "events_per_second": round(events_per_second, 2),
            "healthy_buffers": len(healthy_symbols),
            "stale_buffers": len(stale_symbols),
            "total_events_processed": total_events,
            "critical_alerts": critical_alerts,
            "recommendations": recommendations,
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "error": str(e),
            "health_status": "error",
            "stream_reliability": "unknown",
            "critical_alerts": [f"Health monitoring error: {str(e)}"],
            "last_updated": datetime.now().isoformat(),
        }


async def get_stream_performance() -> dict:
    """Streaming performance metrics and health indicators."""
    try:
        if not _settings_module._stock_stream_active:
            return {
                "status": "unavailable",
                "performance": "idle",
                "last_updated": datetime.now().isoformat(),
            }

        # Get all subscribed symbols
        all_symbols = set()
        for symbol_set in _settings_module._stock_stream_subscriptions.values():
            all_symbols.update(symbol_set)

        # Calculate performance metrics
        total_symbols = len(all_symbols)
        total_buffers = len(_settings_module._stock_data_buffers)
        total_messages = sum(
            len(buffer.get_all()) for buffer in _settings_module._stock_data_buffers.values()
        )

        # Estimate memory usage (rough calculation)
        estimated_memory_mb = total_messages * 0.0002  # ~200 bytes per message estimate

        # Calculate event rates
        runtime_seconds = (
            datetime.now().timestamp() - _settings_module._stock_stream_start_time
            if _settings_module._stock_stream_start_time
            else 1
        )
        events_per_second = (
            sum(_settings_module._stock_stream_stats.values()) / runtime_seconds
            if runtime_seconds > 0
            else 0
        )

        # Performance assessment
        if total_symbols == 0:
            performance_level = "idle"
        elif total_symbols <= 10 and estimated_memory_mb < 50 and events_per_second < 100:
            performance_level = "optimal"
        elif total_symbols <= 50 and estimated_memory_mb < 200 and events_per_second < 500:
            performance_level = "good"
        else:
            performance_level = "heavy"

        return {
            "status": "active",
            "performance_level": performance_level,
            "total_symbols_streaming": total_symbols,
            "total_buffers": total_buffers,
            "total_messages_buffered": total_messages,
            "events_per_second": round(events_per_second, 2),
            "estimated_memory_usage_mb": round(estimated_memory_mb, 2),
            "runtime_minutes": round(runtime_seconds / 60, 2),
            "recommended_action": {
                "idle": "Ready to start streaming",
                "optimal": "Performance is excellent",
                "good": "Performance is good",
                "heavy": "Consider reducing symbols or clearing buffers",
            }.get(performance_level, "Monitor performance"),
            "last_updated": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "error",
            "performance_level": "unknown",
            "last_updated": datetime.now().isoformat(),
        }
