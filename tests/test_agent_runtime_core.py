"""Agent runtime 核心能力测试."""

from pathlib import Path

import pytest

from app.agent_runtime.cron import cron_matches, validate_cron
from app.agent_runtime.mcp import MCPClientManager, normalize_mcp_name
from app.agent_runtime.project_memory import ProjectMemoryCatalog
from app.agent_runtime.skills import SkillCatalog
from app.agent_runtime.tool_policy import ToolPolicy
from app.agent_runtime.workspace import WorkspaceTools
from app.schemas.chat import ChatResponse, Message


def test_tool_policy_requires_approval_for_sensitive_tools(tmp_path: Path):
    """敏感工具命中策略时应返回结构化审批请求."""
    policy = ToolPolicy(workspace_root=tmp_path)

    decision = policy.evaluate("write_file", {"path": "app.py", "content": "print(1)"})

    assert decision.requires_approval is True
    assert decision.reason == "write_file modifies workspace files"
    assert decision.denied is False


def test_tool_policy_denies_command_from_deny_list(tmp_path: Path):
    """硬拒绝命令不应进入人工审批阶段."""
    policy = ToolPolicy(workspace_root=tmp_path)

    decision = policy.evaluate("bash", {"command": "sudo reboot"})

    assert decision.denied is True
    assert decision.requires_approval is False
    assert "sudo" in decision.reason


def test_workspace_tools_reject_path_escape(tmp_path: Path):
    """文件工具只能访问 Agent Workspace 内部路径."""
    tools = WorkspaceTools(workspace_root=tmp_path, max_output_chars=2000)

    with pytest.raises(ValueError, match="path escapes agent workspace"):
        tools.resolve_path("../outside.txt")


def test_workspace_tools_read_and_edit_file(tmp_path: Path):
    """读写和精确替换应在 workspace 内完成."""
    tools = WorkspaceTools(workspace_root=tmp_path, max_output_chars=2000)

    assert tools.write_file("notes/a.txt", "hello old") == "wrote 9 bytes to notes/a.txt"
    assert tools.read_file("notes/a.txt") == "hello old"
    assert tools.edit_file("notes/a.txt", "old", "new") == "edited notes/a.txt"
    assert tools.read_file("notes/a.txt") == "hello new"


def test_skill_catalog_loads_workspace_skills(tmp_path: Path):
    """Workspace 本地 skills 应可列出并按名称加载."""
    skill_file = tmp_path / "skills" / "review" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text("---\nname: code-review\ndescription: Review code.\n---\n\nUse review checklist.\n")

    catalog = SkillCatalog(tmp_path / "skills")

    assert "code-review: Review code." in catalog.describe()
    assert '<skill name="code-review">' in catalog.load("code-review")
    assert "Use review checklist." in catalog.load("code-review")


def test_project_memory_catalog_reads_markdown_files(tmp_path: Path):
    """Project memory 只作为可审阅资料库被读取."""
    memory_dir = tmp_path / ".memory"
    memory_dir.mkdir()
    (memory_dir / "api.md").write_text("---\nname: API\ndescription: API notes.\ntype: project\n---\n\nUse REST.\n")

    catalog = ProjectMemoryCatalog(memory_dir)

    assert "API (api.md) - API notes." in catalog.describe()
    assert "Use REST." in catalog.load("api.md")


def test_cron_validation_and_matching():
    """Cron 支持旧 runtime 已验证的五字段语义."""
    assert validate_cron("*/5 * * * *") is None
    assert validate_cron("* * *") == "expected 5 fields, got 3"

    from datetime import datetime

    assert cron_matches("*/5 * * * *", datetime(2026, 6, 15, 10, 20)) is True
    assert cron_matches("*/5 * * * *", datetime(2026, 6, 15, 10, 21)) is False


def test_mcp_tool_names_are_normalized():
    """MCP server/tool 名称应转换成安全命名空间."""
    assert normalize_mcp_name("docs server!") == "docs_server_"
    assert normalize_mcp_name("get.version") == "get_version"


def test_mcp_manager_loads_configured_servers(tmp_path: Path):
    """MCP client manager 应从配置文件加载真实 server 配置."""
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        """
        {
          "servers": {
            "docs server": {
              "transport": "stdio",
              "command": "python",
              "args": ["server.py"],
              "env": {"A": "B"}
            },
            "deploy": {
              "transport": "streamable_http",
              "url": "http://127.0.0.1:3333/mcp"
            }
          }
        }
        """
    )

    manager = MCPClientManager.from_config_path(config_path)

    assert [server.name for server in manager.servers] == ["docs server", "deploy"]
    assert manager.servers[0].transport == "stdio"
    assert manager.servers[1].url == "http://127.0.0.1:3333/mcp"


def test_chat_response_supports_pending_approval_metadata():
    """聊天响应应能结构化表达待审批状态，同时保留 messages."""
    response = ChatResponse(
        messages=[Message(role="assistant", content="approval required")],
        status="pending_approval",
        approval_id="approval-1",
        tool_name="write_file",
        risk_reason="write_file modifies workspace files",
    )

    assert response.status == "pending_approval"
    assert response.approval_id == "approval-1"
    assert response.messages[0].content == "approval required"
