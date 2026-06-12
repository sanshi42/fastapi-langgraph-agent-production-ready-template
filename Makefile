.DEFAULT_GOAL := help

DOCKER_COMPOSE ?= docker compose
ENV            ?= development
VALID_ENVS     := development staging production test

# ---------------------------------------------------------------------------
# 辅助方法
# ---------------------------------------------------------------------------
define check_env
	@if ! echo "$(VALID_ENVS)" | grep -qw "$(ENV)"; then \
		echo "无效的 ENV=$(ENV)。必须是以下之一: $(VALID_ENVS)"; exit 1; \
	fi
endef

define load_env_file
	$(call check_env)
	@ENV_FILE=.env.$(ENV); \
	if [ ! -f $$ENV_FILE ]; then \
		echo "环境文件 $$ENV_FILE 不存在，请先创建。"; exit 1; \
	fi
endef

# 快捷方法：先加载环境变量，再执行命令。
run_with_env = bash -c "source scripts/set_env.sh $(ENV) && $(1)"

# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------
install:
	pip install uv
	uv sync
	uv run pre-commit install

# ---------------------------------------------------------------------------
# 服务
# ---------------------------------------------------------------------------
dev:
	@$(call run_with_env,uv run uvicorn app.main:app --reload --port 8000)

staging:
	@$(call run_with_env,$(MAKE) _serve ENV=staging)

prod:
	@$(call run_with_env,$(MAKE) _serve ENV=production)

_serve:
	@$(call run_with_env,./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop uvloop)

# ---------------------------------------------------------------------------
# 数据库迁移
# ---------------------------------------------------------------------------
migrate:
	@$(call run_with_env,uv run alembic upgrade head)

migration:
	@if [ -z "$(MSG)" ]; then \
		echo "用法: make migration MSG=\"描述你的变更\""; exit 1; \
	fi
	@$(call run_with_env,uv run alembic revision --autogenerate -m '$(MSG)')

migrate-downgrade:
	@$(call run_with_env,uv run alembic downgrade -1)

migrate-history:
	@$(call run_with_env,uv run alembic history --verbose)

# ---------------------------------------------------------------------------
# 评测
# ---------------------------------------------------------------------------
eval:
	@$(call run_with_env,python -m evals.main --interactive)

eval-quick:
	@$(call run_with_env,python -m evals.main --quick)

eval-no-report:
	@$(call run_with_env,python -m evals.main --no-report)

# ---------------------------------------------------------------------------
# 代码质量
# ---------------------------------------------------------------------------
lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run pyright

check: lint typecheck
	@echo "所有检查通过"

pre-commit:
	uv run pre-commit run --all-files

pre-commit-update:
	uv run pre-commit autoupdate

# ---------------------------------------------------------------------------
# Docker：单服务组合（API + DB）
# ---------------------------------------------------------------------------
docker-build:
	$(call check_env)
	@./scripts/build-docker.sh $(ENV)

docker-up:
	$(call load_env_file)
	@APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file .env.$(ENV) up -d --build db app

docker-down:
	$(call load_env_file)
	@APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file .env.$(ENV) down

docker-logs:
	$(call load_env_file)
	@APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file .env.$(ENV) logs -f app db

# 在运行中的 app 容器里执行 Alembic 迁移，容器内可以解析 POSTGRES_HOST=db。
# 需要先启动栈：make docker-up。
docker-migrate:
	$(call load_env_file)
	@APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file .env.$(ENV) exec -T app /app/.venv/bin/alembic upgrade head

# 在运行中的 app 容器里回滚上一次迁移。
docker-migrate-downgrade:
	$(call load_env_file)
	@APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file .env.$(ENV) exec -T app /app/.venv/bin/alembic downgrade -1

# 在运行中的 app 容器里查看迁移历史。
docker-migrate-history:
	$(call load_env_file)
	@APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file .env.$(ENV) exec -T app /app/.venv/bin/alembic history --verbose

# ---------------------------------------------------------------------------
# Docker：完整栈（API + DB + Prometheus + Grafana）
# ---------------------------------------------------------------------------
stack-up:
	$(call load_env_file)
	@APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file .env.$(ENV) up -d

stack-down:
	$(call load_env_file)
	@APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file .env.$(ENV) down

stack-logs:
	$(call load_env_file)
	@APP_ENV=$(ENV) $(DOCKER_COMPOSE) --env-file .env.$(ENV) logs -f

# ---------------------------------------------------------------------------
# 其他
# ---------------------------------------------------------------------------
clean:
	rm -rf .venv __pycache__ .pytest_cache

# ---------------------------------------------------------------------------
# 帮助
# ---------------------------------------------------------------------------
help:
	@echo "用法: make <target> [ENV=development|staging|production|test]"
	@echo ""
	@echo "初始化:"
	@echo "  install              安装依赖并设置 pre-commit hooks"
	@echo ""
	@echo "服务:"
	@echo "  dev                  启动带热重载的开发服务（端口 8000）"
	@echo "  staging              启动 staging 服务"
	@echo "  prod                 启动 production 服务"
	@echo ""
	@echo "数据库:"
	@echo "  migrate              执行迁移到最新版本（默认 ENV=development）"
	@echo "  migration MSG=...    根据模型变更生成迁移"
	@echo "  migrate-downgrade    回滚上一次迁移"
	@echo "  migrate-history      查看迁移历史"
	@echo ""
	@echo "评测:"
	@echo "  eval                 运行交互式评测"
	@echo "  eval-quick           使用默认设置运行评测"
	@echo "  eval-no-report       运行评测但不生成报告"
	@echo ""
	@echo "代码质量:"
	@echo "  lint                 运行 Ruff lint 检查"
	@echo "  format               运行 Ruff format"
	@echo "  typecheck            运行 Pyright 静态类型检查"
	@echo "  check                运行 lint 和 typecheck"
	@echo "  pre-commit           运行全部 pre-commit hooks"
	@echo "  pre-commit-update    更新 pre-commit hook 版本"
	@echo ""
	@echo "Docker（API + DB）:"
	@echo "  docker-build         构建 Docker 镜像"
	@echo "  docker-up            启动 API + DB 容器"
	@echo "  docker-down          停止容器"
	@echo "  docker-logs          跟踪容器日志"
	@echo "  docker-migrate       在 app 容器内执行数据库迁移"
	@echo "  docker-migrate-downgrade  在 app 容器内回滚上一次迁移"
	@echo "  docker-migrate-history    在 app 容器内查看迁移历史"
	@echo ""
	@echo "Docker（完整栈，包含 Prometheus + Grafana）:"
	@echo "  stack-up             启动完整栈"
	@echo "  stack-down           停止完整栈"
	@echo "  stack-logs           跟踪所有服务日志"
	@echo ""
	@echo "其他:"
	@echo "  clean                删除 .venv、__pycache__、.pytest_cache"

.PHONY: install dev staging prod _serve \
        migrate migration migrate-downgrade migrate-history \
        eval eval-quick eval-no-report \
        lint format typecheck check pre-commit pre-commit-update \
        docker-build docker-up docker-down docker-logs docker-migrate \
        docker-migrate-downgrade docker-migrate-history \
        stack-up stack-down stack-logs \
        clean help
