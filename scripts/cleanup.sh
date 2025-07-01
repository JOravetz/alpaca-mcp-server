# File Cleanup and Reorganization Plan

## 🗑️ **SAFE TO DELETE** (20+ files)

### Test Files (Move to `tests/` or delete)
```bash
# These are development/debugging files scattered in root
rm test_buffer_fix.py
rm test_concurrent_day_trading.py
rm test_corrected_parsing.py
rm test_fastapi_endpoints.py
rm test_fast_functions.py
rm test_final_verification.py
rm test_fixed_parsing.py
rm test_global_config_demo.py
rm test_mcp_protocol.py
rm test_mcp_server.py
rm test_mcp_streaming.py
rm test_peak_trough_direct.py
rm test_stream_buffer.py
rm test_timestamp_parsing.py
rm test_tool_integration.py
```

### Debug Scripts
```bash
rm debug_live_timestamps.py
rm debug_recent.py
rm debug_timestamps.py
rm prove_mcp_fix.py
rm verify_setup.py
```

### Duplicate/Backup Files
```bash
rm peakdetect.py.orig
rm plot.py.backup
rm README.md.backup
```

### Old Development Files
```bash
rm automated_trader.py          # Superseded by monitoring system
rm auto_trader.py              # Duplicate functionality
rm comprehensive_test_summary.py
rm signal_monitor.py           # Integrated into monitoring tools
rm snapshot.py                 # Basic version, advanced in tools/
rm stock_analyzer.py           # Functionality moved to tools/
rm websocket_client.py         # Not used
```

### Cache/Temp Files
```bash
rm -rf __pycache__
rm -rf test_env
```

## 📁 **REORGANIZE**

### Move to `scripts/` directory
```bash
mv cleanup.sh scripts/
mv minute_reporter.sh scripts/
mv monitor_cero_trading.sh scripts/
mv monitor_signals_enhanced.sh scripts/
mv monitor_signals.sh scripts/
mv start_mcp_server_debug.sh scripts/
mv start_mcp_server.sh scripts/
mv start_monitoring.sh scripts/
mv tree.sh scripts/
```

### Move to `data/` or `config/`
```bash
mkdir -p data
mv combined.lis data/
mv momentum.lis data/
mv tickers.py data/            # Or integrate into tools/
```

### Move to `tools/` (standalone tools)
```bash
mv peakdetect.py alpaca_mcp_server/tools/
mv peak_trough_detection_plot.py alpaca_mcp_server/tools/
mv plot.py alpaca_mcp_server/tools/
```

## 📋 **KEEP IN ROOT** (Essential files)

### Core Project Files
- `alpaca_mcp_server/` - Main package ✅
- `pyproject.toml` - Package config ✅
- `requirements.txt` - Dependencies ✅
- `uv.lock` - Lock file ✅
- `LICENSE` - Legal ✅
- `README.md` - Documentation ✅

### Current Operations
- `config/` - Configuration ✅
- `monitoring_data/` - Live data ✅
- `logs/` - System logs ✅
- `scripts/` - Utility scripts ✅

### Documentation (Maybe consolidate)
- `docs/` - Keep main docs ✅
- Consider moving `docs_old/` to `docs/archive/`

## 🎯 **AFTER CLEANUP** (Clean Structure)

```
alpaca-mcp-server-enhanced/
├── alpaca_mcp_server/          # Main package
├── config/                     # Configuration files
├── data/                       # Data files (tickers, lists)
├── docs/                       # Documentation
├── logs/                       # Runtime logs
├── monitoring_data/            # Live monitoring data
├── scripts/                    # Utility scripts
├── LICENSE
├── README.md
├── pyproject.toml
├── requirements.txt
└── uv.lock
```

## 🚀 **Cleanup Commands**

```bash
# 1. Delete test/debug files
rm test_*.py debug_*.py prove_mcp_fix.py verify_setup.py

# 2. Delete backups/duplicates
rm *.orig *.backup

# 3. Delete old development files
rm automated_trader.py auto_trader.py comprehensive_test_summary.py
rm signal_monitor.py snapshot.py stock_analyzer.py websocket_client.py

# 4. Clean cache
rm -rf __pycache__ test_env

# 5. Organize remaining files
mkdir -p data
mv *.lis data/
mv tickers.py data/

# 6. Move scripts (most already in scripts/)
mv *.sh scripts/ 2>/dev/null || true
```

## 💡 **Benefits After Cleanup**

- **~25 fewer files** in root directory
- **Clear separation** of concerns
- **Easier navigation** for new developers
- **Reduced confusion** about what's active vs old
- **Professional project structure**

## ⚠️ **Before Running Cleanup**

1. **Backup** your current state
2. **Test** that your MCP server still works
3. **Update** any scripts that reference moved files
4. **Check** if any files are imported elsewhere

The goal is a **clean, professional structure** that makes it obvious what's important vs what's leftover from development.
