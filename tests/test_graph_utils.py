"""Graph 消息工具函数测试."""

from langchain_core.messages import (
    AIMessage,
    ToolMessage,
)

from app.schemas.chat import Message
from app.utils.graph import dump_messages, prepare_messages


def test_prepare_messages_output_can_be_dumped_for_llm_payload():
    """prepare_messages 经过 trim 后仍应能再次序列化给 LLM."""
    messages = [Message(role="user", content="你好，请介绍当前 agent runtime 的能力。")]

    prepared = prepare_messages(messages, "system prompt")

    assert dump_messages(prepared) == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "你好，请介绍当前 agent runtime 的能力。"},
    ]


def test_dump_messages_preserves_tool_call_metadata():
    """LangChain tool 消息序列化时不能丢失 tool_call_id."""
    messages = [
        AIMessage(
            content="",
            tool_calls=[{"id": "call-1", "name": "read_file", "args": {"path": "README.md"}}],
        ),
        ToolMessage(content="hello", name="read_file", tool_call_id="call-1"),
    ]

    assert dump_messages(messages) == [
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "type": "function",
                    "id": "call-1",
                    "function": {"name": "read_file", "arguments": '{"path": "README.md"}'},
                }
            ],
            "content": "",
        },
        {"role": "tool", "name": "read_file", "tool_call_id": "call-1", "content": "hello"},
    ]
