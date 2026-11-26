import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# SQLite by default. For PostgreSQL:
#   DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/events
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./events.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def initialize_database() -> None:
    """Create missing tables and apply small backwards-compatible schema updates."""
    Base.metadata.create_all(bind=engine)
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "must_change_password" not in user_columns:
        # SQLAlchemy create_all does not add columns to existing installations.
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT FALSE")
            )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
