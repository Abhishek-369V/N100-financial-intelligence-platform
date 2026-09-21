"""
Sprint 6, Day 37: Cluster Profiling & Statistics
"""

import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUTPUT_DIR = BASE_DIR / "output"
REPORTS_DIR = BASE_DIR / "reports"

KPI_10 = [
    "return_on_equity_pct",
    "operating_profit_margin_pct",
    "net_profit_margin_pct",
    "debt_to_equity",
    "interest_coverage",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "eps_cagr_5yr",
    "dividend_payout_ratio_pct",
    "asset_turnover",
]

# Assigned from actual per-cluster medians (computed once, see docstring gap #1):
#   Cluster 0 (57): ROE 17%, D/E 0.14, RevCAGR 10.5%, FCF CAGR 9%,  OPM 19%
#   Cluster 1 (16): ROE 16%, D/E 6.70, RevCAGR 17.8%, FCF CAGR -19%, OPM 40%
#   Cluster 2 (2):  ROE 4280% (HAL, BEL - near-zero equity base outliers)
#   Cluster 3 (15): ROE 15%, D/E 0.06, RevCAGR 13.2%, FCF CAGR 4.9%, OPM 84%
#   Cluster 4 (2):  ROE 11.6%, RevCAGR 6.6% (lowest), FCF CAGR 234% (GAIL, NHPC - low-base effect, not real hypergrowth)
CLUSTER_NAMES = {
    0: "Core Balanced Performers",
    1: "Leveraged Growth Compounders",
    2: "Extreme-ROE Outliers (Low-Equity-Base PSUs)",
    3: "High-Quality Low-Leverage Compounders",
    4: "Low-Growth Utility Value Plays",
}

NAME_REASONING = {
    0: "Largest cluster (57 companies). Median D/E 0.14 (low leverage), "
    "moderate 10.5% revenue growth, OPM 19% -- unremarkable-but-solid "
    "profile, the portfolio's 'average' company.",
    1: "Median D/E 6.70 (by far the highest of any cluster) paired with "
    "negative FCF CAGR (-19%) but strong OPM (40%) and the fastest "
    "revenue growth (17.8%) of the non-outlier clusters -- growth "
    "funded by debt, not by internal cash generation.",
    2: "2 companies (HAL, BEL), median ROE in the thousands of percent -- "
    "a near-zero equity base mechanically inflates ROE, not a genuine "
    "'quality' signal. Named as an outlier grouping, not an archetype.",
    3: "Lowest leverage of any cluster (D/E 0.06) combined with by far the "
    "highest OPM (84%) -- closest fit to the spec's 'High-Quality "
    "Compounders' example, renamed to be explicit about the low-leverage "
    "driver.",
    4: "2 companies (GAIL, NHPC), lowest revenue growth (6.6%) of any "
    "cluster but an extreme 234% FCF CAGR -- a low-base-year effect, not "
    "real hypergrowth. Classic PSU utility value-play profile.",
}


def load_cluster_and_kpi_data():
    """Load cluster and kpi data."""
    con = sqlite3.connect(DB_PATH)
    ratios = pd.read_sql("SELECT * FROM financial_ratios ORDER BY company_id, year", con)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", con)
    con.close()

    ratios_latest = ratios.groupby("company_id").last().reset_index()
    clusters = pd.read_csv(OUTPUT_DIR / "cluster_labels.csv")

    df = clusters.merge(ratios_latest, on="company_id", how="left")
    df = df.merge(sectors, on="company_id", how="left")
    return df


def update_cluster_names(df):
    """Rewrites output/cluster_labels.csv with real descriptive names,
    replacing Day 36's 'Cluster N' placeholders."""
    df = df.copy()
    df["cluster_name"] = df["cluster_id"].map(CLUSTER_NAMES)
    out_cols = ["company_id", "cluster_id", "cluster_name", "distance_from_centroid"]
    df[out_cols].to_csv(OUTPUT_DIR / "cluster_labels.csv", index=False)
    return df


def build_correlation_heatmap(df):
    """Build correlation heatmap for the given df."""
    corr = df[KPI_10].corr(method="pearson")
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        vmin=-1,
        vmax=1,
        square=True,
        ax=ax,
        cbar_kws={"label": "Pearson correlation"},
    )
    ax.set_title(
        "Correlation Matrix — 10 Core KPIs (Latest Year, 92 Companies)", fontsize=12, fontweight="bold"
    )
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.yticks(fontsize=8)
    fig.tight_layout()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(REPORTS_DIR / "correlation_heatmap.png")
    plt.close(fig)
    return corr


def build_outlier_report(df):
    """
    Z-score per metric, computed WITHIN each broad_sector (not portfolio-wide) -- a Z-score against the whole 92-company universe
    would flag "IT company with high OPM" as an outlier just because IT margins differ structurally from, say, Energy margins.
    Sector-relative is the meaningful comparison.
    """
    rows = []
    for sector, group in df.groupby("broad_sector"):
        for col in KPI_10:
            values = group[col]
            std = values.std(skipna=True)
            mean = values.mean(skipna=True)
            if pd.isna(std) or std == 0:
                continue  # can't Z-score a sector with <2 companies or zero variance
            z_scores = (values - mean) / std
            flagged = group[abs(z_scores) > 3]
            for _, row in flagged.iterrows():
                rows.append(
                    {
                        "company_id": row["company_id"],
                        "broad_sector": sector,
                        "metric": col,
                        "value": row[col],
                        "sector_mean": round(mean, 2),
                        "sector_std": round(std, 2),
                        "z_score": round(z_scores.loc[row.name], 2),
                    }
                )

    outlier_df = pd.DataFrame(
        rows,
        columns=["company_id", "broad_sector", "metric", "value", "sector_mean", "sector_std", "z_score"],
    )
    outlier_df.to_csv(OUTPUT_DIR / "outlier_report.csv", index=False)
    return outlier_df


def build_portfolio_stats(df):
    """Build portfolio stats for the given df."""
    rows = []
    for col in KPI_10:
        values = df[col].dropna()
        rows.append(
            {
                "kpi": col,
                "P10": round(values.quantile(0.10), 2),
                "P25": round(values.quantile(0.25), 2),
                "P50": round(values.quantile(0.50), 2),
                "P75": round(values.quantile(0.75), 2),
                "P90": round(values.quantile(0.90), 2),
                "Mean": round(values.mean(), 2),
                "Std": round(values.std(), 2),
                "n": len(values),
            }
        )
    stats_df = pd.DataFrame(rows)
    stats_df.to_csv(OUTPUT_DIR / "portfolio_stats.csv", index=False)
    return stats_df


if __name__ == "__main__":
    df = load_cluster_and_kpi_data()

    named_df = update_cluster_names(df)
    print("Cluster names assigned (self-reviewed, no team lead available):")
    for cid, name in CLUSTER_NAMES.items():
        count = (named_df["cluster_id"] == cid).sum()
        print(f"  {cid} ({count} companies): {name}")

    corr = build_correlation_heatmap(df)
    print(
        f"\nCorrelation heatmap saved. Strongest pair: "
        f"{corr.abs().where(~corr.abs().eq(1.0)).stack().idxmax()} "
        f"= {corr.abs().where(~corr.abs().eq(1.0)).stack().max():.2f}"
    )

    outlier_df = build_outlier_report(df)
    print(f"\nOutliers flagged (|Z|>3, sector-relative): {len(outlier_df)}")
    if len(outlier_df):
        print(outlier_df.to_string(index=False))

    stats_df = build_portfolio_stats(df)
    print(f"\nportfolio_stats.csv: {len(stats_df)} KPIs")
    print(stats_df.to_string(index=False))
