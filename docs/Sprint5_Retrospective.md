# Sprint 5 Retrospective — Intelligence, NLP & PDF Reports

## Day 29 — Analysis Text Parser

`src/nlp/parser.py`. Reads `data/processed/analysis.csv` (not `raw/analysis.xlsx`
— identical content, already flattened, no title-banner row to skip; matches
the project convention of reading processed/DB data over raw files).

Extended the spec's regex `(\d+)\s*Years?:?\s*([\d.]+)%` in two ways, both
documented in the module docstring rather than silently patched:

1. ~25% of entries use "TTM:" / "1 Year:" / "Last Year:" instead of a numbered
   Years label — all mean a trailing-1-year figure. Normalized to
   `period_years = 1` via a second regex pass, tagged `source_label` so the
   normalization is auditable, not silently merged with genuine "1 Year:" rows.
2. The literal spec regex can't match negative values (`3 Years: -1%`, a real
   WIPRO figure) — extended to `[\d.\-]+`. Real CAGR can legitimately be
   negative; excluding it would misclassify valid data as malformed.

**GAP**: only 5 of 92 companies (HDFCBANK, SBILIFE, TCS, WIPRO, INFY) have any
rows in `analysis.xlsx`/`analysis.csv` at all — confirmed by inspecting the raw
file, not a parser bug. `analysis_parsed.csv` will only ever cover these 5.

`parse_failures.csv` is only written when there's an actual failure to log
(and a stale one from a previous run is deleted on a clean re-run) — an empty
file with just a header row reads as "something broke," not "nothing broke."

Verified: 80/80 cells parsed, 0 genuine failures, cross-validated against
`financial_ratios` — 0 divergences >5pp.

## Day 30 — Auto Pros/Cons Generator

`src/nlp/pros_cons_generator.py`. All 12 pro + 12 con rules, confidence-gated
at >60%, against `financial_ratios` and `profitandloss`.

**GAP**: `financial_ratios` is missing SBIN (bank — D/E-style ratios are
structurally meaningless for a bank, correct exclusion by the Ratio Engine)
and ATGL (no clear reason — upstream gap) entirely. Both routed through a
dedicated `FALLBACK` path (confidence 61, clearly tagged) rather than ending
up with zero pros/cons.

**BUG FOUND (Day 33 visual QA) AND FIXED**: HDFCBANK's tearsheet showed
"Debt-to-equity of 6.81 is elevated for a **non-financial** company" as a
con — wrong, high leverage is structurally normal for a bank. C1 (D/E>2),
C6 (ICR<1.5), C10 (ROCE<10%), C11 (Net Debt>3x EBITDA) — all leverage-shaped
rules — now skip Financials-sector companies. The fallback-coverage logic was
*also* defaulting to D/E for its generic con; fixed to use OPM for Financials
so the fallback doesn't reintroduce the same bug it was built to avoid.

Verified (post-fix): 92/92 companies covered, 0 missing a pro, 0 missing a
con, 533 total rows, 44 of them `FALLBACK`.

## Day 31 — Cash Flow Intelligence Module

`src/analytics/cashflow_kpis.py` (extended, not a new file — same module Day
11 already built). Added CFO quality score/label, CapEx intensity/label,
FCF 5yr CAGR, FCF conversion, distress flag, deleveraging flag →
`output/cashflow_intelligence.xlsx` (92 rows).

`fcf_cagr()` returns `None` when start/end FCF ≤ 0 (CAGR is mathematically
undefined for a negative/zero base) rather than a fabricated number — FCF is
allowed to be negative by design, so this is an expected case, not a crash.

**CAVEAT (labelled, not filtered)**: 9 of 13 companies flagged with a
"Distress Signal" (CFO<0 & CFF>0) are banks/NBFCs, where this pattern is
close to normal business model (loan disbursement = operating outflow,
deposits/borrowings = routine financing), not actual distress — all 9 have
strong positive net profit. Added `sector` + `likely_financial_sector_pattern`
columns to `distress_alerts.csv` so this isn't misread at a glance.

2 companies (AMBUJACEM, ATGL) have gaps in cash flow history → `None` values
in the output, not silently dropped from the 92-row file.

## Day 32 — Capital Allocation Report

`src/analytics/capital_allocation_report.py` (new file).

**GAP**: spec says "verify `capital_allocation.csv` from Sprint 2 is
complete" — it doesn't exist anywhere in the project, nothing to verify.
Generated it fresh via the same (now-fixed) `generate_capital_allocation_output()`
Day 31 uses.

`output/pattern_changes.csv`: 527 year-over-year pattern-change events across
91 companies (ATGL has zero cashflow rows at all — the one real gap; can't
have a "change" with 0 or 1 data points). Cross-checked against Day 31's
`cashflow_intelligence.xlsx` labels: 0 mismatches.

## Day 33 — PDF Tearsheet Template

`src/reports/tearsheet.py`. 2-page ReportLab tearsheet: navy header, 6 KPI
tiles, Revenue/Net Profit + ROE/ROCE charts on page 1; Balance Sheet
composition, cash flow waterfall (true cascading bridge, not 4 flat bars),
Pros/Cons, capital allocation badge on page 2. KPI tiles and Pros/Cons built
as Platypus `Table`s with `Paragraph` cells for genuine wordwrap, not raw
canvas text that can silently overflow.

**GAP**: no per-year ROCE anywhere in the schema (`companies.roce_percentage`
is a single static value). Computed a per-year proxy — EBIT/Capital Employed,
using `operating_profit` as the EBIT proxy — charted and labelled
"ROCE (derived)", never presented as an official figure.

**GAP**: `companies.roe_percentage` looks scale-inconsistent vs
`financial_ratios` (TCS: 0.52 vs 50.94 for the same year). Used
`financial_ratios.return_on_equity_pct` throughout, consistent with every
other module in this codebase.

Verified on all 5 spec test companies (TCS, HDFCBANK, RELIANCE, SUNPHARMA,
TATASTEEL): exactly 2 pages, 127–136KB, zero overflow — confirmed by
rendering to PNG and inspecting visually, not just checking exit codes.

## Day 34 — Batch Report Generation

`src/reports/tearsheet.py` (`run_batch_tearsheets`) + new
`src/reports/sector_report.py`.

**BUG FOUND (full-batch run) AND FIXED**: PNB (a bank) has
`operating_profit = None` for at least one year — crashed
`compute_roce_proxy()`. The 5-company spot-check never hit this. Fixed to
return `None` instead of crashing.

**BUG FOUND (visual QA) AND FIXED**: ATGL's capital allocation badge showed
the literal string "Capital Allocation Pattern: nan" — fixed to a clean
"Unavailable (no cash flow data)" message.

**GAP**: spec assumes 11 sectors (repeated again in Sprint 6 Day 40's
`test_sectors.py`). Actual `sectors` table has **10** distinct
`broad_sector` values covering all 92 companies (verified: counts sum to 92,
nothing missing). Generated 10 sector PDFs matching reality, not a
fabricated 11th. **Flagging for Sprint 6**: `test_sectors.py`'s "returns
exactly 11 sectors" assertion will need to be 10, or the sectors table
itself needs revisiting — this is a spec-vs-data mismatch, not a bug in
either sprint's code.

Final: 91 tearsheets generated (JIOFIN correctly skipped — <3yrs data, per
the spec's own skip rule, logged to `output/skipped_tearsheets.csv`), 0
failures, 0 files <30KB. 10 sector PDFs, 92/92 companies covered across them,
largest (Financials, 23 companies) spans 2 pages with correct header repeat
and no overflow.

## Day 35 — Portfolio Summary PDF

`src/reports/portfolio_summary.py` (new file). One page per company,
alphabetical by ticker, same 6 KPIs as Day 33's tearsheet tiles, with a
trend arrow per KPI vs the prior year.

**GAP handled thoughtfully, not literally**: spec says "up arrow if metric
improved, down if declined" — "improved" is direction-specific per metric,
not just "the number went up". For ROE/ROCE/Revenue CAGR/PAT CAGR/OPM,
higher = improved. For D/E, **lower** = improved (less leverage is better).
A literal "value increased = up arrow" would show a company taking on
*more* debt as a green improvement. Implemented direction-aware arrows per
metric instead.

"Flat within 2%" interpreted as *relative* change
(`abs(latest-prior)/abs(prior) < 2%`), not an absolute 2-point move — this
matters because the 6 KPIs sit on very different scales (D/E: 0–10s, OPM:
0–100s), and an absolute threshold would be meaningless on one and too
loose on the other.

ROCE trend reuses the same derived proxy from Day 33 (documented there) since
no per-year ROCE source exists to compare year-over-year.

Verified: 92 pages generated, PDF page count double-checked via `pypdf`
(92 == 92). Spot-checked TCS (real up/down/flat mix, confirmed D/E's red
down-arrow was correct — its D/E actually rose slightly, 0.0850→0.0886,
which *is* a decline in quality even though the printed value rounds to a
smaller-looking "0.1"), and SBIN (all-N/A page, clean caveat text, no crash,
no misleading arrows on missing data).

---

## Sprint 5 exit criteria — status

| Gate                                                             | Status              | Note                                                                                                                                                                                                                                                                                                        |
| ---------------------------------------------------------------- | ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pros_cons_generated.csv` ≥1 pro & 1 con for every company    | ✅ Pass             | 92/92, post sector-fix                                                                                                                                                                                                                                                                                      |
| All 92 tearsheets exist, ≥30KB each                             | ⚠️**91/92** | JIOFIN skipped per the spec's own Day 34 skip rule (<3yrs data). This is a genuine tension between two parts of the same spec (the skip rule vs. the "all 92" gate) - not a missed deliverable. Recommend the gate wording get a "or documented skip" clause before Sprint 6 sign-off references it again. |
| Visual review of 5 tearsheets: no overflow, no blank pages       | ✅ Pass             | Actually spot-checked 10 across Day 33–34 (5 spec companies + PNB/ATGL/INFY/ITC/MARUTI), all rendered to PNG and inspected                                                                                                                                                                                 |
| `cashflow_intelligence.xlsx` has 92 rows, all required columns | ✅ Pass             | 2 rows (AMBUJACEM, ATGL) have`None` in derived columns — documented data gap, not missing rows                                                                                                                                                                                                           |

## Bugs carried INTO Sprint 6

None outstanding from Sprint 5 — the 3 bugs carried over from Sprint 4
(`engine.py` roce merge + composite placeholder, `cashflow_kpis.py`
cfo_pat_ratio) were fixed on Day 29 and verified throughout Sprint 5's own
work (Day 31/32's capital allocation output depends on the `cashflow_kpis.py`
fix and was cross-validated against it).

**One open item for Sprint 6**: the 10-vs-11 sectors mismatch (see Day 34)
will surface again in Sprint 6 Day 40 (`test_sectors.py`) and Day 45
(Gate AC-14, "peer_percentiles table has data for all 11 peer groups" — peer
groups may be a separate concept from broad_sector, needs checking when we
get there, not assumed to be the same number by coincidence).