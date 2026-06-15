# Agent Runtime

`my-agent` 现在把 Claude Code Learning Agent 的核心能力接入现有 FastAPI + LangGraph 聊天链路。默认 `/chat` 和 `/chat/stream` 的模型工具池包含 workspace 文件工具、shell、Todo、task、skills、project memory、cron、teammate 和 background job 入口。

## 运行边界

Agent 只能操作 `AGENT_WORKSPACE_ROOT` 下的文件和命令。默认值是当前项目根目录，生产环境应显式配置：

```bash
AGENT_WORKSPACE_ROOT=/path/to/controlled/repo
AGENT_MAX_OUTPUT_CHARS=100000
AGENT_TOOL_APPROVAL_ENABLED=true
AGENT_WORKER_ENABLED=true
AGENT_JOB_LEASE_SECONDS=60
```

Workspace 本地 skills 从 `AGENT_SKILLS_DIR` 扫描，默认是 `AGENT_WORKSPACE_ROOT/skills`。Project Memory 从 `AGENT_PROJECT_MEMORY_DIR` 读取，默认是 `AGENT_WORKSPACE_ROOT/.memory`。

## 工具审批

默认全量启用工具不代表无条件执行。`write_file`、`edit_file`、`bash`、`background_run`、`worktree_*`、`schedule_cron`、`spawn_teammate` 和可疑 destructive MCP 工具都会先经过 Tool Policy。

命中硬拒绝规则时，工具结果会直接返回 denied。命中审批规则时，LangGraph interrupt 会暂停当前 graph，聊天响应通过结构化 runtime 状态表达 `pending_approval`。用户下一条消息回复 `approve`、`allow`、`yes`、`y`、`同意` 或 `批准` 后继续执行，否则工具结果会按拒绝处理。

## 状态存储

Agent runtime 的生产状态使用 Postgres，并按 `user_id + session_id` 隔离：

- `agent_tasks`
- `agent_worktrees`
- `agent_jobs`
- `agent_crons`
- `agent_teammates`
- `agent_messages`
- `agent_approvals`
- `agent_mcp_servers`
- `agent_events`

这些表由 Alembic migration 管理。LangGraph checkpoint 和 mem0/pgvector 仍由各自组件管理。

## MCP

MCP 使用官方 Python SDK：`ClientSession` 搭配 `stdio_client` 或 `streamable_http_client`，通过 `list_tools()` 发现工具，再按 `mcp__{server}__{tool}` 命名空间暴露给模型。配置文件支持 `servers` 或 `mcpServers` 两种顶层 key：

```json
{
  "servers": {
    "docs": {
      "transport": "stdio",
      "command": "python",
      "args": ["scripts/docs_mcp.py"]
    },
    "deploy": {
      "transport": "streamable_http",
      "url": "http://127.0.0.1:3333/mcp"
    }
  }
}
```

学习项目里的 mock MCP server 只适合测试，不作为生产实现。

## 后台任务

`background_run` 会写入 `agent_jobs`，应用内 worker 通过 Postgres lease 认领后在 Agent Workspace 内执行 shell 命令，并把结果写回 job。`schedule_cron` 会写入 `agent_crons`；worker 发现五字段 cron 到期后创建对应 background job，非 recurring cron 触发后转为 `completed`。

`spawn_teammate` 会写入 teammate 和 teammate job。当前实现把 teammate job 转换为 lead inbox 消息，保证跨请求可恢复；完整 autonomous teammate loop 可以在这个消息协议上继续扩展。

## Worktree

Worktree 工具把路径限制在 Agent Workspace 内。`worktree_create` 默认在 `.worktrees/<name>` 下创建 git worktree，并登记到 `agent_worktrees`；`worktree_track` 可登记已有 worktree；`worktree_remove` 移除默认位置的 worktree 并把状态标记为 `removed`。

## Memory

用户长期记忆继续由 mem0 管理。Project Memory 是 workspace 内可审阅的 Markdown 资料库，只在模型需要项目上下文时通过工具加载，避免和 mem0 自动记忆重复写入。
