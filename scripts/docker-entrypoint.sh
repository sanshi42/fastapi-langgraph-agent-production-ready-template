#!/bin/bash
set -e

# 打印加载 .env 前的初始环境变量。
echo "启动时的初始环境变量："
echo "APP_ENV: ${APP_ENV:-development}"
echo "初始数据库主机: $( [[ -n ${POSTGRES_HOST:-${DB_HOST:-}} ]] && echo '已设置' || echo '未设置' )"
echo "初始数据库端口: $( [[ -n ${POSTGRES_PORT:-${DB_PORT:-}} ]] && echo '已设置' || echo '未设置' )"
echo "初始数据库名称: $( [[ -n ${POSTGRES_DB:-${DB_NAME:-}} ]] && echo '已设置' || echo '未设置' )"
echo "初始数据库用户: $( [[ -n ${POSTGRES_USER:-${DB_USER:-}} ]] && echo '已设置' || echo '未设置' )"

# 从合适的 .env 文件加载环境变量。
if [ -f ".env.${APP_ENV}" ]; then
    echo "正在从 .env.${APP_ENV} 加载环境变量"
    while IFS= read -r line || [[ -n "$line" ]]; do
        # 跳过注释和空行。
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue

        # 提取 key。
        key=$(echo "$line" | cut -d '=' -f 1)

        # 仅当当前环境未设置时才写入。
        if [[ -z "${!key}" ]]; then
            export "$line"
        else
            echo "保留 $key 的已有值"
        fi
    done <".env.${APP_ENV}"
elif [ -f ".env" ]; then
    echo "正在从 .env 加载环境变量"
    while IFS= read -r line || [[ -n "$line" ]]; do
        # 跳过注释和空行。
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$line" ]] && continue

        # 提取 key。
        key=$(echo "$line" | cut -d '=' -f 1)

        # 仅当当前环境未设置时才写入。
        if [[ -z "${!key}" ]]; then
            export "$line"
        else
            echo "保留 $key 的已有值"
        fi
    done <".env"
else
    echo "警告：未找到 .env 文件，将使用系统环境变量。"
fi

# 检查必需的敏感环境变量。
required_vars=("JWT_SECRET_KEY" "OPENAI_API_KEY")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        missing_vars+=("$var")
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo "错误：缺少以下必需环境变量："
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo "请通过环境变量或 .env 文件提供这些变量。"
    exit 1
fi

# 打印最终环境信息。
echo -e "\n最终环境配置："
echo "环境: ${APP_ENV:-development}"

echo "数据库主机: $( [[ -n ${POSTGRES_HOST:-${DB_HOST:-}} ]] && echo '已设置' || echo '未设置' )"
echo "数据库端口: $( [[ -n ${POSTGRES_PORT:-${DB_PORT:-}} ]] && echo '已设置' || echo '未设置' )"
echo "数据库名称: $( [[ -n ${POSTGRES_DB:-${DB_NAME:-}} ]] && echo '已设置' || echo '未设置' )"
echo "数据库用户: $( [[ -n ${POSTGRES_USER:-${DB_USER:-}} ]] && echo '已设置' || echo '未设置' )"

echo "LLM 模型: ${DEFAULT_LLM_MODEL:-未设置}"
echo "Debug 模式: ${DEBUG:-false}"

# 必要时运行数据库迁移。
# 例如：alembic upgrade head

# 执行 CMD。
exec "$@"
