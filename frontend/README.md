# my-agent Console Frontend

这是 my-agent 的 Agent Workspace Console 前端，使用 Vite + React + TypeScript 构建。

## 常用命令

```bash
npm install
npm run dev
npm run lint
npm run test
npm run build
```

开发环境下 Vite 默认启动独立前端服务，并把 `/api/*` 转发到 `http://127.0.0.1:8000`；生产构建产物会输出到 `frontend/dist/`，由 FastAPI 在 `/` 托管。

## 设计边界

- 默认深色 Liquid Glass 风格。
- 聊天是主任务，runtime 状态栏是辅助判断层。
- Pending Approval 复用现有聊天恢复协议，不单独调用审批 API。
- Settings 只展示前端偏好和 runtime 可见性，不编辑密钥、模型或 `.env`。
