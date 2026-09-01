# Quick diagnostic -- To address [WARNING] findings of smoke test in presets.py 
# this to see WHERE each preset's companies are dropping out..

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src" / "screener"))

from presets import load_universe   #type:ignore
df = load_universe()

# 1. Value Pick (2) and Debt-Free Blue Chip (2) -- both far below the 5-50 range. 
# Before assuming the thresholds are "just tight" 
# verify whether this is a genuine business finding or a data-availability problem...
print("Total companies in universe:", len(df))
print("Non-null pe_ratio:", df["pe_ratio"].notna().sum())
print("Non-null pb_ratio:", df["pb_ratio"].notna().sum())
print("Non-null dividend_yield_pct:", df["dividend_yield_pct"].notna().sum())
print()
print("D/E == 0 exactly:", (df["debt_to_equity"] == 0).sum())

print("="*60)

# This tells us which 3 companies qualify on D/E alone, 
# so we can see exactly which one the ROE>12% or Revenue>5000cr filters are additionally excluding
exact_zero = df[df["debt_to_equity"] == 0]
print("Companies with D/E exactly 0:")
print(exact_zero[["company_id", "debt_to_equity", "return_on_equity_pct", "sales"]])

print("="*60)

# On the near-zero-vs-exact-zero D/E question -- worth checking too, since it's a separate, valid concern:
near_zero = df[(df["debt_to_equity"] >= 0) & (df["debt_to_equity"] < 0.05)]
print("\nCompanies with D/E between 0 and 0.05 (near-zero but not exactly 0):")
print(near_zero[["company_id", "debt_to_equity"]])