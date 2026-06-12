"""带重试、循环降级和可选结构化输出的 LLM 服务."""

import asyncio
import logging
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import BaseMessage
from openai import (
    APIError,
    APITimeoutError,
    OpenAIError,
    RateLimitError,
)
from pydantic import BaseModel
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import logger
from app.services.llm.registry import LLMRegistry

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """管理 LLM 调用、重试和循环降级的服务.

    这里区分两条执行路径：

    - **默认路径**（不传 model_name / response_format / model_kwargs）：使用
      ``self._llm``，也就是已经绑定工具的 Agent 模型。循环降级会更新
      ``self._llm``，确保重试切换模型后工具绑定仍然保留。

    - **一次性路径**（传入任意覆盖项）：为本次调用创建新的本地 ``Runnable``，
      不修改 ``self._llm``，因此不会影响并发中的默认路径调用。
    """

    def __init__(self):
        """使用配置中的默认模型初始化 LLM 服务."""
        self._llm: Any = None  # bind_tools 前是 BaseChatModel，之后是 Runnable。
        self._current_model_index: int = 0
        self._bound_tools: List = []

        all_names = LLMRegistry.get_all_names()
        try:
            self._current_model_index = all_names.index(settings.DEFAULT_LLM_MODEL)
            self._llm = LLMRegistry.get(settings.DEFAULT_LLM_MODEL)
            logger.info(
                "llm_service_initialized",
                default_model=settings.DEFAULT_LLM_MODEL,
                model_index=self._current_model_index,
                total_models=len(all_names),
                environment=settings.ENVIRONMENT.value,
            )
        except Exception as e:
            self._current_model_index = 0
            self._llm = LLMRegistry.LLMS[0]["llm"]
            logger.warning(
                "default_model_not_found_using_first",
                requested=settings.DEFAULT_LLM_MODEL,
                using=all_names[0] if all_names else "none",
                error=str(e),
            )

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    @overload
    async def call(
        self,
        messages: LanguageModelInput,
        model_name: Optional[str] = ...,
        response_format: None = ...,
        **model_kwargs: Any,
    ) -> BaseMessage: ...

    @overload
    async def call(
        self,
        messages: LanguageModelInput,
        model_name: Optional[str] = ...,
        *,
        response_format: Type[T],
        **model_kwargs: Any,
    ) -> T: ...

    async def call(
        self,
        messages: LanguageModelInput,
        model_name: Optional[str] = None,
        response_format: Optional[Type[BaseModel]] = None,
        **model_kwargs: Any,
    ) -> Union[BaseMessage, BaseModel]:
        """调用 LLM，并在失败时执行重试和循环降级.

        Args:
            messages: 要发送的对话消息。
            model_name: 覆盖模型名称；``None`` 表示使用当前默认模型。
            response_format: 用于结构化输出的 Pydantic schema。传入后会串接
                ``.with_structured_output(schema)``，返回该 schema 的校验实例，
                而不是原始 ``BaseMessage``。
            **model_kwargs: 创建一次性模型实例时转发给 ``LLMRegistry.get`` 的
                额外参数，例如 ``temperature``、``max_tokens``、``reasoning``。

        Returns:
            ``response_format`` 为 ``None`` 时返回 ``BaseMessage``，
            否则返回 ``response_format`` 的校验实例。

        Raises:
            RuntimeError: 所有模型重试后仍失败，或超过总超时预算。
        """
        try:
            return await asyncio.wait_for(
                self._call_with_fallback(messages, model_name, response_format, model_kwargs),
                timeout=settings.LLM_TOTAL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.exception(
                "llm_total_timeout_exceeded",
                timeout_seconds=settings.LLM_TOTAL_TIMEOUT,
            )
            raise RuntimeError(f"llm call timed out after {settings.LLM_TOTAL_TIMEOUT}s total budget")

    def get_llm(self) -> Any:
        """返回当前已绑定工具的默认 LLM 实例.

        Returns:
            当前 ``BaseChatModel`` 实例；尚未初始化时返回 ``None``。
        """
        return self._llm

    def bind_tools(self, tools: List) -> "LLMService":
        """把工具绑定到默认 LLM 实例.

        Args:
            tools: 要绑定的工具列表。

        Returns:
            返回自身，便于链式调用。
        """
        if self._llm:
            self._bound_tools = tools
            self._llm = self._llm.bind_tools(tools)
            logger.debug("tools_bound_to_llm", tool_count=len(tools))
        return self

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(settings.MAX_LLM_CALL_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _invoke_with_retry(self, llm: Any, messages: LanguageModelInput) -> Any:
        """调用 LLM runnable，并对单个模型应用自动重试.

        Args:
            llm: 任意 LangChain ``Runnable``，可以是普通模型或结构化输出链。
            messages: 要发送的消息。

        Returns:
            runnable 的响应，可能是 ``BaseMessage`` 或 ``BaseModel`` 实例。

        Raises:
            OpenAIError: 所有重试耗尽后继续抛出。
        """
        try:
            response = await llm.ainvoke(messages)
            logger.debug("llm_call_successful")
            return response
        except (RateLimitError, APITimeoutError, APIError) as e:
            logger.warning(
                "llm_call_failed_retrying",
                error_type=type(e).__name__,
                error=str(e),
                exc_info=True,
            )
            raise
        except OpenAIError as e:
            logger.error(
                "llm_call_failed",
                error_type=type(e).__name__,
                error=str(e),
            )
            raise

    def _switch_to_next_model(self) -> bool:
        """把默认模型切换到注册表中的下一个模型（循环）.

        该方法会修改 ``self._llm`` 和 ``self._current_model_index``，
        确保默认 Agent 路径切换模型后仍保留工具绑定。

        Returns:
            切换成功返回 ``True``，失败返回 ``False``。
        """
        try:
            next_index = (self._current_model_index + 1) % len(LLMRegistry.LLMS)
            next_entry = LLMRegistry.get_model_at_index(next_index)
            logger.warning(
                "switching_to_next_model",
                from_index=self._current_model_index,
                to_index=next_index,
                to_model=next_entry["name"],
            )
            self._current_model_index = next_index
            self._llm = next_entry["llm"]
            if self._bound_tools:
                self._llm = self._llm.bind_tools(self._bound_tools)
            logger.info("model_switched", new_model=next_entry["name"], new_index=next_index)
            return True
        except Exception as e:
            logger.error("model_switch_failed", error=str(e))
            return False

    async def _call_with_fallback(
        self,
        messages: LanguageModelInput,
        model_name: Optional[str],
        response_format: Optional[Type[BaseModel]],
        model_kwargs: dict,
    ) -> Union[BaseMessage, BaseModel]:
        """构建不同路径的策略，并委托给共享降级循环.

        一次性路径（传入任意覆盖项）：
            ``get_target`` 每次尝试都会创建新的注册表实例。
            ``advance`` 只推进局部索引，不触碰 ``self._llm``。

        默认路径（没有覆盖项）：
            ``get_target`` 返回已绑定工具的 ``self._llm``。
            ``advance`` 调用 ``_switch_to_next_model``，确保绑定持续生效。
        """

        def _override_target(idx: int) -> Any:
            base = LLMRegistry.get(LLMRegistry.LLMS[idx]["name"], **model_kwargs)
            return base.with_structured_output(response_format) if response_format else base

        def _default_target(_: int) -> Any:
            return self._llm

        def _default_advance(_: int) -> Optional[int]:
            return self._current_model_index if self._switch_to_next_model() else None

        if model_name or response_format or model_kwargs:
            all_names = LLMRegistry.get_all_names()
            if model_name and model_name not in all_names:
                logger.error("requested_model_not_found", model_name=model_name)
                raise ValueError(
                    f"model '{model_name}' not found in registry. available models: {', '.join(all_names)}"
                )

            start = all_names.index(model_name) if model_name else self._current_model_index
            total = len(LLMRegistry.LLMS)
            get_target: Callable[[int], Any] = _override_target

            def _override_advance(idx: int) -> Optional[int]:
                return (idx + 1) % total

            advance: Callable[[int], Optional[int]] = _override_advance
        else:
            start = self._current_model_index
            get_target = _default_target
            advance = _default_advance

        return await self._fallback_loop(messages, start, get_target, advance)

    async def _fallback_loop(
        self,
        messages: LanguageModelInput,
        start: int,
        get_target: Callable[[int], Any],
        advance: Callable[[int], Optional[int]],
    ) -> Any:
        """共享降级循环：依次尝试模型，直到某个模型成功.

        Args:
            messages: 要发送的消息。
            start: 起始注册表索引。
            get_target: 根据索引返回要调用的 ``Runnable``。
            advance: 返回下一个要尝试的索引；返回 ``None`` 表示停止。

        Returns:
            第一个成功响应。

        Raises:
            RuntimeError: 所有模型都尝试失败。
        """
        total = len(LLMRegistry.LLMS)
        current = start
        models_tried = 0
        last_error: Optional[Exception] = None

        for models_tried in range(1, total + 1):
            current_name = LLMRegistry.LLMS[current]["name"]
            try:
                return await self._invoke_with_retry(get_target(current), messages)
            except OpenAIError as e:
                last_error = e
                logger.error(
                    "llm_call_failed_after_retries",
                    model=current_name,
                    models_tried=models_tried,
                    total_models=total,
                    error=str(e),
                )
                if models_tried >= total:
                    logger.error(
                        "all_models_failed", models_tried=models_tried, starting_model=LLMRegistry.LLMS[start]["name"]
                    )
                    break
                next_idx = advance(current)
                if next_idx is None:
                    logger.error("failed_to_switch_to_next_model")
                    break
                current = next_idx

        raise RuntimeError(
            f"failed to get response from llm after trying {models_tried} models. last error: {str(last_error)}"
        )


llm_service = LLMService()
