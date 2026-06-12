# 配置

所有配置都从环境变量读取。使用 `.env.development`、`.env.staging` 或 `.env.production`，应用会根据 `APP_ENV` 变量加载正确文件。

先复制 `.env.example` 开始配置：

```bash
cp .env.example .env.development
```

---

## 应用

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_ENV` | `development` | 环境：`development`、`staging`、`production`、`test` |
| `PROJECT_NAME` | `FastAPI LangGraph Template` | 展示在 API 文档和日志中的项目名 |
| `VERSION` | `1.0.0` | API 版本 |
| `DEBUG` | `false` | 启用 debug 日志和 profiling 中间件 |
| `API_V1_STR` | `/api/v1` | API 前缀 |
| `ALLOWED_ORIGINS` | `*` | 逗号分隔的 CORS origins |

---

## LLM

| 变量 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | — | 是 | OpenAI-compatible API key |
| `OPENAI_BASE_URL` | — | 否 | 可选 OpenAI-compatible endpoint |
| `DEFAULT_LLM_MODEL` | `gpt-5-mini` | 否 | 起始模型；fallback 顺序见 [LLM Service](llm-service.md) |
| `DEFAULT_LLM_TEMPERATURE` | `0.2` | 否 | chat completions 的 temperature |
| `MAX_TOKENS` | `2000` | 否 | 每次 LLM 响应的最大 token 数 |
| `MAX_LLM_CALL_RETRIES` | `3` | 否 | 切换 fallback 前，每个模型的重试次数 |
| `LLM_TOTAL_TIMEOUT` | `60` | 否 | 整个 fallback loop 的最大秒数 |
| `SESSION_NAMING_ENABLED` | `true` | 否 | 使用后台 LLM task 根据用户第一条消息自动生成 session 标题 |

---

## 长期记忆

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LONG_TERM_MEMORY_COLLECTION_NAME` | `longterm_memory` | pgvector collection 名称 |
| `LONG_TERM_MEMORY_MODEL` | `gpt-5-nano` | mem0 用于提取记忆的 LLM |
| `LONG_TERM_MEMORY_EMBEDDER_MODEL` | `text-embedding-3-small` | 语义搜索使用的 embedding 模型 |

---

## 数据库

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `food_order_db` | 数据库名称 |
| `POSTGRES_USER` | `postgres` | 数据库用户 |
| `POSTGRES_PASSWORD` | `postgres` | 数据库密码 |
| `POSTGRES_POOL_SIZE` | `20` | SQLAlchemy 连接池大小 |
| `POSTGRES_MAX_OVERFLOW` | `10` | 超出连接池大小后的最大额外连接数 |

---

## 认证

| 变量 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `JWT_SECRET_KEY` | — | 是 | 用于签名 JWT token 的 secret，生产环境应使用长随机字符串 |
| `JWT_ALGORITHM` | `HS256` | 否 | JWT 签名算法 |
| `JWT_ACCESS_TOKEN_EXPIRE_DAYS` | `30` | 否 | token 有效天数 |

---

## 缓存（Valkey/Redis，可选）

设置 `VALKEY_HOST` 后，应用会使用 Valkey/Redis 做 memory search 缓存和限流。未设置时，会回退到内存 TTL 缓存；该缓存不会在多个实例之间共享。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VALKEY_HOST` | ``（禁用） | Valkey/Redis host；留空时使用内存 fallback |
| `VALKEY_PORT` | `6379` | 端口 |
| `VALKEY_DB` | `0` | 数据库索引 |
| `VALKEY_PASSWORD` | `` | 密码（如需要） |
| `VALKEY_MAX_CONNECTIONS` | `20` | 连接池大小 |
| `CACHE_TTL_SECONDS` | `60` | memory search 缓存结果的 TTL |

---

## 可观测性（Langfuse）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LANGFUSE_TRACING_ENABLED` | `true` | 设置为 `false` 可完全禁用 tracing |
| `LANGFUSE_PUBLIC_KEY` | — | Langfuse 项目 public key |
| `LANGFUSE_SECRET_KEY` | — | Langfuse 项目 secret key |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse host（self-hosted 或 cloud） |

---

## 限流

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `RATE_LIMIT_DEFAULT` | `200 per day, 50 per hour` | fallback 限流值 |
| `RATE_LIMIT_CHAT` | `30 per minute` | POST /chat |
| `RATE_LIMIT_CHAT_STREAM` | `20 per minute` | POST /chat/stream |
| `RATE_LIMIT_MESSAGES` | `50 per minute` | GET/DELETE /messages |
| `RATE_LIMIT_LOGIN` | `20 per minute` | POST /auth/login |
| `RATE_LIMIT_REGISTER` | `10 per hour` | POST /auth/register |

配置 Valkey 后，限流会在所有应用实例之间共享。未配置时，限流按进程独立生效。

---

## Profiling（仅 debug）

仅在 `DEBUG=true` 时启用。它会对每个请求做 profiling，并在请求耗时超过阈值时保存 JSON 报告。

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `PROFILING_DIR` | `/tmp/fastapi_profiles` | profile JSON 文件目录 |
| `PROFILING_THRESHOLD_SECONDS` | `2.0` | 触发保存 profile 的最小 wall time；设置为 `0` 可记录每个请求 |

---

## 日志

| 变量 | 默认值（dev） | 默认值（prod） | 说明 |
| --- | --- | --- | --- |
| `LOG_LEVEL` | `DEBUG` | `WARNING` | 日志级别 |
| `LOG_FORMAT` | `console` | `json` | `console` 用于彩色开发输出，`json` 用于结构化生产日志 |
