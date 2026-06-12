# 安全策略

## 支持版本

这是一个模板仓库。安全修复会应用到 `master` 分支。fork 维护者需要自行保持 fork 与上游同步。

## 报告漏洞

请**不要**为安全漏洞创建公开 GitHub issue。

请通过 [GitHub Security Advisories](../../security/advisories/new) 私密报告，或直接给维护者发邮件。请包含：

- 漏洞描述及潜在影响
- 复现步骤
- 建议的缓解措施

确认收到后，通常会在 48 小时内回复；对已确认漏洞，会在 7 天内给出修复或缓解计划。

## 使用本模板时的安全注意事项

**部署到生产环境前：**

- 设置强随机 `JWT_SECRET_KEY`（至少 32 个字符）
- 轮换所有 secrets，绝不要使用 `.env.example` 中的示例值
- 设置 `DEBUG=false`
- 将 `ALLOWED_ORIGINS` 限制为真实前端域名
- 如果不希望对话数据发送到 Langfuse，设置 `LANGFUSE_TRACING_ENABLED=false`
- 使用按环境区分的 `.env` 文件，绝不要把 secrets 提交到 git

**模板已经提供的保护：**

- 密码使用 bcrypt 哈希，不以明文存储
- JWT token 包含 `jti` claim，保证 token 唯一性
- 所有用户输入在使用前都会清洗
- 认证和聊天端点启用限流
- 通过 `detect-secrets` pre-commit hook 做 secret 检测
- 已配置 CORS，生产环境需要收紧 `ALLOWED_ORIGINS`
