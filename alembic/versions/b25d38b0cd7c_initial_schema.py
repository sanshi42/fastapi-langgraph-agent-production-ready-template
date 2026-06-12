"""初始 schema.

Revision ID: b25d38b0cd7c
Revises:
Create Date: 2026-04-12 17:35:38.132952

"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel  # noqa: F401

from alembic import op

# Alembic 使用的 revision 标识。
revision: str = "b25d38b0cd7c"  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级 schema."""
    # ### Alembic 自动生成的命令，请按需调整。###
    op.add_column("session", sa.Column("username", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column("user", sa.Column("username", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    # ### Alembic 命令结束。###


def downgrade() -> None:
    """降级 schema."""
    # ### Alembic 自动生成的命令，请按需调整。###
    op.drop_column("user", "username")
    op.drop_column("session", "username")
    # ### Alembic 命令结束。###
