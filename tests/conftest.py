import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base
from app.main import create_app

# All models must be imported so Base.metadata is complete.
import app.models  # noqa: F401

_base_url = make_url(settings.database_url)
TEST_DB_URL = _base_url.set(database=f"{_base_url.database}_test").render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def engine():
    # Create the test database if missing, then build the schema.
    admin = create_engine(settings.database_url, isolation_level="AUTOCOMMIT", future=True)
    with admin.connect() as conn:
        exists = conn.exec_driver_sql(
            "SELECT 1 FROM pg_database WHERE datname = 'shipa_test'"
        ).fetchone()
        if not exists:
            conn.exec_driver_sql("CREATE DATABASE shipa_test")
    admin.dispose()

    eng = create_engine(TEST_DB_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db(engine):
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
    session = TestSession()
    yield session
    session.rollback()
    # Clean every table between tests for isolation.
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture()
def client(engine, db):
    from app.deps import get_db

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)
