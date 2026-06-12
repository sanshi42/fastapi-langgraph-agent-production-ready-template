"""带预初始化实例的 LLM 模型注册表."""

from typing import (
    Any,
    Dict,
    List,
)

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import (
    Environment,
    settings,
)
from app.core.logging import logger

_TOKEN_LIMIT: Dict[str, Any] = {"max_completion_tokens": settings.MAX_TOKENS}
_API_KEY = SecretStr(settings.OPENAI_API_KEY)


def _chat_openai_kwargs() -> Dict[str, Any]:
    """返回共享的 ChatOpenAI 参数."""
    kwargs: Dict[str, Any] = {
        "api_key": _API_KEY,
        "model_kwargs": _TOKEN_LIMIT,
    }
    if settings.OPENAI_BASE_URL:
        kwargs["base_url"] = settings.OPENAI_BASE_URL
    return kwargs


def _chat_model(name: str, **kwargs: Any) -> ChatOpenAI:
    """按项目默认参数创建 ChatOpenAI 模型."""
    return ChatOpenAI(model=name, **_chat_openai_kwargs(), **kwargs)


def _build_llms() -> List[Dict[str, Any]]:
    """构建模型注册表，并把配置的模型放在首位."""
    llms: List[Dict[str, Any]] = [
        {
            "name": "gpt-5-mini",
            "llm": _chat_model(
                "gpt-5-mini",
                reasoning={"effort": "low"},
            ),
        },
        {
            "name": "gpt-5.4",
            "llm": _chat_model(
                "gpt-5",
                reasoning={"effort": "medium"},
            ),
        },
        {
            "name": "gpt-5.4-nano",
            "llm": _chat_model(
                "gpt-5.4-nano",
                reasoning={"effort": "low"},
            ),
        },
        {
            "name": "gpt-5",
            "llm": _chat_model(
                "gpt-5",
                top_p=0.95 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.8,
                presence_penalty=0.1 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.0,
                frequency_penalty=0.1 if settings.ENVIRONMENT == Environment.PRODUCTION else 0.0,
            ),
        },
    ]

    configured_model = settings.DEFAULT_LLM_MODEL
    if configured_model not in {entry["name"] for entry in llms}:
        llms.insert(0, {"name": configured_model, "llm": _chat_model(configured_model)})

    return llms


class LLMRegistry:
    """可用 LLM 模型注册表，持有预初始化实例.

    该类维护 LLM 配置列表，并提供按名称获取模型的方法；
    调用方也可以传入参数覆盖默认模型配置。
    """

    LLMS: List[Dict[str, Any]] = _build_llms()

    @classmethod
    def get(cls, model_name: str, **kwargs) -> BaseChatModel:
        """按名称获取 LLM，并可选覆盖参数.

        传入 kwargs 时，会返回应用这些覆盖参数的新 ChatOpenAI 实例，
        不修改共享注册表条目。

        Args:
            model_name: 要获取的模型名称。
            **kwargs: 覆盖默认模型配置的可选参数。

        Returns:
            BaseChatModel 实例。

        Raises:
            ValueError: model_name 不在 LLMS 中时抛出。
        """
        model_entry = next((e for e in cls.LLMS if e["name"] == model_name), None)

        if not model_entry:
            available = ", ".join(e["name"] for e in cls.LLMS)
            raise ValueError(f"model '{model_name}' not found in registry. available models: {available}")

        if kwargs:
            logger.debug("creating_llm_with_custom_args", model_name=model_name, custom_args=list(kwargs.keys()))
            return ChatOpenAI(model=model_name, **_chat_openai_kwargs(), **kwargs)

        logger.debug("using_default_llm_instance", model_name=model_name)
        return model_entry["llm"]

    @classmethod
    def get_all_names(cls) -> List[str]:
        """按顺序返回所有已注册模型名称.

        Returns:
            模型名称字符串列表。
        """
        return [e["name"] for e in cls.LLMS]

    @classmethod
    def get_model_at_index(cls, index: int) -> Dict[str, Any]:
        """返回指定索引的模型条目，越界时回退到 0.

        Args:
            index: LLMS 中的索引。

        Returns:
            模型条目字典。
        """
        if 0 <= index < len(cls.LLMS):
            return cls.LLMS[index]
        return cls.LLMS[0]
