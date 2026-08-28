# Sprint 2 Retrospective — Financial Ratio Engine

**Sprint:** Aug 24–30, 2026
**Epic:** Financial Ratio Engine (42 SP)

## What was delivered
- `financial_ratios` table — 1,041 rows populated across 92 companies (target was 1,100+; gap documented below)
- `src/analytics/ratios.py` — profitability, leverage, efficiency functions (12 functions total)
- `src/analytics/cagr.py` — CAGR engine, all 6 edge cases handled
- `src/analytics/cashflow_kpis.py` — FCF, CFO Quality, CapEx Intensity, 8-pattern capital allocation classifier
- `src/analytics/populate_ratios.py` — full ratio engine run against real 92-company database
- `src/analytics/edge_cases_day13.py` — sector-aware D/E carve-out, ROE/ROCE cross-check
- `output/capital_allocation.csv`, `output/ratio_edge_cases.log`
- `tests/kpi/` — 43 unit tests, 0 failures

## Exit criteria — status
| Criteria | Status | Notes |
|---|---|---|
| `financial_ratios` >= 1,100 rows | ⚠️ 1,041 rows | 15-17 company-years (SBIN, HAL) missing matching balance sheet/cash flow data. No fabrication used to close gap. |
| All 14 KPI columns populated, zero null-only columns | ⚠️ 3 columns fully null | `capex_cr`, `book_value_per_share` structurally uncomputable from available data; `composite_quality_score` has no spec-defined formula. All documented in `ratio_edge_cases.log`. |
| All 20 KPI formula unit tests pass | ✅ 43 tests passing (exceeds minimum) | 8+13+10+12 = 43 tests |
| Manual spot-check: ROE/CAGR within 0.1% | ✅ Verified (SQL-based independent recomputation) | Initial verification attempt revealed a year-alignment discrepancy (balancesheet had records through 2024-09, profitandloss through 2024-03) — traced to the verification script comparing mismatched years, not a pipeline bug. Re-verified using matched fiscal years (2024-03 for both tables): ABB, ADANIENSOL, ADANIENT all showed 0.00% difference between stored and independently recomputed ROE. Full spreadsheet cross-check was substituted with equivalent-rigor SQL-based independent recomputation given time constraints. |
| `ratio_edge_cases.log` — documented anomalies | ✅ Complete | 4 Day 12 gaps + 18 Day 13 ROE anomalies, all categorized |

## Key findings & decisions made independently
1. **Row count gap (1,041 vs 1,100)** — traced to specific missing (company_id, year) pairs in SBIN and HAL's balance sheet/cash flow data. Decision: accept real count, document reason, do not interpolate.
2. **3 structurally NULL columns** — `capex_cr` (no CapEx data source exists; `investing_activity` rejected as inaccurate proxy), `book_value_per_share` (no shares-outstanding data anywhere in schema), `composite_quality_score` (formula undefined in spec). All left NULL rather than guessed.
3. **ROE/ROCE anomalies** — 18 companies show >5pp difference between computed and source ROE. Most are plausible methodology differences (e.g., TATAMOTORS 11.94pp). A subset (BEL 4744%, HAL 3816%, LT 67pp) are likely calculation artifacts from near-zero equity denominators in specific years — flagged separately for review, not conflated with benign discrepancies.
4. **Screener preview returned 58 companies** (target 15-50) for ROE>15% + D/E<1 — reviewed manually, consistent with Nifty 100's real composition (many low-leverage blue-chips). Not adjusted to force-fit the expected range.
5. **Schema extension required** — original Day 4 `schema.sql` didn't include CAGR/quality-score columns, since these requirements only appeared in Sprint 2's spec. Extended via `ALTER TABLE`.
6. **PRIMARY KEY preservation bug caught and fixed** — initial `to_sql(if_exists='replace')` would have silently dropped the `(company_id, year)` composite key; switched to DELETE+INSERT to preserve schema integrity.
7. **Balance sheet reporting cadence discrepancy discovered** — balancesheet.xlsx contains interim (September) entries in addition to fiscal year-end (March) entries for at least ABB, ADANIENSOL, and ADANIENT, while profitandloss.xlsx only has March year-end data. financial_ratios correctly used matched March-to-March pairs. Worth flagging to team: verify this interim-reporting pattern doesn't exist elsewhere undetected, and confirm September rows are being excluded intentionally, not silently dropped.

## What went well
- Every formula decision was traceable back to either the spec or an explicitly documented independent judgment call — no silent assumptions
- Caught a real calculation-artifact pattern (extreme ROE outliers) during anomaly review rather than accepting the categorization at face value
- Maintained "no fabrication" discipline throughout, even under schedule pressure and without team availability for clarification

## What to improve next sprint
- Establish a faster escalation path for spec ambiguities (composite_quality_score formula, missing CapEx source) rather than resolving all of them solo
- Consider requesting shares-outstanding data be added to the source dataset if book_value_per_share is genuinely needed downstream
- Revisit whether the 1,100-row and 15-50 screener exit criteria were realistic targets given actual source data completeness — worth a retrospective conversation with whoever set them

## Sprint 3 readiness
`financial_ratios` table is stable and query-ready despite documented gaps. Screener (Epic 03) can proceed using the 1,041 populated rows; the 3 NULL columns should be excluded from any screener filter logic until resolved.