#!/bin/bash
set -e

# 安全构建 Docker 镜像，避免在构建输出中暴露 secrets。

if [ $# -ne 1 ]; then
    echo "用法: $0 <environment>"
    echo "环境: development, staging, production"
    exit 1
fi

ENV=$1

# 校验环境名称。
if [[ ! "$ENV" =~ ^(development|staging|production)$ ]]; then
    echo "环境无效。必须是以下之一: development, staging, production"
    exit 1
fi

echo "正在为 $ENV 环境构建 Docker 镜像"

# 检查 env 文件是否存在。
ENV_FILE=".env.$ENV"
if [ ! -f "$ENV_FILE" ]; then
    echo "警告：未找到 $ENV_FILE，正在从 .env.example 创建"
    if [ ! -f .env.example ]; then
        echo "错误：未找到 .env.example"
        exit 1
    fi
    cp .env.example "$ENV_FILE"
    echo "运行容器前，请根据你的环境更新 $ENV_FILE"
fi

echo "正在从 $ENV_FILE 加载环境变量（secrets 已遮蔽）"

# 安全加载环境变量。
set -a
source "$ENV_FILE"
set +a

# 打印遮蔽后的确认信息。
echo "环境: $ENV"
# 添加辅助函数，用于遮蔽已设置的值。
mask_env() {
    local value="$1"
    if [ -z "$value" ]; then
        echo "未设置"
    else
        echo "********"
    fi
}

echo "环境: $ENV"
# 遮蔽数据库连接元数据，避免直接打印。
echo "数据库主机: $(mask_env "${POSTGRES_HOST:-${DB_HOST:-}}")"
echo "数据库端口: $(mask_env "${POSTGRES_PORT:-${DB_PORT:-}}")"
echo "数据库名称: $(mask_env "${POSTGRES_DB:-${DB_NAME:-}}")"
echo "数据库用户: $(mask_env "${POSTGRES_USER:-${DB_USER:-}}")"
echo "API keys: ********（为安全已遮蔽）"

# 携带 secrets 构建 Docker 镜像，但不在控制台输出中展示它们。
docker build --no-cache \
    --build-arg APP_ENV="$ENV" \
    --build-arg OPENAI_API_KEY="$OPENAI_API_KEY" \
    --build-arg LANGFUSE_PUBLIC_KEY="$LANGFUSE_PUBLIC_KEY" \
    --build-arg LANGFUSE_SECRET_KEY="$LANGFUSE_SECRET_KEY" \
    --build-arg JWT_SECRET_KEY="$JWT_SECRET_KEY" \
    -t fastapi-langgraph-template:"$ENV" .

echo "Docker 镜像 fastapi-langgraph-template:$ENV 构建成功"
