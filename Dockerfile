FROM node:22-slim AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

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

# 先安装锁定依赖，只有 pyproject.toml / uv.lock 变化时才失效 Docker cache。
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 复制应用代码，并基于锁定依赖安装项目本身。
COPY . .
COPY --from=frontend-builder /frontend/dist /app/frontend/dist
RUN uv sync --frozen

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
