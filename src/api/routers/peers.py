"""Peer-group data endpoints used by the dashboard and API clients."""

from fastapi import APIRouter, Depends, HTTPException

from src.api.database import get_db_connection

router = APIRouter()

# 8 axis metrics for the radar comparison -- a subset of peer_percentiles'
# 10 metrics, chosen for a readable radar chart (10 axes gets cluttered).
RADAR_METRICS = [
    "return_on_equity_pct",
    "roce_percentage",
    "net_profit_margin_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "pat_cagr_5yr",
    "revenue_cagr_5yr",
    "interest_coverage",
]


def _latest_ratio_subquery() -> str:
    return """
        SELECT fr.*
        FROM financial_ratios fr
        JOIN (
            SELECT company_id, MAX(year) AS latest_year
            FROM financial_ratios
            GROUP BY company_id
        ) latest
          ON latest.company_id = fr.company_id
         AND latest.latest_year = fr.year
    """


@router.get("/peers")
def list_peer_groups(conn=Depends(get_db_connection)):
    """Return the distinct peer-group names for the dashboard selector."""
    rows = conn.execute(
        "SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY peer_group_name"
    ).fetchall()
    return {
        "count": len(rows),
        "peer_groups": [row["peer_group_name"] for row in rows],
    }


@router.get("/peers/{group_name}")
def get_peer_group(group_name: str, conn=Depends(get_db_connection)):
    """Return members, names, latest KPIs and percentile metrics for a peer group."""
    known_groups = {
        r["peer_group_name"]
        for r in conn.execute("SELECT DISTINCT peer_group_name FROM peer_groups").fetchall()
    }
    if group_name not in known_groups:
        raise HTTPException(status_code=404, detail=f"Peer group '{group_name}' not found")

    members = conn.execute(
        "SELECT company_id, is_benchmark FROM peer_groups WHERE peer_group_name = ?", (group_name,)
    ).fetchall()

    percentiles = conn.execute(
        """
        SELECT company_id, metric, value, percentile_rank
        FROM peer_percentiles
        WHERE peer_group_name = ?
        """,
        (group_name,),
    ).fetchall()

    by_company = {}
    for row in percentiles:
        entry = by_company.setdefault(row["company_id"], {})
        entry[row["metric"]] = {
            "value": row["value"],
            "percentile_rank": row["percentile_rank"],
        }

    ratios_sql = _latest_ratio_subquery()
    latest_rows = conn.execute(
        f"""
        SELECT c.id AS company_id, c.company_name, c.roce_percentage, fr.*
        FROM companies c
        LEFT JOIN ({ratios_sql}) fr ON fr.company_id = c.id
        WHERE c.id IN (
            SELECT company_id FROM peer_groups WHERE peer_group_name = ?
        )
        """,
        (group_name,),
    ).fetchall()
    latest_by_company = {row["company_id"]: dict(row) for row in latest_rows}

    companies = []
    for member in members:
        company_id = member["company_id"]
        latest = latest_by_company.get(company_id, {})
        latest_kpis = {
            key: latest.get(key)
            for key in [
                "composite_quality_score",
                "return_on_equity_pct",
                "roce_percentage",
                "net_profit_margin_pct",
                "debt_to_equity",
                "free_cash_flow_cr",
                "pat_cagr_5yr",
                "revenue_cagr_5yr",
                "interest_coverage",
            ]
        }
        companies.append(
            {
                "company_id": company_id,
                "company_name": latest.get("company_name"),
                "is_benchmark": bool(member["is_benchmark"]),
                "latest_kpis": latest_kpis,
                "metrics": by_company.get(company_id, {}),
            }
        )

    return {"peer_group_name": group_name, "count": len(companies), "companies": companies}


@router.get("/companies/{ticker}/peers/compare")
def compare_to_peers(ticker: str, conn=Depends(get_db_connection)):
    """Compare a company to its peer group using the stored percentile dataset."""
    company_exists = conn.execute("SELECT 1 FROM companies WHERE id = ?", (ticker,)).fetchone()
    if company_exists is None:
        raise HTTPException(status_code=404, detail=f"Company '{ticker}' not found")

    group_row = conn.execute(
        "SELECT peer_group_name, is_benchmark FROM peer_groups WHERE company_id = ?", (ticker,)
    ).fetchone()
    if group_row is None:
        raise HTTPException(status_code=404, detail=f"'{ticker}' is not assigned to any peer group")

    group_name = group_row["peer_group_name"]

    benchmark_row = conn.execute(
        "SELECT company_id FROM peer_groups WHERE peer_group_name = ? AND is_benchmark = 1", (group_name,)
    ).fetchone()
    benchmark_ticker = benchmark_row["company_id"] if benchmark_row else None

    def get_metrics_for(company_id):
        """Get metrics for for the given company_id."""
        rows = conn.execute(
            "SELECT metric, value FROM peer_percentiles WHERE peer_group_name = ? AND company_id = ?",
            (group_name, company_id),
        ).fetchall()
        return {r["metric"]: r["value"] for r in rows if r["metric"] in RADAR_METRICS}

    company_values = get_metrics_for(ticker)

    peer_rows = conn.execute(
        "SELECT metric, AVG(value) AS avg_value FROM peer_percentiles WHERE peer_group_name = ? GROUP BY metric",
        (group_name,),
    ).fetchall()
    peer_avg = {r["metric"]: r["avg_value"] for r in peer_rows if r["metric"] in RADAR_METRICS}

    benchmark_values = get_metrics_for(benchmark_ticker) if benchmark_ticker else {}

    return {
        "company_id": ticker,
        "peer_group_name": group_name,
        "benchmark_company_id": benchmark_ticker,
        "axes": RADAR_METRICS,
        "company_values": company_values,
        "peer_group_average": peer_avg,
        "benchmark_values": benchmark_values,
    }