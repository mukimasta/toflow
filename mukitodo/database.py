from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_PATH = Path.home() / ".mukitodo" / "todo.db"

_db_initialized = False


class Base(DeclarativeBase):
    pass


def get_engine():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{DB_PATH}")


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """Initialize database. Only runs once per application lifecycle."""
    global _db_initialized
    if _db_initialized:
        return
    from mukitodo.models import Track, Project, TodoItem, IdeaItem, NowSession
    engine = get_engine()
    Base.metadata.create_all(engine)

    _db_initialized = True


@contextmanager
def db_session():
    """Auto-manage session lifecycle with context manager."""
    init_db()
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise

