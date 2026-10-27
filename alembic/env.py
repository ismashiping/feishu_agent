"""Explicit migration entry point, with offline and injected-connection support."""

from sqlalchemy import Connection

from alembic import context
from clinical_agent.adapters.postgres.connection import DatabaseSettings, database_engine
from clinical_agent.adapters.postgres.models import Base

config = context.config


def run_with_connection(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        compare_type=True,
        user_module_prefix="pgvector.sqlalchemy.",
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url="postgresql+psycopg://",
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    run_with_connection(config.attributes["connection"])
else:
    with database_engine(DatabaseSettings()) as engine, engine.connect() as connection:
        run_with_connection(connection)
