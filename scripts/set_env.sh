#!/bin/bash

# 设置和管理环境配置的脚本。
# 用法：source ./scripts/set_env.sh [development|staging|production]

# 检查脚本是否通过 source 加载。
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "错误：这个脚本必须通过 source 加载，不能直接执行。"
    echo "用法：source ./scripts/set_env.sh [development|staging|production]"
    exit 1
fi

# 定义输出颜色。
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m' # 无颜色。

# 默认环境为 development。
ENV=${1:-development}

# 校验环境名称。
if [[ ! "$ENV" =~ ^(development|staging|production)$ ]]; then
    echo -e "${RED}错误：环境无效。请选择 development、staging 或 production。${NC}"
    return 1
fi

# 设置环境变量。
export APP_ENV=$ENV

# 获取脚本目录和项目根目录。
# 使用较简单的写法，适配大多数 source 场景下的 shell。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 检查当前环境对应的 .env 文件。
ENV_FILE="$PROJECT_ROOT/.env.$ENV"

if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}正在从 $ENV_FILE 加载环境配置${NC}"

    # 导出文件中的所有环境变量。
    set -a
    source "$ENV_FILE"
    set +a

    echo -e "${GREEN}已从 $ENV_FILE 成功加载环境变量${NC}"
else
    echo -e "${YELLOW}警告：未找到 $ENV_FILE，正在从 .env.example 创建...${NC}"

    EXAMPLE_FILE="$PROJECT_ROOT/.env.example"
    if [ -f "$EXAMPLE_FILE" ]; then
        cp "$EXAMPLE_FILE" "$ENV_FILE"
        echo -e "${GREEN}已根据模板创建 $ENV_FILE。${NC}"
        echo -e "${PURPLE}请根据你的环境更新其中配置。${NC}"

        # 导出新文件中的所有环境变量。
        set -a
        source "$ENV_FILE"
        set +a

        echo -e "${GREEN}已从新的 $ENV_FILE 成功加载环境变量${NC}"
    else
        echo -e "${RED}错误：在 $EXAMPLE_FILE 未找到 .env.example${NC}"
        return 1
    fi
fi

# 打印当前环境摘要。
echo -e "\n${GREEN}======= 环境摘要 =======${NC}"
echo -e "${GREEN}环境:           ${YELLOW}$ENV${NC}"
echo -e "${GREEN}项目根目录:     ${YELLOW}$PROJECT_ROOT${NC}"
echo -e "${GREEN}项目名称:       ${YELLOW}${PROJECT_NAME:-未设置}${NC}"
echo -e "${GREEN}API 版本:       ${YELLOW}${VERSION:-未设置}${NC}"

echo -e "${GREEN}数据库主机:     ${YELLOW}${POSTGRES_HOST:-${DB_HOST:-未设置}}${NC}"
echo -e "${GREEN}数据库端口:     ${YELLOW}${POSTGRES_PORT:-${DB_PORT:-未设置}}${NC}"
echo -e "${GREEN}数据库名称:     ${YELLOW}${POSTGRES_DB:-${DB_NAME:-未设置}}${NC}"
echo -e "${GREEN}数据库用户:     ${YELLOW}${POSTGRES_USER:-${DB_USER:-未设置}}${NC}"

echo -e "${GREEN}LLM 模型:       ${YELLOW}${DEFAULT_LLM_MODEL:-未设置}${NC}"
echo -e "${GREEN}日志级别:       ${YELLOW}${LOG_LEVEL:-未设置}${NC}"
echo -e "${GREEN}Debug 模式:     ${YELLOW}${DEBUG:-未设置}${NC}"

# 创建辅助函数。
start_app() {
    echo -e "${GREEN}正在以 $ENV 环境启动应用...${NC}"
    cd "$PROJECT_ROOT" && uvicorn app.main:app --reload --port 8000
}

# 定义可在 shell 中使用的函数，同时处理 bash 和 zsh。
if [[ -n "$BASH_VERSION" ]]; then
    export -f start_app
elif [[ -n "$ZSH_VERSION" ]]; then
    # ZSH 中重新定义函数，不使用 export -f。
    function start_app() {
        echo -e "${GREEN}正在以 $ENV 环境启动应用...${NC}"
        cd "$PROJECT_ROOT" && uvicorn app.main:app --reload --port 8000
    }
else
    echo -e "${YELLOW}警告：不支持的 shell，将使用 fallback 方式。${NC}"
    # 其他 shell 不导出函数。
fi

# 打印帮助信息。
echo -e "\n${GREEN}可用命令:${NC}"
echo -e "  ${YELLOW}start_app${NC} - 以 $ENV 环境启动应用"

# 创建环境切换 aliases。
alias dev_env="source '$SCRIPT_DIR/set_env.sh' development"
alias stage_env="source '$SCRIPT_DIR/set_env.sh' staging"
alias prod_env="source '$SCRIPT_DIR/set_env.sh' production"

echo -e "  ${YELLOW}dev_env${NC} - 切换到 development 环境"
echo -e "  ${YELLOW}stage_env${NC} - 切换到 staging 环境"
echo -e "  ${YELLOW}prod_env${NC} - 切换到 production 环境"
