# Agent Workspace Console 实现计划

## 设计方向

首版采用 Chat-Centered Console：左侧 session/navigation，中间聊天主舞台，右侧 runtime 状态栏。Liquid Glass 只用于导航、侧栏、审批卡、输入区和浮层；聊天正文、代码块和错误信息保持高对比，避免透明层损害可读性。

## 后端

- 新增 `app/api/v1/runtime.py`，挂载到 `/api/v1/runtime`。
- 新增只读 `GET /api/v1/runtime/state`，使用 `get_current_session` 读取当前 session 和 user scope。
- response 使用 Pydantic schema，返回 settings 可见性和 runtime store 摘要。
- 在 `AgentRuntimeStore` 中补 `list_approvals(user_id, session_id)`，其余列表复用已有方法。
- 所有新增 route 使用 slowapi rate limiting、type hints、structured logging，保持 imports 在文件顶部。

## 前端

- 新增 `frontend/` Vite React TypeScript 工程，使用 npm。
- Tailwind + CSS variables 定义深色 Liquid Glass token、semantic color、radius、motion 和 z-index。
- API client 封装 auth、session、chat stream、runtime state。
- localStorage 保存 user token、active session token、active session id 和 UI preferences。
- React 状态按 auth/session/chat/runtime/preferences 拆分；避免首版引入大型状态库。
- UI 包含 Auth screen、Console layout、Right runtime rail、Settings view/sheet、错误/空状态/加载状态。

## 集成

- FastAPI 在生产构建存在时挂载 SPA 静态资源，并对非 API/docs 路由回退到 `index.html`。
- Dockerfile 安装 Node/npm 并构建前端，再运行 Python app。
- Makefile 增加前端 install/build/dev/check 相关目标，并让现有后端目标保持可用。

## 验证

- 后端 pytest 覆盖 runtime state API 和 store approval list。
- 前端至少执行 `npm run build`。
- 全仓执行 `make lint` 和 `make typecheck`。
- 启动本地服务后用浏览器检查 `/`、`/docs`、登录页、Console 响应式布局和无空白页面。
