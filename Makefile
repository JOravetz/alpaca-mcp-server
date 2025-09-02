# Makefile for alpaca-mcp-server-enhanced
# Ensures all Python commands use the correct uv environment

.PHONY: help run-script news server web-service monitoring test lint format clean install

# Default target
help:
	@echo "Available commands:"
	@echo "  make run-script SCRIPT=path/to/script.py  - Run any Python script"
	@echo "  make news SYMBOLS='AAPL MSFT'            - Fetch news for stocks"
	@echo "  make server                               - Start MCP server"
	@echo "  make web-service                          - Start MCP Execution Service (REST API port 8002)"
	@echo "  make monitoring                           - Start monitoring service (FastAPI port 8001)"
	@echo "  make test                                 - Run test suite"
	@echo "  make lint                                 - Run code quality checks"
	@echo "  make format                               - Auto-format code"
	@echo "  make clean                                - Clean cache and temp files"
	@echo "  make install                              - Install/sync dependencies"

# Run any Python script with uv
run-script:
	@if [ -z "$(SCRIPT)" ]; then \
		echo "Error: Please specify SCRIPT=path/to/script.py"; \
		exit 1; \
	fi
	uv run python $(SCRIPT) $(ARGS)

# Fetch stock news
news:
	@if [ -z "$(SYMBOLS)" ]; then \
		echo "Error: Please specify SYMBOLS='AAPL MSFT'"; \
		exit 1; \
	fi
	uv run python ./external_tools/news_scrapers/yf_rss.py $(SYMBOLS)

# Start MCP server
server:
	uv run python -m alpaca_mcp_server.main

# Start MCP Execution Service (REST API on port 8002)
web-service:
	uv run python -m alpaca_mcp_server.web.mcp_execution_service

# Start monitoring service (FastAPI dashboard on port 8001)  
monitoring:
	uv run python -m alpaca_mcp_server.monitoring.fastapi_service

# Run test suite
test:
	uv run pytest --cov=alpaca_mcp_server --cov-report=html

# Quick tests
test-quick:
	uv run python alpaca_mcp_server/tests/run_focused_tests.py

# Code quality checks
lint:
	uv run ruff check alpaca_mcp_server/
	uv run mypy alpaca_mcp_server/

# Auto-format code
format:
	uv run black alpaca_mcp_server/
	uv run isort alpaca_mcp_server/
	uv run ruff check --fix alpaca_mcp_server/

# Clean cache and temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete

# Install/sync dependencies
install:
	uv sync

# Common Python scripts shortcuts
plot:
	uv run python plot.py $(ARGS)

stock-analyzer:
	uv run python alpaca_mcp_server/utils/stock_analyzer.py $(ARGS)

scanner:
	uv run python alpaca_mcp_server/tools/day_trading_scanner.py $(ARGS)