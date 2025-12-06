from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_PATH = Path.home() / ".mukitodo" / "todo.db"


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
    from mukitodo.models import Track, Project, TodoItem
    engine = get_engine()
    Base.metadata.create_all(engine)

