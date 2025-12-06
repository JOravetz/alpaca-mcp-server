# Real Integration Tests: test_streaming_tools_real.py

## Overview
**NO MOCKING** - Real integration tests for `streaming_tools.py` using actual Alpaca API connections and live market data streaming.

## Test Statistics
- **Total Tests**: 19 comprehensive integration tests
- **Pass Rate**: 100% (19/19 when run with proper timing)
- **Test Type**: Real API connections with actual streaming data
- **Execution Time**: ~3-5 minutes (includes wait times for data accumulation)
- **API Requirements**: Valid Alpaca API credentials (APCA_API_KEY_ID, APCA_API_SECRET_KEY)

## Key Differences from Unit Tests
1. **No Mocking**: Uses real Alpaca StockDataStream connections
2. **Real Data**: Receives actual market data (when markets are open)
3. **Timing Sensitive**: Tests include realistic wait times for data accumulation
4. **Connection Limits**: Manages real WebSocket connection limits
5. **Environment Dependent**: Requires valid API credentials
6. **Market Hours Aware**: Some tests may show no data when markets are closed

## Test Coverage by Category

### 1. TestRealStreamHandlers (3 tests)
Tests with actual streaming data collection.

**Tests:**
- ✅ `test_real_stream_startup_and_data_collection` - Full lifecycle: start → collect data → stop
  - Starts stream with real symbols (AAPL, MSFT)
  - Waits 10 seconds for data accumulation
  - Verifies stream status and event collection
  - Duration: ~17 seconds

- ✅ `test_real_trade_data_collection` - Collect actual trade data
  - Streams SPY trades (high liquidity symbol)
  - Waits 15 seconds for trade data
  - Retrieves and validates trade format
  - Note: May show no trades if market is closed
  - Duration: ~22 seconds

- ✅ `test_real_quote_data_collection` - Collect actual quote data
  - Streams AAPL quotes (bid/ask prices)
  - Waits 15 seconds for quote data
  - Validates bid x ask format
  - Note: May show no quotes if market is closed
  - Duration: ~22 seconds

**Real-World Behavior:**
- During market hours: Receives live trades and quotes
- After hours: Connection successful but minimal/no data
- Pre-market/after-hours: May receive quotes but limited trades

### 2. TestRealStreamManagement (4 tests)
Tests stream lifecycle with real WebSocket connections.

**Tests:**
- ✅ `test_real_start_and_stop_stream` - Complete lifecycle test
  - Starts stream with SPY
  - Verifies active status
  - Stops stream and confirms shutdown
  - Duration: ~8 seconds

- ✅ `test_real_prevent_duplicate_streams` - Connection limit enforcement
  - Starts first stream
  - Attempts to start second stream (should fail)
  - Verifies duplicate prevention
  - Requires 5-second wait for stream to become fully active
  - Duration: ~15 seconds

- ✅ `test_real_add_symbols_to_active_stream` - Dynamic symbol addition
  - Starts stream with AAPL
  - Adds MSFT and SPY to active stream
  - Verifies all symbols in subscription list
  - Duration: ~10 seconds

- ✅ `test_real_replace_existing_stream` - Stream replacement
  - Starts stream with AAPL
  - Replaces with new stream (MSFT, SPY)
  - Verifies old stream stopped and new stream active
  - Duration: ~12 seconds

**Connection Management:**
- Alpaca enforces concurrent connection limits
- Tests include cleanup delays to avoid rate limiting
- HTTP 429 errors indicate connection limit exceeded
- Tests automatically retry with exponential backoff

### 3. TestRealStreamDataRetrieval (4 tests)
Tests data access from real streaming buffers.

**Tests:**
- ✅ `test_real_get_stream_data_with_filters` - Data filtering
  - Collects SPY data for 15 seconds
  - Tests: all data, limited data, recent data filters
  - Verifies filter parameters work correctly
  - Duration: ~22 seconds

- ✅ `test_real_buffer_statistics` - Buffer metrics
  - Streams AAPL and MSFT for 15 seconds
  - Retrieves comprehensive buffer statistics
  - Verifies buffer counts and sizes
  - Duration: ~22 seconds

- ✅ `test_real_list_active_streams` - Stream status reporting
  - Starts stream with AAPL and SPY
  - Retrieves active stream configuration
  - Verifies subscription details
  - Duration: ~10 seconds

- ✅ `test_real_clear_buffers` - Buffer management
  - Collects data for 10 seconds
  - Clears all buffers
  - Verifies buffers are empty
  - Duration: ~17 seconds

**Data Volumes (Market Hours):**
- SPY: Typically 100-500 trades/minute
- AAPL: Typically 50-200 trades/minute
- Quotes: Much higher frequency (1000s per minute)

### 4. TestRealStreamAnalysis (2 tests)
Tests stream-aware analysis with real data.

**Tests:**
- ✅ `test_real_stream_aware_price_monitor` - Real-time monitoring
  - Streams SPY for 15 seconds
  - Monitors price, bid/ask spread, volume
  - Validates real-time analysis output
  - Duration: ~22 seconds

- ✅ `test_real_concurrent_data_access` - Concurrent operations
  - Streams AAPL, MSFT, SPY simultaneously
  - Retrieves data for all symbols concurrently
  - Verifies no race conditions or exceptions
  - Duration: ~22 seconds

**Analysis Features:**
- Current price calculation from stream
- Bid-ask spread analysis
- Volume and liquidity metrics
- Trading conditions assessment

### 5. TestRealStreamEdgeCases (6 tests)
Tests edge cases and error conditions with real API.

**Tests:**
- ✅ `test_real_stream_with_lowercase_symbols` - Symbol normalization
  - Starts stream with lowercase symbols ("aapl", "msft")
  - Verifies conversion to uppercase
  - Duration: ~7 seconds

- ✅ `test_real_stream_data_when_no_stream_active` - Error handling
  - Attempts to get data without active stream
  - Verifies appropriate error message
  - Duration: <1 second

- ✅ `test_real_add_symbols_without_active_stream` - Error handling
  - Attempts to add symbols without active stream
  - Verifies appropriate error message
  - Duration: ~2 seconds

- ✅ `test_real_stream_invalid_data_type` - Input validation
  - Attempts stream with invalid data type
  - Verifies validation error message
  - Duration: ~2 seconds

- ✅ `test_real_stream_invalid_feed` - Feed validation
  - Attempts stream with invalid feed
  - Verifies feed validation (sip/iex only)
  - Duration: ~2 seconds

- ✅ `test_real_stream_runtime_statistics` - Timing accuracy
  - Runs stream for 10 seconds
  - Verifies runtime statistics are accurate
  - Compares reported vs actual runtime
  - Duration: ~12 seconds

## Real-World Observations

### Market Hours Behavior
**During Regular Hours (9:30 AM - 4:00 PM ET):**
- High trade frequency (100s-1000s per minute)
- Continuous quote updates
- Tests typically collect significant data

**Pre-Market (4:00 AM - 9:30 AM ET):**
- Lower trade frequency
- Quotes still active
- Some tests may show limited data

**After Hours (4:00 PM - 8:00 PM ET):**
- Minimal trade activity
- Quote updates less frequent
- Tests verify connection, may not collect much data

**Closed Market (Evenings, Weekends):**
- WebSocket connection successful
- No trade or quote data received
- Tests verify infrastructure, not data

### Connection Limits
**Alpaca API Limits:**
- Maximum concurrent WebSocket connections per account
- Rate limits on connection attempts
- Tests manage this via:
  - Proper cleanup between tests
  - Wait times after stream stop
  - Connection limit error handling

**Error Messages Seen:**
```
ValueError: connection limit exceeded
HTTP 429: Too Many Requests
```

**Mitigation:**
- 2-5 second waits between tests
- Proper stream cleanup
- Exponential backoff on retries

### Data Feed Differences
**IEX Feed (Free):**
- IEX exchange data only
- Lower quote/trade frequency
- Suitable for testing
- Used in most tests

**SIP Feed (Paid):**
- All exchanges aggregated
- Higher data frequency
- Requires paid subscription
- More expensive for testing

## Test Fixtures

### `check_credentials`
```python
@pytest.fixture(scope="module")
def check_credentials():
    """Check if API credentials are available"""
    has_creds = os.getenv("APCA_API_KEY_ID") and os.getenv("APCA_API_SECRET_KEY")
    if not has_creds:
        pytest.skip("Alpaca API credentials not found in environment")
    return has_creds
```

**Purpose:** Skip tests if credentials not available
**Scope:** Module-level (once per test file)

### `test_symbols`
```python
@pytest.fixture(scope="module")
def test_symbols():
    """High-liquidity symbols for testing"""
    return ["AAPL", "MSFT", "SPY"]
```

**Symbols Chosen:**
- SPY: S&P 500 ETF - extremely liquid
- AAPL: Apple - high volume stock
- MSFT: Microsoft - high volume stock

### `cleanup_streams`
```python
@pytest.fixture(scope="module")
async def cleanup_streams():
    """Cleanup fixture to ensure streams are stopped after tests"""
    yield
    try:
        await streaming_tools.stop_global_stock_stream()
        await streaming_tools.clear_stock_stream_buffers()
    except Exception as e:
        print(f"Cleanup error: {e}")
    await asyncio.sleep(2)
```

**Purpose:** Ensure clean state after test module
**Critical:** Prevents connection leaks

## Running the Tests

### Run All Tests
```bash
uv run pytest alpaca_mcp_server/tests/integration/test_streaming_tools_real.py -v -s
```

### Run Specific Test Class
```bash
uv run pytest alpaca_mcp_server/tests/integration/test_streaming_tools_real.py::TestRealStreamHandlers -v -s
```

### Run Single Test
```bash
uv run pytest alpaca_mcp_server/tests/integration/test_streaming_tools_real.py::TestRealStreamHandlers::test_real_stream_startup_and_data_collection -v -s
```

### Run with Timing Info
```bash
uv run pytest alpaca_mcp_server/tests/integration/test_streaming_tools_real.py --durations=10
```

### Run with Debug Output
```bash
uv run pytest alpaca_mcp_server/tests/integration/test_streaming_tools_real.py -vv -s --tb=long
```

## Environment Setup

### Required Environment Variables
```bash
export APCA_API_KEY_ID="your_alpaca_key"
export APCA_API_SECRET_KEY="your_alpaca_secret"
export PAPER="true"  # Use paper trading account
```

### Alternative Names (Also Supported)
```bash
export ALPACA_API_KEY="your_alpaca_key"
export ALPACA_SECRET_KEY="your_alpaca_secret"
```

## Performance Characteristics

### Typical Test Execution Times
- **Quick tests** (error handling): <1-2 seconds
- **Basic lifecycle tests**: 7-10 seconds
- **Data collection tests**: 15-25 seconds (includes wait for data)
- **Full test suite**: 3-5 minutes

### Wait Times Explained
- **2 seconds**: Stream initialization/cleanup
- **5 seconds**: Stream to become fully active
- **10-15 seconds**: Data accumulation for testing
- **Extra delays**: Avoid connection limit errors

## Debugging Tips

### If Tests Fail

**1. Check Credentials**
```bash
echo $APCA_API_KEY_ID
echo $APCA_API_SECRET_KEY
```

**2. Verify API Access**
```bash
curl -u "$APCA_API_KEY_ID:$APCA_API_SECRET_KEY" \
  https://paper-api.alpaca.markets/v2/account
```

**3. Check Connection Limits**
- Error: "connection limit exceeded"
- Solution: Wait 60 seconds between test runs
- Increase wait times in tests

**4. Market Hours**
- If no data received, check if market is open
- Tests should pass regardless (they check connection)

**5. Rate Limiting**
- Error: HTTP 429
- Solution: Reduce test frequency
- Add longer waits between tests

### Common Issues

**Issue**: `connection limit exceeded`
**Cause**: Too many concurrent connections
**Fix**: Increase wait times, ensure cleanup

**Issue**: No data received
**Cause**: Market is closed
**Fix**: Expected behavior, tests should still pass

**Issue**: Tests timeout
**Cause**: Waiting for data that never arrives
**Fix**: Check stream initialization logs

## Test Quality Indicators

### ✅ Strengths
1. **Real API Testing** - Validates actual Alpaca integration
2. **Market Hours Aware** - Tests work regardless of market state
3. **Proper Cleanup** - Prevents connection leaks
4. **Error Handling** - Tests both success and failure paths
5. **Realistic Timing** - Waits match real-world usage patterns
6. **Connection Management** - Handles rate limits gracefully

### 🎯 What's Tested
- ✅ Real WebSocket connections
- ✅ Actual data streaming (when available)
- ✅ Connection lifecycle management
- ✅ Error handling and recovery
- ✅ Buffer management with real data
- ✅ Concurrent operations
- ✅ Input validation
- ✅ Rate limit handling

### 📊 Real-World Validation
- Tests verify the system works with Alpaca's actual API
- Validates connection management under real constraints
- Confirms error handling matches API behavior
- Ensures timing is realistic for production use

## Maintenance Notes

### When to Update Tests
1. **Alpaca API Changes** - Update connection parameters
2. **New Features** - Add tests for new streaming capabilities
3. **Connection Limits Change** - Adjust wait times
4. **New Error Conditions** - Add error handling tests

### Best Practices
1. Always stop streams in cleanup
2. Wait 2-5 seconds between tests
3. Use high-liquidity symbols (SPY, AAPL)
4. Test with IEX feed (free tier)
5. Include timing information in test names
6. Handle market hours gracefully

## Comparison: Unit vs Integration Tests

| Aspect | Unit Tests | Integration Tests (This File) |
|--------|-----------|-------------------------------|
| Mocking | Extensive | None - real API |
| Speed | Fast (~5s total) | Slower (~5min total) |
| API Calls | None | Real API calls |
| Data | Synthetic | Real market data |
| Reliability | 100% consistent | Depends on API/market |
| Cost | Free | API rate limits |
| Purpose | Code logic | Real-world validation |

## Conclusion
These integration tests provide **real-world validation** of the streaming_tools module against Alpaca's actual API. They verify that:
- WebSocket connections work correctly
- Data streaming functions as expected
- Error handling matches real API behavior
- Connection management is robust
- The system handles market hours appropriately

**Test Status**: ✅ 19/19 tests passing with real API connections

**Best Use**: Run before releases to validate Alpaca API integration

**CI/CD**: Can be included in nightly builds with proper credentials
