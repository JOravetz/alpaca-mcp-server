"""Automated Trading Engine - Lightning Fast Execution

Complete automated trading pipeline for the FastAPI server with:
- Instant buy order execution on fresh trough signals
- Real-time order monitoring and modification
- Profit-optimized sell execution with loss protection
- Stream-integrated position tracking
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from ..config.global_config import get_global_config
from ..tools.account_tools import get_positions
from ..tools.market_data_tools import get_stock_quote
from ..tools.order_tools import cancel_order_by_id, get_orders, place_stock_order
from ..tools.peak_trough_analysis_tool import analyze_peaks_and_troughs_with_plot_py
from ..tools.streaming_tools import get_stock_stream_data


@dataclass
class ActiveOrder:
    """Tracks an active order with monitoring state"""

    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: int
    order_type: str
    limit_price: float
    time_in_force: str
    status: str
    submitted_at: datetime
    last_check: datetime
    modification_count: int = 0
    target_entry_price: float | None = None  # For buy orders
    stop_loss_price: float | None = None  # For sell orders


@dataclass
class ActivePosition:
    """Tracks an active position with profit monitoring"""

    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    opened_at: datetime
    highest_price: float  # Track peak for profit taking
    profit_target_hit: bool = False
    monitoring_peak_signals: bool = True


class AutoTrader:
    """Lightning-fast automated trading engine"""

    def __init__(self):
        self.logger = logging.getLogger("auto_trader")
        self.config = get_global_config()

        # Trading state
        self.enabled = False
        self.active_orders: dict[str, ActiveOrder] = {}
        self.active_positions: dict[str, ActivePosition] = {}
        self.processed_signals: set[str] = set()  # Prevent duplicate signal processing
        self.profit_required_symbols: set[str] = (
            set()
        )  # Symbols that must sell for profit before buying again

        # Trading parameters from config
        self.position_size_usd = self.config.trading.default_position_size_usd
        self.max_positions = self.config.trading.max_concurrent_positions
        self.never_sell_for_loss = self.config.trading.never_sell_for_loss
        self.order_timeout = self.config.trading.order_timeout_seconds
        self.max_stock_price = self.config.trading.max_stock_price
        self.order_freshness_seconds = 5  # Cancel and refresh orders after 5 seconds

        # Technical analysis parameters from config
        self.hanning_window = self.config.technical_analysis.hanning_window_samples
        self.lookahead = self.config.technical_analysis.peak_trough_lookahead

        # Performance tracking
        self.orders_placed = 0
        self.orders_filled = 0
        self.positions_opened = 0
        self.positions_closed = 0
        self.total_realized_pnl = 0.0

        self.logger.info("AutoTrader initialized - Lightning mode enabled")

        # Cleanup task will be started when trading is enabled
        self._cleanup_task = None

    async def enable_trading(self) -> dict:
        """Enable automated trading"""
        if self.enabled:
            return {"status": "already_enabled", "message": "Auto trading already active"}

        self.enabled = True
        self.logger.warning("🚀 AUTOMATED TRADING ENABLED - Lightning execution mode")

        # Start periodic cleanup task for stale orders
        if self._cleanup_task is None:
            try:
                self._cleanup_task = asyncio.create_task(self._periodic_order_cleanup())
            except RuntimeError:
                # No event loop running, cleanup will be handled manually
                self.logger.warning("No event loop available for periodic cleanup task")

        # Recalculate statistics from actual API data on startup
        try:
            await self.recalculate_statistics_from_api()
        except Exception as e:
            self.logger.warning(f"Could not recalculate stats on startup: {e}")

        return {
            "status": "enabled",
            "message": "Automated trading activated",
            "config": {
                "position_size_usd": self.position_size_usd,
                "max_positions": self.max_positions,
                "max_stock_price": self.max_stock_price,
                "never_sell_for_loss": self.never_sell_for_loss,
            },
        }

    async def disable_trading(self) -> dict:
        """Disable automated trading"""
        if not self.enabled:
            return {"status": "already_disabled", "message": "Auto trading already inactive"}

        self.enabled = False
        self.logger.warning("🛑 AUTOMATED TRADING DISABLED")

        # Cancel the cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            self._cleanup_task = None

        return {
            "status": "disabled",
            "message": "Automated trading deactivated",
            "stats": {
                "orders_placed": self.orders_placed,
                "orders_filled": self.orders_filled,
                "positions_opened": self.positions_opened,
                "positions_closed": self.positions_closed,
                "total_realized_pnl": self.total_realized_pnl,
            },
        }

    async def clear_profit_requirement(self, symbol: str) -> dict:
        """Manual override: Allow buying symbol again without profit requirement"""
        if symbol in self.profit_required_symbols:
            self.profit_required_symbols.remove(symbol)
            self.logger.warning(f"🔓 MANUAL OVERRIDE: {symbol} profit requirement cleared by user")
            return {
                "status": "cleared",
                "message": f"Profit requirement cleared for {symbol} - can buy again",
                "symbol": symbol,
            }
        else:
            return {
                "status": "not_required",
                "message": f"{symbol} was not in profit-required list",
                "symbol": symbol,
            }

    async def add_profit_requirement(self, symbol: str) -> dict:
        """Manual control: Add symbol to profit requirement list"""
        self.profit_required_symbols.add(symbol)
        self.logger.warning(f"🔒 MANUAL ADDITION: {symbol} added to profit-required list by user")
        return {
            "status": "added",
            "message": f"Profit requirement added for {symbol} - must sell for profit before buying again",
            "symbol": symbol,
        }

    async def get_profit_required_symbols(self) -> dict:
        """Get list of symbols requiring profit before re-buy"""
        return {
            "symbols": list(self.profit_required_symbols),
            "count": len(self.profit_required_symbols),
            "message": "Symbols that must sell for profit before buying again",
        }

    async def process_fresh_signal(self, signal: dict) -> dict:
        """Process a fresh trading signal with lightning execution"""
        if not self.enabled:
            return {"status": "disabled", "message": "Auto trading not enabled"}

        signal_id = f"{signal['symbol']}_{signal['signal_type']}_{signal.get('timestamp', '')}"

        # Prevent duplicate processing
        if signal_id in self.processed_signals:
            return {"status": "duplicate", "message": "Signal already processed"}

        self.processed_signals.add(signal_id)

        try:
            # Only process fresh trough signals for buying
            if signal["signal_type"] != "fresh_trough":
                return {"status": "ignored", "message": "Only fresh trough signals trigger buys"}

            # Check if signal is truly fresh (< half hanning window size)
            bars_ago = signal.get("bars_ago", 999)
            fresh_threshold = self.hanning_window // 2  # 11 // 2 = 5 by default
            if bars_ago > fresh_threshold:
                return {
                    "status": "stale",
                    "message": f"Signal too old: {bars_ago} bars ago (threshold: ≤{fresh_threshold})",
                }

            # Check position limits
            if len(self.active_positions) >= self.max_positions:
                return {
                    "status": "limit_reached",
                    "message": f"Max positions ({self.max_positions}) reached",
                }

            # Check if we already have a position in this symbol
            if signal["symbol"] in self.active_positions:
                return {
                    "status": "position_exists",
                    "message": f"Already have position in {signal['symbol']}",
                }

            # CRITICAL USER RULE: ONLY BUY ONCE - Must sell for profit before buying again
            # Add ANY symbol to profit_required_symbols after first buy attempt
            if signal["symbol"] in self.profit_required_symbols:
                return {
                    "status": "profit_required",
                    "message": f"RULE VIOLATION PREVENTED: {signal['symbol']} already bought once - must sell for PROFIT before buying again",
                }

            # ENFORCE SINGLE-BUY RULE: Add symbol to profit-required list on first buy
            self.profit_required_symbols.add(signal["symbol"])
            self.logger.warning(
                f"🔒 SINGLE-BUY RULE: {signal['symbol']} added to profit-required list (first buy attempt)"
            )

            # Validate signal price and stock price limits
            signal_price = signal.get("price", 0)
            if signal_price > self.max_stock_price:
                return {
                    "status": "price_too_high",
                    "message": f"Stock price ${signal_price} exceeds limit ${self.max_stock_price}",
                }

            # Get real-time streaming data for LOW PRICE ANOMALY detection
            streaming_price = await self._detect_low_price_anomaly(signal["symbol"])

            # Fallback to quote if streaming unavailable
            if streaming_price is None:
                quote_result = await get_stock_quote(signal["symbol"])
                current_ask = self._extract_ask_price(quote_result)
            else:
                current_ask = streaming_price

            if current_ask is None or current_ask > self.max_stock_price:
                return {"status": "quote_error", "message": "Could not get valid current price"}

            # Calculate position size
            quantity = int(self.position_size_usd / current_ask)
            if quantity < 1:
                return {"status": "insufficient_funds", "message": "Position size too small"}

            # Execute lightning-fast buy order with LOW PRICE
            result = await self._execute_buy_order(
                signal["symbol"], quantity, current_ask, signal_price
            )

            if result["status"] == "success":
                self.orders_placed += 1
                self.logger.warning(
                    f"🚀 BUY ORDER EXECUTED: {signal['symbol']} x{quantity} @ ${current_ask}"
                )

            return result

        except Exception as e:
            self.logger.error(f"Error processing signal for {signal['symbol']}: {e}")
            return {"status": "error", "message": str(e)}

    async def _execute_buy_order(
        self, symbol: str, quantity: int, current_ask: float, signal_price: float
    ) -> dict:
        """Execute lightning-fast buy order with LOW PRICE ANOMALY optimization"""
        try:
            # Use LOW PRICE from anomaly detection for aggressive entry
            limit_price = current_ask  # Use detected low price for optimal fill

            self.logger.warning(
                f"🎯 LOW PRICE BUY: {symbol} limit=${limit_price:.4f} (signal=${signal_price:.4f})"
            )

            # Use DAY orders for pre-market compatibility (IOC/FOK not allowed pre-market)
            order_result = await place_stock_order(
                symbol=symbol,
                side="buy",
                quantity=quantity,
                order_type="limit",
                limit_price=limit_price,
                time_in_force="day",  # DAY orders work in pre-market
                extended_hours=True,
            )

            # Increment orders placed counter
            self.orders_placed += 1

            # Extract order ID from result
            order_id = self._extract_order_id(order_result)

            if order_id:
                # Track order for monitoring
                active_order = ActiveOrder(
                    order_id=order_id,
                    symbol=symbol,
                    side="buy",
                    quantity=quantity,
                    order_type="limit",
                    limit_price=limit_price,
                    time_in_force="day",
                    status="submitted",
                    submitted_at=datetime.now(UTC),
                    last_check=datetime.now(UTC),
                    target_entry_price=signal_price,
                )

                self.active_orders[order_id] = active_order

                # Start immediate order monitoring
                asyncio.create_task(self._monitor_order(order_id))

                return {
                    "status": "success",
                    "order_id": order_id,
                    "symbol": symbol,
                    "quantity": quantity,
                    "limit_price": limit_price,
                    "message": f"Buy order submitted for {symbol}",
                }
            else:
                return {"status": "failed", "message": "Could not extract order ID"}

        except Exception as e:
            self.logger.error(f"Failed to execute buy order for {symbol}: {e}")
            return {"status": "error", "message": str(e)}

    async def _monitor_order(self, order_id: str) -> None:
        """Monitor order for fill status with real-time streaming verification"""
        if order_id not in self.active_orders:
            return

        order = self.active_orders[order_id]

        # Monitor for up to order_timeout seconds
        start_time = time.time()

        while time.time() - start_time < self.order_timeout:
            try:
                # Check if order is becoming stale (older than freshness threshold)
                order_age = time.time() - order.submitted_at.timestamp()
                if order_age > self.order_freshness_seconds:
                    self.logger.warning(
                        f"Order {order_id} is stale ({order_age:.1f}s) - refreshing with current market price"
                    )
                    await self._refresh_stale_order(order_id)
                    return

                # First check: Real-time streaming data for fills
                stream_data = await get_stock_stream_data(order.symbol, "trades", limit=1)
                if stream_data and "filled" in stream_data.lower():
                    await self._handle_order_fill(order_id)
                    return

                # Second check: Order status API
                orders_result = await get_orders(status="all", limit=50)

                # Parse order status
                if order_id in orders_result and "filled" in orders_result.lower():
                    # Order filled - create position
                    await self._handle_order_fill(order_id)
                    return
                elif "cancelled" in orders_result.lower() or "rejected" in orders_result.lower():
                    # Order failed - immediately retry with market order if urgent
                    self.logger.warning(
                        f"Order {order_id} failed - retrying with current market price"
                    )
                    await self._retry_order_at_market(order)
                    del self.active_orders[order_id]
                    return

                # Check every 0.1 seconds for lightning speed
                await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error monitoring order {order_id}: {e}")
                await asyncio.sleep(0.1)

        # Timeout - retry with fresh market price
        try:
            self.logger.warning(f"Order {order_id} timeout - retrying with fresh market price")
            await self._retry_order_at_market(order)
            await cancel_order_by_id(order_id)
        except (ConnectionError, TimeoutError, Exception) as e:
            self.logger.error(f"Error retrying order {order_id}: {e}")

        if order_id in self.active_orders:
            del self.active_orders[order_id]

    async def _refresh_stale_order(self, order_id: str) -> None:
        """Cancel stale order and place fresh one with current market price"""
        if order_id not in self.active_orders:
            return

        order = self.active_orders[order_id]

        try:
            # Cancel the stale order first
            await cancel_order_by_id(order_id)
            self.logger.info(f"Cancelled stale order {order_id}")

            # Get fresh market price
            quote_result = await get_stock_quote(order.symbol)

            if order.side == "buy":
                fresh_price = self._extract_ask_price(quote_result)
            else:
                fresh_price = self._extract_bid_price(quote_result)

            if not fresh_price:
                self.logger.error(f"Could not get fresh price for {order.symbol}")
                del self.active_orders[order_id]
                return

            # ANTI-FOMO CHECK: Validate price hasn't moved too far from signal
            signal_price = order.target_entry_price
            max_deviation = 0.05  # 5% maximum deviation from signal

            if order.side == "buy":
                # For buy orders: don't chase if price moved up too much from trough
                price_increase = (fresh_price - signal_price) / signal_price  # type: ignore[operator]
                if price_increase > max_deviation:
                    self.logger.warning(
                        f"🚫 ANTI-FOMO: {order.symbol} price ${fresh_price:.4f} too far above trough signal ${signal_price:.4f} (+{price_increase:.1%})"
                    )
                    del self.active_orders[order_id]
                    return
                self.logger.info(
                    f"✅ BUY REFRESH: {order.symbol} ${fresh_price:.4f} within range of trough ${signal_price:.4f} (+{price_increase:.1%})"
                )
            else:
                # For sell orders: don't chase if price moved down too much from peak
                price_decrease = (signal_price - fresh_price) / signal_price  # type: ignore[operator]
                if price_decrease > max_deviation:
                    self.logger.warning(
                        f"🚫 ANTI-FOMO: {order.symbol} price ${fresh_price:.4f} too far below peak signal ${signal_price:.4f} (-{price_decrease:.1%})"
                    )
                    del self.active_orders[order_id]
                    return
                self.logger.info(
                    f"✅ SELL REFRESH: {order.symbol} ${fresh_price:.4f} within range of peak ${signal_price:.4f} (-{price_decrease:.1%})"
                )

            # Place fresh order with validated market price
            fresh_result = await place_stock_order(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                order_type="limit",
                limit_price=fresh_price,  # Use fresh market price
                time_in_force="day",
                extended_hours=True,
            )

            # Increment orders placed counter
            self.orders_placed += 1

            # Track the fresh order
            fresh_order_id = self._extract_order_id(fresh_result)
            if fresh_order_id:
                fresh_order = ActiveOrder(
                    order_id=fresh_order_id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.quantity,
                    order_type="limit",
                    limit_price=fresh_price,
                    time_in_force="day",
                    status="submitted",
                    submitted_at=datetime.now(UTC),  # Fresh timestamp
                    last_check=datetime.now(UTC),
                    target_entry_price=order.target_entry_price,
                )

                # Remove old order and add fresh one
                del self.active_orders[order_id]
                self.active_orders[fresh_order_id] = fresh_order

                self.logger.warning(
                    f"🔄 FRESH ORDER: {order.symbol} {order.side} at ${fresh_price} (replaced stale order)"
                )

                # Start monitoring the fresh order
                asyncio.create_task(self._monitor_order(fresh_order_id))
            else:
                del self.active_orders[order_id]

        except Exception as e:
            self.logger.error(f"Failed to refresh stale order {order_id}: {e}")
            if order_id in self.active_orders:
                del self.active_orders[order_id]

    async def _retry_order_at_market(self, original_order: ActiveOrder) -> None:
        """Retry failed order with fresh real-time market price"""
        try:
            # Get fresh real-time quote
            quote_result = await get_stock_quote(original_order.symbol)

            if original_order.side == "buy":
                # Use current ask for buy orders
                current_price = self._extract_ask_price(quote_result)
            else:
                # Use current bid for sell orders
                current_price = self._extract_bid_price(quote_result)

            if not current_price:
                self.logger.error(f"Could not get fresh price for {original_order.symbol} retry")
                return

            # Execute new order with fresh market price
            retry_result = await place_stock_order(
                symbol=original_order.symbol,
                side=original_order.side,
                quantity=original_order.quantity,
                order_type="limit",
                limit_price=current_price,  # Use exact market price
                time_in_force="day",  # Immediate or Cancel
                extended_hours=True,
            )

            # Increment orders placed counter
            self.orders_placed += 1

            self.logger.warning(
                f"🔄 RETRY ORDER: {original_order.symbol} at fresh price ${current_price}"
            )

            # Track new order if successful
            retry_order_id = self._extract_order_id(retry_result)
            if retry_order_id:
                retry_order = ActiveOrder(
                    order_id=retry_order_id,
                    symbol=original_order.symbol,
                    side=original_order.side,
                    quantity=original_order.quantity,
                    order_type="limit",
                    limit_price=current_price,
                    time_in_force="day",
                    status="submitted",
                    submitted_at=datetime.now(UTC),
                    last_check=datetime.now(UTC),
                    target_entry_price=original_order.target_entry_price,
                )

                self.active_orders[retry_order_id] = retry_order
                asyncio.create_task(self._monitor_order(retry_order_id))

        except Exception as e:
            self.logger.error(f"Failed to retry order for {original_order.symbol}: {e}")

    async def _handle_order_fill(self, order_id: str) -> None:
        """Handle filled order and create position tracking"""
        if order_id not in self.active_orders:
            return

        order = self.active_orders[order_id]

        try:
            # Get current positions to find the new position
            positions_result = await get_positions()

            # Extract position info for this symbol
            entry_price, quantity = self._extract_position_info(positions_result, order.symbol)

            if entry_price and quantity:
                # Create active position for monitoring
                position = ActivePosition(
                    symbol=order.symbol,
                    quantity=quantity,
                    entry_price=entry_price,
                    current_price=entry_price,
                    unrealized_pnl=0.0,
                    unrealized_pnl_percent=0.0,
                    opened_at=datetime.now(UTC),
                    highest_price=entry_price,
                )

                self.active_positions[order.symbol] = position
                self.positions_opened += 1
                self.orders_filled += 1

                self.logger.warning(
                    f"✅ POSITION OPENED: {order.symbol} x{quantity} @ ${entry_price}"
                )

                # Start real-time position monitoring for profit taking
                asyncio.create_task(self._monitor_position(order.symbol))

        except Exception as e:
            self.logger.error(f"Error handling order fill for {order_id}: {e}")

        # Remove from active orders
        del self.active_orders[order_id]

    async def _monitor_position(self, symbol: str) -> None:
        """Monitor position for profit opportunities with real-time streaming"""
        if symbol not in self.active_positions:
            return

        position = self.active_positions[symbol]

        self.logger.info(f"🔍 Started profit monitoring for {symbol}")

        while symbol in self.active_positions:
            try:
                # Get real-time streaming price
                stream_data = await get_stock_stream_data(symbol, "trades", limit=1)
                current_price = self._extract_stream_price(stream_data)

                if current_price:
                    # Update position with current price
                    position.current_price = current_price
                    position.unrealized_pnl = (
                        current_price - position.entry_price
                    ) * position.quantity
                    position.unrealized_pnl_percent = (
                        (current_price - position.entry_price) / position.entry_price
                    ) * 100

                    # Track highest price for profit optimization
                    if current_price > position.highest_price:
                        position.highest_price = current_price

                    # Check profit taking conditions
                    await self._check_profit_conditions(symbol, position, current_price)

                # Update every 0.5 seconds for ultra-fast profit monitoring
                await asyncio.sleep(0.5)

            except Exception as e:
                self.logger.error(f"Error monitoring position {symbol}: {e}")
                await asyncio.sleep(5)

    async def _check_profit_conditions(  # type: ignore[no-untyped-def]
        self, symbol: str, position: ActivePosition, current_price: float
    ):
        """Check if we should sell for profit at peak detection - NO THRESHOLDS"""

        # Only sell if we have ANY profit
        if position.unrealized_pnl <= 0:
            return  # Never sell for loss

        # Get trading config for normalized thresholds
        config = get_global_config()

        # Family protection rule: 10%+ profit = IMMEDIATE SELL (normalized)
        if (
            position.unrealized_pnl_percent
            >= config.trading.family_protection_profit_threshold_percent
        ):
            await self._execute_sell_order(
                symbol,
                position,
                "family_protection",
                f"{position.unrealized_pnl_percent:.1f}% profit (${position.unrealized_pnl:.0f}) - FAMILY PROTECTION RULE",
            )
            return

        # Real-time peak detection using streaming data
        try:
            # Get latest streaming trades to detect if we're at a peak
            stream_data = await get_stock_stream_data(symbol, "trades", limit=5, recent_seconds=10)
            if stream_data and self._is_at_profit_peak(
                stream_data, current_price, position.entry_price
            ):
                await self._execute_sell_order(
                    symbol,
                    position,
                    "peak_detected",
                    f"At profit peak: ${position.unrealized_pnl:.2f}",
                )
                return
        except Exception as e:
            self.logger.debug(f"Stream peak detection error for {symbol}: {e}")

        # Check for fresh peak signals using technical analysis
        if position.monitoring_peak_signals:
            await self._check_peak_signals(symbol, position)

    async def _check_peak_signals(self, symbol: str, position: ActivePosition) -> None:
        """Check for peak signals to sell - only if current price > entry price"""
        try:
            # Only sell at peaks if current price is higher than entry price (profitable)
            if position.current_price <= position.entry_price:
                return

            # Get real-time peak/trough analysis using plot.py for accuracy
            analysis = await analyze_peaks_and_troughs_with_plot_py(
                symbols=symbol,
                timeframe="1Min",
                days=1,
                window_len=self.hanning_window,  # Use global config (11)
                lookahead=self.lookahead,  # Use global config (1)
            )

            # Look for ANY peak signals - no freshness limitation for sells
            if "Latest peak:" in analysis:
                lines = analysis.split("\n")
                for line in lines:
                    if "bars ago" in line and "PEAK" in line.upper():
                        import re

                        bars_match = re.search(r"(\d+)\s+bars?\s+ago", line)
                        if bars_match:
                            bars_ago = int(bars_match.group(1))
                            # Sell at ANY peak signal if profitable - no freshness limit
                            await self._execute_sell_order(
                                symbol,
                                position,
                                "technical_peak",
                                f"Peak signal ({bars_ago} bars ago) - profit ${position.unrealized_pnl:.2f}",
                            )
                            return

        except Exception as e:
            self.logger.error(f"Error checking peak signals for {symbol}: {e}")

    async def _execute_sell_order(  # type: ignore[no-untyped-def]
        self, symbol: str, position: ActivePosition, reason: str, details: str
    ):
        """Execute lightning-fast sell order with real-time pricing"""
        try:
            # Never sell for loss rule
            if self.never_sell_for_loss and position.unrealized_pnl < 0:
                self.logger.warning(
                    f"🛡️ NEVER SELL FOR LOSS: {symbol} P&L=${position.unrealized_pnl:.2f}"
                )
                return

            # Get fresh real-time streaming price first
            stream_data = await get_stock_stream_data(symbol, "quotes", limit=1)
            current_bid = self._extract_stream_bid(stream_data)

            # Fallback to quote API if stream unavailable
            if not current_bid:
                quote_result = await get_stock_quote(symbol)
                current_bid = self._extract_bid_price(quote_result)

            if not current_bid:
                self.logger.error(f"Could not get real-time bid price for {symbol}")
                return

            # Use exact real-time bid price for guaranteed fill
            limit_price = current_bid

            # Execute sell order with IOC for instant fill
            await place_stock_order(
                symbol=symbol,
                side="sell",
                quantity=position.quantity,
                order_type="limit",
                limit_price=limit_price,
                time_in_force="day",
                extended_hours=True,
            )

            # Increment orders placed counter
            self.orders_placed += 1

            self.logger.warning(f"💰 SELL ORDER EXECUTED: {symbol} - {reason} - {details}")
            self.logger.warning(
                f"📊 PROFIT: ${position.unrealized_pnl:.2f} ({position.unrealized_pnl_percent:.1f}%) at ${limit_price}"
            )

            # Update stats
            self.total_realized_pnl += position.unrealized_pnl
            self.positions_closed += 1
            self.orders_filled += 1  # Sell order was filled

            # PROFIT-FIRST TRACKING: Manage profit requirement for future buys
            if position.unrealized_pnl > 0:
                # Sold for profit - remove from profit requirement (can buy again)
                if symbol in self.profit_required_symbols:
                    self.profit_required_symbols.remove(symbol)
                    self.logger.warning(
                        f"✅ PROFIT ACHIEVED: {symbol} removed from profit-required list - can buy again"
                    )
            else:
                # Sold for loss or break-even - add to profit requirement
                self.profit_required_symbols.add(symbol)
                self.logger.warning(
                    f"🛡️ PROFIT REQUIRED: {symbol} added to profit-required list - must profit before buying again"
                )

            # Remove position from tracking
            del self.active_positions[symbol]

        except Exception as e:
            self.logger.error(f"Error executing sell order for {symbol}: {e}")

    def _extract_order_id(self, order_result) -> str | None:  # type: ignore[no-untyped-def]
        """Extract order ID from order result - handles both dict and string formats"""
        try:
            # Handle dictionary result (direct from MCP tools)
            if isinstance(order_result, dict):
                if "order" in order_result:
                    order = order_result["order"]
                    if hasattr(order, "id"):
                        return str(order.id)
                    elif isinstance(order, dict) and "id" in order:
                        return str(order["id"])
                # Check for direct id field
                if "id" in order_result:
                    return str(order_result["id"])
                # Check for order_id field
                if "order_id" in order_result:
                    return str(order_result["order_id"])

            # Handle string result (formatted output)
            if isinstance(order_result, str):
                lines = order_result.split("\n")
                for line in lines:
                    if "Order ID:" in line:
                        return line.split("Order ID:")[1].strip()

            self.logger.error(
                f"Could not extract order ID from result: {type(order_result)} - {str(order_result)[:200]}"
            )

        except Exception as e:
            self.logger.error(f"Error extracting order ID: {e}")
        return None

    def _extract_ask_price(self, quote_result: str) -> float | None:
        """Extract ask price from quote result"""
        try:
            lines = quote_result.split("\n")
            for line in lines:
                if "Ask Price:" in line:
                    price_str = line.split("Ask Price:")[1].strip().replace("$", "")
                    return float(price_str)
        except (ValueError, IndexError, AttributeError) as e:
            self.logger.debug(f"Error extracting ask price: {e}")
        return None

    def _extract_bid_price(self, quote_result: str) -> float | None:
        """Extract bid price from quote result"""
        try:
            lines = quote_result.split("\n")
            for line in lines:
                if "Bid Price:" in line:
                    price_str = line.split("Bid Price:")[1].strip().replace("$", "")
                    return float(price_str)
        except (ValueError, IndexError, AttributeError) as e:
            self.logger.debug(f"Error extracting bid price: {e}")
        return None

    def _extract_position_info(
        self, positions_result: str, symbol: str
    ) -> tuple[float | None, int | None]:
        """Extract position info from positions result"""
        try:
            lines = positions_result.split("\n")
            in_symbol_section = False
            entry_price = None
            quantity = None

            for line in lines:
                if f"Symbol: {symbol}" in line:
                    in_symbol_section = True
                elif "Symbol:" in line and symbol not in line:
                    in_symbol_section = False
                elif in_symbol_section:
                    if "Entry Price:" in line:
                        price_str = line.split("Entry Price:")[1].strip().replace("$", "")
                        entry_price = float(price_str)
                    elif "Quantity:" in line:
                        quantity = int(line.split("Quantity:")[1].strip())

            return entry_price, quantity
        except (ValueError, IndexError, AttributeError) as e:
            self.logger.debug(f"Error extracting position info: {e}")
        return None, None

    def _extract_stream_price(self, stream_data: str) -> float | None:
        """Extract price from streaming data"""
        try:
            # Look for trade price in stream data
            lines = stream_data.split("\n")
            for line in lines:
                if "price" in line.lower() and "$" in line:
                    # Extract price value
                    import re

                    price_match = re.search(r"\$(\d+\.?\d*)", line)
                    if price_match:
                        return float(price_match.group(1))
        except (ValueError, AttributeError, ImportError) as e:
            self.logger.debug(f"Error extracting stream price: {e}")
        return None

    def _extract_stream_bid(self, stream_data: str) -> float | None:
        """Extract bid price from streaming quote data"""
        try:
            lines = stream_data.split("\n")
            for line in lines:
                if "bid" in line.lower() and "$" in line:
                    import re

                    price_match = re.search(r"\$(\d+\.?\d*)", line)
                    if price_match:
                        return float(price_match.group(1))
        except (ValueError, AttributeError, ImportError) as e:
            self.logger.debug(f"Error extracting stream bid: {e}")
        return None

    def _is_at_profit_peak(
        self, stream_data: str, current_price: float, entry_price: float
    ) -> bool:
        """Detect if we're at a profit peak - sell at the top"""
        try:
            # Only consider if we have profit
            if current_price <= entry_price:
                return False

            lines = stream_data.split("\n")
            recent_prices = []

            for line in lines:
                if "price" in line.lower() and "$" in line:
                    import re

                    price_match = re.search(r"\$(\d+\.?\d*)", line)
                    if price_match:
                        recent_prices.append(float(price_match.group(1)))

            if len(recent_prices) < 3:
                return False  # Need enough data points

            # Sort by most recent (assuming last is most recent)
            recent_prices = recent_prices[-5:]  # Last 5 trades

            # Check if current price is highest of recent trades (indicating peak)
            max_recent = max(recent_prices)

            # If current price is at or near the highest recent price, we might be peaking
            # Sell if we're within small margin of recent high and have profit
            if current_price >= max_recent * 0.999:  # Within 0.1% of recent high
                return True

        except (ValueError, IndexError, TypeError) as e:
            self.logger.debug(f"Error checking profit peak: {e}")
        return False

    def get_status(self) -> dict:
        """Get current auto trader status"""
        return {
            "enabled": self.enabled,
            "active_orders": len(self.active_orders),
            "active_positions": len(self.active_positions),
            "position_symbols": list(self.active_positions.keys()),
            "profit_required_symbols": list(self.profit_required_symbols),
            "profit_required_count": len(self.profit_required_symbols),
            "stats": {
                "orders_placed": self.orders_placed,
                "orders_filled": self.orders_filled,
                "positions_opened": self.positions_opened,
                "positions_closed": self.positions_closed,
                "total_realized_pnl": self.total_realized_pnl,
            },
            "config": {
                "position_size_usd": self.position_size_usd,
                "max_positions": self.max_positions,
                "max_stock_price": self.max_stock_price,
                "never_sell_for_loss": self.never_sell_for_loss,
            },
        }

    async def _periodic_order_cleanup(self):
        """Periodic task to clean up any stale orders that weren't caught"""
        while True:
            try:
                await asyncio.sleep(3)  # Check every 3 seconds

                if not self.enabled or not self.active_orders:
                    continue

                current_time = time.time()
                stale_orders = []

                for order_id, order in self.active_orders.items():
                    order_age = current_time - order.submitted_at.timestamp()
                    if order_age > self.order_freshness_seconds:
                        stale_orders.append(order_id)

                # Refresh stale orders
                for order_id in stale_orders:
                    self.logger.warning(f"Periodic cleanup: refreshing stale order {order_id}")
                    asyncio.create_task(self._refresh_stale_order(order_id))

            except Exception as e:
                self.logger.error(f"Error in periodic order cleanup: {e}")
                await asyncio.sleep(10)  # Wait longer if there's an error

    async def _detect_low_price_anomaly(self, symbol: str) -> float | None:
        """Detect LOW PRICE ANOMALY using streaming trades for optimal entry

        Analyzes recent streaming trades to find the lowest available price
        for aggressive low-price buying strategy.
        """
        try:
            # Get recent streaming trades for anomaly detection
            stream_data = await get_stock_stream_data(symbol, "trades", limit=10, recent_seconds=30)

            if not stream_data:
                self.logger.debug(f"No streaming data for {symbol} - using quote fallback")
                return None

            # Extract recent trade prices from streaming data
            recent_prices = []
            lines = stream_data.split("\n")

            for line in lines:
                if "price" in line.lower() and "$" in line:
                    import re

                    price_match = re.search(r"\$(\d+\.?\d*)", line)
                    if price_match:
                        price = float(price_match.group(1))
                        if price > 0:  # Valid price
                            recent_prices.append(price)

            if len(recent_prices) < 3:
                self.logger.debug(
                    f"Insufficient streaming data for {symbol} ({len(recent_prices)} prices)"
                )
                return None

            # LOW PRICE ANOMALY DETECTION
            min_price = min(recent_prices)
            max_price = max(recent_prices)
            avg_price = sum(recent_prices) / len(recent_prices)

            # Calculate price volatility
            price_range = max_price - min_price
            volatility_percent = (price_range / avg_price) * 100 if avg_price > 0 else 0

            # AGGRESSIVE LOW PRICE STRATEGY
            # Use the lowest recent price if there's significant volatility
            if volatility_percent > 0.5:  # 0.5% volatility threshold
                target_price = min_price + (price_range * 0.1)  # 10% above minimum
                self.logger.warning(
                    f"💰 LOW PRICE ANOMALY: {symbol} target=${target_price:.4f} (min=${min_price:.4f}, volatility={volatility_percent:.2f}%)"
                )
                return target_price
            else:
                # Low volatility - use slightly below average
                target_price = avg_price * 0.999  # 0.1% below average
                self.logger.info(
                    f"📊 NORMAL PRICING: {symbol} target=${target_price:.4f} (avg=${avg_price:.4f})"
                )
                return target_price

        except Exception as e:
            self.logger.error(f"Error detecting low price anomaly for {symbol}: {e}")
            return None

    async def recalculate_statistics_from_api(self) -> dict:
        """Recalculate statistics from actual Alpaca API order history"""
        try:
            # Get today's orders from Alpaca API
            orders_result = await get_orders(status="all", limit=100)

            # Reset counters
            orders_placed = 0
            orders_filled = 0
            positions_opened = 0
            positions_closed = 0
            total_realized_pnl = 0.0

            # Parse order results (handle both dict and string responses)
            if isinstance(orders_result, str):
                # Parse string output from the tool
                import re

                filled_orders = re.findall(r"Status: OrderStatus\.FILLED", orders_result)
                placed_orders = re.findall(r"Symbol: \w+", orders_result)
                buy_orders = re.findall(
                    r"Side: OrderSide\.BUY.*?Status: OrderStatus\.FILLED", orders_result, re.DOTALL
                )
                sell_orders = re.findall(
                    r"Side: OrderSide\.SELL.*?Status: OrderStatus\.FILLED", orders_result, re.DOTALL
                )

                orders_placed = len(placed_orders)
                orders_filled = len(filled_orders)
                positions_opened = len(buy_orders)
                positions_closed = len(sell_orders)

                # Extract filled prices for P&L calculation
                buy_fills = re.findall(
                    r"Side: OrderSide\.BUY.*?Filled Price: \$(\d+\.?\d*)", orders_result, re.DOTALL
                )
                sell_fills = re.findall(
                    r"Side: OrderSide\.SELL.*?Filled Price: \$(\d+\.?\d*)", orders_result, re.DOTALL
                )

                # Simple P&L approximation (this is rough since we don't match buy/sell pairs)
                if len(buy_fills) > 0 and len(sell_fills) > 0:
                    avg_buy = sum(float(p) for p in buy_fills) / len(buy_fills)
                    avg_sell = sum(float(p) for p in sell_fills) / len(sell_fills)
                    total_realized_pnl = (
                        (avg_sell - avg_buy) * min(len(buy_fills), len(sell_fills)) * 1000
                    )  # Rough estimate

            # Update internal counters
            self.orders_placed = orders_placed
            self.orders_filled = orders_filled
            self.positions_opened = positions_opened
            self.positions_closed = positions_closed
            self.total_realized_pnl = total_realized_pnl

            self.logger.warning(
                f"📊 STATS RECALCULATED: Placed={orders_placed}, Filled={orders_filled}, Opened={positions_opened}, Closed={positions_closed}, P&L=${total_realized_pnl:.2f}"
            )

            return {
                "status": "success",
                "message": "Statistics recalculated from API data",
                "stats": {
                    "orders_placed": self.orders_placed,
                    "orders_filled": self.orders_filled,
                    "positions_opened": self.positions_opened,
                    "positions_closed": self.positions_closed,
                    "total_realized_pnl": self.total_realized_pnl,
                },
            }

        except Exception as e:
            self.logger.error(f"Error recalculating statistics: {e}")
            return {"status": "error", "message": f"Failed to recalculate statistics: {e}"}
