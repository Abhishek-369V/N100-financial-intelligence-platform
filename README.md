# N100 Financial Intelligence Platform

Production-grade financial analytics platform for all 92 (Nifty 100) companies: ETL pipeline, 30+ KPI engine, investment screener, peer benchmarking, NLP-generated pros/cons, PDF reporting, KMeans clustering, and a 16-endpoint REST API on top of an 8-screen Streamlit dashboard.

---

## Project Scope
- 92 companies · 12 source datasets (7 core + 5 supporting)
- **13-table** SQLite schema (`nifty100.db`) see [Known data limitations](#known-data-limitations) for why this isn't the 10 originally planned
- 30+ financial KPIs per company-year (profitability, leverage, efficiency, cash flow, CAGR)
- 6 preset investment screeners + custom filter engine
- Auto-generated pros/cons (24 rules, confidence-scored) for all 92 companies
- Cash flow intelligence: CFO quality, CapEx intensity, distress/deleveraging flags, 8-pattern capital allocation classification
- KMeans clustering (5 clusters) with descriptive naming and outlier detection
- Peer percentile rankings across **11** peer groups 
- PDF reporting: 91 company tearsheets, 10 sector reports, 1 portfolio summary(92 pages)
- 16-endpoint REST API (FastAPI) with OpenAPI docs + Postman collection
- 8-screen Streamlit dashboard + valuation module
- 167 passing tests, 0 failure -- across ETL, KPI, DQ, screener, and API layers

## Sprint Progress

| Sprint | Epic | Status |
|---|---|---|
| Sprint 1 | Data Ingestion & ETL | ✅ Complete |
| Sprint 2 | Financial Ratio Engine | ✅ Complete |
| Sprint 3 | Screener + Peer Engine | ✅ Complete |
| Sprint 4 | Streamlit Dashboard + Valuation | ✅ Complete |
| Sprint 5 | Intelligence, NLP & PDF Reports | ✅ Complete |
| Sprint 6 | Clustering, REST API & Final QA | ✅ Complete |

## Folder Structure
```
N100_Financial_Intelligence/
├── config/
│   └── screener_config.yaml
├── data/
│   ├── raw/ <----------------------- 12 source Excel files
│   └── processed/ <----------------- cleaned CSVs
├── db/
│   ├── schema.sql
│   └── nifty100.db <---------------- 13 tables, SQLite_database
├── docs/
│   ├── acceptance_checklist.pdf
│   ├── analyst_guide.pdf
│   ├── openapi.json
│   ├── postman_collection.json
│   └── sprint1-6_Retrospective.md
├── notebooks/ 
│   └── exploratory_queries.sql
├── output/ <------------------------ validation_failures.csv, cluster_labels.csv,
│                                     pros_cons_generated.csv, cashflow_intelligence.xlsx,
│                                     portfolio_stats.csv, perf_notes.md,...
├── reports/
│   ├── portfolio/ <----------------- portfolio_summary.pdf (92 pages)
│   ├── radar_charts/ <-------------- peer-relative + standalone PNGs
│   ├── sector/ <-------------------- 10 sector PDFs 
│   ├── tearsheets/ <---------------- 91 per-company PDFs (JIOFIN skipped, <3yrs data)
│   ├── elbow_plot.png
│   ├── correlation_heatmap.png
│   └── pytest_report.html
├── src/
│   ├── etl/ <----------------------- loader, validator, database_setup       [Sprint 1]
│   ├── analytics/ <----------------- ratios, cagr, cashflow_kpis, peer,      [Sprints 2, 6]
│   │                                 populate_ratios, radar_charts, clustering,
│   │                                 cluster_profiling, capital_allocation_report,
│   │                                 add_indexes                             
│   ├── screener/ <------------------ engine, presets, composite_score        [Sprint 3]
│   ├── dashboard/ <----------------- app, 8 pages, utils                     [Sprint 4]
│   ├── nlp/ <----------------------- parser, pros_cons_generator             [Sprint 5]
│   ├── reports/ <------------------- tearsheet, sector_report,
│   │                                 portfolio_summary                       [Sprint 5]
│   ├── api/ <----------------------- main, database, export_openapi,
│   │                                 routers/ (8 files, 16 endpoints)        [Sprint 6]
│   ├── testing/ <------------------- performance_tests                       [Sprint 6]
│   └── tools/ <--------------------- add_docstrings                          [Sprint 6]
└── tests/
    ├── etl/, kpi/, dq/, screener/, api/
```

## 1. Setup
```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python src/etl/data_ingestion.py    # or run_pipeline.py for full ETL
python src/etl/database_setup.py
python -m src.analytics.add_indexes # adds company_id/year indexes (Day 43)
```

## 2. Running the dashboard
```bash
streamlit run src/dashboard/app.py
```
Run this from the project root (not from inside `src/dashboard/`); the data loader resolves paths relative to the project root.

## 3. Running the API
```bash
uvicorn src.api.main:app --port 8000 --reload
```
Docs at `http://127.0.0.1:8000/docs`. Example calls:
```bash
curl http://127.0.0.1:8000/api/v1/health
curl "http://127.0.0.1:8000/api/v1/screener?min_roe=15&max_de=1.0"
curl http://127.0.0.1:8000/api/v1/companies/TCS
curl http://127.0.0.1:8000/api/v1/companies/TCS/tearsheet -o TCS_tearsheet.pdf
```
Full endpoint list and request/response schemas: `docs/openapi.json`, or import `docs/postman_collection.json` into Postman.

## 4. Running the test suite 
```bash
# Quick console run
python -m pytest tests/ -q 

# Full audit run with HTML report
pytest tests/ --html=reports/pytest_report.html --self-contained-html -v

167 tests across `tests/etl/`, `tests/kpi/`, `tests/dq/`, `tests/screener/`, `tests/api/`.
```

## Dashboard screens

1. **Home**: 6 portfolio-wide KPI tiles (winsorized average ROE, median
   P/E, median D/E, total companies, median revenue CAGR, debt-free
   count), a sector breakdown donut chart, and a Top-5 companies table
   by composite quality score.

2. **Company Profile**: search any of the 92 companies, see a company
   card, 6 KPI tiles, a 10-year Revenue/Net Profit bar chart, an ROE
   trend line (ROCE shown as a static reference -- see limitations), and
   pros/cons where available.

3. **Screener**: 10 sliders filter the universe live via
   `src/screener/engine.py`'s `run_screener()` -- the same function the
   API's `/screener` endpoint calls (verified identical, `tests/api/test_integration.py`).

4. **Peer Comparison**: pick one of 11 peer groups and a company within
   it to see an 8-axis radar chart against the group average and benchmark.

5. **Trend Analysis**: overlay up to 3 metrics for one company over its
   available history.

6. **Sector Analysis**: Revenue-vs-ROE bubble chart + sector median KPIs.

7. **Capital Allocation Map**: treemap of all 92 companies across 8
   capital-allocation patterns.

8. **Annual Reports**: annual report links per company, flagged by
   validity (same rule the API's `/documents` endpoint and DQ-10 use).

## Known data limitations
Documented as found, not hidden: full detail in each sprint's retrospective:

- **10 sectors, not 11**: `sectors.broad_sector` has 10 distinct values; early planning docs assumed 11. (Peer groups, separately, genuinely do have 11: not the same thing.)
- **13 database tables, not 10**: the schema grew organically past the original plan; `/api/v1/health` reports all 13 real ones.
- **16 DQ rules, not 14**: `validator.py` implements 16; all 16 are tested.
- `roce_percentage` is a single latest-snapshot value, not a time series: a derived EBIT/Capital-Employed proxy is used wherever a ROCE *trend* is shown, and always labelled "(derived)".
- Only 5 of 92 companies have any `analysis.xlsx` data; only 16 have raw `prosandcons.xlsx` data (Sprint 5 generates pros/cons independently of this file).
- SBIN and ATGL are absent from `financial_ratios` entirely: SBIN because D/E-style ratios don't apply to a bank (correct exclusion), ATGL for no clear reason (upstream gap). Both are still covered in pros/cons (via fallback), clustering (via sector-median imputation), and tearsheets/portfolio summary (shown as N/A): but the **screener excludes them entirely** (a narrower, real gap -- see `tests/api/test_screener.py`).
- `documents` table's own columns are `Year`/`Annual_Report` (capitalized), inconsistent with every other table's lowercase convention.
- JIOFIN has no tearsheet PDF (correctly skipped: <3 years of data).

## Key Findings
- 16 data quality rules enforced (not 14 as originally scoped); all CRITICAL issues resolved before load
- 167 unit/integration tests passing (100% pass rate), 100% docstring coverage (`interrogate`), 0 `ruff` findings
- Winsorization (P10/P90) applied to neutralize extreme-value artifacts in composite scoring
- Load test: 10 concurrent screener calls complete in ~1s (target: <10s); dashboard data-load timing ~3-10ms per ticker (target: <3s) -- see `output/perf_notes.md`
- Several sector-blind bugs found and fixed during Sprint 5-6 (leverage-based con-rules and the Distress Signal flag both originally mis-flagged banks/NBFCs for having normal-for-a-bank leverage) -- full traceability in the sprint retrospectives


## Author
Madanala Abhishek Varma, Data Analyst Intern, Bluestock Fintech