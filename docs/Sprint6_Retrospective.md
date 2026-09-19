## **DAY 35:**

GAP HANDLING (decided and documented, not silently patched):

1. fcf_cagr_5yr is None for 43/92 companies (Day 31's fcf_cagr() correctly
   returns None when FCF is negative at either end of the window -- CAGR is
   undefined there, not a missing-data bug). Sector-median imputation (as
   the spec asks) works for 9 of 10 sectors, but Communication Services has
   ZERO non-null fcf_cagr_5yr values -- its own sector median is also NaN,
   so sector-median imputation alone would leave those 2 companies
   unimputed. Added a global-median fallback for exactly this case: impute
   with sector median where available, else the portfolio-wide median.
2. SBIN and ATGL are missing from financial_ratios entirely (established
   Day 30/31) -- all 4 financial_ratios-sourced features are NaN for them
   before imputation. Sector-median imputation still resolves this (SBIN's
   Financials-sector median, ATGL's Energy-sector median both have enough
   other companies to compute from), so they still get clustered rather
   than being dropped from the exercise entirely.
3. cluster_name at this stage is a placeholder ("Cluster 0".."Cluster 4"),
   NOT the descriptive name the spec's Day 37 task asks for -- Day 37 is
   explicitly where cluster profiles get reviewed and descriptive names
   assigned based on what's actually in each cluster. Naming them here
   before profiling them would be guessing blind.

## **Day 36:**

GAP HANDLING (decided and documented, not silently patched):

1. Spec says "review cluster names with team lead -- adjust based on which
   actual companies are in each cluster." There is no team lead available
   on this compressed solo schedule. Names below are assigned from the
   actual computed per-cluster medians (not guessed, not forced to match
   the spec's 5 example names where the data doesn't support it), with
   the reasoning for each name spelled out in NAME_REASONING so a real
   reviewer could sanity-check the call later. This is flagged as a
   self-reviewed decision, not represented as team-approved anywhere.
2. Two clusters (2 companies each) are extreme-outlier pairs, not clean
   archetypes: {HAL, BEL} share a ROE in the thousands of percent (near-
   zero equity base), {GAIL, NHPC} share an extreme FCF CAGR from a low
   base effect. Named descriptively as outlier groupings rather than
   forced into one of the spec's 5 example archetype names that don't
   actually fit 2-company extreme clusters.
3. "10 KPIs" for the correlation heatmap / outlier report / portfolio
   stats isn't specified by name. Used the 10 most decision-relevant
   columns already in financial_ratios (profitability, leverage, growth,
   payout) rather than introducing a new derived metric -- consistent with
   reusing existing pipeline outputs everywhere else in this project.