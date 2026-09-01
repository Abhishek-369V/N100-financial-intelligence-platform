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
