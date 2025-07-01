# Multi-stage Docker build for Alpaca MCP Server
FROM python:3.12-slim as builder

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Production stage
FROM python:3.12-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PAPER=true

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY alpaca_mcp_server/ ./alpaca_mcp_server/
COPY README.md LICENSE ./

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs /app/monitoring_data \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import alpaca_mcp_server; print('OK')" || exit 1

# Default command
CMD ["python", "-m", "alpaca_mcp_server.server"]

# Development stage
FROM production as development

# Switch back to root for dev tools installation
USER root

# Install development dependencies
RUN pip install uv && uv sync --dev

# Install pre-commit for development
RUN pip install pre-commit

# Switch back to appuser
USER appuser

# Override command for development
CMD ["python", "-m", "alpaca_mcp_server.server"]