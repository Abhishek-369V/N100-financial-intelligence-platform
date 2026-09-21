"""
Sprint 6, Day 42: tests/api/test_sectors.py
"""


def test_sectors_returns_10_not_11(client):
    """The spec assumes 11; the real data has 10 — asserting reality."""
    response = client.get("/api/v1/sectors")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 10


def test_sectors_have_required_fields(client):
    data = client.get("/api/v1/sectors").json()
    for sector in data["sectors"]:
        assert "broad_sector" in sector
        assert "company_count" in sector
        assert "median_roe" in sector
        assert "median_pe" in sector
        assert "median_de" in sector


def test_sectors_company_counts_sum_to_92(client):
    data = client.get("/api/v1/sectors").json()
    assert sum(s["company_count"] for s in data["sectors"]) == 92


def test_sector_companies_information_technology(client):
    """Spec calls this 'IT' — real value is 'Information Technology'."""
    response = client.get("/api/v1/sectors/Information Technology/companies")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 5
    assert all("company_id" in c for c in data["companies"])


def test_sector_companies_unknown_sector_404(client):
    response = client.get("/api/v1/sectors/NotASector/companies")
    assert response.status_code == 404


def test_sector_companies_literal_it_is_unknown(client):
    """Confirms the spec's literal 'IT' shorthand does NOT match any real
    sector name — documents the gap as a test, not just a comment."""
    response = client.get("/api/v1/sectors/IT/companies")
    assert response.status_code == 404
