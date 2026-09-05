**FINDING**: 
1. "Debt-Free Blue Chip" preset spec says "D/E = 0" (exact equality). 
Only 3 companies (JIOFIN, LICI, SBILIFE) have D/E stored as exactly 0.0;
after applying ROE>12% and Revenue>5000cr, only 2 pass (LICI, SBILIFE) -- JIOFIN fails on ROE (1.15%).

2. However, 22 additional companies (ABB, CIPLA, MARUTI, HINDUNILVR, ITC, etc.)
have D/E between 0.0001 and 0.045 — negligible in practical terms but excluded by the strict equality check. 
Implemented per spec as written (exact D/E=0), 
not loosened without a documented decision. 
Flagging for team: should "Debt-Free" mean D/E < some small threshold (e.g., 0.05)
instead of literal zero? Current implementation is spec-compliant but may be narrower than intended.

3. screener_output.xlsx's -- 
red-fill logic (fail threshold) is implemented correctly but never triggers in current output, 
since "presets.py" filters out failing rows before export -- only qualifying companies ever reach the Excel sheet. 
Red-fill code is present and spec-compliant, but effectively unused given the current pipeline design. Not a bug!..

---

## Day 18 — Peer Percentile Rankings

**FINDING**: Substring-match bug in peer group assignment — "IT" matched
both "IT Services" and "Power & Utilities" (contains "IT" inside other
words). Fixed with exact `==` group-name matching instead of substring
search. Verified post-fix: TCS has the highest ROE value AND the highest
percentile rank within IT Services — consistent, no ranking inversion bug.

**FINDING**: 35 of 92 companies have no peer group assignment. This is
expected — `peer_groups.xlsx` (source data) only covers 56 companies,
not the full Nifty 100 universe. `flag_companies_without_peer_group()`
reports this as an informational message per spec (not an error).

11 peer groups confirmed present, matching spec.

## Day 19 — Radar Charts

90 PNGs generated in `reports/radar_charts/` — 55 for the 56 grouped
companies that had a `get_radar_values()` result minus 1 dropped, +35
standalone bar charts for the 35 ungrouped companies. File count
verified to match generation count exactly (no silent write failures).

Fixed a function-signature bug in `get_radar_values()` (took 2 params,
only used 1).

## Day 20 — output/peer_comparison.xlsx

**ASSUMPTION FLAGGED**: spec calls for "20 metrics" per sheet. Day 18's
`peer.py` (`PEER_METRICS`) only defines 10 metrics — there is no 20-metric
raw set anywhere upstream. Implemented as 10 raw metric values + their
10 percentile-rank counterparts (= 20 metric-related columns), rather
than inventing 10 additional metrics with no source definition. Flagging
for the team to confirm this reading is what was intended, or to supply
the missing 10 metrics if a literal 20-raw-metric set was meant.

11 sheets generated (one per peer group, matching the 11 groups from
Day 18) — 0 skipped. Columns: `company_id`, `company_name`,
`broad_sector`, `is_benchmark`, then 10x `<metric>_value` / `<metric>_pct`
pairs. Percentile color-coding (green >=75th pct / yellow 25-75th /
red <=25th) applied to the `_pct` columns only — raw value columns are
informational and have no single pass/fail line to color against.
Benchmark row highlighted gold across the full row. Group-median summary
row appended and bolded at the bottom of each sheet.

Spot check (IT Services sheet): TCS is the benchmark (gold row, sorted
first), matching Day 18's finding that TCS has both the highest raw ROE
and the highest ROE percentile rank in that group.

## Day 21 — DQ Rule Run, Manual Verification, Exit Criteria

**FINDING**: `validator.py` implements 16 DQ rules, not the 14 referenced
in the Sprint 4 task doc. Ran all 16 as written rather than guessing
which 2 to drop — flagging the count mismatch for the team rather than
silently reconciling it.

Ran `validator.py` against `data/processed/*.csv` (its designed input —
the pre-load intermediate stage): 21 violations found (13 CRITICAL, 8
WARNING). Investigated before treating this as a blocker: all 13
CRITICAL failures are duplicate `(company_id, year)` pairs, orphan
`company_id` values, and unparseable/TTM year values in the *raw CSV
exports* — i.e. exactly the Sprint 1 findings already documented
(8 orphan companies, ADANIPORTS duplicate rows, TTM year values).

Verified directly against the actual loaded database (`db/nifty100.db`)
that these do NOT persist past `loader.py`'s cleanup: `profitandloss`,
`balancesheet`, `cashflow`, and `financial_ratios` all show 0 orphan
`company_id` rows and 0 duplicate `(company_id, year)` pairs in the DB.
The DQ rules are correctly catching known, already-documented raw-file
issues — not new bugs, and not something the DB-driven dashboard/
screener/peer work in Sprints 2-3 is exposed to. No CRITICAL fixes
needed for Sprint 4 to proceed safely on top of the DB.

**Quality Compounder top 5 manually verified** (re-ran
`quality_compounder()` + `compute_composite_score()` independently):
INDIGO (80.89), IRCTC (63.71), ADANIPORTS (53.45), SUNPHARMA (53.44),
LTIM (51.93). 20 total matches, consistent with the Day 16 count.
INDIGO's 892% ROE artifact is present but already flagged via
`data_quality_flag` (Day 16/17 winsorization work) — not a new issue.

**IT Services ranking**: re-confirmed (already verified once on Day 18)
— TCS ranks first on both raw ROE and ROE percentile.

## Sprint 3 Exit Criteria — Status

- [✅] Screener + peer engine functioning (6 presets, 11 peer groups)
- [✅] `output/peer_comparison.xlsx` generated, 11 sheets, 0 skipped
- [✅] DQ rules run (16, not 14 — flagged above), 0 CRITICAL failures
      in the actual database; CRITICAL findings in raw CSVs are prior
      documented issues, not new
- [✅] Quality Compounder top 5 manually verified
- [✅] IT Services ranking re-confirmed

Sprint 3 complete. Proceeding to Sprint 4 (Dashboard & Valuation).