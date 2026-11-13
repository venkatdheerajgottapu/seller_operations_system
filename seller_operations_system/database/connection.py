import logging
import time
import os
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import Dict, Any, Generator
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from sqlalchemy.engine import Engine
import mysql.connector

from app.config import Config, BASE_DIR

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    """Return current naive UTC datetime, replacing deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Base class for SQLAlchemy models
Base = declarative_base()

_engines: Dict[str, Any] = {}
_session_factories: Dict[str, Any] = {}


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass


def get_default_uri() -> str:
    """
    Determine default database URI.
    If MySQL password is provided, connects to MySQL Server 8.0;
    Otherwise, defaults to high-performance local SQLite database.
    """
    if os.getenv('DATABASE_URL'):
        return os.getenv('DATABASE_URL')

    sqlite_path = BASE_DIR / 'seller_ops_db.sqlite'
    default_sqlite = f"sqlite:///{sqlite_path.as_posix()}"

    # Only attempt MySQL socket connection if DB_PASSWORD is provided in .env
    if not Config.DB_PASSWORD:
        return default_sqlite

    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=int(Config.DB_PORT),
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            connection_timeout=1
        )
        conn.close()
        return Config.MYSQL_URI
    except (Exception, BaseException):
        return default_sqlite


def get_engine(database_uri: str = None):
    """Retrieve or create the SQLAlchemy engine keyed by URI."""
    uri = database_uri or get_default_uri()
    if uri not in _engines:
        engine_options = Config.SQLALCHEMY_ENGINE_OPTIONS if 'mysql' in uri else {}
        _engines[uri] = create_engine(uri, **engine_options)
    return _engines[uri]


def get_session_factory(database_uri: str = None):
    """Retrieve or create the scoped session factory keyed by URI."""
    uri = database_uri or get_default_uri()
    if uri not in _session_factories:
        engine = get_engine(uri)
        _session_factories[uri] = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
        )
    return _session_factories[uri]


@contextmanager
def get_session(database_uri: str = None) -> Generator:
    """Context manager for handling database sessions cleanly."""
    session_factory = get_session_factory(database_uri)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error(f"Database session error: {exc}")
        raise
    finally:
        session.close()


def create_database_if_not_exists(
    host: str = None,
    port: int = None,
    user: str = None,
    password: str = None,
    db_name: str = None
) -> Dict[str, Any]:
    """
    Connect to MySQL server and ensure the target database exists.
    """
    host = host or Config.DB_HOST
    port = int(port or Config.DB_PORT)
    user = user or Config.DB_USER
    password = password or Config.DB_PASSWORD
    db_name = db_name or Config.DB_NAME

    result = {
        "success": False,
        "database": db_name,
        "message": ""
    }

    try:
        conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connection_timeout=3
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        cursor.close()
        conn.close()
        result["success"] = True
        result["message"] = f"MySQL Database '{db_name}' verified / created successfully."
        logger.info(result["message"])
    except mysql.connector.Error as err:
        result["message"] = f"MySQL connection notice: [{err.errno}] {err.msg} (SQLite fallback active)."
        logger.info(result["message"])
    except Exception as exc:
        result["message"] = f"Database notice: {exc} (SQLite fallback active)."

    return result


def init_db(database_uri: str = None):
    """Initialize all tables defined in Base."""
    engine = get_engine(database_uri)
    Base.metadata.create_all(bind=engine)
    logger.info(f"Database initialized with tables: {list(Base.metadata.tables.keys())}")


def check_db_connection(database_uri: str = None) -> Dict[str, Any]:
    """
    Perform a health check on the database connection.
    Returns diagnostic details including latency, engine dialect, and server version.
    """
    uri = database_uri or get_default_uri()
    engine = get_engine(uri)
    start_time = time.time()
    
    status = {
        "connected": False,
        "dialect": engine.dialect.name,
        "database_uri": uri.split('@')[-1] if '@' in uri else uri,  # Redact credentials
        "latency_ms": None,
        "server_version": None,
        "error": None
    }

    try:
        with engine.connect() as connection:
            if 'mysql' in uri:
                result = connection.execute(text("SELECT VERSION()"))
                version = result.scalar()
                status["server_version"] = f"MySQL {version}"
            else:
                result = connection.execute(text("SELECT sqlite_version()"))
                version = result.scalar()
                status["server_version"] = f"SQLite {version}"
            
            status["connected"] = True
            status["latency_ms"] = round((time.time() - start_time) * 1000, 2)
    except Exception as exc:
        status["error"] = str(exc)
        status["connected"] = False

    return status
