FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

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

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

RUN npm install -g @modelcontextprotocol/server-filesystem @playwright/mcp

COPY pyproject.toml uv.lock ./

RUN uv venv --python 3.12 && \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=django_config.settings \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY . .

RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

RUN mkdir -p /app/staticfiles /app/media /app/logs

RUN ln -sf /ms-playwright/chromium-*/chrome-linux/chrome /usr/bin/chromium-bundled


ENTRYPOINT ["/app/entrypoint.sh"]

EXPOSE 8000

HEALTHCHECK --interval=2m --timeout=10s --start-period=1m --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/')" || exit 1

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
