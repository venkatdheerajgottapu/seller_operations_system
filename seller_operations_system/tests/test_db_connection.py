import pytest
from sqlalchemy import text
from database.connection import check_db_connection, get_session, get_engine


def test_sqlite_in_memory_connection():
    """Verify that the connection checker works cleanly with SQLite in-memory."""
    status = check_db_connection("sqlite:///:memory:")
    assert status["connected"] is True
    assert status["dialect"] == "sqlite"
    assert status["latency_ms"] is not None
    assert status["error"] is None


def test_session_lifecycle():
    """Verify that get_session creates and manages transactions."""
    uri = "sqlite:///:memory:"
    engine = get_engine(uri)
    with get_session(uri) as session:
        result = session.execute(text("SELECT 42 AS value")).fetchone()
        assert result[0] == 42


def test_invalid_connection_handling():
    """Verify that connection failure is handled gracefully without unhandled exceptions."""
    # Attempt connecting to a non-existent port
    bad_uri = "mysql+mysqlconnector://invalid_user:invalid_pass@127.0.0.1:59999/invalid_db"
    status = check_db_connection(bad_uri)
    assert status["connected"] is False
    assert status["error"] is not None

