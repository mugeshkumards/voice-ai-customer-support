"""
Pytest configuration, fixtures, test database setup, and FastAPI test client.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models import Customer, Ticket

# Use an in-memory SQLite database with StaticPool so all sessions share the same in-memory DB
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """
    Creates a fresh database schema for each test function and seeds baseline test data.
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()

    # Seed baseline test customer and ticket
    test_cust = Customer(
        id="CUST-TEST-001",
        name="Test User",
        phone="+15550001111",
        email="testuser@example.com",
        plan="Premium",
        status="active",
        notes="Test account"
    )
    session.add(test_cust)
    session.commit()

    test_ticket = Ticket(
        id="TICK-TEST-001",
        customer_id="CUST-TEST-001",
        issue="Test network latency issue",
        priority="high",
        status="open"
    )
    session.add(test_ticket)
    session.commit()

    yield session

    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    """
    FastAPI TestClient with overridden get_db dependency pointing to the test session.
    """
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
