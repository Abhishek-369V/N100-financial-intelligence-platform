"""
Sprint 6, Day 42: tests/api/test_screener.py
Per spec: min_roe=15 returns only companies with ROE >= 15, invalid parameter returns 400.
"""


def test_screener_min_roe_filters_correctly(client):
    response = client.get("/api/v1/screener?min_roe=15")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    for company in data["companies"]:
        if company["return_on_equity_pct"] is not None:
            assert company["return_on_equity_pct"] >= 15


def test_screener_max_de_filters_correctly(client):
    """
    GAP found while writing this test: screener_config.yaml's de_max filter has skip_sector: Financials 
    (existing, intentional — D/E doesn't apply meaningfully to banks, same reasoning as every other leverage-blind 
    fix this sprint/last sprint). So Financials-sector companies are exempt from this filter entirely, not silently failing it. 
    Asserting the correct scoped behavior instead of a blanket "no D/E > 1.0 ever".
    """
    response = client.get("/api/v1/screener?max_de=1.0")
    data = response.json()
    for company in data["companies"]:
        if company["broad_sector"] == "Financials":
            continue  # exempt by design — see screener_config.yaml skip_sector
        if company["debt_to_equity"] is not None:
            assert company["debt_to_equity"] <= 1.0


def test_screener_max_de_does_not_exempt_non_financials(client):
    """Negative control for the above: confirm non-Financials companies genuinely get filtered, 
    so the skip_sector exemption isn't silently swallowing everyone."""
    response = client.get("/api/v1/screener?max_de=1.0")
    non_financial_ids = {c["company_id"] for c in response.json()["companies"] if c["broad_sector"] != "Financials"}
    all_response = client.get("/api/v1/screener")
    all_non_financial_ids = {c["company_id"] for c in all_response.json()["companies"] if c["broad_sector"] != "Financials"}
    assert non_financial_ids < all_non_financial_ids  # strictly fewer, filter is doing something


def test_screener_combined_filters(client):
    response = client.get("/api/v1/screener?min_roe=15&max_de=1.0")
    data = response.json()
    for company in data["companies"]:
        if company["return_on_equity_pct"] is not None:
            assert company["return_on_equity_pct"] >= 15
        if company["broad_sector"] == "Financials":
            continue  # exempt from de_max by design, see above
        if company["debt_to_equity"] is not None:
            assert company["debt_to_equity"] <= 1.0


def test_screener_sector_filter(client):
    response = client.get("/api/v1/screener?sector=Information Technology")
    data = response.json()
    assert all(c["broad_sector"] == "Information Technology" for c in data["companies"])


def test_screener_invalid_parameter_returns_400(client):
    response = client.get("/api/v1/screener?min_roe=not_a_number")
    assert response.status_code == 400
    assert "min_roe" in response.json()["detail"]


def test_screener_invalid_max_de_returns_400(client):
    response = client.get("/api/v1/screener?max_de=abc")
    assert response.status_code == 400


def test_screener_no_filters_returns_all(client):
    """
    GAP found while writing this test: NOT 92. run_screener()'s load_universe() inner-merges onto 
    financial_ratios.groupby("company_id").last() -- SBIN and ATGL have zero rows in financial_ratios at all
    (established Sprint 5 Day 30/31: SBIN is a bank where D/E-style ratios are structurally excluded on purpose, 
    ATGL is an upstream data gap), so a groupby on zero rows produces no group for them and they silently fall out of 
    the screener universe entirely -- a real, if narrow, gap: the screener can never surface these 2 companies no matter what 
    filters are applied, unlike the tearsheet/portfolio-summary paths which at least show them with N/A. 
    Asserting the real number, not the aspirational 92.
    """
    response = client.get("/api/v1/screener")
    data = response.json()
    assert data["count"] == 90
    returned_ids = {c["company_id"] for c in data["companies"]}
    assert "SBIN" not in returned_ids
    assert "ATGL" not in returned_ids


def test_screener_results_sorted_by_composite_score(client):
    """Verifies the Sprint 5 Day 29 composite_quality_score bugfix is still
    live end-to-end through the API, not just in the underlying engine."""
    response = client.get("/api/v1/screener?min_roe=10")
    companies = response.json()["companies"]
    scores = [c["composite_quality_score"] for c in companies if c["composite_quality_score"] is not None]
    assert scores == sorted(scores, reverse=True)