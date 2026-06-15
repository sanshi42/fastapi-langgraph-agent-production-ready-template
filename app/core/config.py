"""应用配置管理.

本模块负责按环境加载、解析和管理应用配置，包括环境识别、.env 文件加载
和配置值解析。
"""

import os
from enum import StrEnum
from pathlib import Path

from dotenv import load_dotenv


# 定义应用运行环境类型。
class Environment(StrEnum):
    """应用运行环境类型.

    应用可运行在 development、staging、production 和 test 环境中。
    """

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


# 判断当前运行环境。
def get_environment() -> Environment:
    """获取当前运行环境.

    Returns:
        Environment: 当前环境（development、staging、production 或 test）。
    """
    match os.getenv("APP_ENV", "development").lower():
        case "production" | "prod":
            return Environment.PRODUCTION
        case "staging" | "stage":
            return Environment.STAGING
        case "test":
            return Environment.TEST
        case _:
            return Environment.DEVELOPMENT


# 根据当前环境加载对应的 .env 文件。
def load_env_file():
    """加载当前环境对应的 .env 文件."""
    env = get_environment()
    print(f"Loading environment: {env}")
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # 按优先级排列候选 env 文件。
    env_files = [
        os.path.join(base_dir, f".env.{env.value}.local"),
        os.path.join(base_dir, f".env.{env.value}"),
        os.path.join(base_dir, ".env.local"),
        os.path.join(base_dir, ".env"),
    ]

    # 加载第一个存在的 env 文件。
    for env_file in env_files:
        if os.path.isfile(env_file):
            load_dotenv(dotenv_path=env_file)
            print(f"Loaded environment from {env_file}")
            return env_file

    # 没有找到 env 文件时返回 None，使用代码内默认值。
    return None


ENV_FILE = load_env_file()


# 从环境变量解析列表值。
def parse_list_from_env(env_key, default=None):
    """从环境变量解析逗号分隔的列表."""
    value = os.getenv(env_key)
    if not value:
        return default or []

    # 去掉可能存在的引号。
    value = value.strip("\"'")
    # 处理单值场景。
    if "," not in value:
        return [value]
    # 拆分逗号分隔的多个值。
    return [item.strip() for item in value.split(",") if item.strip()]


# 从同一前缀的一组环境变量解析字典列表。
def parse_dict_of_lists_from_env(prefix, default_dict=None):
    """从同一前缀的环境变量解析字典列表."""
    result = default_dict or {}

    # 查找所有带指定前缀的环境变量。
    for key, value in os.environ.items():
        if key.startswith(prefix):
            endpoint = key[len(prefix) :].lower()  # 提取 endpoint 名称。
            # 解析当前 endpoint 对应的限流值。
            if value:
                value = value.strip("\"'")
                if "," in value:
                    result[endpoint] = [item.strip() for item in value.split(",") if item.strip()]
                else:
                    result[endpoint] = [value]

    return result


class Settings:
    """不依赖 pydantic 的应用配置对象."""

    def __init__(self):
        """从环境变量初始化应用配置.

        从环境变量读取所有配置值，并为每项配置提供合理默认值；
        随后根据当前环境应用对应的覆盖配置。
        """
        # 设置当前环境。
        self.ENVIRONMENT = get_environment()

        # 应用基础配置。
        self.PROJECT_NAME = os.getenv("PROJECT_NAME", "FastAPI LangGraph Template")
        self.VERSION = os.getenv("VERSION", "1.0.0")
        self.DESCRIPTION = os.getenv(
            "DESCRIPTION", "A production-ready FastAPI template with LangGraph and Langfuse integration"
        )
        self.API_V1_STR = os.getenv("API_V1_STR", "/api/v1")
        self.DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "t", "yes")

        # CORS 配置。
        self.ALLOWED_ORIGINS = parse_list_from_env("ALLOWED_ORIGINS", ["*"])

        # Langfuse 配置。
        self.LANGFUSE_TRACING_ENABLED = os.getenv("LANGFUSE_TRACING_ENABLED", "true").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )
        self.LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
        self.LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
        self.LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        # LangGraph 配置。
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
        self.DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-5-mini")
        self.SESSION_NAMING_ENABLED = os.getenv("SESSION_NAMING_ENABLED", "true").lower() == "true"
        self.DEFAULT_LLM_TEMPERATURE = float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.2"))
        self.MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
        self.MAX_LLM_CALL_RETRIES = int(os.getenv("MAX_LLM_CALL_RETRIES", "3"))
        self.LLM_TOTAL_TIMEOUT = int(os.getenv("LLM_TOTAL_TIMEOUT", "60"))

        # Agent runtime 配置。
        project_root = Path(__file__).resolve().parents[2]
        self.AGENT_WORKSPACE_ROOT = Path(os.getenv("AGENT_WORKSPACE_ROOT", str(project_root))).resolve()
        self.AGENT_MAX_OUTPUT_CHARS = int(os.getenv("AGENT_MAX_OUTPUT_CHARS", "100000"))
        self.AGENT_TOOL_APPROVAL_ENABLED = os.getenv("AGENT_TOOL_APPROVAL_ENABLED", "true").lower() in (
            "true",
            "1",
            "t",
            "yes",
        )
        self.AGENT_JOB_LEASE_SECONDS = int(os.getenv("AGENT_JOB_LEASE_SECONDS", "60"))
        self.AGENT_WORKER_ENABLED = os.getenv("AGENT_WORKER_ENABLED", "true").lower() in ("true", "1", "t", "yes")
        self.AGENT_MCP_CONFIG_PATH = Path(os.getenv("AGENT_MCP_CONFIG_PATH", "")).expanduser()
        self.AGENT_SKILLS_DIR = Path(
            os.getenv("AGENT_SKILLS_DIR", str(self.AGENT_WORKSPACE_ROOT / "skills"))
        ).resolve()
        self.AGENT_PROJECT_MEMORY_DIR = Path(
            os.getenv("AGENT_PROJECT_MEMORY_DIR", str(self.AGENT_WORKSPACE_ROOT / ".memory"))
        ).resolve()

        # 长期记忆配置。
        self.LONG_TERM_MEMORY_MODEL = os.getenv("LONG_TERM_MEMORY_MODEL", "gpt-5-nano")
        self.LONG_TERM_MEMORY_EMBEDDER_MODEL = os.getenv("LONG_TERM_MEMORY_EMBEDDER_MODEL", "text-embedding-3-small")
        self.LONG_TERM_MEMORY_COLLECTION_NAME = os.getenv("LONG_TERM_MEMORY_COLLECTION_NAME", "longterm_memory")
        # JWT 配置。
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.JWT_ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_DAYS", "30"))

        # 日志配置。
        self.LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # "json" 或 "console"

        # Profiling 配置，仅 DEBUG 模式启用。
        self.PROFILING_DIR = Path(os.getenv("PROFILING_DIR", "/tmp/fastapi_profiles"))
        self.PROFILING_THRESHOLD_SECONDS = float(os.getenv("PROFILING_THRESHOLD_SECONDS", "2.0"))

        # Postgres 配置。
        self.POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_DB = os.getenv("POSTGRES_DB", "food_order_db")
        self.POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
        self.POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
        self.POSTGRES_POOL_SIZE = int(os.getenv("POSTGRES_POOL_SIZE", "20"))
        self.POSTGRES_MAX_OVERFLOW = int(os.getenv("POSTGRES_MAX_OVERFLOW", "10"))
        self.CHECKPOINT_TABLES = ["checkpoint_blobs", "checkpoint_writes", "checkpoints"]

        # Valkey/Redis 缓存配置；设置 host 后启用缓存。
        self.VALKEY_HOST = os.getenv("VALKEY_HOST", "")
        self.VALKEY_PORT = int(os.getenv("VALKEY_PORT", "6379"))
        self.VALKEY_DB = int(os.getenv("VALKEY_DB", "0"))
        self.VALKEY_PASSWORD = os.getenv("VALKEY_PASSWORD", "")
        self.VALKEY_MAX_CONNECTIONS = int(os.getenv("VALKEY_MAX_CONNECTIONS", "20"))
        self.CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))

        # 限流配置。
        self.RATE_LIMIT_DEFAULT = parse_list_from_env("RATE_LIMIT_DEFAULT", ["200 per day", "50 per hour"])

        # 各 endpoint 默认限流值。
        default_endpoints = {
            "chat": ["30 per minute"],
            "chat_stream": ["20 per minute"],
            "messages": ["50 per minute"],
            "register": ["10 per hour"],
            "login": ["20 per minute"],
            "root": ["10 per minute"],
            "health": ["20 per minute"],
        }

        # 使用环境变量覆盖各 endpoint 限流值。
        self.RATE_LIMIT_ENDPOINTS = default_endpoints.copy()
        for endpoint in default_endpoints:
            env_key = f"RATE_LIMIT_{endpoint.upper()}"
            value = parse_list_from_env(env_key)
            if value:
                self.RATE_LIMIT_ENDPOINTS[endpoint] = value

        # 评测配置。
        self.EVALUATION_LLM = os.getenv("EVALUATION_LLM", "gpt-5")
        self.EVALUATION_BASE_URL = os.getenv("EVALUATION_BASE_URL", "https://api.openai.com/v1")
        self.EVALUATION_API_KEY = os.getenv("EVALUATION_API_KEY", self.OPENAI_API_KEY)
        self.EVALUATION_SLEEP_TIME = int(os.getenv("EVALUATION_SLEEP_TIME", "10"))

        # 应用环境特定配置。
        self.apply_environment_settings()

    def apply_environment_settings(self):
        """根据当前环境应用特定配置."""
        env_settings = {
            Environment.DEVELOPMENT: {
                "DEBUG": True,
                "LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "console",
                "RATE_LIMIT_DEFAULT": ["1000 per day", "200 per hour"],
            },
            Environment.STAGING: {
                "DEBUG": False,
                "LOG_LEVEL": "INFO",
                "RATE_LIMIT_DEFAULT": ["500 per day", "100 per hour"],
            },
            Environment.PRODUCTION: {
                "DEBUG": False,
                "LOG_LEVEL": "WARNING",
                "RATE_LIMIT_DEFAULT": ["200 per day", "50 per hour"],
            },
            Environment.TEST: {
                "DEBUG": True,
                "LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "console",
                "RATE_LIMIT_DEFAULT": ["1000 per day", "1000 per hour"],  # 测试环境放宽限流。
            },
        }

        # 获取当前环境的配置覆盖项。
        current_env_settings = env_settings.get(self.ENVIRONMENT, {})

        # 环境变量没有显式设置时，才应用环境默认覆盖项。
        for key, value in current_env_settings.items():
            env_var_name = key.upper()
            # 只覆盖未通过环境变量显式设置的配置。
            if env_var_name not in os.environ:
                setattr(self, key, value)


# 创建 settings 实例。
settings = Settings()
