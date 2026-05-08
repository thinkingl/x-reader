from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.models.database import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/xreader.db")

is_sqlite = "sqlite" in DATABASE_URL

def _build_kwargs():
    if is_sqlite:
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": NullPool,
        }
    return {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 60,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }

engine = create_engine(DATABASE_URL, **_build_kwargs())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
