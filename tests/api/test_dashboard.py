"""Step 3 integration coverage for the Streamlit -> FastAPI boundary."""


def test_home_dashboard_returns_read_model(client):
    response = client.get("/api/v1/dashboard/home?year=2024")
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2024
    assert data["company_count"] == 92
    assert len(data["sector_breakdown"]) == 10
    assert len(data["top5"]) == 5
    assert "average_roe" in data["kpis"]
    assert "median_pe" in data["kpis"]


def test_capital_allocation_dashboard_returns_classifications(client):
    response = client.get("/api/v1/dashboard/capital-allocation")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 90
    assert all("company_id" in row for row in data["companies"])
    assert all("pattern_label" in row for row in data["companies"])


def test_peer_metadata_and_group_include_company_names(client):
    metadata = client.get("/api/v1/peers")
    assert metadata.status_code == 200
    assert metadata.json()["count"] == 11

    group = client.get("/api/v1/peers/IT Services")
    assert group.status_code == 200
    companies = group.json()["companies"]
    assert len(companies) == 5
    assert all("company_name" in row for row in companies)
    assert all("latest_kpis" in row for row in companies)


def test_screener_supports_all_dashboard_slider_parameters(client):
    response = client.get(
        "/api/v1/screener"
        "?min_roe=10&max_de=2&min_fcf=0&min_rev_cagr_5yr=5"
        "&min_pat_cagr_5yr=5&min_opm=5&max_pe=60&max_pb=12"
        "&min_dividend_yield=0.5&min_icr=1"
    )
    assert response.status_code == 200
    filters = response.json()["filters_applied"]
    assert len(filters) == 10
    assert all(value is not None for value in filters.values())


def test_sector_companies_endpoint_contains_chart_fields(client):
    response = client.get("/api/v1/sectors/Information Technology/companies")
    assert response.status_code == 200
    companies = response.json()["companies"]
    assert companies
    required = {"company_name", "sales", "market_cap_crore", "return_on_equity_pct", "sub_sector"}
    assert required.issubset(companies[0])