"""应用主入口."""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uvicorn

from asgi_correlation_id import CorrelationIdMiddleware

from app.api.v1.api import api_router
from app.api.v1.chatbot import agent
from app.core.cache import cache_service
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.metrics import setup_metrics
from app.core.middleware import (
    LoggingContextMiddleware,
    MetricsMiddleware,
    ProfilingMiddleware,
)
from app.core.observability import langfuse_init
from app.agent_runtime.worker import agent_runtime_worker
from app.services.database import database_service
from app.services.memory import memory_service

FRONTEND_DIST_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST_DIR / "index.html"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"

# 加载环境变量。
load_dotenv()
langfuse_init()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """处理应用启动和关闭事件."""
    logger.info(
        "application_startup",
        project_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        api_prefix=settings.API_V1_STR,
    )

    # 初始化缓存服务；配置 Valkey 时会建立连接。
    try:
        await cache_service.initialize()
    except Exception as e:
        logger.exception("cache_initialization_failed", error=str(e))

    # 预热 LangGraph agent：启动时创建 graph 和连接池，避免首个请求冷启动延迟。
    try:
        await agent.create_graph()
        logger.info("graph_pre_warmed")
    except Exception as e:
        logger.exception("graph_pre_warm_failed", error=str(e))

    # 预热 mem0 AsyncMemory：初始化 pgvector 连接和 schema 检查，
    # 避免首次 search() cache miss 或 add() 承担约 130ms 的冷启动成本。
    try:
        await memory_service.initialize()
    except Exception as e:
        logger.exception("memory_service_pre_warm_failed", error=str(e))

    # 应用内 Agent runtime worker 使用 Postgres lease 去重执行后台 job。
    if settings.AGENT_WORKER_ENABLED:
        try:
            agent_runtime_worker.start()
        except Exception as e:
            logger.exception("agent_runtime_worker_start_failed", error=str(e))

    yield

    # 应用关闭时清理资源。
    await agent_runtime_worker.stop()
    await cache_service.close()
    if agent._connection_pool:
        await agent._connection_pool.close()
        logger.info("connection_pool_closed")
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# 设置 Prometheus 指标。
setup_metrics(app)

# 添加日志上下文中间件；必须早于其他中间件添加，才能捕获上下文。
app.add_middleware(LoggingContextMiddleware)

# 添加自定义指标中间件。
app.add_middleware(MetricsMiddleware)

# 添加 profiling 中间件；仅 DEBUG 模式启用，慢请求报告保存到 /tmp。
if settings.DEBUG:
    app.add_middleware(ProfilingMiddleware)

# 添加 correlation ID 中间件；它必须在最外层，确保其他中间件前已设置 request_id。
app.add_middleware(CorrelationIdMiddleware)

# 设置限流异常处理器。
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # pyright: ignore[reportArgumentType]


# 添加参数校验异常处理器。
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求数据校验错误.

    Args:
        request: 触发校验错误的请求。
        exc: 校验错误对象。

    Returns:
        JSONResponse: 格式化后的错误响应。
    """
    # 记录校验错误。
    logger.error(
        "validation_error",
        client_host=request.client.host if request.client else "unknown",
        path=request.url.path,
        errors=str(exc.errors()),
    )

    # 把错误格式化得更适合用户阅读。
    formatted_errors = []
    for error in exc.errors():
        loc = " -> ".join([str(loc_part) for loc_part in error["loc"] if loc_part != "body"])
        formatted_errors.append({"field": loc, "message": error["msg"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": formatted_errors},
    )


# 设置 CORS 中间件。
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 API router。
app.include_router(api_router, prefix=settings.API_V1_STR)

if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="frontend-assets")


@app.get("/", response_model=None)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["root"][0])
async def root(request: Request) -> Response | dict[str, str]:
    """返回 React SPA 入口；未构建前端时返回基础 API 信息."""
    logger.info("root_endpoint_called")
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)

    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "environment": settings.ENVIRONMENT.value,
        "swagger_url": "/docs",
        "redoc_url": "/redoc",
    }


@app.get("/health")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["health"][0])
async def health_check(request: Request) -> JSONResponse:
    """带环境信息的健康检查端点.

    Returns:
        JSONResponse: 健康状态 payload；数据库不可达时返回 HTTP 503，
        方便负载均衡器摘除实例。
    """
    logger.info("health_check_called")

    # 检查数据库连通性。
    db_healthy = await database_service.health_check()

    response = {
        "status": "healthy" if db_healthy else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT.value,
        "components": {"api": "healthy", "database": "healthy" if db_healthy else "unhealthy"},
        "timestamp": datetime.now().isoformat(),
    }

    # 数据库不健康时返回对应状态码。
    status_code = status.HTTP_200_OK if db_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)


@app.get("/{spa_path:path}", response_model=None)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["root"][0])
async def spa_fallback(request: Request, spa_path: str) -> Response:
    """让前端路由刷新时回退到 React SPA."""
    if spa_path.startswith(("api/", "docs", "redoc", "health", "metrics", "assets/")):
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "Not Found"})

    static_file = FRONTEND_DIST_DIR / spa_path
    if static_file.exists() and static_file.is_file():
        return FileResponse(static_file)

    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "frontend build not found"})


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
