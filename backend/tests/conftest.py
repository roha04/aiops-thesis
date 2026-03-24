"""
Shared pytest fixtures for backend tests.
Uses SQLite in-memory database instead of PostgreSQL so tests run without
a live database server.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Point to SQLite before the app (and its modules) load the real DATABASE_URL
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_aiops.db")

from db.models import Base
from db.config import get_db
from main import app

SQLITE_URL = "sqlite:///./test_aiops.db"
_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
_TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


# ── database scope: create tables once per test session ─────────────────────
@pytest.fixture(scope="session", autouse=True)
def create_tables():
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()
    try:
        if os.path.exists("./test_aiops.db"):
            os.remove("./test_aiops.db")
    except OSError:
        pass  # Windows may still hold a handle; file will be cleaned on next run


# ── per-test database session, rolls back after each test ───────────────────
@pytest.fixture
def db_session(create_tables):
    connection = _engine.connect()
    transaction = connection.begin()
    session = _TestingSession(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ── FastAPI test client wired to the test DB ─────────────────────────────────
@pytest.fixture
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
