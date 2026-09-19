from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "db_row_counts" in data

def test_list_companies():
    response = client.get("/api/v1/companies")
    assert response.status_code == 200
    assert "companies" in response.json()

def test_company_detail():
    # Fetch first available company to test dynamic ticker
    companies_res = client.get("/api/v1/companies")
    companies = companies_res.json().get("companies", [])
    if companies:
        ticker = companies[0]["id"]
        response = client.get(f"/api/v1/companies/{ticker}")
        assert response.status_code == 200
        assert "company" in response.json()

def test_list_sectors():
    response = client.get("/api/v1/sectors")
    assert response.status_code == 200
    assert "sectors" in response.json()

def test_screener():
    response = client.get("/api/v1/screener?min_roe=10")
    assert response.status_code == 200
    assert "companies" in response.json()

def test_invalid_company_404():
    response = client.get("/api/v1/companies/NONEXISTENT_TICKER")
    assert response.status_code == 404

def test_financial_statements():
    companies_res = client.get("/api/v1/companies")
    companies = companies_res.json().get("companies", [])
    if companies:
        ticker = companies[0]["id"]
        # P&L, Balance Sheet, Cashflow
        assert client.get(f"/api/v1/companies/{ticker}/pl").status_code == 200
        assert client.get(f"/api/v1/companies/{ticker}/bs").status_code == 200
        assert client.get(f"/api/v1/companies/{ticker}/cashflow").status_code == 200
        assert client.get(f"/api/v1/companies/{ticker}/ratios").status_code == 200

def test_market_cap_history():
    companies_res = client.get("/api/v1/companies")
    companies = companies_res.json().get("companies", [])
    if companies:
        ticker = companies[0]["id"]
        res = client.get(f"/api/v1/market-cap/{ticker}")
        assert res.status_code == 200
        assert "market_cap_history" in res.json()

def test_documents():
    companies_res = client.get("/api/v1/companies")
    companies = companies_res.json().get("companies", [])
    if companies:
        ticker = companies[0]["id"]
        res = client.get(f"/api/v1/companies/{ticker}/documents")
        assert res.status_code == 200
        assert "documents" in res.json()