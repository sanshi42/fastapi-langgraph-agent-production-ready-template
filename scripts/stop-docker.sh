#!/bin/bash
set -e

# 停止并删除 Docker 容器。

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

CONTAINER_NAME="fastapi-langgraph-$ENV"

echo "正在停止 $ENV 环境的容器"

# 检查容器是否存在。
if [ ! "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
    echo "容器 $CONTAINER_NAME 不存在，无需处理。"
    exit 0
fi

# 停止并删除容器。
echo "正在停止容器 $CONTAINER_NAME..."
docker stop $CONTAINER_NAME >/dev/null 2>&1 || echo "容器未运行"

echo "正在删除容器 $CONTAINER_NAME..."
docker rm $CONTAINER_NAME >/dev/null 2>&1

echo "容器 $CONTAINER_NAME 已成功停止并删除"
