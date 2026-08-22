# Sprint 1 Retrospective — Data Foundation

**Sprint:** Aug 15–22, 2026 
**Epic:** Data Ingestion & ETL (34 SP)

## What was delivered
- `nifty100.db` — 12 tables loaded (7 core + 5 supporting; source docs listed 10, verified 12 via project documentation cross-check)
- `output/load_audit.csv` — full source/loaded/rejected reconciliation, all rows balance correctly
- `output/validation_failures.csv` — 16 DQ rules executed, all CRITICAL issues traced to root cause and resolved
- `output/year_coverage_report.csv` — coverage check across all 92 companies
- `src/etl/loader.py`, `validator.py`, `database_setup.py`, `manual_review.py`
- `db/schema.sql` — 12-table schema with PK/FK constraints
- `tests/etl/test_normalizer.py` — 35 unit tests, 0 failures
- `notebooks/exploratory_queries.sql` — 10 queries

## Exit criteria — status
| Criteria | Status |
|---|---|
| `SELECT COUNT(*) FROM companies` = 92 | ✅ |
| `PRAGMA foreign_key_check` → 0 rows | ✅ |
| `load_audit.csv` → zero CRITICAL rejections unaccounted for | ✅ |
| 35+ ETL unit tests pass | ✅ |
| Manual review: 5 companies correct | ✅ (with 1 flagged data issue) |

## Key findings from validation & manual review
1. **8 orphan companies** — `profitandloss.xlsx` contained financial data for 100 companies, but `companies.xlsx` master list has only 92. Excluded orphan rows from load; flagged for team follow-up on whether master list needs updating.
2. **ADANIPORTS duplicate rows** — every P&L row for this company appeared exactly twice in source data. Confirmed as a genuine source file error via raw inspection, not a code bug. Deduplicated during load.
3. **TTM year values** — `"TTM"` (Trailing Twelve Months) rows exist in year columns; correctly excluded as `PARSE_ERROR` since TTM isn't a discrete fiscal year.
4. **Data labeling error: ticker `ABB`** — `company_name` field incorrectly reads "Abbott India Ltd"; sector and financial data confirm this is actually ABB India Ltd (Industrials/Capital Goods), not Abbott India (Healthcare). Flagged to team, not auto-corrected pending confirmation.
5. **JIOFIN — 2 years coverage** — confirmed as expected, not a defect (company listed in 2023 post-demerger).
6. **Bug caught and fixed in our own code**: `load_audit.csv`'s `rejected` counter was being reset mid-loop instead of accumulating across orphan/duplicate/parse-error checks — found via manual cross-check against raw row-count deltas, not automated testing. Fixed by initializing `rejected = 0` once per table at the top of the loop.

## What went well
- 16 DQ rules caught real, meaningful data issues rather than trivial ones — validated the rules were designed thoughtfully
- Cross-checking console output against the actual saved CSV caught a real reporting bug that would have otherwise gone unnoticed
- Manual review (Day 6) surfaced a genuine data labeling error a purely automated pipeline would have missed

## What to improve next sprint
- Get earlier access to complete project documentation (missing DQ rule definitions in the source PDF caused rework on Day 3-4)
- Establish column-name conventions with the team before Sprint 2 begins, to avoid repeated verification cycles
- Confirm with team on ABB naming discrepancy and 8 orphan companies before Sprint 2 ratio calculations depend on this data

## Sprint 2 readiness
Foundation is stable: schema, loader, validator, and audit trail are all functioning and tested. Sprint 2 (Financial Ratio Engine) can begin on the current `nifty100.db` as-is.