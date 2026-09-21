"""
Sprint 6, Day 42: test_health.py
"""

from src.api.database import ALL_TABLES


def test_health_returns_200(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_status_is_ok(client):
    response = client.get("/api/v1/health")
    assert response.json()["status"] == "ok"


def test_health_db_row_counts_present(client):
    data = client.get("/api/v1/health").json()
    assert "db_row_counts" in data


def test_health_db_row_counts_has_all_tables(client):
    """GAP: real schema has 13 tables"""
    data = client.get("/api/v1/health").json()
    assert set(data["db_row_counts"].keys()) == set(ALL_TABLES)
    assert len(data["db_row_counts"]) == 13


def test_health_row_counts_are_positive():
    from fastapi.testclient import TestClient

    from src.api.main import app

    client = TestClient(app)
    data = client.get("/api/v1/health").json()
    for table, count in data["db_row_counts"].items():
        assert count > 0, f"{table} has 0 rows"


def test_health_has_uptime_and_version(client):
    data = client.get("/api/v1/health").json()
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0
    assert "version" in data
    assert isinstance(data["version"], str)
