# Multi-stage build for FinGPT Backend
# Optimized for layer caching and fast rebuilds

# ==========================================
# Stage 1: UV installer (cached separately)
FROM python:3.12-slim AS uv-installer

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv (this layer is cached unless uv version changes)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# ==========================================
# Stage 2: Dependencies builder
FROM python:3.12-slim AS builder

# Copy uv from previous stage
COPY --from=uv-installer /root/.local /root/.local
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy only dependency files first (better caching)
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies
# This layer is cached unless dependencies change
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv && \
    uv sync --python 3.12 --frozen --no-dev

# ==========================================
# Stage 3: Playwright installer (separate for caching)
FROM python:3.12-slim AS playwright-installer

# Install minimal Playwright dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv

# Install Playwright browsers (chromium and chrome) with system dependencies
# This runs as root, so --with-deps can install system packages
RUN /app/.venv/bin/playwright install chromium chrome --with-deps

# ==========================================
# Stage 4: Final production image
FROM python:3.12-slim

# Install only runtime dependencies (smaller set)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxss1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install MCP servers globally to improve startup time and reliability
RUN npm install -g @modelcontextprotocol/server-filesystem @playwright/mcp

# Create non-root user
RUN groupadd -r fingpt && useradd -r -g fingpt -u 1000 fingpt \
    && mkdir -p /app /home/fingpt/.cache && chown -R fingpt:fingpt /app /home/fingpt

WORKDIR /app

# Copy Playwright browser cache from playwright-installer stage
COPY --from=playwright-installer --chown=fingpt:fingpt /root/.cache/ms-playwright /home/fingpt/.cache/ms-playwright

# Copy virtual environment from builder
COPY --from=builder --chown=fingpt:fingpt /app/.venv /app/.venv

# Set environment variables before copying app code
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=django_config.settings \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy application code (changes frequently, so last)
COPY --chown=fingpt:fingpt . .

# Normalize line endings and ensure entrypoint is executable
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R fingpt:fingpt /app

# Switch to non-root user
USER fingpt

# Browsers already installed in playwright-installer stage and copied at line 96
# No need to install again here

# Entrypoint handles optional collectstatic before launching Gunicorn
ENTRYPOINT ["/app/entrypoint.sh"]

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=2m --timeout=10s --start-period=1m --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1

# Use array form for better signal handling
CMD ["gunicorn", \
    "django_config.wsgi:application", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "2", \
    "--threads", "4", \
    "--timeout", "120", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "--worker-tmp-dir", "/dev/shm", \
    "--worker-class", "sync"]
