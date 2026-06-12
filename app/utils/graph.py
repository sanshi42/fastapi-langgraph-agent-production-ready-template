"""应用 graph 工具函数."""

import tiktoken
from langchain_core.messages import BaseMessage
from langchain_core.messages import trim_messages as _trim_messages

from app.core.config import settings
from app.core.logging import logger
from app.schemas import Message

# 在模块级缓存 tiktoken encoding，线程安全且可复用。
try:
    _TIKTOKEN_ENCODING = tiktoken.encoding_for_model(settings.DEFAULT_LLM_MODEL)
except KeyError:
    _TIKTOKEN_ENCODING = tiktoken.get_encoding("cl100k_base")


def _count_tokens_tiktoken(messages: list) -> int:
    """使用 tiktoken 在本地统计 token，无需 API 调用."""
    num_tokens = 0
    for message in messages:
        # 每条消息都有 role/name 相关的额外 token。
        num_tokens += 4
        if isinstance(message, dict):
            for _, value in message.items():
                if isinstance(value, str):
                    num_tokens += len(_TIKTOKEN_ENCODING.encode(value))
        elif isinstance(message, BaseMessage):
            content = message.content
            if isinstance(content, str):
                num_tokens += len(_TIKTOKEN_ENCODING.encode(content))
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, str):
                        num_tokens += len(_TIKTOKEN_ENCODING.encode(block))
                    elif isinstance(block, dict) and "text" in block:
                        num_tokens += len(_TIKTOKEN_ENCODING.encode(block["text"]))
    num_tokens += 2  # 每个回复都会预置 assistant。
    return num_tokens


def dump_messages(messages: list[Message]) -> list[dict]:
    """把消息序列化为字典列表.

    Args:
        messages (list[Message]): 待序列化消息。

    Returns:
        list[dict]: 序列化后的消息。
    """
    return [message.model_dump() for message in messages]


def extract_text_content(content: str | list) -> str:
    """从 LLM content 值中提取纯文本.

    同时处理简单字符串格式，以及 GPT-5 / Responses API 模型返回的结构化块列表：
        [{'type': 'reasoning', ...}, {'type': 'text', 'text': '...'}]

    Args:
        content: 来自 LangChain BaseMessage 的原始 content。

    Returns:
        纯文本字符串；没有可提取内容时返回空字符串。
    """
    if isinstance(content, str):
        return content

    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "reasoning":
                logger.debug(
                    "reasoning_block_received",
                    reasoning_id=block.get("id"),
                    has_summary=bool(block.get("summary")),
                )
    return "".join(parts)


def process_llm_response(response: BaseMessage) -> BaseMessage:
    """规范化原始 LLM 响应，确保 ``response.content`` 始终是纯字符串.

    Args:
        response: LLM 返回的原始响应。

    Returns:
        同一个 BaseMessage 实例，但 ``content`` 已设置为纯字符串。
    """
    if isinstance(response.content, list):
        response.content = extract_text_content(response.content)
        logger.debug(
            "processed_structured_content",
            content_block_count=len(response.content),
            extracted_length=len(response.content),
        )
    return response


def prepare_messages(messages: list[Message], system_prompt: str) -> list[Message]:
    """为 LLM 准备消息列表.

    Args:
        messages (list[Message]): 待准备消息。
        system_prompt (str): 要使用的 system prompt。

    Returns:
        list[Message]: 准备好的消息列表。
    """
    try:
        trimmed_messages = _trim_messages(
            dump_messages(messages),
            strategy="last",
            token_counter=_count_tokens_tiktoken,
            max_tokens=settings.MAX_TOKENS,
            start_on="human",
            include_system=False,
            allow_partial=False,
        )
    except ValueError as e:
        # 处理无法识别的内容块，例如 GPT-5 reasoning blocks。
        if "Unrecognized content block type" in str(e):
            logger.warning(
                "token_counting_failed_skipping_trim",
                error=str(e),
                message_count=len(messages),
            )
            # 跳过裁剪，返回全部消息。
            trimmed_messages = messages
        else:
            raise

    return [Message(role="system", content=system_prompt)] + trimmed_messages
