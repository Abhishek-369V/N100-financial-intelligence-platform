"""
Sprint 5, Day 34: Batch Sector Report Generation
One PDF per sector: a summary page with median KPIs, then every company in that sector with 8 metrics each.
"""

import sqlite3
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
SECTOR_DIR = BASE_DIR / "reports" / "sector"

NAVY = colors.HexColor("#0A2540")
LIGHT_GREY = colors.HexColor("#F2F4F7")
PAGE_W, PAGE_H = landscape(A4)

METRIC_COLUMNS = [
    ("ROE %", "return_on_equity_pct"),
    ("ROCE %", "roce_percentage"),
    ("D/E", "debt_to_equity"),
    ("Revenue CAGR 5yr %", "revenue_cagr_5yr"),
    ("PAT CAGR 5yr %", "pat_cagr_5yr"),
    ("OPM %", "operating_profit_margin_pct"),
    ("P/E", "pe_ratio"),
    ("Div Yield %", "dividend_yield_pct"),
]

styles = {
    "title": ParagraphStyle("title", fontSize=16, textColor=colors.white, fontName="Helvetica-Bold"),
    "subtitle": ParagraphStyle("subtitle", fontSize=10, textColor=colors.white),
    "section_header": ParagraphStyle(
        "section_header", fontSize=11, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=6
    ),
    "cell": ParagraphStyle("cell", fontSize=7.5, leading=9),
}


def load_sector_universe():
    """One row per company with the latest-year value for every metric this report needs -- built once, sliced per sector below."""
    con = sqlite3.connect(DB_PATH)
    ratios = pd.read_sql("SELECT * FROM financial_ratios ORDER BY company_id, year", con)
    market_cap = pd.read_sql("SELECT * FROM market_cap ORDER BY company_id, year", con)
    companies = pd.read_sql("SELECT id AS company_id, company_name, roce_percentage FROM companies", con)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", con)
    con.close()

    ratios_latest = ratios.groupby("company_id").last().reset_index()
    mc_latest = market_cap.groupby("company_id").last().reset_index()

    df = companies.merge(sectors, on="company_id", how="left")
    df = df.merge(ratios_latest, on="company_id", how="left", suffixes=("", "_ratios"))
    df = df.merge(mc_latest[["company_id", "pe_ratio", "dividend_yield_pct"]], on="company_id", how="left")
    return df


def build_sector_summary_table(sector_df, sector_name):
    """Median of each of the 8 metrics across every company in this sector."""
    rows = [["Metric", "Median"]]
    for label, col in METRIC_COLUMNS:
        median_val = sector_df[col].median(skipna=True)
        rows.append([label, f"{median_val:.2f}" if pd.notna(median_val) else "N/A"])

    table = Table(rows, colWidths=[8 * cm, 4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build_company_metrics_table(sector_df):
    """Every company in the sector with all 8 metrics -- Paragraph cells for wordwrap safety on the company-name column
    (some names run long, e.g.'Bajaj Holdings & Investment Ltd')."""
    header = ["Company"] + [label for label, _ in METRIC_COLUMNS]
    rows = [header]
    for _, row in sector_df.sort_values("company_name").iterrows():
        cells = [Paragraph(f"{row['company_name']} ({row['company_id']})", styles["cell"])]
        for _, col in METRIC_COLUMNS:
            val = row[col]
            cells.append(f"{val:.2f}" if pd.notna(val) else "N/A")
        rows.append(cells)

    col_widths = [6 * cm] + [2.6 * cm] * len(METRIC_COLUMNS)
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def navy_header(canvas_obj, doc, sector_name, company_count):
    """Navy header for the given canvas_obj, doc, sector_name, company_count."""
    canvas_obj.saveState()
    canvas_obj.setFillColor(NAVY)
    canvas_obj.rect(0, PAGE_H - 2.0 * cm, PAGE_W, 2.0 * cm, fill=1, stroke=0)
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica-Bold", 16)
    canvas_obj.drawString(1.5 * cm, PAGE_H - 1.2 * cm, f"{sector_name} — Sector Report")
    canvas_obj.setFont("Helvetica", 10)
    canvas_obj.drawString(1.5 * cm, PAGE_H - 1.7 * cm, f"{company_count} companies")
    canvas_obj.restoreState()


def build_sector_report(sector_name, sector_df):
    """Build sector report for the given sector_name, sector_df."""
    SECTOR_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = sector_name.replace(" ", "_").replace("/", "-")
    out_path = SECTOR_DIR / f"{safe_name}_report.pdf"

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=landscape(A4),
        topMargin=2.4 * cm,
        bottomMargin=1.2 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
    )

    story = [
        Paragraph("Sector Median KPIs", styles["section_header"]),
        build_sector_summary_table(sector_df, sector_name),
        Spacer(1, 0.5 * cm),
        Paragraph("Companies in this Sector", styles["section_header"]),
        build_company_metrics_table(sector_df),
    ]

    def on_page(canvas_obj, doc_obj):
        """On page for the given canvas_obj, doc_obj."""
        navy_header(canvas_obj, doc_obj, sector_name, len(sector_df))

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return out_path


def run_batch_sector_reports():
    """Run batch sector reports."""
    universe = load_sector_universe()
    sector_names = sorted(universe["broad_sector"].dropna().unique())

    generated = []
    for sector_name in sector_names:
        sector_df = universe[universe["broad_sector"] == sector_name]
        path = build_sector_report(sector_name, sector_df)
        generated.append((sector_name, len(sector_df), path))

    return generated


if __name__ == "__main__":
    generated = run_batch_sector_reports()
    total_companies = sum(count for _, count, _ in generated)
    print(
        f"Sector PDFs generated: {len(generated)} (spec assumed 11; actual data has {len(generated)} distinct broad_sector values)"
    )
    for sector_name, count, path in generated:
        size_kb = path.stat().st_size / 1024
        print(f"  {sector_name}: {count} companies, {size_kb:.1f} KB")
    print(f"Total companies across all sector PDFs: {total_companies} / 92")
