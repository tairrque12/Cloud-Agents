import asyncio
import os
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool

from alembic import context

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from db.database import Base
from db import models  # noqa: F401 — registers all ORM models with Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url_and_connect_args():
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

    url = os.getenv("DATABASE_URL", "")
    if not url:
        url = config.get_main_option("sqlalchemy.url")

    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # asyncpg doesn't accept sslmode/channel_binding as URL params —
    # strip them and pass ssl as a connect_arg instead.
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    needs_ssl = params.pop("sslmode", [None])[0] in ("require", "verify-full", "verify-ca")
    params.pop("channel_binding", None)

    clean_query = urlencode({k: v[0] for k, v in params.items()})
    clean_url = urlunparse(parsed._replace(query=clean_query))

    connect_args = {"ssl": "require"} if needs_ssl else {}
    return clean_url, connect_args


def run_migrations_offline() -> None:
    url, _ = get_url_and_connect_args()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    url, connect_args = get_url_and_connect_args()
    connectable = create_async_engine(url, poolclass=pool.NullPool, connect_args=connect_args)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
