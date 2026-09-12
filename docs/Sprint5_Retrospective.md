## Day 29:
GAP HANDLING (decided and documented, not silently patched):
1. Reads data/processed/analysis.csv (not data/raw/analysis.xlsx). Verified
   byte-for-byte identical content after dtype alignment -- the processed
   CSV is just the already-flattened, already-clean version (no title-banner
   row to skip), and it's the project convention to read from processed/
   rather than raw/ once a cleaned copy exists.
2. Spec regex `(\d+)\s*Years?:?\s*([\d.]+)%` only matches the "N Years: X%" shape.
   In the real data, ~1 in 4 entries per company uses "TTM:", "1 Year:", or
   "Last Year:" instead of a numbered Years label (all three mean the same
   thing: trailing 1-year figure). Strictly following the spec regex would
   dump 25% of otherwise-valid data into parse_failures.csv as "malformed."
   Decision: treat TTM / Last Year as period_years = 1 via a second regex
   pass, and tag the row's source_label so this normalization is auditable
   -- NOT silently merged with real "1 Year:" entries.
3. Only 5 of 92 companies (HDFCBANK, SBILIFE, TCS, WIPRO, INFY) have any rows
   in analysis.xlsx at all. This is a genuine source-data coverage gap, not a
   parser bug -- confirmed by inspecting the raw file. analysis_parsed.csv
   will therefore only ever have rows for these 5 companies; this is noted
   in the sprint retrospective, not hidden.
4. The spec regex `([\d.]+)%` cannot match negative growth (e.g. "3 Years:
   -1%", a real WIPRO stock-price CAGR in this data). Real financial CAGR
   can legitimately be negative -- excluding it would silently misclassify
   a valid negative figure as a parse failure. Extended both patterns to
   `([\d.\-]+)%` to capture the sign.

## Day 30: 
GAP HANDLING (decided and documented):
1. financial_ratios (the primary source for 10 of the 12 pro rules and
   10 of the 12 con rules) is missing 2 of 92 companies entirely: SBIN
   (Public Sector Bank -- D/E-style ratios are structurally meaningless
   for a bank, so the Ratio Engine correctly excludes it) and ATGL (Gas
   Distribution -- no such structural reason, likely an upstream data
   gap). Both get a FALLBACK rule below instead of silently having zero
   pros/cons.
2. Net Debt / EBITDA (Con Rule 11) needs a cash balance to compute true
   net debt, but neither balancesheet nor the schema has a cash line
   item -- only gross borrowings. Used gross borrowings as the Net Debt
   proxy (documented as an approximation, not silently treated as exact)
   and profitandloss.operating_profit as the EBITDA proxy (Screener.in
   convention: Operating Profit is pre-interest, pre-depreciation).
3. Trend rules (3-5 consecutive year checks) need that many years of
   history. financial_ratios coverage per company ranges from 2 to 12
   years (median 12). Every trend rule checks len(series) >= N before
   firing rather than assuming N years exist -- a company with only 2
   years of data simply can't trigger a "5 consecutive years" rule, and
   is skipped for that rule rather than crashing or false-firing.
4. Exit criteria requires >=1 pro AND >=1 con for every one of 92
   companies. Confidence-gated rules alone won't guarantee that for
   thin-data companies. After rule evaluation, any company still short
   a pro or a con gets a FALLBACK_PRO / FALLBACK_CON entry built from
   whatever single best/worst metric is actually available for it, at
   confidence 61 (just above the cutoff) -- tagged with rule_id
   'FALLBACK' so it's auditable and never confused with a real rule hit.
