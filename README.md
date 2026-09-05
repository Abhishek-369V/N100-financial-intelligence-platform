# N100 Financial Intelligence Platform

Production-grade financial analytics platform for all 92 Nifty 100 companies — ETL pipeline, 30+ KPI engine, investment screener, peer benchmarking, and (in progress) an interactive Streamlit dashboard with valuation analysis.

**Status: In Progress — Sprint 4 of 6 (Screener + Peer Engine)**

---

## Project Scope
- 92 companies · 12 source datasets (7 core + 5 supporting)
- 12-table SQLite star schema (`nifty100.db`)
- 30+ financial KPIs per company-year (profitability, leverage, efficiency, cash flow, CAGR)
- 6 preset investment screeners + custom filter engine
- Peer percentile rankings across 11 peer groups
- Radar chart visualizations (peer-relative and standalone)
- *(Upcoming)* 8-screen Streamlit dashboard + valuation module

## Sprint Progress

| Sprint | Epic | Status |
|---|---|---|
| Sprint 1 | Data Ingestion & ETL | ✅ Complete |
| Sprint 2 | Financial Ratio Engine | ✅ Complete |
| Sprint 3 | Screener + Peer Engine | ✅ Complete |
| Sprint 4 | Streamlit Dashboard + Valuation | 🔄 In Progress |
| Sprint 5 | (Reporting, per roadmap) | ⏳ Upcoming |
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
│   └── Sprint3_Retrospective.md
├── output/ <---------------- validation_failures.csv, load_audit.csv, screener_output.xlsx, etc.
├── reports/
│ └── radar_charts/ <-------- 90 PNGs (55 peer-relative + 35 standalone)
├── src/
│   ├── etl/ <--------------- loader, validator, database_setup
│   ├── analytics/ <--------- ratios, cagr, cashflow_kpis, peer, populate_ratios, radar_charts
│   └── screener/ <---------- engine, presets, composite_score, export_excel
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

## Key Findings So Far
- Sector concentration and data-labeling errors caught during Sprint 1 manual review (documented in retrospective)
- 16 data quality rules enforced; all CRITICAL issues resolved before load
- 43+ unit tests passing across ETL and KPI modules
- Winsorization (P10/P90) applied to neutralize extreme-value artifacts (e.g., near-zero-equity ROE distortions) in composite scoring

## Author
Madanala Abhishek Varma — Data Analyst Intern, Bluestock Fintech