# UniFi MCP Server - Multi-stage Docker Build
# Optimized for minimal image size and security

# Stage 1: Builder
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency files first (for layer caching)
COPY pyproject.toml ./
COPY README.md ./

# Copy source code
COPY src/ ./src/

# Install dependencies and build wheel
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir build && \
    python -m build --wheel

# Stage 2: Runtime
FROM python:3.11-slim

# Metadata
LABEL maintainer="Austin Anderson <austinanderson94@proton.me>"
LABEL description="Model Context Protocol server for UniFi Network Controller"
LABEL version="0.1.0"

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash unifi && \
    mkdir -p /app /config && \
    chown -R unifi:unifi /app /config

# Set working directory
WORKDIR /app

# Copy wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/

# Install the package and runtime dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /tmp/*.whl && \
    rm -rf /tmp/*.whl /root/.cache

# Copy configuration template
COPY --chown=unifi:unifi .env.example /config/.env.example

# Switch to non-root user
USER unifi

# Environment variables with defaults
ENV UNIFI_HOST="" \
    UNIFI_PORT="443" \
    UNIFI_SITE="default" \
    UNIFI_VERIFY_SSL="false" \
    UNIFI_API_KEY="" \
    UNIFI_USERNAME="" \
    UNIFI_PASSWORD="" \
    LOG_LEVEL="INFO" \
    PYTHONUNBUFFERED="1"

# Health check (optional - checks if Python can import the package)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import unifi_mcp; print('OK')" || exit 1

# Expose no ports (stdio-based MCP server)
# MCP servers communicate via stdin/stdout, not network ports

# Entry point
ENTRYPOINT ["python", "-m", "unifi_mcp"]

# Default command (can be overridden)
CMD []
