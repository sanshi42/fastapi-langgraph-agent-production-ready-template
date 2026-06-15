# my-agent Agent Runtime

这个上下文描述当前项目中 Web Agent runtime 的稳定领域语言。它只记录项目概念，不记录实现细节。

## Language

**Agent Workspace**:
聊天 Agent 被授权读取、修改和执行命令的服务端工作区。所有文件、shell 和 worktree 操作都必须被限制在这个边界内。
_Avoid_: workspace, repo path, current directory

**Tool Policy**:
在工具执行前判断调用应直接执行、拒绝，还是进入人工审批的规则集合。它用于统一处理 shell、文件写入、worktree、cron、teammate 和 MCP 工具风险。
_Avoid_: permission hook, safety check

**Pending Approval**:
某个工具调用已经暂停，正在等待用户明确批准或拒绝的状态。它不是普通 assistant 文本，而是聊天运行时状态。
_Avoid_: confirmation message, question

**Runtime Job**:
可跨请求继续存在的 Agent 工作单元，例如后台命令、cron 触发或 teammate 任务。Runtime Job 需要租约来避免重复执行。
_Avoid_: background thread, worker task

**Task Board**:
Agent 用于拆分和跟踪多步骤工作的任务板。它表达 Agent 工作状态，不替代用户的项目管理系统。
_Avoid_: todo list, issue tracker

**Teammate**:
由主 Agent 启动并通过消息协议协作的后台 Agent 工作单元。Teammate 必须遵守同一 Tool Policy。
_Avoid_: subagent, worker

**Project Memory**:
Agent Workspace 中可审阅的项目资料文件。它用于补充项目上下文，不替代用户长期记忆系统。
_Avoid_: long-term memory, mem0 memory
