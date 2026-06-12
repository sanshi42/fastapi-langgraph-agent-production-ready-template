#!/bin/bash
set -e

# 查看 Docker 容器日志。

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

echo "正在查看 $ENV 环境容器日志"

# 检查容器是否存在。
if [ ! "$(docker ps -a -q -f name=$CONTAINER_NAME)" ]; then
  echo "容器 $CONTAINER_NAME 不存在。请先运行："
  echo "make docker-run-env ENV=$ENV"
  exit 1
fi

# 获取容器状态。
STATUS=$(docker inspect --format='{{.State.Status}}' $CONTAINER_NAME 2>/dev/null)

if [ "$STATUS" != "running" ]; then
  echo "容器 $CONTAINER_NAME 未运行（状态: $STATUS）"
  echo "要启动它，请运行: docker start $CONTAINER_NAME"
  exit 1
fi

# 持续显示日志。
echo "正在跟踪 $CONTAINER_NAME 日志（按 Ctrl+C 退出）"
docker logs -f $CONTAINER_NAME
