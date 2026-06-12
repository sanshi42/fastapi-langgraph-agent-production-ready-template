FROM python:3.13.2-slim

# 设置工作目录。
WORKDIR /app

# 设置非敏感环境变量。
ARG APP_ENV=production

ENV APP_ENV=${APP_ENV} \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# 安装系统依赖。
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && pip install --upgrade pip \
    && pip install uv \
    && rm -rf /var/lib/apt/lists/*

# 先复制 pyproject.toml，以便复用 Docker cache。
COPY pyproject.toml .
RUN uv venv && . .venv/bin/activate && uv pip install -e .

# 复制应用代码。
COPY . .

# 切换用户前先给 entrypoint 脚本添加可执行权限。
RUN chmod +x /app/scripts/docker-entrypoint.sh

# 创建非 root 用户。
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 创建日志目录。
RUN mkdir -p /app/logs

# 默认端口。
EXPOSE 8000

# 输出当前使用的环境。
RUN echo "使用 ${APP_ENV} 环境"

# 启动应用的命令。
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
