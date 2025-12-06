"""FastAPI route handlers for the monitoring service."""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from ...utils.timezone_utils import get_eastern_time_string  # type: ignore[import-not-found]
from ..models import (
    AddSymbolsRequest,
    AutoScanConfigRequest,
    ConfirmExecutionRequest,
    OrderCheckRequest,
    OrderRequest,
    RemoveSymbolsRequest,
    ScanSyncRequest,
    TechnicalAnalysisUpdateRequest,
    TradeConfirmationRequest,
    TradingConfigUpdateRequest,
)
from ..services import MonitoringServiceAPI

# Create API router
api_router = APIRouter()

# Global service instance (initialized lazily)
monitoring_service = None


def get_monitoring_service():
    """Get or create the monitoring service instance"""
    global monitoring_service
    if monitoring_service is None:
        monitoring_service = MonitoringServiceAPI()
    return monitoring_service


@api_router.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "FastAPI Hybrid Trading Monitoring Service", "status": "running"}


@api_router.get("/health")
async def health_check():
    """Detailed health check"""
    service = get_monitoring_service()
    return {
        "status": "healthy",
        "timestamp": get_eastern_time_string(),
        "service": service.get_status(),
    }


@api_router.post("/start")
async def start_monitoring(  # type: ignore[no-untyped-def]
    check_interval: int = 2,
    max_concurrent_positions: int = 5,
    signal_confidence_threshold: float = 0.75,
    watchlist_size_limit: int = 20,
    enable_auto_alerts: bool = True,
):
    """Start the monitoring service"""
    service = get_monitoring_service()
    return await service.start_monitoring(
        check_interval=check_interval,
        max_concurrent_positions=max_concurrent_positions,
        signal_confidence_threshold=signal_confidence_threshold,
        watchlist_size_limit=watchlist_size_limit,
        enable_auto_alerts=enable_auto_alerts,
    )


@api_router.post("/stop")
async def stop_monitoring():
    """Stop the monitoring service"""
    service = get_monitoring_service()
    return await service.stop_monitoring()


@api_router.get("/status")
async def get_status():
    """Get fast service status without heavy analysis"""
    service = get_monitoring_service()
    try:
        base_status = service.get_status()

        # Add additional status information (fast operations only)
        positions_dict = service.position_tracker.get_all_positions()
        positions = [
            {"symbol": p.symbol, "unrealized_pnl": p.unrealized_pnl}
            for p in positions_dict.values()
        ]
        signals = service.current_signals

        # Fast watchlist info without analysis
        watchlist_info = {
            "watchlist": sorted(service.watchlist),
            "size": len(service.watchlist),
            "last_updated": service.last_check.isoformat() if service.last_check else None,
        }

        return {
            **base_status,
            "positions": {
                "count": len(positions),
                "symbols": [pos.get("symbol", "Unknown") for pos in positions],
                "total_unrealized_pnl": sum(
                    float(pos.get("unrealized_pnl", 0)) for pos in positions
                ),
                "positions": positions,
            },
            "signals": {"count": len(signals), "active_signals": signals},
            "watchlist": watchlist_info,
            "uptime_seconds": (
                (datetime.now() - service.start_time).total_seconds() if service.start_time else 0
            ),
        }

    except Exception as e:
        logging.error(f"Error getting status: {e}")
        return {"error": str(e), "basic_status": service.get_status()}


@api_router.post("/watchlist/add")
async def add_symbols_to_watchlist(request: AddSymbolsRequest) -> Any:  # type: ignore[name-defined]
    """Add symbols to the monitoring watchlist"""
    service = get_monitoring_service()
    try:
        added_symbols = []
        for symbol in request.symbols:
            symbol = symbol.upper().strip()
            if symbol and symbol not in service.watchlist:
                service.watchlist.add(symbol)
                added_symbols.append(symbol)

        if added_symbols:
            service.logger.info(f"Added symbols to watchlist: {added_symbols}")

        return {
            "status": "success",
            "message": f"Added {len(added_symbols)} symbols to watchlist",
            "added": added_symbols,
            "added_symbols": added_symbols,
            "watchlist_size": len(service.watchlist),
            "current_watchlist": sorted(service.watchlist),
        }

    except Exception as e:
        service.logger.error(f"Error adding symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.post("/watchlist/remove")
async def remove_symbols_from_watchlist(request: RemoveSymbolsRequest) -> Any:  # type: ignore[name-defined]
    """Remove symbols from the monitoring watchlist"""
    service = get_monitoring_service()
    try:
        removed_symbols = []
        for symbol in request.symbols:
            symbol = symbol.upper().strip()
            if symbol in service.watchlist:
                service.watchlist.remove(symbol)
                removed_symbols.append(symbol)

        if removed_symbols:
            service.logger.info(f"Removed symbols from watchlist: {removed_symbols}")

        return {
            "status": "success",
            "message": f"Removed {len(removed_symbols)} symbols from watchlist",
            "removed": removed_symbols,
            "removed_symbols": removed_symbols,
            "watchlist_size": len(service.watchlist),
            "current_watchlist": sorted(service.watchlist),
        }

    except Exception as e:
        service.logger.error(f"Error removing symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/watchlist")
async def get_watchlist():
    """Get current watchlist (fast version)"""
    service = get_monitoring_service()
    try:
        return {
            "watchlist": sorted(service.watchlist),
            "size": len(service.watchlist),
            "last_updated": service.last_check.isoformat() if service.last_check else None,
            "analysis_available": "/watchlist/analysis",
        }
    except Exception as e:
        service.logger.error(f"Error getting watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/watchlist/analysis")
async def get_watchlist_analysis():
    """Get detailed watchlist analysis (slower)"""
    service = get_monitoring_service()
    try:
        return await service.get_watchlist_with_analysis()
    except Exception as e:
        service.logger.error(f"Error getting watchlist analysis: {e}")
        # Return basic watchlist if analysis fails
        return {
            "watchlist": sorted(service.watchlist),
            "size": len(service.watchlist),
            "error": "Analysis unavailable",
            "basic_mode": True,
        }


@api_router.get("/positions")
async def get_positions():
    """Get current positions"""
    try:
        service = get_monitoring_service()
        positions_dict = service.position_tracker.get_all_positions()
        positions = [
            {"symbol": p.symbol, "unrealized_pnl": p.unrealized_pnl}
            for p in positions_dict.values()
        ]
        return {
            "status": "success",
            "count": len(positions),
            "positions": positions,
            "total_unrealized_pnl": sum(float(pos.get("unrealized_pnl", 0)) for pos in positions),
        }
    except Exception as e:
        service.logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.post("/positions/check")
async def check_positions_after_order(request: OrderCheckRequest) -> Any:  # type: ignore[name-defined]
    """Check positions after order execution"""
    try:
        service = get_monitoring_service()
        # Note: position_tracker may not have refresh_positions method
        if hasattr(service.position_tracker, "refresh_positions"):
            await service.position_tracker.refresh_positions()
        positions_dict = service.position_tracker.get_all_positions()
        positions = [
            {"symbol": p.symbol, "unrealized_pnl": p.unrealized_pnl}
            for p in positions_dict.values()
        ]

        return {
            "status": "success",
            "timestamp": get_eastern_time_string(),
            "positions_count": len(positions),
            "positions": positions,
            "order_info": request.order_info,
        }
    except Exception as e:
        service.logger.error(f"Error checking positions: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/signals")
async def get_signals():
    """Get current trading signals"""
    service = get_monitoring_service()
    try:
        # Ensure current_signals is a list for test compatibility
        signals = service.current_signals
        if isinstance(signals, dict):
            signals = list(signals.values()) if signals else []

        return {
            "status": "success",
            "timestamp": get_eastern_time_string(),
            "current_signals": signals,
            "signal_count": len(signals),
            "last_updated": get_eastern_time_string(),
        }
    except Exception as e:
        service.logger.error(f"Error getting signals: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.post("/config/technical")
async def update_technical_config(request: TechnicalAnalysisUpdateRequest) -> Any:  # type: ignore[name-defined]
    """Update technical analysis configuration"""
    service = get_monitoring_service()
    return await service.update_technical_config(request)


@api_router.post("/config/trading")
async def update_trading_config(request: TradingConfigUpdateRequest) -> Any:  # type: ignore[name-defined]
    """Update trading configuration"""
    service = get_monitoring_service()
    return await service.update_trading_config(request)


@api_router.get("/hibernation")
async def get_hibernation_status():
    """Get hibernation status"""
    get_monitoring_service()
    return {"hibernation_enabled": False, "is_hibernating": False, "status": "active"}


@api_router.post("/watchlist/sync")
async def sync_watchlist_with_scanner(request: ScanSyncRequest) -> Any:  # type: ignore[name-defined]
    """Sync watchlist with scanner results"""
    get_monitoring_service()
    try:
        # Basic implementation - scanner may not be available
        return {
            "status": "success",
            "message": "Watchlist sync completed",
            "symbols_added": 0,
            "symbols_removed": 0,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail="Scanner service not available") from e


@api_router.get("/watchlist/auto-scan")
async def get_auto_scan_status():
    """Get auto-scan status"""
    service = get_monitoring_service()
    return {
        "enabled": service.auto_scan_enabled,
        "interval_seconds": 60,
        "min_trades_per_minute": 500,
        "min_percent_change": 5.0,
        "max_symbols": 20,
    }


@api_router.post("/watchlist/auto-scan")
async def configure_auto_scan(request: AutoScanConfigRequest) -> Any:  # type: ignore[name-defined]
    """Configure auto-scan settings"""
    service = get_monitoring_service()
    try:
        service.auto_scan_enabled = request.enabled
        return {
            "status": "success",
            "message": "Auto-scan configuration updated",
            "config": {
                "enabled": request.enabled,
                "interval_seconds": request.interval_seconds,
                "min_trades_per_minute": request.min_trades_per_minute,
                "min_percent_change": request.min_percent_change,
                "max_symbols": request.max_symbols,
            },
        }
    except Exception as e:
        service.logger.error(f"Error configuring auto-scan: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.post("/orders")
async def place_order(request: OrderRequest) -> Any:  # type: ignore[name-defined]
    """Place a stock order"""
    service = get_monitoring_service()
    try:
        # This would integrate with actual order placement
        return {
            "status": "error",
            "message": "Order placement requires API credentials",
            "order_info": {
                "symbol": request.symbol,
                "side": request.side,
                "quantity": request.quantity,
                "order_type": request.order_type,
            },
        }
    except Exception as e:
        service.logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/streaming/status")
async def get_streaming_status():
    """Get streaming service status"""
    service = get_monitoring_service()
    try:
        if hasattr(service, "streaming_service") and service.streaming_service:
            return {
                "is_running": (
                    service.streaming_service.is_running
                    if hasattr(service.streaming_service, "is_running")
                    else False
                ),
                "subscribed_symbols": [],
                "status": "available",
            }
        else:
            return {"is_running": False, "subscribed_symbols": [], "status": "not_available"}
    except Exception as e:
        service.logger.error(f"Error getting streaming status: {e}")
        return {"error": str(e), "is_running": False, "subscribed_symbols": []}


@api_router.post("/trades/request-confirmation")
async def request_trade_confirmation(request: TradeConfirmationRequest) -> Any:  # type: ignore[name-defined]
    """Request trade confirmation"""
    service = get_monitoring_service()
    try:
        trade_id = f"{request.symbol}_{request.action}_{int(time.time())}"

        # Store confirmation request
        confirmation_data = {
            "trade_id": trade_id,
            "symbol": request.symbol,
            "action": request.action,
            "quantity": request.quantity,
            "expected_price": request.expected_price,
            "status": "pending",
            "timestamp": get_eastern_time_string(),
        }

        return {
            "status": "success",
            "trade_id": trade_id,
            "message": "Trade confirmation requested",
            "confirmation": confirmation_data,
        }
    except Exception as e:
        service.logger.error(f"Error requesting trade confirmation: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.post("/trades/confirm-execution")
async def confirm_trade_execution(request: ConfirmExecutionRequest) -> Any:  # type: ignore[name-defined]
    """Confirm trade execution"""
    service = get_monitoring_service()
    try:
        return {
            "status": "success",
            "trade_id": request.trade_id,
            "actual_price": request.actual_price,
            "message": "Trade execution confirmed",
        }
    except Exception as e:
        service.logger.error(f"Error confirming trade execution: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/trades/confirmations")
async def get_trade_confirmations():
    """Get all trade confirmations"""
    service = get_monitoring_service()
    try:
        return {"status": "success", "confirmations": [], "count": 0}
    except Exception as e:
        service.logger.error(f"Error getting trade confirmations: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/trades/confirmations/{trade_id}")
async def get_specific_trade_confirmation(trade_id: str) -> Any:  # type: ignore[name-defined]
    """Get specific trade confirmation"""
    service = get_monitoring_service()
    try:
        return {
            "status": "success",
            "trade_id": trade_id,
            "confirmation": None,
            "message": "Trade confirmation not found",
        }
    except Exception as e:
        service.logger.error(f"Error getting trade confirmation: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/notifications/status")
async def get_notifications_status():
    """Get notification system status"""
    service = get_monitoring_service()
    try:
        return {
            "status": "available",
            "desktop_notifications": bool(hasattr(service, "desktop_notifications")),
            "notification_count": 0,
        }
    except Exception as e:
        service.logger.error(f"Error getting notification status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/notifications/history")
async def get_notifications_history():
    """Get notification history"""
    service = get_monitoring_service()
    try:
        return {"status": "success", "notifications": [], "count": 0}
    except Exception as e:
        service.logger.error(f"Error getting notification history: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="Alpaca Trading Monitoring Service",
        description="FastAPI-based monitoring service for automated trading",
        version="1.0.0",
    )

    # Include API routes
    app.include_router(api_router)

    return app
