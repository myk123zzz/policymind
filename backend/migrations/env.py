from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from policymind.core.config import get_settings
from policymind.infrastructure.postgres.base import Base

# 导入所有模型以确保迁移包含所有表
import policymind.auth.models  # noqa: F401
import policymind.documents.orm  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# 从项目配置读取数据库 URL，适配同步引擎
settings = get_settings()
sync_url = settings.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
