# Pinned to bookworm (Debian 12): the floating `python:3.11-slim` tag has moved
# to trixie (Debian 13), whose t64 ABI transition renamed libasound2/libcups2/
# libgtk-3-0/etc., breaking the apt package names below (apt exit code 100).
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update -o Acquire::Retries=5 \
    && apt-get install -y --no-install-recommends \
    -o Acquire::Retries=5 -o Acquire::http::Timeout=30 \
    ca-certificates \
    curl \
    gnupg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE /app/
COPY crawler /app/crawler

# Split into separate layers so a network hiccup on a big download (crawl4ai's
# deps, or the ~150MB Chromium) only re-runs the failed step on retry instead of
# the whole chain. PIP_RETRIES/timeout harden against flaky mirrors.
ENV PIP_RETRIES=10 \
    PIP_DEFAULT_TIMEOUT=120
RUN pip install --no-cache-dir -U pip
RUN pip install --no-cache-dir -e .
RUN python -m playwright install --with-deps chromium

CMD ["python", "-m", "crawler.mcp_server"]
