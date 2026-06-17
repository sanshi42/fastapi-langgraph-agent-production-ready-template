# Product

## Register

product

## Users

开发者、Agent 操作者和项目维护者在浏览器中使用这个工具。他们通常已经有一个后端 Agent 服务在本机或容器中运行，需要登录、选择 session、与 Agent 对话，并观察工具审批、后台任务和 runtime 状态。

## Product Purpose

my-agent 是一个 FastAPI + LangGraph 的 Agent 应用骨架。前端的目标不是营销展示，而是提供一个真实可用的 Agent Workspace Console：把聊天、session、Tool Policy、Pending Approval、Runtime Job、Task Board、Worktree 和 Teammate 状态组织到一个现代工作台中。

成功标准是用户可以从登录开始进入 Console，完成会话选择、流式聊天、审批响应和 runtime 状态查看，而不需要手写 token 或只依赖 Swagger。

## Brand Personality

精确、安静、高级。界面应该像可信赖的开发者控制台，而不是营销落地页；Liquid Glass 是材质语言，不是装饰噱头。

## Anti-references

- 不做纯聊天皮肤，不能弱化 Agent runtime 的差异点。
- 不做满屏半透明玻璃，避免代码、日志和长文本读不清。
- 不做重运营 dashboard，让指标卡抢走聊天主任务。
- 不做在线编辑 API key、模型或 `.env` 的设置中心。
- 不使用 emoji 作为结构性图标。

## Design Principles

1. 聊天是中心舞台，runtime 状态是辅助判断层。
2. 高级材质必须服务可读性；正文、代码和错误信息优先高对比。
3. 所有危险动作都要能看懂原因和恢复路径。
4. 首版偏真实闭环，不用假数据冒充产品能力。
5. 熟悉的产品 UI 优先于新奇控件。

## Accessibility & Inclusion

首版按 WCAG AA 约束设计：正文对比度至少 4.5:1，交互控件有可见 focus state，icon-only 控件提供 accessible label，状态信息不能只靠颜色表达。动效必须尊重 `prefers-reduced-motion`。
