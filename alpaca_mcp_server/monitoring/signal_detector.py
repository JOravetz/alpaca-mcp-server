"""Signal Detector - Automated trading signal detection

Uses existing MCP tools to detect fresh trading signals for the watchlist,
providing the intelligence layer for the hybrid trading system.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

from ..tools.market_data_tools import get_stock_snapshots

# Import existing MCP tools for signal detection
from ..tools.peak_trough_analysis_tool import (
    analyze_peaks_and_troughs_with_plot_py as get_stock_peak_trough_analysis,
)


class SignalDetector:
    """
    Automated signal detection using existing MCP tools.

    This class provides intelligent signal detection by:
    1. Using peak/trough analysis to identify fresh signals
    2. Validating signals with streaming data
    3. Confirming liquidity with snapshot data
    4. Ranking signals by confidence score
    """

    def __init__(self):
        self.logger = logging.getLogger("signal_detector")

        # Load global configuration
        from ..config.global_config import get_global_config, get_technical_config

        self.config = get_global_config()
        self.tech_config = get_technical_config()

        # Detection state
        self.last_scan: datetime | None = None
        self.scan_count = 0
        self.signals_detected = 0
        self.error_count = 0

        # Signal parameters from global config
        self.hanning_window = self.tech_config.hanning_window_samples
        self.lookahead = self.tech_config.peak_trough_lookahead
        self.fresh_signal_bars = self.hanning_window  # Signal must be within hanning window samples
        self.min_volume_threshold = 100000

        # Cache for recent scans to avoid duplicate signals
        self.recent_signals: dict[str, dict] = {}
        self.signal_cache_duration = 300  # 5 minutes

        self.logger.info(
            f"SignalDetector initialized with global config: window={self.hanning_window}, lookahead={self.lookahead}"
        )

    async def scan_for_signals(self, symbols: list[str]) -> list[dict]:
        """
        Scan watchlist symbols for trading signals.

        Args:
            symbols: List of symbols to scan

        Returns:
            List of all detected signals
        """
        self.last_scan = datetime.now(UTC)
        self.scan_count += 1

        all_signals = []

        try:
            # Clean expired signals from cache
            self._clean_signal_cache()

            # Process symbols in batches for efficiency
            batch_size = 5
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i : i + batch_size]

                # Run peak/trough analysis for batch
                batch_signals = await self._analyze_symbol_batch(batch)
                all_signals.extend(batch_signals)

                # Small delay to avoid overwhelming the API
                if i + batch_size < len(symbols):
                    await asyncio.sleep(0.5)

            # Update detection stats
            self.signals_detected += len(all_signals)

            if all_signals:
                self.logger.info(
                    f"🎯 Detected {len(all_signals)} signals " f"from {len(symbols)} symbols"
                )

            return all_signals

        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Error in signal scanning: {e}")
            return []

    async def _analyze_symbol_batch(self, symbols: list[str]) -> list[dict]:
        """Analyze a batch of symbols for signals"""
        signals = []

        for symbol in symbols:
            try:
                # Skip if we recently detected a signal for this symbol
                if self._has_recent_signal(symbol):
                    continue

                # Get peak/trough analysis using existing MCP tool with global config values
                analysis_result = await get_stock_peak_trough_analysis(
                    symbols=symbol,
                    timeframe="1Min",
                    days=1,
                    window_len=self.hanning_window,  # Use global config value (11)
                    lookahead=self.lookahead,  # Use global config value (1)
                )

                # Parse analysis for signals
                symbol_signals = await self._parse_peak_trough_analysis(symbol, analysis_result)
                signals.extend(symbol_signals)

            except Exception as e:
                self.logger.warning(f"Error analyzing {symbol}: {e}")
                continue

        return signals

    async def _parse_peak_trough_analysis(self, symbol: str, analysis_result: str) -> list[dict]:
        """Parse peak/trough analysis result for trading signals from plot.py output"""
        signals = []

        try:
            # Look for the "LATEST PEAK/TROUGH SIGNALS" section in plot.py output
            lines = analysis_result.split("\n")

            in_signals_section = False

            for line in lines:
                # Check if we're in the signals table section
                if "LATEST PEAK/TROUGH SIGNALS" in line:
                    in_signals_section = True
                    continue
                elif "Signals found:" in line and in_signals_section:
                    break  # End of signals section
                elif not in_signals_section:
                    continue

                # Skip header and separator lines
                if (
                    "Symbol" in line and "Signal" in line and "Ago" in line
                ) or line.strip().startswith("--"):
                    continue

                # Parse signal line format: "AAPL       ^P      4       201.1500       200.9837      -0.1663     -0.08%       24/06/2025 10:34"
                if symbol in line and ("^P" in line or "vT" in line):
                    signal = await self._extract_signal_from_plot_line(
                        symbol, line, analysis_result
                    )
                    if signal:
                        signals.append(signal)
                        self.logger.info(
                            f"🎯 Found signal for {symbol}: {signal['signal_type']} {signal['bars_ago']} bars ago"
                        )

            # Cache any detected signals
            if signals:
                for signal in signals:
                    self._cache_signal(symbol, signal)

        except Exception as e:
            self.logger.error(f"Error parsing plot.py analysis for {symbol}: {e}")

        return signals

    async def _extract_signal_from_plot_line(
        self, symbol: str, line: str, full_analysis: str
    ) -> dict | None:
        """Extract signal from plot.py output line format"""
        try:
            import pytz

            # Parse line format: "    AAPL       ^P      8       201.2400       201.0100      -0.2300     -0.11%       24/06/2025 10:25"
            parts = line.split()
            if len(parts) < 8:
                return None

            signal_symbol = parts[0].strip()
            if signal_symbol != symbol:
                return None

            signal_indicator = parts[1].strip()  # ^P for peak, vT for trough
            bars_ago = int(parts[2].strip())
            signal_price = float(parts[3].strip())
            current_price = float(parts[4].strip())

            # Apply max stock price filter from global config
            if current_price > self.config.trading.max_stock_price:
                self.logger.debug(
                    f"Skipping {symbol} - price ${current_price:.2f} exceeds max ${self.config.trading.max_stock_price}"
                )
                return None

            # Determine signal type
            if signal_indicator == "^P":
                signal_type = "fresh_peak"
                action = "sell_candidate"
            elif signal_indicator == "vT":
                signal_type = "fresh_trough"
                action = "buy_candidate"
            else:
                return None

            # Check if signal is fresh enough
            if bars_ago > self.fresh_signal_bars:
                self.logger.debug(
                    f"Signal for {symbol} is {bars_ago} bars ago, threshold is {self.fresh_signal_bars}"
                )
                return None

            # Validate signal
            is_valid = await self._validate_signal(
                symbol, signal_price, signal_type.replace("fresh_", "")
            )
            if not is_valid:
                return None

            # Convert to NYC/EDT timezone
            utc_now = datetime.now(UTC)
            nyc_tz = pytz.timezone("America/New_York")
            nyc_time = utc_now.astimezone(nyc_tz)

            signal = {
                "symbol": symbol,
                "signal_type": signal_type,
                "price": signal_price,
                "current_price": current_price,
                "bars_ago": bars_ago,
                "action": action,
                "detected_at": nyc_time.isoformat(),
                "source": "plot_py_analysis",
            }

            return signal

        except Exception as e:
            self.logger.error(f"Error extracting signal from plot line for {symbol}: {e}")
            return None

    async def _extract_signal_from_summary(
        self, symbol: str, line: str, full_analysis: str
    ) -> dict | None:
        """Extract signal from trading signal summary line"""
        try:
            # Parse line like: "📊 Last signal: PEAK at sample 381 ($1.5700)"
            import re

            import pytz

            # Extract signal type
            signal_type = None
            if "PEAK" in line.upper():
                signal_type = "fresh_peak"
            elif "TROUGH" in line.upper():
                signal_type = "fresh_trough"
            else:
                return None

            # Extract price
            price_match = re.search(r"\$(\d+\.?\d*)", line)
            price = float(price_match.group(1)) if price_match else None

            # Apply max stock price filter from global config
            if price and price > self.config.trading.max_stock_price:
                self.logger.debug(
                    f"Skipping {symbol} - price ${price:.2f} exceeds max ${self.config.trading.max_stock_price}"
                )
                return None

            # Look for bars ago information in the analysis context
            bars_ago = self._find_bars_ago_in_analysis(full_analysis, symbol, signal_type)

            # DEBUG: Print signal parsing results
            print(
                f"🔍 SIGNAL DEBUG - {symbol}: {signal_type}, price=${price}, bars_ago={bars_ago}, threshold={self.fresh_signal_bars}"
            )

            # Only accept truly fresh signals (≤5 bars ago)
            if bars_ago is None or bars_ago > self.fresh_signal_bars:
                print(
                    f"❌ REJECTED - {symbol}: bars_ago={bars_ago} > threshold={self.fresh_signal_bars}"
                )
                return None

            print(f"✅ ACCEPTED - {symbol}: Fresh signal detected!")

            # Validate signal
            is_valid = await self._validate_signal(symbol, price, signal_type.replace("fresh_", ""))
            if not is_valid:
                return None

            action = "buy_candidate" if signal_type == "fresh_trough" else "sell_candidate"

            # Convert to NYC/EDT timezone
            utc_now = datetime.now(UTC)
            nyc_tz = pytz.timezone("America/New_York")
            nyc_time = utc_now.astimezone(nyc_tz)

            signal = {
                "symbol": symbol,
                "signal_type": signal_type,
                "price": price,
                "bars_ago": bars_ago,
                "action": action,
                "detected_at": nyc_time.isoformat(),
                "source": "peak_trough_analysis",
            }

            return signal

        except Exception as e:
            self.logger.error(f"Error extracting signal from summary for {symbol}: {e}")
            return None

    async def _extract_latest_signal(
        self, symbol: str, line: str, signal_type: str, full_analysis: str
    ) -> dict | None:
        """Extract signal from latest peak/trough line"""
        try:
            # Parse line like: "Latest peak: Sample 381, $1.5700 (7 bars ago)"
            import re

            import pytz

            # Extract price
            price_match = re.search(r"\$(\d+\.?\d*)", line)
            price = float(price_match.group(1)) if price_match else None

            # Extract bars ago
            bars_match = re.search(r"\((\d+)\s+bars?\s+ago\)", line)
            bars_ago = int(bars_match.group(1)) if bars_match else None

            if bars_ago is None or bars_ago > self.fresh_signal_bars * 2:  # Allow some flexibility
                return None

            # Validate signal
            is_valid = await self._validate_signal(symbol, price, signal_type)
            if not is_valid:
                return None

            signal_type_name = f"fresh_{signal_type}"
            action = "buy_candidate" if signal_type == "trough" else "sell_candidate"

            # Convert to NYC/EDT timezone
            utc_now = datetime.now(UTC)
            nyc_tz = pytz.timezone("America/New_York")
            nyc_time = utc_now.astimezone(nyc_tz)

            signal = {
                "symbol": symbol,
                "signal_type": signal_type_name,
                "price": price,
                "bars_ago": bars_ago,
                "action": action,
                "detected_at": nyc_time.isoformat(),
                "source": "peak_trough_analysis",
            }

            return signal

        except Exception as e:
            self.logger.error(f"Error extracting latest signal for {symbol}: {e}")
            return None

    async def _extract_trough_signal(
        self, symbol: str, line: str, full_analysis: str
    ) -> dict | None:
        """Extract trough signal from analysis line"""
        try:
            # Parse the line to extract trough information
            # Example: "Fresh trough detected at $150.25 (2 bars ago)"

            # Look for price in the line
            price = None
            bars_ago = None

            # Extract price (look for $ followed by number)
            import re

            price_match = re.search(r"\$?(\d+\.?\d*)", line)
            if price_match:
                price = float(price_match.group(1))

            # Extract bars ago
            bars_match = re.search(r"(\d+)\s+bars?\s+ago", line)
            if bars_match:
                bars_ago = int(bars_match.group(1))

            # Only consider fresh signals
            if bars_ago is None or bars_ago > self.fresh_signal_bars:
                return None

            # Validate with additional data
            is_valid = await self._validate_signal(symbol, price, "trough")
            if not is_valid:
                return None

            # Convert to NYC/EDT timezone
            import pytz

            utc_now = datetime.now(UTC)
            nyc_tz = pytz.timezone("America/New_York")
            nyc_time = utc_now.astimezone(nyc_tz)

            signal = {
                "symbol": symbol,
                "signal_type": "fresh_trough",
                "price": price,
                "bars_ago": bars_ago,
                "action": "buy_candidate",
                "detected_at": nyc_time.isoformat(),
                "source": "peak_trough_analysis",
            }

            return signal

        except Exception as e:
            self.logger.error(f"Error extracting trough signal for {symbol}: {e}")
            return None

    async def _extract_peak_signal(self, symbol: str, line: str, full_analysis: str) -> dict | None:
        """Extract peak signal from analysis line"""
        try:
            # Similar to trough extraction but for peaks (sell signals)
            import re

            price = None
            bars_ago = None

            price_match = re.search(r"\$?(\d+\.?\d*)", line)
            if price_match:
                price = float(price_match.group(1))

            bars_match = re.search(r"(\d+)\s+bars?\s+ago", line)
            if bars_match:
                bars_ago = int(bars_match.group(1))

            if bars_ago is None or bars_ago > self.fresh_signal_bars:
                return None

            is_valid = await self._validate_signal(symbol, price, "peak")
            if not is_valid:
                return None

            # Convert to NYC/EDT timezone
            import pytz

            utc_now = datetime.now(UTC)
            nyc_tz = pytz.timezone("America/New_York")
            nyc_time = utc_now.astimezone(nyc_tz)

            signal = {
                "symbol": symbol,
                "signal_type": "fresh_peak",
                "price": price,
                "bars_ago": bars_ago,
                "action": "sell_candidate",
                "detected_at": nyc_time.isoformat(),
                "source": "peak_trough_analysis",
            }

            return signal

        except Exception as e:
            self.logger.error(f"Error extracting peak signal for {symbol}: {e}")
            return None

    def _find_bars_ago_in_analysis(
        self, analysis: str, symbol: str, signal_type: str
    ) -> int | None:
        """Find the actual bars ago for the latest signal in the analysis"""
        try:
            import re

            print(f"🔎 PARSING DEBUG - {symbol}: Looking for {signal_type} bars_ago in analysis")
            lines = analysis.split("\n")

            # Look for the symbol section
            in_symbol_section = False
            for line in lines:
                if line.strip().startswith(f"## {symbol}"):
                    in_symbol_section = True
                    continue
                elif line.strip().startswith("## ") and not line.strip().startswith(f"## {symbol}"):
                    in_symbol_section = False
                    continue

                if not in_symbol_section:
                    continue

                # Look for the trading signal summary with bars ago
                if "Last signal:" in line and ("PEAK" in line.upper() or "TROUGH" in line.upper()):
                    # Check if signal type matches
                    line_upper = line.upper()
                    if (signal_type == "fresh_peak" and "PEAK" in line_upper) or (
                        signal_type == "fresh_trough" and "TROUGH" in line_upper
                    ):
                        # Look for pattern like "(15 bars ago)" in the analysis section
                        # Search in the next few lines for bars ago information
                        for _i, check_line in enumerate(
                            lines[lines.index(line) : lines.index(line) + 5]
                        ):
                            bars_match = re.search(r"\((\d+)\s+bars?\s+ago\)", check_line)
                            if bars_match:
                                return int(bars_match.group(1))

                        # If no explicit bars ago found, look for latest peak/trough line
                        latest_line = None
                        if signal_type == "fresh_peak":
                            for check_line in lines:
                                if "Latest peak:" in check_line and symbol in analysis:
                                    latest_line = check_line
                                    break
                        else:
                            for check_line in lines:
                                if "Latest trough:" in check_line and symbol in analysis:
                                    latest_line = check_line
                                    break

                        if latest_line:
                            print(f"🔍 FOUND latest line for {symbol}: {latest_line}")
                            # Extract bars ago from latest line
                            bars_match = re.search(r"\((\d+)\s+bars?\s+ago\)", latest_line)
                            if bars_match:
                                bars_ago_value = int(bars_match.group(1))
                                print(f"📊 EXTRACTED bars_ago for {symbol}: {bars_ago_value}")
                                return bars_ago_value

            # If no bars ago found, signal is likely stale
            print(f"⚠️ NO bars_ago found for {symbol} - returning 999 (stale)")
            return 999  # Very high number to indicate stale signal

        except Exception as e:
            self.logger.error(f"Error finding bars ago for {symbol}: {e}")
            return 999

    def _calculate_signal_confidence(self, bars_ago: int, signal_type: str, analysis: str) -> float:
        """Calculate confidence score for a signal"""
        try:
            # Base confidence from freshness (fresher = higher confidence)
            freshness_score = max(0, 1.0 - (bars_ago / self.fresh_signal_bars))

            # Bonus for signal quality indicators in analysis
            quality_bonus = 0

            # Look for quality indicators in the analysis text
            quality_keywords = {
                "high volume": 0.1,
                "strong momentum": 0.1,
                "confirmed": 0.15,
                "significant": 0.1,
                "clear pattern": 0.1,
            }

            analysis_lower = analysis.lower()
            for keyword, bonus in quality_keywords.items():
                if keyword in analysis_lower:
                    quality_bonus += bonus  # type: ignore[assignment]

            # Combine scores
            confidence = min(1.0, freshness_score * 0.7 + quality_bonus)

            return confidence

        except Exception:
            return 0.5  # Default confidence

    async def _validate_signal(self, symbol: str, price: float | None, signal_type: str) -> bool:
        """Validate signal with additional market data"""
        try:
            # Get current snapshot for volume validation
            snapshot_result = await get_stock_snapshots(symbols=symbol)

            if isinstance(snapshot_result, dict) and "snapshots" in snapshot_result:
                snapshots = snapshot_result["snapshots"]
                if symbol in snapshots:
                    snapshot = snapshots[symbol]

                    # Check volume threshold
                    daily_volume = snapshot.get("daily_volume", 0)
                    if daily_volume < self.min_volume_threshold:
                        return False

                    # Check if price is reasonable vs current market
                    current_price = snapshot.get("latest_trade", {}).get("price")
                    if price and current_price:
                        price_diff = abs(price - current_price) / current_price
                        if price_diff > 0.1:  # Price too far from current (>10%)
                            return False

            return True

        except Exception as e:
            self.logger.warning(f"Error validating signal for {symbol}: {e}")
            return True  # Default to valid if validation fails

    def _has_recent_signal(self, symbol: str) -> bool:
        """Check if we have a recent signal for this symbol"""
        if symbol not in self.recent_signals:
            return False

        last_signal_time = self.recent_signals[symbol].get("timestamp", 0)
        return (time.time() - last_signal_time) < self.signal_cache_duration

    def _cache_signal(self, symbol: str, signal: dict) -> Any:  # type: ignore[name-defined]
        """Cache a signal to avoid duplicates"""
        self.recent_signals[symbol] = {"signal": signal, "timestamp": time.time()}

    def _clean_signal_cache(self):
        """Remove expired signals from cache"""
        current_time = time.time()
        expired_symbols = [
            symbol
            for symbol, data in self.recent_signals.items()
            if (current_time - data.get("timestamp", 0)) > self.signal_cache_duration
        ]

        for symbol in expired_symbols:
            del self.recent_signals[symbol]

    def get_status(self) -> dict:
        """Get signal detector status"""
        return {
            "active": True,
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "scan_count": self.scan_count,
            "signals_detected": self.signals_detected,
            "error_count": self.error_count,
            "cached_signals": len(self.recent_signals),
            "parameters": {
                "fresh_signal_bars": self.fresh_signal_bars,
                "min_volume_threshold": self.min_volume_threshold,
            },
        }


# Future enhancement: Multi-timeframe signal detection
class MultiTimeframeSignalDetector:
    """
    Future implementation for multi-timeframe signal analysis.

    This will combine signals from multiple timeframes (1min, 5min, 15min)
    to increase signal confidence and reduce false positives.
    """

    def __init__(self, base_detector: SignalDetector):
        self.base_detector = base_detector
        self.logger = logging.getLogger("multi_timeframe_detector")

    async def analyze_multi_timeframe(self, symbol: str) -> dict:
        """Analyze signal across multiple timeframes"""
        # Future implementation:
        # 1. Run analysis on 1min, 5min, 15min timeframes
        # 2. Combine signals for higher confidence
        # 3. Weight newer timeframes more heavily
        # 4. Return consensus signal with high confidence

        self.logger.info("Multi-timeframe analysis planned for Phase 2")
        return {}
