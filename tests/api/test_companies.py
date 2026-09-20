"""
Sprint 6, Day 42: test_companies.py
Per spec: /companies returns 92 records, /companies/TCS returns correct data, /companies/INVALID returns 404.
"""


def test_list_companies_returns_92(client):
    response = client.get("/api/v1/companies")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 92
    assert len(data["companies"]) == 92


def test_list_companies_sector_filter(client):
    response = client.get("/api/v1/companies?sector=Information Technology")
    data = response.json()
    assert data["count"] == 5  # confirmed sector size from Sprint 5 Day 34
    assert all(c["broad_sector"] == "Information Technology" for c in data["companies"])


def test_list_companies_search_filter(client):
    response = client.get("/api/v1/companies?search=Tata")
    data = response.json()
    assert data["count"] > 0
    assert all("tata" in c["company_name"].lower() or "tata" in c["id"].lower() for c in data["companies"])


def test_get_company_tcs_returns_correct_data(client):
    response = client.get("/api/v1/companies/TCS")
    assert response.status_code == 200
    data = response.json()
    assert data["company"]["id"] == "TCS"
    assert data["company"]["company_name"] == "Tata Consultancy Services Ltd"
    assert data["sector"]["broad_sector"] == "Information Technology"
    assert data["latest_year_kpis"] is not None


def test_get_company_invalid_returns_404(client):
    response = client.get("/api/v1/companies/INVALID")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_company_pl_history(client):
    response = client.get("/api/v1/companies/TCS/pl")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert all(row["company_id"] == "TCS" for row in data["profit_and_loss"])


def test_get_company_pl_year_filter(client):
    response = client.get("/api/v1/companies/TCS/pl?from_year=2023-03&to_year=2024-03")
    data = response.json()
    assert data["count"] == 2
    assert {row["year"] for row in data["profit_and_loss"]} == {"2023-03", "2024-03"}


def test_get_company_pl_invalid_ticker_404(client):
    response = client.get("/api/v1/companies/INVALID/pl")
    assert response.status_code == 404


def test_get_company_bs_history(client):
    response = client.get("/api/v1/companies/TCS/bs")
    assert response.status_code == 200
    assert response.json()["count"] > 0


def test_get_company_cashflow_history(client):
    response = client.get("/api/v1/companies/TCS/cashflow")
    assert response.status_code == 200
    assert response.json()["count"] > 0


def test_get_company_ratios_full_history(client):
    response = client.get("/api/v1/companies/TCS/ratios")
    data = response.json()
    assert data["count"] > 1


def test_get_company_ratios_single_year(client):
    response = client.get("/api/v1/companies/TCS/ratios?year=2024-03")
    data = response.json()
    assert data["count"] == 1
    assert data["ratios"][0]["year"] == "2024-03"


def test_get_company_tearsheet_returns_pdf(client):
    response = client.get("/api/v1/companies/TCS/tearsheet")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 30 * 1024  # matches Sprint 5's own 30KB minimum


def test_get_company_tearsheet_skipped_company_404(client):
    """JIOFIN was deliberately skipped in Sprint 5 Day 34 batch generation (<3 years of data) 
    -- should 404 with a message explaining why, not a generic 'not found'."""
    response = client.get("/api/v1/companies/JIOFIN/tearsheet")
    assert response.status_code == 404
    assert "skipped" in response.json()["detail"].lower()


def test_get_company_tearsheet_invalid_ticker_404(client):
    response = client.get("/api/v1/companies/INVALID/tearsheet")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()