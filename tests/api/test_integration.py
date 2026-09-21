"""
Sprint 6, Day 42 : Integration test - dashboard screener vs API screener
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src" / "screener"))
sys.path.insert(0, str(BASE_DIR / "src" / "analytics"))

from engine import run_screener  #type:ignore


def test_dashboard_and_api_use_identical_underlying_function(client):
    """
    The dashboard's screener page and the API's screener router both call engine.run_screener()
    (dashboard indirectly via load_universe + apply_filter + compute_composite_score,
    which is what run_screener() itself does internally)
    -- so calling run_screener() directly here reproduces exactly what the dashboard page does when its
    sliders are set to roe_min=15, de_max=1.0.
    """
    dashboard_equivalent_filters = {"roe_min": 15.0, "de_max": 1.0}
    dashboard_result_df = run_screener(dashboard_equivalent_filters)

    api_response = client.get("/api/v1/screener?min_roe=15&max_de=1.0")
    api_companies = api_response.json()["companies"]

    dashboard_ids = set(dashboard_result_df["company_id"])
    api_ids = {c["company_id"] for c in api_companies}

    assert dashboard_ids == api_ids, (
        f"Dashboard and API screener disagree on results. "
        f"Dashboard-only: {dashboard_ids - api_ids}, API-only: {api_ids - dashboard_ids}"
    )


def test_dashboard_and_api_agree_on_composite_scores(client):
    """Beyond just which companies match, the actual scores must match too
    -- catches a case where the same companies pass but with different scores."""
    dashboard_result_df = run_screener({"roe_min": 10.0})
    api_response = client.get("/api/v1/screener?min_roe=10")
    api_companies = {c["company_id"]: c["composite_quality_score"] for c in api_response.json()["companies"]}

    for _, row in dashboard_result_df.iterrows():
        company_id = row["company_id"]
        dashboard_score = row["composite_quality_score"]
        api_score = api_companies.get(company_id)
        if dashboard_score is not None and api_score is not None:
            assert (
                abs(dashboard_score - api_score) < 0.01
            ), f"{company_id}: dashboard={dashboard_score} api={api_score}"
