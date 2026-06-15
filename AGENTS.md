# AI Agent 开发指南

本文档为 AI agent 在这个 LangGraph FastAPI Agent 项目中工作时提供必要约定。

## 轻量敏捷开发框架

只有当目标大到无法通过一个可直接验证的任务完成时，才使用这个轻量 Topic 工作流。小任务应直接实现，不需要创建工作流文档。

### 工作方式

- 用户描述目标；agent 在内部维护 Topic 和 Task 状态。
- 当复杂目标需要多个可独立验证的 Task、依赖顺序、并行工作或跨会话上下文时，创建 Topic。
- 同一时间最多保持一个 `active` Topic。当前目标内的新工作更新这个 Topic；相互独立的复杂目标创建各自的 Topic。
- 对用户沟通时，优先使用“复杂目标”或“当前目标”这类表达，避免使用“activate Topic”“claim Task”等内部工作流术语。

### Topic 文档

复杂目标放在 `docs/<english-kebab-case-topic>/` 下。一个 Topic 最多包含三个文件：

- `proposal.md`：记录目标、边界、`status` 和 `priority`。这是扫描入口；允许的状态为 `draft`、`active`、`paused`、`done` 和 `closed`。允许的优先级为 `P0` 到 `P3`，默认是 `P2`。
- `plan.md`：记录实现思路、关键决策和 Topic 级验证方式。只有开始执行时才创建。
- `tasks.md`：记录 Task 列表、依赖关系、状态和每个 Task 的验证方式。它用于表达顺序和验收，不应写成第二份计划文档。

## 常用命令

```bash
make install              # 安装依赖（uv sync）并安装 pre-commit hooks
make dev                  # 启动热重载开发服务（端口 8000）
make lint                 # 运行 ruff check .
make format               # 运行 ruff format .
make typecheck            # 运行 uv run pyright（静态类型检查）
make check                # 运行 lint + typecheck
make eval                 # 运行 LLM evals（交互模式）
make eval-quick           # 运行 LLM evals（默认设置）
make migrate              # 执行 Alembic 数据库迁移到最新版本
make docker-up            # Docker 启动 API + DB（默认 ENV=development）
make stack-up ENV=development  # 启动完整栈：API + DB + Prometheus + Grafana
```

> 所有 server、DB、Docker 目标都接受 `ENV=development|staging|production|test`。
> 运行 `make help` 查看完整目标列表。

## 项目结构

```text
app/
  api/v1/          # 路由处理器（auth.py、chatbot.py、api.py）
  core/
    config.py      # Pydantic Settings 配置
    database.py    # Async DB 设置
    langgraph/     # LangGraph agent graph 与 tools
    logging.py     # structlog 设置
    llm.py         # 带 retry 逻辑的 LLM service
    limiter.py     # rate limiting（slowapi）
    metrics.py     # Prometheus metrics
    middleware.py  # ASGI middleware
    prompts/       # System prompts
  models/          # SQLModel ORM models
  schemas/         # Pydantic request/response schemas + graph state
  services/        # 业务逻辑 services
  utils/           # 共享工具函数
evals/             # 基于 Langfuse 的 LLM evaluation framework
scripts/           # 环境设置和 Docker build 脚本
```

## 项目概览

这是一个 production-ready 的 AI agent 应用，核心技术包括：

- **LangGraph**：用于有状态、多步骤的 AI agent workflow。
- **FastAPI**：用于高性能 async REST API endpoints。
- **Langfuse**：用于 LLM observability 和 tracing。
- **PostgreSQL + pgvector**：用于长期记忆存储（mem0ai）。
- **JWT authentication**：配合 session management。
- **Prometheus + Grafana**：用于 monitoring。

## 关键规则速查

### Import 规则

- **所有 imports 必须放在文件顶部**，不要在函数或类内部新增 import。

### Logging 规则

- 所有 logging 都使用 **structlog**。
- log message 必须使用 **lowercase_with_underscores**，例如 `"user_login_successful"`。
- **structlog event 中不要使用 f-string**，变量通过 kwargs 传入。
- 使用 `logger.exception()` 而不是 `logger.error()`，以保留 traceback。
- 示例：`logger.info("chat_request_received", session_id=session.id, message_count=len(messages))`

### Retry 规则

- retry 逻辑必须使用 **tenacity**。
- 使用 exponential backoff。
- 示例：`@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))`

### Output 规则

- console output 必须启用 **rich**。
- progress bars、tables、panels 和 formatted text 都使用 rich。

### Caching 规则

- **只缓存成功响应**，不要缓存错误响应。
- 根据数据变化频率设置合适的 cache TTL。

### FastAPI 规则

- 所有 routes 都必须带 rate limiting decorators。
- 使用 dependency injection 注入 services、database connections 和 auth。
- 所有 database operations 必须是 async。

## 代码风格约定

### Python/FastAPI

- async 操作使用 `async def`。
- 所有函数签名都要有 type hints。
- 优先使用 Pydantic models，不要直接传裸 dict。
- 优先使用 functional、declarative programming；除 services 和 agents 外，避免新增 class。
- 文件命名使用 lowercase with underscores，例如 `user_routes.py`。
- 使用 RORO pattern（Receive an Object, Return an Object）。

### Error Handling

- 在函数开头处理错误条件。
- 对错误条件使用 early returns。
- happy path 放在最后。
- 使用 guard clauses 表达 preconditions。
- 对预期错误使用 `HTTPException`，并设置合适的 status code。

## LangGraph 与 LangChain 模式

### Graph 结构

- 使用 `StateGraph` 构建 AI agent workflows。
- 使用 Pydantic models 定义清晰的 state schemas（参考 `app/schemas/graph.py`）。
- 生产 workflow 使用 `CompiledStateGraph`。
- 使用 `AsyncPostgresSaver` 实现 checkpointing 和 persistence。
- 使用 `Command` 控制 graph 节点流转。

### Tracing

- 使用 Langfuse 的 LangChain `CallbackHandler` tracing 所有 LLM calls。
- 所有 LLM operations 都必须启用 Langfuse tracing。

### Memory（mem0ai）

- 使用 `AsyncMemory` 存储 semantic memory。
- 按 `user_id` 存储 memories，用于个性化体验。
- 使用 async methods：`add()`、`get()`、`search()`、`delete()`。

## Authentication 与 Security

- 使用 JWT tokens 做 authentication。
- 实现基于 session 的 user management（参考 `app/api/v1/auth.py`）。
- protected endpoints 使用 `get_current_session` dependency。
- 敏感信息必须存放在 environment variables 中。
- 所有用户输入都使用 Pydantic models 校验。

## Database Operations

- 使用 SQLModel 定义 ORM models（结合 SQLAlchemy + Pydantic）。
- models 放在 `app/models/` 目录。
- database operations 使用 asyncpg 做 async 操作。
- agent checkpointing 使用 LangGraph 的 `AsyncPostgresSaver`。

## Performance Guidelines

- 尽量减少 blocking I/O operations。
- database 和外部 API calls 都使用 async。
- 对频繁访问的数据实现 caching。
- database connections 使用 connection pooling。
- 通过 streaming responses 优化 LLM calls。

## Observability

- 所有 agent operations 都接入 Langfuse 做 LLM tracing。
- 导出 Prometheus metrics，用于 API performance 观测。
- 使用 structured logging，并绑定 request_id、session_id、user_id 等上下文。
- 跟踪 LLM inference duration、token usage 和 costs。

## Testing 与 Evaluation

- 为 LLM outputs 实现 metric-based evaluations（参考 `evals/` 目录）。
- 自定义 evaluation metrics 以 markdown 文件形式放在 `evals/metrics/prompts/`。
- 使用 Langfuse traces 作为 evaluation data sources。
- 生成包含 success rates 的 JSON reports。

## Configuration Management

- 使用环境专属配置文件：`.env.development`、`.env.staging`、`.env.production`。
- 使用 Pydantic Settings 做 type-safe configuration（参考 `app/core/config.py`）。
- 不要 hardcode secrets 或 API keys。

## Key Dependencies

- **FastAPI**：Web framework。
- **LangGraph**：Agent workflow orchestration。
- **LangChain**：LLM abstraction 和 tools。
- **Langfuse**：LLM observability 和 tracing。
- **Pydantic v2**：Data validation 和 settings。
- **structlog**：Structured logging。
- **mem0ai**：Long-term memory management。
- **PostgreSQL + pgvector**：Database 和 vector storage。
- **SQLModel**：Database models 的 ORM。
- **tenacity**：Retry logic。
- **rich**：Terminal formatting。
- **slowapi**：Rate limiting。
- **prometheus-client**：Metrics collection。

## 本项目 11 条铁律

1. 所有 routes 都必须带 rate limiting decorators。
2. 所有 LLM operations 都必须启用 Langfuse tracing。
3. 所有 async operations 都必须有适当的 error handling。
4. 所有 logs 都必须遵循 structured logging 格式，event name 使用 lowercase_underscore。
5. 所有 retries 都必须使用 tenacity。
6. 所有 console outputs 都应使用 rich formatting。
7. 所有 caching 都只应存储成功响应。
8. 所有 imports 都必须放在文件顶部。
9. 所有 database operations 都必须是 async。
10. 所有 endpoints 都必须有合适的 type hints 和 Pydantic models。
11. 所有代码都必须通过 `make typecheck`（pyright standard mode）。

## 常见坑

- ❌ 在 structlog event 中使用 f-string。
- ❌ 在函数内部新增 imports。
- ❌ routes 缺少 rate limiting decorators。
- ❌ LLM calls 缺少 Langfuse tracing。
- ❌ 缓存错误响应。
- ❌ 对 exception 使用 `logger.error()` 而不是 `logger.exception()`。
- ❌ 使用 blocking I/O operations，却没有 async 处理。
- ❌ hardcode secrets 或 API keys。
- ❌ 函数签名缺少 type hints。

## 修改代码前

修改代码前先做这些事：

1. 先阅读现有实现。
2. 检查代码库里相关的既有模式。
3. 确保与现有代码风格一致。
4. 添加合适的 structured logging。
5. 使用 early returns 补足 error handling。
6. 添加 type hints 和 Pydantic models。
7. 确认 LLM calls 已启用 Langfuse tracing。

## References

- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- LangChain Documentation: https://python.langchain.com/docs/
- FastAPI Documentation: https://fastapi.tiangolo.com/
- Langfuse Documentation: https://langfuse.com/docs
