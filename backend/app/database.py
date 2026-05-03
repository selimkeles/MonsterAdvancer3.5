"""Database connection setup for SQLite."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
# Use prod.db when available (new atomic schema); fall back to legacy monsters.db.
_PROD = os.path.join(_DATA_DIR, "prod.db")
_LEGACY = os.path.join(_DATA_DIR, "monsters.db")
DB_PATH = _PROD if os.path.exists(_PROD) else _LEGACY
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
