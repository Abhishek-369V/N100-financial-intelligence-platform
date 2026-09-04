"""
Day 19: Radar charts (8 axes) for peer-grouped companies, standalone bar charts for ungrouped companies. 
        Exports PNG to reports/radar_charts/. 
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sqlalchemy import create_engine
import sys

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src" / "analytics"))
sys.path.insert(0, str(BASE_DIR / "src" / "screener"))

from composite_score import winsorize, scale_0_100, compute_composite_score #type:ignore
from presets import load_universe #type:ignore

DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUTPUT_DIR = BASE_DIR / "reports" / "radar_charts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

db_engine = create_engine(f"sqlite:///{DB_PATH}")

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
})

RADAR_AXES = ["ROE", "ROCE", "NPM", "D/E", "FCF Score", "PAT CAGR 5yr", "Revenue CAGR 5yr", "Composite Score"]

RAW_METRIC_MAP = {
    "ROE": "return_on_equity_pct",
    "ROCE": "roce_percentage",
    "NPM": "net_profit_margin_pct",
    "D/E": "debt_to_equity",
    "PAT CAGR 5yr": "pat_cagr_5yr",
    "Revenue CAGR 5yr": "revenue_cagr_5yr",
}


def load_all_data():
    """Loads everything needed: universe (financial_ratios + sectors), peer_groups, composite scores."""
    universe = load_universe()
    peer_groups = pd.read_sql("SELECT peer_group_name, company_id FROM peer_groups", db_engine)
    scored = compute_composite_score(universe, sector_relative=False)
    return scored, peer_groups


def scale_metrics_0_100(df, columns):
    """
    Scales each metric column to 0-100 using the same winsorize+scale pipeline built in Day 17 
    -- reused here rather than reinvented, so the same outlier-safety (BEL/INDIGO-style capping) applies to radar charts too.
    """
    scaled_df = df.copy()
    for col in columns:
        if col not in scaled_df.columns:
            scaled_df[col] = np.nan
            continue
        invert = (col == "debt_to_equity")  # lower D/E = better = higher score
        scaled_df[col + "_scaled"] = scale_0_100(winsorize(scaled_df[col]), invert=invert)
    return scaled_df


def get_radar_values(company_row):
    """Extracts the 8 scaled values for one company, in RADAR_AXES order."""
    values = []
    for axis in RADAR_AXES:
        if axis == "FCF Score":
            values.append(company_row.get("free_cash_flow_cr_scaled", 0) or 0)
        elif axis == "Composite Score":
            values.append(company_row.get("composite_quality_score", 0) or 0)
        else:
            raw_col = RAW_METRIC_MAP[axis]
            values.append(company_row.get(raw_col + "_scaled", 0) or 0)
    return values


def draw_radar_chart(company_id, company_name, company_values, peer_avg_values, save_path):
    """
    Draws one 8-axis radar chart: 
    company as a filled polygon, peer group average as a dashed outline overlay -- per spec exactly.
    """
    n_axes = len(RADAR_AXES)
    angles = np.linspace(0, 2 * np.pi, n_axes, endpoint=False).tolist()
    angles += angles[:1]  # close the polygon loop

    company_plot_values = company_values + company_values[:1]
    peer_plot_values = peer_avg_values + peer_avg_values[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

    ax.plot(angles, company_plot_values, color="#1B998B", linewidth=2, label=company_id)
    ax.fill(angles, company_plot_values, color="#1B998B", alpha=0.25)

    ax.plot(angles, peer_plot_values, color="#5B6472", linewidth=1.5, linestyle="--", label="Peer Group Avg")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(RADAR_AXES, fontsize=10)
    ax.set_ylim(0, 100)
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(["20", "40", "60", "80", "100"], fontsize=8, color="gray")

    ax.set_title(f"{company_id} — {company_name}\nvs. Peer Group Average", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def draw_standalone_chart(company_id, company_name, composite_score, universe_avg, save_path):
    """
    For companies with NO peer group assignment (spec requirement):
    a single-metric standalone bar chart comparing the company's Composite Score against the full Nifty 100 universe average.
    """
    fig, ax = plt.subplots(figsize=(5, 4))

    bars = ax.bar(
        [company_id, "Nifty 100 Avg"],
        [composite_score, universe_avg],
        color=["#1B998B", "#5B6472"],
    )
    ax.set_ylim(0, 100)
    ax.set_ylabel("Composite Quality Score (0-100)")
    ax.set_title(f"{company_id} — {company_name}\n(No peer group assigned — compared to Nifty 100 average)", fontsize=11)

    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 1, f"{height:.1f}", ha="center", fontsize=10)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def generate_all_radar_charts():
    scored, peer_groups = load_all_data()

    raw_cols = list(RAW_METRIC_MAP.values()) + ["free_cash_flow_cr"]
    scored = scale_metrics_0_100(scored, raw_cols)

    grouped_ids = set(peer_groups["company_id"].unique())
    all_ids = set(scored["company_id"].unique())
    ungrouped_ids = all_ids - grouped_ids

    universe_avg_score = scored["composite_quality_score"].mean()

    company_names = pd.read_sql("SELECT id as company_id, company_name FROM companies", db_engine)
    scored = scored.merge(company_names, on="company_id", how="left")

    radar_count = 0
    standalone_count = 0
    errors = []

    print("=" * 60)
    print(f"GENERATING RADAR/STANDALONE CHARTS — {len(scored)} companies")
    print(f"  {len(grouped_ids & all_ids)} with peer groups (radar charts)")
    print(f"  {len(ungrouped_ids)} without peer groups (standalone charts)")
    print("=" * 60)

    for _, company_row in scored.iterrows():
        company_id = company_row["company_id"]
        company_name = company_row.get("company_name", company_id)
        safe_name = str(company_name).strip().replace("\n", "")

        try:
            if company_id in grouped_ids:
                # Find this company's peer group
                group_name = peer_groups[peer_groups["company_id"] == company_id]["peer_group_name"].iloc[0]
                peer_ids = peer_groups[peer_groups["peer_group_name"] == group_name]["company_id"].tolist()
                peer_rows = scored[scored["company_id"].isin(peer_ids)]

                company_values = get_radar_values(company_row)
                peer_avg_values = [
                    peer_rows[col].mean() if col in peer_rows.columns else 0
                    for col in [
                        RAW_METRIC_MAP[a] + "_scaled" if a in RAW_METRIC_MAP else
                        ("free_cash_flow_cr_scaled" if a == "FCF Score" else "composite_quality_score")
                        for a in RADAR_AXES
                    ]
                ]
                peer_avg_values = [v if not pd.isna(v) else 0 for v in peer_avg_values]

                save_path = OUTPUT_DIR / f"{company_id}_radar.png"
                draw_radar_chart(company_id, safe_name, company_values, peer_avg_values, save_path)
                radar_count += 1

            else:
                composite = company_row.get("composite_quality_score", 0) or 0
                save_path = OUTPUT_DIR / f"{company_id}_radar.png"
                draw_standalone_chart(company_id, safe_name, composite, universe_avg_score, save_path)
                standalone_count += 1

        except Exception as e:
            errors.append((company_id, str(e)))

    print(f"\n[DONE] Radar charts generated: {radar_count}")
    print(f"[DONE] Standalone charts generated: {standalone_count}")
    print(f"Total PNGs expected: {radar_count + standalone_count} (should equal {len(scored)})")

    if errors:
        print(f"\n[ERROR] {len(errors)} companies failed to generate a chart:")
        for cid, err in errors:
            print(f"   {cid}: {err}")

    # Verification: confirm files actually exist on disk
    actual_files = list(OUTPUT_DIR.glob("*_radar.png"))
    print(f"\nActual PNG files found in {OUTPUT_DIR}: {len(actual_files)}")
    if len(actual_files) != (radar_count + standalone_count):
        print("[WARNING] MISMATCH between reported count and actual files on disk — investigate.")
    else:
        print("[DONE] File count matches reported generation count.")

    return radar_count, standalone_count, errors


if __name__ == "__main__":
    generate_all_radar_charts()