"""
Sprint 5, Day 33: PDF Tearsheet Template (ReportLab)
"""

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "db" / "nifty100.db"
OUTPUT_DIR = BASE_DIR / "output"
TEARSHEET_DIR = BASE_DIR / "reports" / "tearsheets"
TMP_CHART_DIR = BASE_DIR / "reports" / "_tmp_charts"

NAVY = colors.HexColor("#0A2540")
GREEN = colors.HexColor("#1E7B34")
RED = colors.HexColor("#B3261E")
LIGHT_GREY = colors.HexColor("#F2F4F7")

PAGE_W, PAGE_H = A4

styles = {
    "tile_label": ParagraphStyle("tile_label", fontSize=8, textColor=colors.grey, leading=10),
    "tile_value": ParagraphStyle("tile_value", fontSize=14, textColor=NAVY, leading=16, fontName="Helvetica-Bold"),
    "pro": ParagraphStyle("pro", fontSize=8.5, textColor=colors.HexColor("#14532D"), leading=11),
    "con": ParagraphStyle("con", fontSize=8.5, textColor=colors.HexColor("#7F1D1D"), leading=11),
    "section_header": ParagraphStyle("section_header", fontSize=11, textColor=NAVY, fontName="Helvetica-Bold", spaceAfter=6),
    "badge_text": ParagraphStyle("badge_text", fontSize=11, textColor=colors.white, fontName="Helvetica-Bold", alignment=1),
}


def load_company_data(ticker):
    """Pulls every table this tearsheet needs for one company into a dict."""
    con = sqlite3.connect(DB_PATH)
    data = {
        "company": pd.read_sql("SELECT * FROM companies WHERE id = ?", con, params=(ticker,)),
        "ratios": pd.read_sql(
            "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year", con, params=(ticker,)
        ),
        "pnl": pd.read_sql(
            "SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year", con, params=(ticker,)
        ),
        "bs": pd.read_sql(
            "SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year", con, params=(ticker,)
        ),
        "cf": pd.read_sql(
            "SELECT * FROM cashflow WHERE company_id = ? ORDER BY year", con, params=(ticker,)
        ),
        "sector": pd.read_sql(
            "SELECT broad_sector, sub_sector FROM sectors WHERE company_id = ?", con, params=(ticker,)
        ),
    }
    con.close()

    pros_cons_path = OUTPUT_DIR / "pros_cons_generated.csv"
    if pros_cons_path.exists():
        pc = pd.read_csv(pros_cons_path)
        data["pros_cons"] = pc[pc["company_id"] == ticker]
    else:
        data["pros_cons"] = pd.DataFrame(columns=["type", "text", "confidence_pct"])

    ci_path = OUTPUT_DIR / "cashflow_intelligence.xlsx"
    if ci_path.exists():
        ci = pd.read_excel(ci_path)
        match = ci[ci["company_id"] == ticker]
        data["capital_allocation_label"] = match.iloc[0]["capital_allocation_label"] if len(match) else "Unavailable"
    else:
        data["capital_allocation_label"] = "Unavailable"

    return data


def has_enough_history(data, min_years=3):
    """Day 34 skip rule: fewer than 3 years of data -> skip this company."""
    return len(data["pnl"]) >= min_years


def compute_roce_proxy(bs_row, pnl_row):
    capital_employed = (bs_row["equity_capital"] or 0) + (bs_row["reserves"] or 0) + (bs_row["borrowings"] or 0)
    if capital_employed <= 0:
        return None
    return round((pnl_row["operating_profit"] / capital_employed) * 100, 2)


def build_kpi_tiles(data):
    """6 KPI tiles, 2 rows of 3, as a wordwrap-safe Table (not raw canvas text)."""
    ratios = data["ratios"]
    company = data["company"].iloc[0]
    latest = ratios.iloc[-1] if len(ratios) else None

    def fmt(value, suffix=""):
        return f"{value:.1f}{suffix}" if pd.notna(value) else "N/A"

    tiles = [
        ("ROE (latest)", fmt(latest["return_on_equity_pct"], "%") if latest is not None else "N/A"),
        ("ROCE (company ref.)", fmt(company["roce_percentage"], "%")),
        ("Debt/Equity", fmt(latest["debt_to_equity"]) if latest is not None else "N/A"),
        ("Revenue CAGR 5yr", fmt(latest["revenue_cagr_5yr"], "%") if latest is not None else "N/A"),
        ("PAT CAGR 5yr", fmt(latest["pat_cagr_5yr"], "%") if latest is not None else "N/A"),
        ("OPM (latest)", fmt(latest["operating_profit_margin_pct"], "%") if latest is not None else "N/A"),
    ]

    cells = []
    for label, value in tiles:
        cell_content = [Paragraph(label, styles["tile_label"]), Paragraph(value, styles["tile_value"])]
        cells.append(cell_content)

    rows = [cells[0:3], cells[3:6]]
    tile_width = (PAGE_W - 2 * 1.5 * cm) / 3
    table = Table(rows, colWidths=[tile_width] * 3, rowHeights=[2.1 * cm] * 2)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def chart_revenue_profit(data, ticker, tmp_dir):
    pnl = data["pnl"].tail(10)
    fig, ax = plt.subplots(figsize=(6.4, 2.6), dpi=150)
    x = range(len(pnl))
    width = 0.38
    ax.bar([i - width / 2 for i in x], pnl["sales"], width, label="Revenue", color="#0A2540")
    ax.bar([i + width / 2 for i in x], pnl["net_profit"], width, label="Net Profit", color="#4FA3D9")
    ax.set_xticks(list(x))
    ax.set_xticklabels(pnl["year"], rotation=45, ha="right", fontsize=7)
    ax.set_title("Revenue vs Net Profit (₹ Cr)", fontsize=9, fontweight="bold")
    ax.legend(fontsize=7, loc="upper left")
    ax.tick_params(axis="y", labelsize=7)
    fig.tight_layout()
    path = tmp_dir / f"{ticker}_rev_profit.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_roe_roce(data, ticker, tmp_dir):
    ratios = data["ratios"].tail(10)
    bs = data["bs"]
    pnl = data["pnl"]

    roce_values = []
    for _, r_row in ratios.iterrows():
        bs_match = bs[bs["year"] == r_row["year"]]
        pnl_match = pnl[pnl["year"] == r_row["year"]]
        if len(bs_match) and len(pnl_match):
            roce_values.append(compute_roce_proxy(bs_match.iloc[0], pnl_match.iloc[0]))
        else:
            roce_values.append(None)

    fig, ax1 = plt.subplots(figsize=(6.4, 2.6), dpi=150)
    ax1.plot(ratios["year"], ratios["return_on_equity_pct"], color="#0A2540", marker="o", markersize=3, label="ROE %")
    ax1.set_ylabel("ROE %", fontsize=7, color="#0A2540")
    ax1.tick_params(axis="y", labelsize=7, labelcolor="#0A2540")
    ax1.set_xticks(range(len(ratios)))
    ax1.set_xticklabels(ratios["year"], rotation=45, ha="right", fontsize=7)

    ax2 = ax1.twinx()
    ax2.plot(ratios["year"], roce_values, color="#B3261E", marker="s", markersize=3, label="ROCE % (derived)")
    ax2.set_ylabel("ROCE % (derived)", fontsize=7, color="#B3261E")
    ax2.tick_params(axis="y", labelsize=7, labelcolor="#B3261E")

    ax1.set_title("ROE vs ROCE (derived)", fontsize=9, fontweight="bold")
    fig.tight_layout()
    path = tmp_dir / f"{ticker}_roe_roce.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_balance_sheet_composition(data, ticker, tmp_dir):
    bs = data["bs"].tail(10).copy()
    bs["equity"] = bs["equity_capital"] + bs["reserves"]
    fig, ax = plt.subplots(figsize=(6.4, 2.6), dpi=150)
    ax.bar(bs["year"], bs["equity"], label="Equity", color="#0A2540")
    ax.bar(bs["year"], bs["borrowings"], bottom=bs["equity"], label="Borrowings", color="#B3261E")
    ax.bar(bs["year"], bs["other_liabilities"], bottom=bs["equity"] + bs["borrowings"],
           label="Other Liabilities", color="#9CA3AF")
    ax.set_xticks(range(len(bs)))
    ax.set_xticklabels(bs["year"], rotation=45, ha="right", fontsize=7)
    ax.tick_params(axis="y", labelsize=7)
    ax.set_title("Balance Sheet Composition (₹ Cr)", fontsize=9, fontweight="bold")
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    path = tmp_dir / f"{ticker}_bs_composition.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_cashflow_waterfall(data, ticker, tmp_dir):
    """True cascading waterfall: CFO -> CFI -> CFF -> Net Cash Flow."""
    cf = data["cf"]
    if len(cf) == 0:
        return None
    latest = cf.iloc[-1]
    cfo, cfi, cff = latest["operating_activity"], latest["investing_activity"], latest["financing_activity"]
    net = cfo + cfi + cff

    labels = ["CFO", "CFI", "CFF", "Net Cash Flow"]
    values = [cfo, cfi, cff, net]
    cumulative = [0, cfo, cfo + cfi, 0]  # Net Cash Flow bar starts at 0 (it's a total, not incremental)
    colors_bar = ["#1E7B34" if v >= 0 else "#B3261E" for v in [cfo, cfi, cff]] + ["#0A2540"]

    fig, ax = plt.subplots(figsize=(6.4, 2.6), dpi=150)
    for i, (label, value, base) in enumerate(zip(labels, values, cumulative)):
        ax.bar(label, value, bottom=base, color=colors_bar[i])
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title("Cash Flow Waterfall — Latest Year (₹ Cr)", fontsize=9, fontweight="bold")
    ax.tick_params(axis="both", labelsize=8)
    fig.tight_layout()
    path = tmp_dir / f"{ticker}_cf_waterfall.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def build_pros_cons_table(data):
    pc = data["pros_cons"]
    pros = pc[pc["type"] == "pro"].sort_values("confidence_pct", ascending=False)
    cons = pc[pc["type"] == "con"].sort_values("confidence_pct", ascending=False)

    elements = [Paragraph("Pros", styles["section_header"])]
    if len(pros):
        rows = [[Paragraph(f"+ {row['text']}", styles["pro"])] for _, row in pros.iterrows()]
        table = Table(rows, colWidths=[PAGE_W - 3 * cm])
        table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No pros generated for this company.", styles["pro"]))

    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph("Cons", styles["section_header"]))
    if len(cons):
        rows = [[Paragraph(f"- {row['text']}", styles["con"])] for _, row in cons.iterrows()]
        table = Table(rows, colWidths=[PAGE_W - 3 * cm])
        table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph("No cons generated for this company.", styles["con"]))

    return elements


def build_capital_allocation_badge(data):
    label = data["capital_allocation_label"]
    badge_colors = {
        "Shareholder Returns": GREEN, "Reinvestor": colors.HexColor("#1D4ED8"),
        "Mixed": colors.HexColor("#B45309"), "Growth Funded by Debt": colors.HexColor("#B45309"),
        "Liquidating Assets": colors.HexColor("#B45309"), "Distress Signal": RED,
        "Pre-Revenue": RED, "Cash Accumulator": colors.HexColor("#1D4ED8"), "Unclassified": colors.grey,
    }
    bg = badge_colors.get(label, colors.grey)
    table = Table([[Paragraph(f"Capital Allocation Pattern: {label}", styles["badge_text"])]],
                  colWidths=[PAGE_W - 3 * cm], rowHeights=[1.1 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return table


def navy_header(canvas_obj, doc, company_name, ticker):
    canvas_obj.saveState()
    canvas_obj.setFillColor(NAVY)
    canvas_obj.rect(0, PAGE_H - 2.2 * cm, PAGE_W, 2.2 * cm, fill=1, stroke=0)
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica-Bold", 16)
    canvas_obj.drawString(1.5 * cm, PAGE_H - 1.3 * cm, company_name)
    canvas_obj.setFont("Helvetica", 11)
    canvas_obj.drawString(1.5 * cm, PAGE_H - 1.9 * cm, ticker)
    canvas_obj.restoreState()


def build_tearsheet(ticker):
    """
    Returns "generated", "skipped" (insufficient history), or raises on
    genuine failure -- callers (batch generation in Day 34) rely on this
    distinction.
    """
    data = load_company_data(ticker)
    if len(data["company"]) == 0:
        raise ValueError(f"{ticker} not found in companies table")
    if not has_enough_history(data):
        return "skipped"

    TEARSHEET_DIR.mkdir(parents=True, exist_ok=True)
    TMP_CHART_DIR.mkdir(parents=True, exist_ok=True)

    company_name = data["company"].iloc[0]["company_name"]
    out_path = TEARSHEET_DIR / f"{ticker}_tearsheet.pdf"

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        topMargin=2.6 * cm, bottomMargin=1.5 * cm, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )

    story = []
    story.append(build_kpi_tiles(data))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Image(str(chart_revenue_profit(data, ticker, TMP_CHART_DIR)), width=17 * cm, height=6.9 * cm))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Image(str(chart_roe_roce(data, ticker, TMP_CHART_DIR)), width=17 * cm, height=6.9 * cm))

    story.append(PageBreak())
    story.append(Image(str(chart_balance_sheet_composition(data, ticker, TMP_CHART_DIR)), width=17 * cm, height=6.9 * cm))
    story.append(Spacer(1, 0.2 * cm))

    waterfall_path = chart_cashflow_waterfall(data, ticker, TMP_CHART_DIR)
    if waterfall_path:
        story.append(Image(str(waterfall_path), width=17 * cm, height=6.9 * cm))
    else:
        story.append(Paragraph("No cash flow data available for this company.", styles["con"]))
    story.append(Spacer(1, 0.3 * cm))

    story.extend(build_pros_cons_table(data))
    story.append(Spacer(1, 0.3 * cm))
    story.append(build_capital_allocation_badge(data))

    def on_page(canvas_obj, doc_obj):
        navy_header(canvas_obj, doc_obj, company_name, ticker)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return "generated"


if __name__ == "__main__":
    test_tickers = ["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL"]
    for ticker in test_tickers:
        try:
            result = build_tearsheet(ticker)
            path = TEARSHEET_DIR / f"{ticker}_tearsheet.pdf"
            size_kb = path.stat().st_size / 1024 if path.exists() else 0
            print(f"{ticker}: {result} ({size_kb:.1f} KB)")
        except Exception as exc:
            print(f"{ticker}: FAILED - {exc}")