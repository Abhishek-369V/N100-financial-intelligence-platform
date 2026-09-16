"""
Sprint 5, Day 35: Portfolio Summary PDF
One page per company, alphabetical by ticker: 
company name, sector, top 6 KPIs, and a trend arrow per KPI vs the prior year.
"""

import sqlite3
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUT_PATH = BASE_DIR / "reports" / "portfolio" / "portfolio_summary.pdf"

NAVY = colors.HexColor("#0A2540")
GREEN = colors.HexColor("#1E7B34")
RED = colors.HexColor("#B3261E")
GREY = colors.HexColor("#6B7280")
LIGHT_GREY = colors.HexColor("#F2F4F7")
PAGE_W, PAGE_H = A4

FLAT_THRESHOLD_PCT = 2.0

# True = higher value is an improvement, False = lower value is an improvement.
METRIC_DIRECTION = {
    "return_on_equity_pct": True,
    "roce_proxy": True,
    "debt_to_equity": False,
    "revenue_cagr_5yr": True,
    "pat_cagr_5yr": True,
    "operating_profit_margin_pct": True,
}

METRIC_LABELS = {
    "return_on_equity_pct": "ROE %",
    "roce_proxy": "ROCE % (derived)",
    "debt_to_equity": "Debt/Equity",
    "revenue_cagr_5yr": "Revenue CAGR 5yr %",
    "pat_cagr_5yr": "PAT CAGR 5yr %",
    "operating_profit_margin_pct": "OPM %",
}

styles = {
    "value": ParagraphStyle("value", fontSize=13, textColor=NAVY, fontName="Helvetica-Bold"),
    "label": ParagraphStyle("label", fontSize=8, textColor=colors.grey),
    "arrow_up": ParagraphStyle("arrow_up", fontSize=13, textColor=GREEN, fontName="Helvetica-Bold"),
    "arrow_down": ParagraphStyle("arrow_down", fontSize=13, textColor=RED, fontName="Helvetica-Bold"),
    "arrow_flat": ParagraphStyle("arrow_flat", fontSize=13, textColor=GREY, fontName="Helvetica-Bold"),
}


def compute_roce_proxy(bs_row, pnl_row):
    """Same proxy as tearsheet.py -- see that module's docstring for why."""
    if bs_row is None or pnl_row is None:
        return None
    if pnl_row["operating_profit"] is None or pd.isna(pnl_row["operating_profit"]):
        return None
    capital_employed = (bs_row["equity_capital"] or 0) + (bs_row["reserves"] or 0) + (bs_row["borrowings"] or 0)
    if capital_employed <= 0:
        return None
    return round((pnl_row["operating_profit"] / capital_employed) * 100, 2)


def load_portfolio_data():
    con = sqlite3.connect(DB_PATH)
    companies = pd.read_sql("SELECT id AS company_id, company_name FROM companies ORDER BY id", con)
    sectors = pd.read_sql("SELECT company_id, broad_sector FROM sectors", con)
    ratios = pd.read_sql("SELECT * FROM financial_ratios ORDER BY company_id, year", con)
    pnl = pd.read_sql("SELECT * FROM profitandloss ORDER BY company_id, year", con)
    bs = pd.read_sql("SELECT * FROM balancesheet ORDER BY company_id, year", con)
    con.close()
    return companies, sectors, ratios, pnl, bs


def get_trend(latest_val, prior_val, higher_is_better):
    """Returns (direction, style_key) where direction in {'up','down','flat','na'}."""
    if latest_val is None or prior_val is None or pd.isna(latest_val) or pd.isna(prior_val):
        return "→", "arrow_flat"
    if prior_val == 0:
        return "→", "arrow_flat"

    pct_change = abs(latest_val - prior_val) / abs(prior_val) * 100
    if pct_change < FLAT_THRESHOLD_PCT:
        return "→", "arrow_flat"

    increased = latest_val > prior_val
    improved = increased if higher_is_better else not increased
    return ("↑", "arrow_up") if improved else ("↓", "arrow_down")


def build_company_page(company_id, company_name, sector, ratios_c, pnl_c, bs_c):
    latest_r = ratios_c.iloc[-1] if len(ratios_c) else None
    prior_r = ratios_c.iloc[-2] if len(ratios_c) >= 2 else None

    latest_roce = compute_roce_proxy(
        bs_c[bs_c["year"] == latest_r["year"]].iloc[0] if latest_r is not None and len(bs_c[bs_c["year"] == latest_r["year"]]) else None,
        pnl_c[pnl_c["year"] == latest_r["year"]].iloc[0] if latest_r is not None and len(pnl_c[pnl_c["year"] == latest_r["year"]]) else None,
    ) if latest_r is not None else None
    prior_roce = compute_roce_proxy(
        bs_c[bs_c["year"] == prior_r["year"]].iloc[0] if prior_r is not None and len(bs_c[bs_c["year"] == prior_r["year"]]) else None,
        pnl_c[pnl_c["year"] == prior_r["year"]].iloc[0] if prior_r is not None and len(pnl_c[pnl_c["year"] == prior_r["year"]]) else None,
    ) if prior_r is not None else None

    metric_values = {
        "return_on_equity_pct": (latest_r["return_on_equity_pct"] if latest_r is not None else None,
                                   prior_r["return_on_equity_pct"] if prior_r is not None else None),
        "roce_proxy": (latest_roce, prior_roce),
        "debt_to_equity": (latest_r["debt_to_equity"] if latest_r is not None else None,
                            prior_r["debt_to_equity"] if prior_r is not None else None),
        "revenue_cagr_5yr": (latest_r["revenue_cagr_5yr"] if latest_r is not None else None,
                              prior_r["revenue_cagr_5yr"] if prior_r is not None else None),
        "pat_cagr_5yr": (latest_r["pat_cagr_5yr"] if latest_r is not None else None,
                          prior_r["pat_cagr_5yr"] if prior_r is not None else None),
        "operating_profit_margin_pct": (latest_r["operating_profit_margin_pct"] if latest_r is not None else None,
                                          prior_r["operating_profit_margin_pct"] if prior_r is not None else None),
    }

    cells = []
    for metric_key, (latest_val, prior_val) in metric_values.items():
        label = METRIC_LABELS[metric_key]
        value_text = f"{latest_val:.1f}" if pd.notna(latest_val) else "N/A"
        arrow, style_key = get_trend(latest_val, prior_val, METRIC_DIRECTION[metric_key])
        cell = [
            Paragraph(label, styles["label"]),
            Paragraph(f"{value_text} {arrow}", styles[style_key] if pd.notna(latest_val) else styles["arrow_flat"]),
        ]
        cells.append(cell)

    rows = [cells[0:3], cells[3:6]]
    tile_width = (PAGE_W - 3 * cm) / 3
    table = Table(rows, colWidths=[tile_width] * 3, rowHeights=[2.3 * cm] * 2)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))

    year_note = ""
    if latest_r is not None and prior_r is not None:
        year_note = f"Trend: {prior_r['year']} → {latest_r['year']}"
    elif latest_r is not None:
        year_note = f"Only one year of data ({latest_r['year']}) — no trend available"
    else:
        year_note = "No financial_ratios data available for this company"

    return table, year_note


def navy_header(canvas_obj, doc, company_name, ticker, sector):
    canvas_obj.saveState()
    canvas_obj.setFillColor(NAVY)
    canvas_obj.rect(0, PAGE_H - 2.4 * cm, PAGE_W, 2.4 * cm, fill=1, stroke=0)
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica-Bold", 16)
    canvas_obj.drawString(1.5 * cm, PAGE_H - 1.3 * cm, f"{company_name} ({ticker})")
    canvas_obj.setFont("Helvetica", 10)
    canvas_obj.drawString(1.5 * cm, PAGE_H - 1.9 * cm, sector or "Sector unavailable")
    canvas_obj.restoreState()


def build_portfolio_summary():
    companies, sectors, ratios, pnl, bs = load_portfolio_data()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(OUT_PATH), pagesize=A4,
        topMargin=2.8 * cm, bottomMargin=1.5 * cm, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )

    story = []
    page_headers = []  # parallel list so onPage callback knows which header per page

    for i, (_, row) in enumerate(companies.iterrows()):
        company_id = row["company_id"]
        sector_match = sectors[sectors["company_id"] == company_id]
        sector = sector_match.iloc[0]["broad_sector"] if len(sector_match) else None

        ratios_c = ratios[ratios["company_id"] == company_id].reset_index(drop=True)
        pnl_c = pnl[pnl["company_id"] == company_id].reset_index(drop=True)
        bs_c = bs[bs["company_id"] == company_id].reset_index(drop=True)

        table, year_note = build_company_page(company_id, row["company_name"], sector, ratios_c, pnl_c, bs_c)
        story.append(Spacer(1, 0.3 * cm))
        story.append(table)
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(year_note, styles["label"]))

        page_headers.append((row["company_name"], company_id, sector))
        if i < len(companies) - 1:
            story.append(PageBreak())

    def on_page(canvas_obj, doc_obj):
        page_num = canvas_obj.getPageNumber() - 1  # 0-indexed
        if 0 <= page_num < len(page_headers):
            company_name, ticker, sector = page_headers[page_num]
            navy_header(canvas_obj, doc_obj, company_name, ticker, sector)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return OUT_PATH, len(companies)


if __name__ == "__main__":
    out_path, company_count = build_portfolio_summary()
    size_kb = out_path.stat().st_size / 1024
    print(f"portfolio_summary.pdf: {company_count} pages, {size_kb:.1f} KB")

    import sys
    sys.path.insert(0, str(BASE_DIR / "src" / "reports"))
    from pypdf import PdfReader
    actual_pages = len(PdfReader(str(out_path)).pages)
    print(f"Actual PDF page count: {actual_pages} (expected {company_count})")