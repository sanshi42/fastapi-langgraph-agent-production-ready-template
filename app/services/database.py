"""应用数据库服务."""

from typing import (
    List,
    Optional,
)

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from sqlmodel import (
    Session,
    col,
    create_engine,
    select,
)

from app.core.config import (
    Environment,
    settings,
)
from app.core.logging import logger
from app.models.session import Session as ChatSession
from app.models.user import User


class DatabaseService:
    """数据库操作服务类.

    该类处理 Users、Sessions 和 Messages 相关的数据库操作。
    它使用 SQLModel 执行 ORM 操作，并维护连接池。
    """

    def __init__(self):
        """初始化带连接池的数据库服务."""
        try:
            # 配置环境相关的数据库连接池参数。
            pool_size = settings.POSTGRES_POOL_SIZE
            max_overflow = settings.POSTGRES_MAX_OVERFLOW

            # 使用合适的连接池配置创建 engine。
            connection_url = (
                f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
            )

            self.engine = create_engine(
                connection_url,
                pool_pre_ping=True,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=30,  # 连接超时时间（秒）。
                pool_recycle=1800,  # 30 分钟后回收连接。
            )

            logger.info(
                "database_initialized",
                environment=settings.ENVIRONMENT.value,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )
        except SQLAlchemyError as e:
            logger.error("database_initialization_error", error=str(e), environment=settings.ENVIRONMENT.value)
            # 生产环境不抛出，让应用即使数据库异常也能启动。
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise

    async def create_user(self, email: str, password: str, username: str | None = None) -> User:
        """创建新用户.

        Args:
            email: 用户 email 地址。
            password: 已哈希的密码。
            username: 可选展示名称。

        Returns:
            User: 已创建用户。
        """
        with Session(self.engine) as session:
            user = User(email=email, hashed_password=password, username=username)
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("user_created", email=email)
            return user

    async def get_user(self, user_id: int) -> Optional[User]:
        """根据 ID 获取用户.

        Args:
            user_id: 要获取的用户 ID。

        Returns:
            Optional[User]: 找到时返回用户，否则返回 None。
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据 email 获取用户.

        Args:
            email: 要获取的用户 email。

        Returns:
            Optional[User]: 找到时返回用户，否则返回 None。
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.email == email)
            user = session.exec(statement).first()
            return user

    async def delete_user_by_email(self, email: str) -> bool:
        """根据 email 删除用户.

        Args:
            email: 要删除的用户 email。

        Returns:
            bool: 删除成功返回 True；用户不存在返回 False。
        """
        with Session(self.engine) as session:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                return False

            session.delete(user)
            session.commit()
            logger.info("user_deleted", email=email)
            return True

    async def create_session(
        self, session_id: str, user_id: int, name: str = "", username: str | None = None
    ) -> ChatSession:
        """创建新的聊天 session.

        Args:
            session_id: 新 session 的 ID。
            user_id: session 所属用户 ID。
            name: 可选 session 名称，默认空字符串。
            username: 从用户复制的展示名称，用于 LLM 个性化。

        Returns:
            ChatSession: 已创建 session。
        """
        with Session(self.engine) as session:
            chat_session = ChatSession(id=session_id, user_id=user_id, name=name, username=username)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_created", session_id=session_id, user_id=user_id, name=name)
            return chat_session

    async def delete_session(self, session_id: str) -> bool:
        """根据 ID 删除 session.

        Args:
            session_id: 要删除的 session ID。

        Returns:
            bool: 删除成功返回 True；session 不存在返回 False。
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                return False

            session.delete(chat_session)
            session.commit()
            logger.info("session_deleted", session_id=session_id)
            return True

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """根据 ID 获取 session.

        Args:
            session_id: 要获取的 session ID。

        Returns:
            Optional[ChatSession]: 找到时返回 session，否则返回 None。
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            return chat_session

    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        """获取某个用户的全部 sessions.

        Args:
            user_id: 用户 ID。

        Returns:
            List[ChatSession]: 用户 session 列表。
        """
        with Session(self.engine) as session:
            statement = (
                select(ChatSession).where(col(ChatSession.user_id) == user_id).order_by(col(ChatSession.created_at))
            )
            sessions = session.exec(statement).all()
            return list(sessions)

    async def update_session_name(self, session_id: str, name: str) -> ChatSession:
        """更新 session 名称.

        Args:
            session_id: 要更新的 session ID。
            name: session 新名称。

        Returns:
            ChatSession: 更新后的 session。

        Raises:
            HTTPException: session 不存在时抛出。
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")

            chat_session.name = name
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_name_updated", session_id=session_id, name=name)
            return chat_session

    def get_session_maker(self):
        """获取用于创建数据库 session 的 session maker.

        Returns:
            Session: SQLModel session maker。
        """
        return Session(self.engine)

    async def health_check(self) -> bool:
        """检查数据库连接健康状态.

        Returns:
            bool: 数据库健康返回 True，否则返回 False。
        """
        try:
            with Session(self.engine) as session:
                # 执行简单查询以检查连接。
                session.exec(select(1)).first()
                return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False


# 创建单例实例。
database_service = DatabaseService()
