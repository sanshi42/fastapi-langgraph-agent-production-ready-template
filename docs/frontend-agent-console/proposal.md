# Agent Workspace Console 前端

status: active
priority: P2

## 目标

为当前 FastAPI + LangGraph Agent 后端新增首版 Web 前端：一个现代化的 Agent Workspace Console。首屏以聊天为中心，配合 session 管理、runtime 状态栏、轻量 Settings 和深色 Liquid Glass 视觉风格，让已有 Agent runtime 能力可以被真实使用和观察。

## 边界

- 使用 Vite + React + TypeScript + Tailwind 构建 `frontend/`。
- `/` 由 FastAPI 托管构建后的 React SPA；`/api/v1/*`、`/docs`、`/redoc`、`/health`、`/metrics` 保持后端入口。
- 登录/注册/session 管理接现有 Auth API。
- 聊天默认走 `/api/v1/chatbot/chat/stream`，必要时回退 `/chatbot/chat`。
- Pending Approval 不新增决策 API，首版按钮复用现有聊天恢复协议发送 `approve` 或拒绝文本。
- 新增只读 runtime state API，为右侧状态栏提供当前 session 范围内的任务、job、cron、teammate、worktree 和 approval 摘要。
- Settings 只显示偏好和 runtime 可见性，不在线编辑密钥、模型、base URL 或 `.env`。

## 非目标

- 不做 React Native。
- 不做完整账号中心、密码找回或在线配置管理。
- 不把 Grafana/Prometheus 改造成完整前端监控产品。
- 不提交 `.superpowers/` brainstorm 临时产物。
