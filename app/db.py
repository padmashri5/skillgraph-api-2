import os
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import DeclarativeBase, sessionmaker

URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")  # prod: ******host/db
_kw = ({"connect_args": {"check_same_thread": False}} if URL.startswith("sqlite") else
       {"pool_size": int(os.getenv("DB_POOL", "20")), "max_overflow": 10, "pool_pre_ping": True})
engine = create_engine(URL, **_kw)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as s:
        yield s


def insert_fn():
    return (postgresql if engine.dialect.name == "postgresql" else sqlite).insert


def sync_postgres_sequences(session, models):
    """Advance serial sequences after inserting explicit primary-key values on PostgreSQL."""
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return

    preparer = bind.dialect.identifier_preparer
    for model in models:
        table = model.__table__
        if len(table.primary_key.columns) != 1:
            continue
        column = next(iter(table.primary_key.columns))
        quoted_table = preparer.quote(table.name)
        quoted_column = preparer.quote(column.name)
        sequence = session.scalar(
            text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
            {"table_name": table.fullname, "column_name": column.name},
        )
        if sequence:
            session.execute(
                text(
                    f"SELECT setval(CAST(:sequence AS regclass), "
                    f"COALESCE((SELECT MAX({quoted_column}) FROM {quoted_table}), 1), "
                    f"EXISTS (SELECT 1 FROM {quoted_table}))"
                ),
                {"sequence": sequence},
            )


def upsert(session, model, rows, keys, update, chunk=5000):
    """Bulk INSERT ... ON CONFLICT DO UPDATE (works on Postgres and SQLite)."""
    for i in range(0, len(rows), chunk):
        stmt = insert_fn()(model)
        stmt = stmt.on_conflict_do_update(index_elements=keys, set_={c: stmt.excluded[c] for c in update})
        session.execute(stmt, rows[i:i + chunk])
