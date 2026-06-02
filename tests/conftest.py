import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base
from app.main import create_app

# All models must be imported so Base.metadata is complete.
import app.models  # noqa: F401

TEST_DB_URL = settings.database_url.rsplit("/shipa", 1)[0] + "/shipa_test"


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
    TestSession = sessionmaker(bind=engine, expire_on_commit=False, future=True)
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
