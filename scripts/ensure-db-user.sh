#!/bin/bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "用法: $0 <environment>"
  echo "环境: development, staging, production"
  exit 1
fi

ENV=$1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.$ENV"

if [ -f "$ENV_FILE" ]; then
  echo "正在从 $ENV_FILE 加载数据库初始化所需环境变量"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  echo "警告：未找到 $ENV_FILE，将使用当前环境变量进行数据库初始化。"
fi

POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
POSTGRES_DB=${POSTGRES_DB:-food_order_db}

DOCKER_COMPOSE_BIN=${DOCKER_COMPOSE_BIN:-docker compose}
IFS=' ' read -r -a DC_CMD <<< "$DOCKER_COMPOSE_BIN"

echo "正在等待 PostgreSQL 服务就绪..."
MAX_ATTEMPTS=30
SLEEP_SECONDS=2
attempt=1

until "${DC_CMD[@]}" exec -T db pg_isready -U postgres >/dev/null 2>&1; do
  if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
    echo "PostgreSQL 服务未在限定时间内就绪。"
    exit 1
  fi
  attempt=$((attempt + 1))
  sleep "$SLEEP_SECONDS"
done

echo "正在确保 role '$POSTGRES_USER' 和数据库 '$POSTGRES_DB' 存在"

role_escaped=${POSTGRES_USER//"/""}
role_escaped=${role_escaped//\'/''}
password_escaped=${POSTGRES_PASSWORD//\'/''}
db_escaped=${POSTGRES_DB//"/""}
db_escaped=${db_escaped//\'/''}

role_exists=$("${DC_CMD[@]}" exec -T db psql -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='${role_escaped}'" | tr -d '[:space:]')
if [ "$role_exists" != "1" ]; then
  echo "正在创建 role $POSTGRES_USER"
  "${DC_CMD[@]}" exec -T db psql -U postgres -c "CREATE ROLE \"${role_escaped}\" WITH LOGIN PASSWORD '${password_escaped}'"
else
  echo "正在更新 role $POSTGRES_USER 的密码"
  "${DC_CMD[@]}" exec -T db psql -U postgres -c "ALTER ROLE \"${role_escaped}\" WITH PASSWORD '${password_escaped}'"
fi

db_exists=$("${DC_CMD[@]}" exec -T db psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${db_escaped}'" | tr -d '[:space:]')
if [ "$db_exists" != "1" ]; then
  echo "正在创建数据库 $POSTGRES_DB，owner 为 $POSTGRES_USER"
  "${DC_CMD[@]}" exec -T db psql -U postgres -c "CREATE DATABASE \"${db_escaped}\" OWNER \"${role_escaped}\""
else
  echo "数据库 $POSTGRES_DB 已存在，正在确保 owner 正确"
  "${DC_CMD[@]}" exec -T db psql -U postgres -c "ALTER DATABASE \"${db_escaped}\" OWNER TO \"${role_escaped}\""
fi

echo "正在把数据库 $POSTGRES_DB 的权限授予 $POSTGRES_USER"
"${DC_CMD[@]}" exec -T db psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE \"${db_escaped}\" TO \"${role_escaped}\""

echo "PostgreSQL role 和数据库已确认完成"
