"""LangGraph Agent runtime 工具接入测试."""

import asyncio

from langchain_core.messages import AIMessage

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.graph import GraphState
from app.schemas.chat import Message


def test_tool_call_denies_hard_blocked_command():
    """命中 deny list 的 shell 命令应回写 denied tool result."""
    agent = LangGraphAgent()
    state = GraphState(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call-1",
                        "name": "bash",
                        "args": {"command": "sudo reboot"},
                    }
                ],
            )
        ]
    )

    command = asyncio.run(agent._tool_call(state))

    output = command.update["messages"][0]
    assert output.name == "bash"
    assert "tool execution denied" in output.content


def test_tool_call_executes_safe_read_without_approval(tmp_path, monkeypatch):
    """非敏感 read_file 可直接执行并返回文件内容."""
    file_path = tmp_path / "note.txt"
    file_path.write_text("hello")

    from app.agent_runtime.runtime import agent_runtime

    monkeypatch.setattr(agent_runtime, "workspace_root", tmp_path)
    monkeypatch.setattr(agent_runtime.workspace_tools, "workspace_root", tmp_path)
    monkeypatch.setattr(agent_runtime.tool_policy, "workspace_root", tmp_path)

    agent = LangGraphAgent()
    state = GraphState(
        messages=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call-1",
                        "name": "read_file",
                        "args": {"path": "note.txt"},
                    }
                ],
            )
        ]
    )

    command = asyncio.run(agent._tool_call(state))

    output = command.update["messages"][0]
    assert output.name == "read_file"
    assert output.content == "hello"


def test_runtime_status_extracts_pending_approval_metadata():
    """Graph 返回的审批 payload 应能转换为 API runtime 状态."""
    metadata = LangGraphAgent.runtime_status_from_messages(
        [
            Message(
                role="assistant",
                content=(
                    "{'status': 'pending_approval', 'approval_id': 'approval-1', "
                    "'tool_name': 'write_file', 'risk_reason': 'write_file modifies workspace files'}"
                ),
            )
        ]
    )

    assert metadata["status"] == "pending_approval"
    assert metadata["approval_id"] == "approval-1"
    assert metadata["tool_name"] == "write_file"
