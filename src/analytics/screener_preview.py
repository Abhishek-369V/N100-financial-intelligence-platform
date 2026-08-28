# screener_preview.py - to check exit criteria!
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("sqlite:///db/nifty100.db")
ratios = pd.read_sql("SELECT * FROM financial_ratios", engine)

filtered = ratios[(ratios["return_on_equity_pct"] > 15) & (ratios["debt_to_equity"] < 1)]
unique_companies = filtered["company_id"].nunique()

print(f"Companies matching ROE > 15% and D/E < 1: {unique_companies}")
print(f"Exit criteria: 15-50 companies -> {'[SUCCESS] PASS' if 15 <= unique_companies <= 50 else '[ERROR] CHECK'}")
print(filtered["company_id"].unique())


# FINDING: 
# Screener preview (ROE>15%, D/E<1) returned 58 companies vs. exit criteria's expected 15-50 range. 
# Reviewed full company list — dominated by genuinely strong, low-leverage large-caps (TCS, INFY, 
# MARUTI, ASIANPAINT, HDFCLIFE), consistent with Nifty 100's composition skewing toward
# established, low-debt companies. 
# Not adjusted to artificially fit the expected range - treated as a legitimate market-composition finding.