# Use official Playwright image which has browsers pre-installed and dependencies met
# This avoids the "browser not found" and missing dependency issues
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Install Python 3.12 (Jammy defaults to 3.10) and Node.js (for MCP)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    software-properties-common \
    gpg-agent \
    curl \
    && add-apt-repository ppa:deadsnakes/ppa \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Install MCP servers globally
RUN npm install -g @modelcontextprotocol/server-filesystem @playwright/mcp

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Sync dependencies using uv and Python 3.12
RUN uv venv --python 3.12 && \
    uv sync --frozen --no-dev

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=django_config.settings \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
# PLAYWRIGHT_BROWSERS_PATH is already set by the base image!

# Copy application code
COPY . .

# Normalize line endings and ensure entrypoint is executable
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/logs

# Create symlink for bundled chromium to a fixed path
# This allows us to explicitly point to it in the config, bypassing auto-detection issues
RUN ln -sf /ms-playwright/chromium-*/chrome-linux/chrome /usr/bin/chromium-bundled

# We run as root to ensure access to the pre-installed browsers in /ms-playwright
# (The official image is designed this way)

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
