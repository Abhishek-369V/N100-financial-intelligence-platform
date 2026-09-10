# N100 Financial Intelligence Platform

Production-grade financial analytics platform for all 92 Nifty 100 companies — ETL pipeline, 30+ KPI engine, investment screener, peer benchmarking, and (in progress) an interactive Streamlit dashboard with valuation analysis.

**Status: In Progress — Sprint 5 of 6 (INTELLIGENCE, NLP & PDF REPORTS)**

---

## Project Scope
- 92 companies · 12 source datasets (7 core + 5 supporting)
- 12-table SQLite star schema (`nifty100.db`)
- 30+ financial KPIs per company-year (profitability, leverage, efficiency, cash flow, CAGR)
- 6 preset investment screeners + custom filter engine
- Peer percentile rankings across 11 peer groups
- Radar chart visualizations (peer-relative and standalone)
- 8-screen Streamlit dashboard + valuation module

## Sprint Progress

| Sprint | Epic | Status |
|---|---|---|
| Sprint 1 | Data Ingestion & ETL | ✅ Complete |
| Sprint 2 | Financial Ratio Engine | ✅ Complete |
| Sprint 3 | Screener + Peer Engine | ✅ Complete |
| Sprint 4 | Streamlit Dashboard + Valuation | ✅ Complete |
| Sprint 5 | (Reporting, per roadmap) | 🔄 In Progress |
| Sprint 6 | (Alerts, Testing, Docs, per roadmap) | ⏳ Upcoming |

## Folder Structure
```
N100_Financial_Intelligence/
├── config/
│   └── screener_config.yaml
├── data/
│   ├── raw/ <--------------- 12 source Excel files
│   └── processed/ <--------- cleaned CSVs
├── db/
│   ├── schema.sql
│   └── nifty100.db
├── docs/
│   ├── Sprint1_Retrospective.md
│   ├── Sprint2_Retrospective.md
│   ├── Sprint3_Retrospective.md
│   └── Sprint4_Retrospective.md
├── output/ <---------------- validation_failures.csv, load_audit.csv, screener_output.xlsx, etc.
├── reports/
│ └── radar_charts/ <-------- 90 PNGs (55 peer-relative + 35 standalone)
├── src/
│   ├── etl/ <--------------- loader, validator, database_setup [SPRINT1]
│   ├── analytics/ <--------- ratios, cagr, cashflow_kpis, peer, populate_ratios, radar_charts [SPRINT2]
│   ├── screener/ <---------- engine, presets, composite_score, export_excel [SPRINT3]
    └── dashboard/ <--------- app, 8 pages, utils [SPRINT4]
└── tests/
    ├── etl/
    ├── kpi/
    └── screener/
```


## Setup
```bash
python -m venv venv
pip install -r requirements.txt
python src/etl/data_ingestion.py    # or run_pipeline.py for full ETL
python src/etl/database_setup.py
```

## Running the dashboard

```bash
pip install -r requirements.txt
streamlit run src/dashboard/app.py
```

Run this from the project root (not from inside `src/dashboard/`) —
the data loader resolves paths relative to the project root.

## Dashboard screens

1. **Home** — 6 portfolio-wide KPI tiles (winsorized average ROE, median
   P/E, median D/E, total companies, median revenue CAGR, debt-free
   count), a sector breakdown donut chart, and a Top-5 companies table
   by composite quality score. A year selector (2019-2024) drives the
   KPI tiles; the sector chart and Top-5 table are intentionally
   year-invariant (sector is a static attribute, composite score is
   inherently latest-data-only).

2. **Company Profile** — search any of the 92 companies, see a company
   card (sector, sub-sector, description), 6 KPI tiles, a 10-year
   Revenue/Net Profit bar chart, an ROE trend line (with ROCE shown as
   a static reference line, since ROCE has no year-by-year history in
   the source data), and pros/cons badges where available.

3. **Screener** — 10 sliders (ROE, D/E, FCF, Revenue CAGR, PAT CAGR,
   OPM, P/E, P/B, Dividend Yield, ICR) filter the universe live. 6
   preset buttons pre-fill the sliders to approximate the Sprint 3
   presets (2 presets use conditions beyond what sliders express —
   flagged in-app when clicked). Results export to CSV.

4. **Peer Comparison** — pick one of 11 peer groups and a company
   within it to see an 8-axis radar chart against the group average,
   plus a full KPI table with the benchmark company highlighted.

5. **Trend Analysis** — overlay up to 3 metrics for one company over
   its available history, with YoY % change annotated at each point.

6. **Sector Analysis** — a Revenue-vs-ROE bubble chart (bubble size =
   market cap) for a selected sector, plus sector median KPIs.

7. **Capital Allocation Map** — a treemap of all 92 companies grouped
   into 8 capital-allocation patterns (Reinvestor, Shareholder Returns,
   Growth Funded by Debt, etc.), derived from each company's latest
   operating/investing/financing cash flow signs. Click a pattern (or
   a company within it) to drill into the member list.

8. **Annual Reports** — search a company to see its available report
   years with links to BSE; unreachable or missing links are flagged
   in red.

## Known data limitations (carried from Sprints 1-3)

- `sectors` has 10 distinct `broad_sector` values, not the 11
  referenced in early planning docs.
- `roce_percentage` is a single latest-snapshot value per company
  (in `companies`), not a time series — anywhere ROCE trend would be
  expected, it's shown as a flat reference line instead.
- Only 14 of 92 companies have `prosandcons` data.
- `documents` (annual report links) coverage and BSE link liveness
  vary by company.


## Key Findings So Far
- Sector concentration and data-labeling errors caught during Sprint 1 manual review (documented in retrospective)
- 16 data quality rules enforced; all CRITICAL issues resolved before load
- 43+ unit tests passing across ETL and KPI modules
- Winsorization (P10/P90) applied to neutralize extreme-value artifacts (e.g., near-zero-equity ROE distortions) in composite scoring

## Author
Madanala Abhishek Varma — Data Analyst Intern, Bluestock Fintech