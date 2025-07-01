"""Pydantic models for FastAPI requests and responses."""

from typing import Optional

from pydantic import BaseModel, Field


class AddSymbolsRequest(BaseModel):
    symbols: list[str] = Field(..., description="List of stock symbols to add")


class RemoveSymbolsRequest(BaseModel):
    symbols: list[str] = Field(..., description="List of stock symbols to remove")


class OrderCheckRequest(BaseModel):
    order_info: dict | None = Field(None, description="Order information for tracking")


class ScanSyncRequest(BaseModel):
    min_trades_per_minute: int = Field(
        500, description="Minimum trades per minute for active stocks"
    )
    min_percent_change: float = Field(5.0, description="Minimum percentage change")
    max_symbols: int = Field(20, description="Maximum symbols to monitor")
    force_update: bool = Field(False, description="Force update even if symbols are the same")


class TechnicalAnalysisUpdateRequest(BaseModel):
    hanning_window_samples: int | None = Field(
        None, ge=3, le=101, description="Hanning window size (odd numbers only)"
    )
    peak_trough_lookahead: int | None = Field(
        None, ge=1, le=50, description="Peak/trough detection sensitivity"
    )
    peak_trough_min_distance: int | None = Field(
        None, ge=1, le=20, description="Minimum distance between peaks"
    )


class TradingConfigUpdateRequest(BaseModel):
    trades_per_minute_threshold: int | None = Field(
        None, ge=1, le=10000, description="Minimum trades per minute"
    )
    min_percent_change_threshold: float | None = Field(
        None, ge=0.1, le=100.0, description="Minimum % change"
    )
    max_stock_price: float | None = Field(
        None, ge=0.01, le=1000.0, description="Maximum stock price"
    )
    family_protection_profit_threshold_percent: float | None = Field(
        None, ge=1.0, le=50.0, description="Family protection profit threshold %"
    )
    automatic_profit_threshold_percent: float | None = Field(
        None, ge=0.1, le=20.0, description="Automatic profit threshold %"
    )
    default_position_size_usd: int | None = Field(
        None, ge=1000, le=500000, description="Default position size in USD"
    )
    max_concurrent_positions: int | None = Field(
        None, ge=1, le=20, description="Maximum concurrent positions"
    )


class AutoScanConfigRequest(BaseModel):
    enabled: bool = Field(..., description="Enable/disable automatic scanning")
    interval_seconds: int = Field(60, description="Scan interval in seconds (minimum 30)")
    min_trades_per_minute: int = Field(500, description="Minimum trades per minute threshold")
    min_percent_change: float = Field(5.0, description="Minimum percentage change threshold")
    max_symbols: int = Field(20, description="Maximum symbols to monitor")


class TradeConfirmationRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    action: str = Field(..., description="BUY or SELL")
    quantity: int = Field(..., description="Number of shares")
    expected_price: float = Field(..., description="Expected execution price")


class ConfirmExecutionRequest(BaseModel):
    trade_id: str = Field(..., description="Trade confirmation ID")
    actual_price: float = Field(..., description="Actual execution price")
    fill_timestamp: str = Field(..., description="Execution timestamp")
    screenshot_path: str | None = Field(None, description="Path to screenshot proof")


class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol")
    side: str = Field(..., description="buy or sell")
    quantity: int = Field(..., description="Number of shares")
    order_type: str = Field("limit", description="Order type")
    limit_price: float | None = Field(None, description="Limit price for limit orders")
    time_in_force: str = Field("day", description="Time in force")
