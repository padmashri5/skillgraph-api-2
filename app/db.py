import os
from sqlalchemy import create_engine
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import DeclarativeBase, sessionmaker

URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")  # prod: postgresql+psycopg://user:pw@host/db
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


def upsert(session, model, rows, keys, update, chunk=5000):
    """Bulk INSERT ... ON CONFLICT DO UPDATE (works on Postgres and SQLite)."""
    for i in range(0, len(rows), chunk):
        stmt = insert_fn()(model)
        stmt = stmt.on_conflict_do_update(index_elements=keys, set_={c: stmt.excluded[c] for c in update})
        session.execute(stmt, rows[i:i + chunk])
