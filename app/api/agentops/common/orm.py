from typing import Optional, Callable, Generator
import logging
from functools import wraps
from contextlib import contextmanager

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import (
    sessionmaker,
    selectinload,
    joinedload,
    Session,
    DeclarativeBase,
)
from sqlalchemy.inspection import inspect
from sqlalchemy.orm.state import LoaderCallableStatus

from agentops.common.environment import (
    API_DOMAIN,
    SQLALCHEMY_LOG_LEVEL,
    SUPABASE_MIN_POOL_SIZE,
    SUPABASE_MAX_POOL_SIZE,
)


__all__ = [
    "require_loaded",
    "get_orm_session",
    "session_scope",
    "selectinload",
    "joinedload",
    "Session",
    "BaseModel",
]


logging.getLogger("sqlalchemy.engine").setLevel(
    getattr(
        logging,
        str(SQLALCHEMY_LOG_LEVEL).upper(),
        logging.ERROR,
    )
)

_engine: Optional[Engine] = None


class BaseModel(DeclarativeBase):
    pass


def patch_relationship() -> None:
    """
    Patch the SQLAlchemy relationship function to raise an error if the relationship
    is not loaded. This is useful for ensuring that relationships are always loaded
    when accessed, preventing lazy loading in production code.
    """
    import sqlalchemy.orm as orm

    _orig_relationship = orm.relationship

    def raise_lazy_relationships(*args, **kwargs):
        """
        Override the default behavior of SQLAlchemy's relationship to raise an error
        if the relationship is not loaded. This is useful for ensuring that
        relationships are always loaded when accessed, preventing lazy loading
        in production code.
        """
        kwargs.setdefault("lazy", "raise")
        return _orig_relationship(*args, **kwargs)

    orm.relationship = raise_lazy_relationships


if 'localhost' in API_DOMAIN:
    # If running locally, patch `orm.relationship` to raise an error if not loaded.
    patch_relationship()


def require_loaded(*fields) -> Callable:
    """
    Decorator that requires that the specified fields are loaded before calling the
    decorated function.

    This is useful for ensuring that relationships are loaded before accessing them,
    since we can encounter false negatives/positives and do not ever want to run
    lazy loading in production code.

    Usage:

    class MyModel(BaseModel):
        related_field1 = relationship("RelatedModel1")
        related_field2 = relationship("RelatedModel2")

        @require_loaded('related_field1', 'related_field2')
        def my_method(self):
            return self.related_field1, self.related_field2
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            state = inspect(self)
            for field in fields:
                attr_state = state.attrs.get(field)
                try:
                    assert attr_state is not None
                    assert hasattr(attr_state, 'loaded_value')
                    assert attr_state.loaded_value is not LoaderCallableStatus.NO_VALUE
                except AssertionError:
                    raise RuntimeError(f"relationship '{field}' not loaded for {self.__class__.__name__}")

            return fn(self, *args, **kwargs)

        return wrapper

    return decorator


def get_engine() -> Engine:
    """
    Get the SQLAlchemy engine for the application.
    """
    # import the ConnectionConfig late so that we ensure it has the correct values
    # in testing, for example, we patch this to update it with test values
    from .postgres import ConnectionConfig

    global _engine

    if _engine is None:
        # create an engine in parallel with the supabase postgres connection.
        # originally, I tried to utilize the existing pool, but it ended up being
        # very unreliable in longer running tasks. it's possible we can dig deeper
        # into the internals of psycopg_pool to make it work, but for now,
        # we create a new engine that uses the same connection string.
        _engine = create_engine(
            ConnectionConfig.to_connection_string(protocol="postgresql+psycopg"),
            pool_size=SUPABASE_MIN_POOL_SIZE,
            max_overflow=SUPABASE_MAX_POOL_SIZE - SUPABASE_MIN_POOL_SIZE,
            pool_pre_ping=True,  # Test connections before use
            pool_recycle=3600,  # Recycle idle connections after 1 hour
        )

    return _engine


def _create_session() -> Session:
    """Internal function to create a new SQLAlchemy session."""
    return sessionmaker(bind=get_engine(), expire_on_commit=False)()


def get_orm_session() -> Generator[Session, None, None]:
    """
    Create a new SQLAlchemy ORM session.
    When used with FastAPI's Depends(), it will automatically close the session.
    Example: `orm: Session = Depends(get_orm_session)`
    """
    session = _create_session()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = _create_session()
    try:
        session.begin()
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
