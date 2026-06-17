# Agent Workspace Console Tasks

## Task 1: 后端 runtime state API

status: done

- 添加 store approval list。
- 添加 runtime state schema。
- 添加 `/api/v1/runtime/state`。
- 添加 API router 挂载。
- 增加 pytest 覆盖认证、session scope、空状态和基础数据返回。
- 验证：相关 pytest、`make lint`、`make typecheck`。

## Task 2: 前端工程骨架

status: done

- 创建 `frontend/` npm + Vite + React + TypeScript + Tailwind。
- 添加基础 scripts：`dev`、`build`、`preview`、`lint`。
- 建立 CSS variables、Tailwind config、入口文件。
- 验证：`npm install`、`npm run build`。

## Task 3: API client 与本地状态

status: done

- 实现 auth/session/chat/runtime API client。
- 实现 SSE parser 和 non-stream fallback。
- 实现 localStorage token/session/preferences 管理。
- 验证：前端 build 和核心工具单元测试（若测试工具已配置）。

## Task 4: Console UI

status: done

- 实现 Auth screen。
- 实现三栏 Console layout。
- 实现 chat composer、message list、streaming/loading/error states。
- 实现 Pending Approval 卡片和 approve/reject 操作。
- 实现 runtime right rail 和 Settings。
- 验证：浏览器检查桌面、平板、手机尺寸。

## Task 5: FastAPI 与 Docker 集成

status: done

- FastAPI 托管前端构建产物。
- Dockerfile 构建前端。
- Makefile 增加前端目标。
- 文档补启动方式。
- 验证：`/` 打开 SPA，`/docs` 保持 Swagger，`/api/v1/health` 正常。
