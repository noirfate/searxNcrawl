FROM ubuntu:noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN sed -i "s@http://archive.ubuntu.com@http://mirrors.tuna.tsinghua.edu.cn@g" /etc/apt/sources.list.d/ubuntu.sources && \
    sed -i "s@http://security.ubuntu.com@http://mirrors.tuna.tsinghua.edu.cn@g" /etc/apt/sources.list.d/ubuntu.sources && \
    apt-get update && \
    DEBIAN_FRONTEND="noninteractive" apt-get -y install tzdata

RUN apt-get install -y --no-install-recommends \
    net-tools \
    iputils-ping \
    procps \
    ca-certificates \
    curl \
    gnupg \
    python3 \
    python3-pip \
    python3-venv \
    python-is-python3 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone

WORKDIR /app

COPY pyproject.toml README.md LICENSE /app/
COPY crawler /app/crawler

ENV PATH="/opt/venv/bin:$PATH" \
    PIP_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple \
    PIP_TRUSTED_HOST=mirrors.tuna.tsinghua.edu.cn \
    PIP_RETRIES=10 \
    PIP_DEFAULT_TIMEOUT=120

RUN python3 -m venv /opt/venv
RUN pip install --no-cache-dir -U pip
RUN pip install --no-cache-dir -e .
RUN python -m playwright install --with-deps chromium

CMD ["python", "-m", "crawler.mcp_server"]
