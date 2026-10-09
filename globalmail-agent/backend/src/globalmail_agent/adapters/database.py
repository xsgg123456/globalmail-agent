from sqlalchemy import create_engine, text, select
from sqlalchemy.engine import Engine

from globalmail_agent.settings import Settings
from globalmail_agent.adapters.schema import metadata
from globalmail_agent.adapters import conversation_schema, business_schema, knowledge_schema, knowledge_index_schema, agent_schema, attachment_schema  # Register scoped metadata.
from globalmail_agent.adapters import after_sales_schema

SCHEMA_REVISION = "0008_after_sales_ledger"


def make_engine(settings: Settings) -> Engine | None:
    url = settings.database_url.get_secret_value()
    if not url:
        return None
    try:
        engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3},
                               hide_parameters=True)
        if engine.dialect.name != "postgresql":
            engine.dispose()
            raise ValueError("unsupported_database")
        return engine
    except Exception:
        raise ValueError("invalid_database_configuration") from None


def database_status(engine: Engine | None) -> tuple[str, str]:
    if engine is None:
        return "unavailable", "unavailable"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            try:
                revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
                for table in metadata.sorted_tables:
                    connection.execute(select(table).limit(0))
                return "ready", "ready" if revision == SCHEMA_REVISION else "unavailable"
            except Exception:
                return "ready", "unavailable"
    except Exception:
        return "unavailable", "unavailable"

