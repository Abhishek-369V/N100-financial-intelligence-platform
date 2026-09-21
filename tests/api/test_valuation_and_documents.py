"""
Sprint 6, Day 42(backfill): market-cap and documents endpoint tests.

These 2 endpoints were only covered by tests/api/test_api.py's
"test_market_cap_history" and "test_documents"
-- a file prev written for smoke-test the API as it was being built.
That file is being deleted as redundant with remaining tests/api (7 of its 9 tests duplicate those, with weaker assertions),
but now these 2 tests covered ground nothing else did, so backfilling proper versions here first rather than just losing the coverage.
"""


def test_market_cap_history_tcs(client):
    response = client.get("/api/v1/market-cap/TCS")
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == "TCS"
    assert data["count"] == 6  # confirmed 2019-03 through 2024-03, Sprint 6 Day 40
    years = {row["year"] for row in data["market_cap_history"]}
    assert years == {"2019-03", "2020-03", "2021-03", "2022-03", "2023-03", "2024-03"}
    assert all("pe_ratio" in row for row in data["market_cap_history"])


def test_market_cap_history_invalid_ticker_404(client):
    response = client.get("/api/v1/market-cap/INVALID")
    assert response.status_code == 404


def test_documents_tcs(client):
    """
    GAP found while writing this test: TCS's own documents table has 2 rows
    (2009-03, 2010-03) where Annual_Report is the literal string "Null"
    (not real NULL, not an http URL) -- a genuine upstream data quality
    issue, the exact shape DQ-10 (url_format) already exists to catch.
    16 total rows, 14 valid, 2 invalid -- asserting the real split, not a
    blanket "all valid" that isn't true.
    """
    response = client.get("/api/v1/companies/TCS/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["company_id"] == "TCS"
    assert data["count"] == 16
    assert all("is_url_valid" in doc for doc in data["documents"])
    valid_count = sum(1 for doc in data["documents"] if doc["is_url_valid"])
    assert valid_count == 14
    invalid_years = {doc["year"] for doc in data["documents"] if not doc["is_url_valid"]}
    assert invalid_years == {"2009-03", "2010-03"}


def test_documents_invalid_ticker_404(client):
    response = client.get("/api/v1/companies/INVALID/documents")
    assert response.status_code == 404
