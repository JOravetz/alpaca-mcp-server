"""FastAPI Monitoring Tools

MCP tools for interacting with the FastAPI-based monitoring service.
Provides HTTP-based communication with the persistent monitoring service.
"""

import asyncio
import json
import logging
from datetime import UTC

import aiohttp

logger = logging.getLogger(__name__)

# Service configuration
SERVICE_BASE_URL = "http://localhost:8001"
SERVICE_TIMEOUT = 10  # seconds


class FastAPIMonitoringClient:
    """Client for communicating with FastAPI monitoring service"""

    def __init__(self, base_url: str = SERVICE_BASE_URL):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=SERVICE_TIMEOUT)

    async def _make_request(self, method: str, endpoint: str, data: dict | None = None) -> dict:
        """Make HTTP request to monitoring service"""
        url = f"{self.base_url}{endpoint}"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                if method.upper() == "GET":
                    async with session.get(url) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            return {
                                "status": "error",
                                "message": f"HTTP {response.status}: {error_text}",
                                "endpoint": endpoint,
                            }

                elif method.upper() == "POST":
                    headers = {"Content-Type": "application/json"}
                    json_data = json.dumps(data) if data else None

                    async with session.post(url, data=json_data, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            return {
                                "status": "error",
                                "message": f"HTTP {response.status}: {error_text}",
                                "endpoint": endpoint,
                            }

        except aiohttp.ClientConnectorError:
            return {
                "status": "error",
                "message": "Connection failed - monitoring service may not be running",
                "endpoint": endpoint,
                "hint": "Start the service with: ./scripts/start_monitoring_service.sh",
            }

        except TimeoutError:
            return {
                "status": "error",
                "message": f"Request timeout after {SERVICE_TIMEOUT}s",
                "endpoint": endpoint,
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "endpoint": endpoint,
            }


# Global client instance
client = FastAPIMonitoringClient()


async def ping_fastapi_monitoring_service() -> dict:
    """
    Ping the FastAPI monitoring service to verify it's alive and responsive.
    Returns comprehensive health metrics including uptime, response time, and monitoring status.
    """
    response = await client._make_request("GET", "/health")

    if response.get("status") == "error":
        return {
            "status": "error",
            "service_available": False,
            "message": response.get("message", "Unknown error"),
            "response_time_ms": None,
            "hint": "Use ./scripts/start_monitoring_service.sh to start the service",
        }

    return {
        "status": "success",
        "service_available": True,
        "health_data": response,
        "monitoring_active": response.get("status") == "healthy",
        "uptime_seconds": response.get("uptime_seconds", 0),
        "check_count": response.get("check_count", 0),
        "watchlist_size": response.get("watchlist_size", 0),
        "active_positions": response.get("active_positions", 0),
    }


async def get_fastapi_monitoring_status() -> dict:
    """
    Get comprehensive status from the FastAPI monitoring service.
    Returns detailed information about service health, watchlist, positions, and signals.
    """
    response = await client._make_request("GET", "/status")

    if response.get("status") == "error":
        return {
            "status": "error",
            "message": response.get("message", "Failed to get status"),
            "service_available": False,
        }

    return {"status": "success", "service_available": True, "monitoring_status": response}


async def get_current_watchlist() -> dict:
    """
    Get the current watchlist from the live FastAPI monitoring service.
    This queries the actual running service, not just state files.
    """
    response = await client._make_request("GET", "/watchlist")

    if response.get("status") == "error":
        return {
            "status": "error",
            "message": response.get("message", "Failed to get watchlist"),
            "watchlist": [],
            "monitoring_active": False,
        }

    return {
        "status": "success",
        "watchlist": response.get("watchlist", []),
        "watchlist_size": response.get("size", 0),
        "limit": response.get("limit", 0),
        "last_updated": response.get("last_updated"),
        "monitoring_active": True,
    }


async def add_symbols_to_fastapi_watchlist(symbols: list[str]) -> dict:
    """
    Add symbols to the FastAPI monitoring service watchlist.

    Args:
        symbols: List of stock symbols to add to monitoring

    Returns:
        Dict with operation results and updated watchlist
    """
    data = {"symbols": symbols}
    response = await client._make_request("POST", "/watchlist/add", data)

    if response.get("status") == "error":
        return {
            "status": "error",
            "message": response.get("message", "Failed to add symbols"),
            "added": [],
            "watchlist_size": 0,
        }

    return response


async def remove_symbols_from_fastapi_watchlist(symbols: list[str]) -> dict:
    """
    Remove symbols from the FastAPI monitoring service watchlist.

    Args:
        symbols: List of stock symbols to remove from monitoring

    Returns:
        Dict with operation results and updated watchlist
    """
    data = {"symbols": symbols}
    response = await client._make_request("POST", "/watchlist/remove", data)

    if response.get("status") == "error":
        return {
            "status": "error",
            "message": response.get("message", "Failed to remove symbols"),
            "removed": [],
            "watchlist_size": 0,
        }

    return response


async def get_fastapi_positions() -> dict:
    """
    Get current positions from the FastAPI monitoring service.
    Returns live position data with profit/loss information.
    """
    response = await client._make_request("GET", "/positions")

    if response.get("status") == "error":
        return {
            "status": "error",
            "message": response.get("message", "Failed to get positions"),
            "positions": [],
            "count": 0,
        }

    return {
        "status": "success",
        "positions": response.get("positions", []),
        "position_count": response.get("count", 0),
        "total_market_value": response.get("total_market_value", 0),
        "total_unrealized_pl": response.get("total_unrealized_pl", 0),
    }


async def check_positions_after_order_fastapi(order_info: dict | None = None) -> dict:
    """
    Check positions immediately after an order using the FastAPI service.

    Args:
        order_info: Optional order information for tracking

    Returns:
        Dict with current position status
    """
    data = {"order_info": order_info} if order_info else {}
    response = await client._make_request("POST", "/positions/check", data)

    if response.get("status") == "error":
        return {
            "status": "error",
            "message": response.get("message", "Failed to check positions"),
            "position_count": 0,
            "positions": [],
        }

    return response


async def get_fastapi_signals() -> dict:
    """
    Get current trading signals from the FastAPI monitoring service.
    Returns active signals detected by the monitoring system.
    """
    response = await client._make_request("GET", "/signals")

    if response.get("status") == "error":
        return {
            "status": "error",
            "message": response.get("message", "Failed to get signals"),
            "signals": [],
            "signal_count": 0,
        }

    return {
        "status": "success",
        "current_signals": response.get("current_signals", []),
        "signal_count": response.get("signal_count", 0),
        "last_updated": response.get("last_updated"),
    }


async def start_fastapi_monitoring_service() -> dict:
    """
    Start the FastAPI monitoring service.
    Creates a persistent HTTP-based monitoring service with REST endpoints.

    IMPORTANT: Only starts during trading hours or market sessions.
    Prevents unnecessary resource usage during weekends/holidays.
    """
    import subprocess
    from datetime import datetime, time, timedelta, timezone

    # MARKET VALIDATION: Check if markets are open or in any trading session
    try:
        # Get current Eastern time
        utc_now = datetime.now(UTC)
        month = utc_now.month
        if 3 <= month <= 11:  # EDT
            eastern = timezone(timedelta(hours=-4))
        else:  # EST
            eastern = timezone(timedelta(hours=-5))
        now_et = utc_now.astimezone(eastern)
        current_time = now_et.time()

        # Define trading sessions (same logic as enhanced_market_clock)
        premarket_start = time(4, 0)  # 4:00 AM
        postmarket_end = time(20, 0)  # 8:00 PM

        # Allow service during any trading session (pre-market, regular, post-market)
        is_trading_session = premarket_start <= current_time < postmarket_end

        if not is_trading_session:
            return {
                "status": "blocked",
                "message": "FastAPI monitoring service blocked - outside trading hours",
                "reason": "Service only runs during pre-market (4 AM), regular (9:30 AM-4 PM), or after-hours (4-8 PM) ET",
                "service_available": False,
                "recommendation": "Start service during pre-market (4:00 AM), regular hours (9:30 AM-4:00 PM), or after-hours (4:00-8:00 PM) ET",
                "current_time_et": now_et.strftime("%Y-%m-%d %H:%M:%S EDT"),
                "trading_window": "4:00 AM - 8:00 PM ET",
            }

    except Exception as e:
        logger.warning(f"Could not verify market status: {e}")
        # Continue with startup if market check fails
        pass

    # First check if service is already running
    health_check = await ping_fastapi_monitoring_service()
    if health_check.get("service_available"):
        return {
            "status": "success",
            "message": "Service already running - Dashboard available at http://localhost:8001/status/html",
            "service_available": True,
            "dashboard_url": "http://localhost:8001/status/html",
            "health_data": health_check.get("health_data", {}),
        }

    try:
        # Start the service using the script
        script_path = "./scripts/start_monitoring_service.sh"
        result = subprocess.run([script_path], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return {
                "status": "error",
                "message": f"Failed to start service: {result.stderr}",
                "service_available": False,
            }

        # Wait for service to become available
        for attempt in range(10):  # Wait up to 10 seconds
            await asyncio.sleep(1)
            health_check = await ping_fastapi_monitoring_service()
            if health_check.get("service_available"):
                # Auto-open HTML dashboard in browser
                try:
                    import os
                    import subprocess
                    import webbrowser

                    dashboard_url = "http://localhost:8001/status/html"

                    # Try chromium first (user preference), then webbrowser module
                    browser_opened = False
                    try:
                        result = subprocess.run(
                            ["chromium", dashboard_url], capture_output=True, check=False, timeout=5
                        )
                        if result.returncode == 0:
                            browser_opened = True
                    except (subprocess.TimeoutExpired, FileNotFoundError):
                        pass

                    # Fallback to webbrowser module if chromium failed
                    if not browser_opened:
                        try:
                            webbrowser.open(dashboard_url)
                            browser_opened = True
                        except Exception:
                            pass

                    # Last resort - system specific commands
                    if not browser_opened:
                        try:
                            if os.name == "posix":  # Linux/Unix
                                subprocess.run(
                                    ["xdg-open", dashboard_url], capture_output=True, check=False
                                )
                            elif os.name == "nt":  # Windows
                                subprocess.run(
                                    ["start", dashboard_url],
                                    shell=True,
                                    capture_output=True,
                                    check=False,
                                )
                            elif os.name == "mac":  # macOS
                                subprocess.run(
                                    ["open", dashboard_url], capture_output=True, check=False
                                )
                        except Exception:
                            pass
                except Exception as e:
                    logger.debug(f"Failed to open browser: {e}")
                    pass  # Ignore browser open failures

                return {
                    "status": "success",
                    "message": "Service started successfully - HTML dashboard opened in browser",
                    "service_available": True,
                    "startup_time_seconds": attempt + 1,
                    "dashboard_url": "http://localhost:8001/status/html",
                    "health_data": health_check.get("health_data", {}),
                }

        return {
            "status": "error",
            "message": "Service started but not responding to health checks",
            "service_available": False,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Service startup timed out",
            "service_available": False,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to start service: {str(e)}",
            "service_available": False,
        }


async def stop_fastapi_monitoring_service() -> dict:
    """
    Stop the FastAPI monitoring service gracefully.
    """
    import subprocess

    try:
        # Stop the service using the script
        script_path = "./scripts/stop_monitoring_service.sh"
        result = subprocess.run([script_path], capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return {
                "status": "error",
                "message": f"Failed to stop service: {result.stderr}",
                "details": result.stdout,
            }

        # Verify service is stopped
        health_check = await ping_fastapi_monitoring_service()
        service_stopped = not health_check.get("service_available", True)

        return {
            "status": "success" if service_stopped else "warning",
            "message": (
                "Service stopped successfully"
                if service_stopped
                else "Service may still be running"
            ),
            "service_available": not service_stopped,
            "stop_output": result.stdout,
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Service shutdown timed out",
            "service_available": True,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to stop service: {str(e)}",
            "service_available": True,
        }


# Backward compatibility - these functions provide the same interface as the old tools
# but use the FastAPI service instead of the direct asyncio service


async def get_hybrid_monitoring_status() -> dict:
    """Get comprehensive monitoring status (backward compatibility)"""
    return await get_fastapi_monitoring_status()


async def start_hybrid_monitoring(symbols: list[str] | None = None) -> dict:
    """Start monitoring service with optional symbols (backward compatibility)

    IMPORTANT: Only starts during trading hours or market sessions.
    """
    # Start the service (includes market validation)
    start_result = await start_fastapi_monitoring_service()

    if start_result.get("status") in ["error", "blocked"]:
        return start_result

    # Add symbols if provided
    if symbols:
        add_result = await add_symbols_to_fastapi_watchlist(symbols)
        return {
            **start_result,
            "symbols_added": add_result.get("added", []),
            "watchlist_size": add_result.get("watchlist_size", 0),
        }

    return start_result


async def stop_hybrid_monitoring() -> dict:
    """Stop monitoring service (backward compatibility)"""
    return await stop_fastapi_monitoring_service()


async def add_symbols_to_watchlist(symbols: list[str]) -> dict:
    """Add symbols to watchlist (backward compatibility)"""
    return await add_symbols_to_fastapi_watchlist(symbols)


async def remove_symbols_from_watchlist(symbols: list[str]) -> dict:
    """Remove symbols from watchlist (backward compatibility)"""
    return await remove_symbols_from_fastapi_watchlist(symbols)


async def check_positions_after_order(order_info: dict | None = None) -> dict:
    """Check positions after order (backward compatibility)"""
    return await check_positions_after_order_fastapi(order_info)


async def ping_monitoring_service() -> dict:
    """Ping monitoring service (backward compatibility)"""
    return await ping_fastapi_monitoring_service()
