"""
Sprint 6, Day 36: KMeans Clustering
5 features: 
    return_on_equity_pct, 
    debt_to_equity, 
    revenue_cagr_5yr (all from financial_ratios, latest year), 
    fcf_cagr_5yr (from Day 31's cashflow_intelligence.xlsx -- the only place this figure exists), 
    operating_profit_margin_pct (financial_ratios, latest year).
"""

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUTPUT_DIR = BASE_DIR / "output"
REPORTS_DIR = BASE_DIR / "reports"

FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]
N_CLUSTERS = 5
RANDOM_STATE = 42


def load_feature_data():
    con = sqlite3.connect(DB_PATH)
    ratios = pd.read_sql("SELECT * FROM financial_ratios ORDER BY company_id, year", con)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", con)
    companies = pd.read_sql("SELECT id AS company_id FROM companies", con)
    con.close()

    ratios_latest = ratios.groupby("company_id").last().reset_index()
    ci = pd.read_excel(OUTPUT_DIR / "cashflow_intelligence.xlsx")[["company_id", "fcf_cagr_5yr"]]

    df = companies.merge(sectors, on="company_id", how="left")
    df = df.merge(
        ratios_latest[["company_id", "return_on_equity_pct", "debt_to_equity",
                        "revenue_cagr_5yr", "operating_profit_margin_pct"]],
        on="company_id", how="left"
    )
    df = df.merge(ci, on="company_id", how="left")
    return df


def impute_with_sector_median(df):
    """
    Sector median first (per spec), add global median fallback - where a sector's own median is itself NaN 
    (e.g. Communication Services has 0 non-null fcf_cagr_5yr values -- see sprint5_retro gap #1).
    """
    df = df.copy()
    for col in FEATURES:
        sector_medians = df.groupby("broad_sector")[col].transform("median")
        global_median = df[col].median()
        df[col] = df[col].fillna(sector_medians).fillna(global_median)
    return df


def run_elbow_analysis(X_scaled):
    inertias = []
    k_range = range(2, 11)
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)

    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)
    ax.plot(list(k_range), inertias, marker="o", color="#0A2540")
    ax.axvline(5, color="#B3261E", linestyle="--", label="k=5 (chosen)")
    ax.set_xlabel("Number of clusters (k)")
    ax.set_ylabel("Inertia")
    ax.set_title("Elbow Plot — KMeans Inertia vs k")
    ax.legend()
    fig.tight_layout()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(REPORTS_DIR / "elbow_plot.png")
    plt.close(fig)
    return dict(zip(k_range, inertias))


def run_clustering():
    df = load_feature_data()
    df_imputed = impute_with_sector_median(df)

    X = df_imputed[FEATURES].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    inertias = run_elbow_analysis(X_scaled)

    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
    cluster_ids = kmeans.fit_predict(X_scaled)

    distances = kmeans.transform(X_scaled)
    distance_from_centroid = [distances[i, cluster_ids[i]] for i in range(len(cluster_ids))]

    result_df = pd.DataFrame({
        "company_id": df_imputed["company_id"],
        "cluster_id": cluster_ids,
        "cluster_name": [f"Cluster {c}" for c in cluster_ids],  # placeholder, see docstring gap #3
        "distance_from_centroid": [round(d, 4) for d in distance_from_centroid],
    })
    result_df.to_csv(OUTPUT_DIR / "cluster_labels.csv", index=False)

    return result_df, inertias, df_imputed


if __name__ == "__main__":
    result_df, inertias, df_imputed = run_clustering()

    print("Elbow inertia by k:")
    for k, inertia in inertias.items():
        print(f"  k={k}: {inertia:.1f}")

    print(f"\nCompanies clustered: {len(result_df)} / 92")
    print(f"All 5 clusters populated: {result_df['cluster_id'].nunique()} / 5")
    print(result_df["cluster_id"].value_counts().sort_index())

    imputed_counts = {
        col: df_imputed[col].isna().sum() for col in FEATURES
    }
    print(f"\nRemaining NaNs after imputation (should all be 0): {imputed_counts}")