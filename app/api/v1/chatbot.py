"""处理聊天交互的 Chatbot API 端点.

本模块提供普通聊天、流式聊天、消息历史查询和聊天历史清理等端点。
"""

import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)
from fastapi.responses import StreamingResponse

from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.langgraph.graph import LangGraphAgent
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.metrics import llm_stream_duration_seconds
from app.models.session import Session
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Message,
    StreamResponse,
)
from app.services.session_naming import maybe_name_session

router = APIRouter()
agent = LangGraphAgent()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
):
    """使用 LangGraph 处理聊天请求.

    Args:
        request: 用于限流的 FastAPI request 对象。
        chat_request: 包含消息的聊天请求。
        session: 从 auth token 获取的当前 session。

    Returns:
        ChatResponse: 处理后的聊天响应。

    Raises:
        HTTPException: 请求处理失败时抛出。
    """
    try:
        logger.info(
            "chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        if settings.SESSION_NAMING_ENABLED:
            maybe_name_session(session.id, session.name, chat_request.messages)

        result = await agent.get_response(
            chat_request.messages, session.id, user_id=str(session.user_id), username=session.username
        )

        logger.info("chat_request_processed", session_id=session.id)

        runtime_status = agent.runtime_status_from_messages(result)
        return ChatResponse(
            messages=result,
            status=runtime_status["status"],
            approval_id=runtime_status.get("approval_id"),
            tool_name=runtime_status.get("tool_name"),
            risk_reason=runtime_status.get("risk_reason"),
            job_id=runtime_status.get("job_id"),
        )
    except Exception as e:
        logger.exception("chat_request_failed", session_id=session.id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream", responses={200: {"model": StreamResponse}})
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat_stream"][0])
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
):
    """使用 LangGraph 处理聊天请求，并返回流式响应.

    Args:
        request: 用于限流的 FastAPI request 对象。
        chat_request: 包含消息的聊天请求。
        session: 从 auth token 获取的当前 session。

    Returns:
        StreamingResponse: 聊天补全的流式响应。

    Raises:
        HTTPException: 请求处理失败时抛出。
    """
    try:
        logger.info(
            "stream_chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        if settings.SESSION_NAMING_ENABLED:
            maybe_name_session(session.id, session.name, chat_request.messages)

        async def event_generator():
            """生成流式事件.

            Yields:
                str: JSON 格式的 server-sent events。

            Raises:
                Exception: 流式输出过程中出错时抛出。
            """
            try:
                with llm_stream_duration_seconds.labels(model=agent.llm_service.get_llm().get_name()).time():
                    async for chunk in agent.get_stream_response(
                        chat_request.messages, session.id, user_id=str(session.user_id), username=session.username
                    ):
                        runtime_status = agent.runtime_status_from_messages([Message(role="assistant", content=chunk)])
                        stream_status = (
                            runtime_status["status"] if runtime_status["status"] == "pending_approval" else "running"
                        )
                        response = StreamResponse(
                            content=chunk,
                            done=False,
                            status=stream_status,
                            approval_id=runtime_status.get("approval_id"),
                            tool_name=runtime_status.get("tool_name"),
                            risk_reason=runtime_status.get("risk_reason"),
                            job_id=runtime_status.get("job_id"),
                        )
                        yield f"data: {json.dumps(response.model_dump(mode='json'))}\n\n"

                # 发送表示完成的最终消息。
                final_response = StreamResponse(content="", done=True)
                yield f"data: {json.dumps(final_response.model_dump(mode='json'))}\n\n"

            except Exception as e:
                logger.exception(
                    "stream_chat_request_failed",
                    session_id=session.id,
                    error=str(e),
                )
                error_response = StreamResponse(content=str(e), done=True)
                yield f"data: {json.dumps(error_response.model_dump(mode='json'))}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.exception(
            "stream_chat_request_failed",
            session_id=session.id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def get_session_messages(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """获取某个 session 的全部消息.

    Args:
        request: 用于限流的 FastAPI request 对象。
        session: 从 auth token 获取的当前 session。

    Returns:
        ChatResponse: 当前 session 中的全部消息。

    Raises:
        HTTPException: 获取消息失败时抛出。
    """
    try:
        messages = await agent.get_chat_history(session.id)
        return ChatResponse(messages=messages)
    except Exception as e:
        logger.exception("get_messages_failed", session_id=session.id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def clear_chat_history(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """清空某个 session 的全部消息.

    Args:
        request: 用于限流的 FastAPI request 对象。
        session: 从 auth token 获取的当前 session。

    Returns:
        dict: 表示聊天历史已清空的消息。
    """
    try:
        await agent.clear_chat_history(session.id)
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        logger.exception("clear_chat_history_failed", session_id=session.id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
