#!/bin/bash
set -e

# 安全运行 Docker 容器。

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

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.$ENV"

if [ -f "$ENV_FILE" ]; then
  echo "正在从 $ENV_FILE 加载环境变量"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  echo "警告：未找到 $ENV_FILE，将依赖当前已有环境变量。"
fi

cd "$PROJECT_ROOT"

if [ -f "$ENV_FILE" ]; then
  echo "正在使用 env 文件 $ENV_FILE 运行 docker compose"
  APP_ENV=$ENV docker compose --env-file "$ENV_FILE" up -d --build db app
else
  APP_ENV=$ENV docker compose up -d --build db app
fi
