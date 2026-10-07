from alembic import context
from globalmail_agent.adapters.schema import metadata
from globalmail_agent.adapters.database import make_engine
from globalmail_agent.settings import Settings

if context.is_offline_mode():
    raise RuntimeError("Offline migration is unsupported; use the configured local PostgreSQL")

connection = context.config.attributes.get("connection")
if connection is not None:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(Settings.from_env())
    if engine is None:
        raise RuntimeError("GLOBALMAIL_DATABASE_URL is required")
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()

