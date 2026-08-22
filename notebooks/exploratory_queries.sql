-- ============================================
-- N100 Financial Intelligence Platform
-- Day 7: Exploratory Queries — Sprint 1 Demo
-- ============================================

-- 1. Total companies loaded, confirm exit criteria
SELECT COUNT(*) AS total_companies FROM companies;

-- 2. Companies per broad sector — sanity check sector distribution
SELECT broad_sector, COUNT(*) AS company_count
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC;

-- 3. Top 10 companies by latest net_profit
SELECT p.company_id, c.company_name, p.year, p.net_profit
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
WHERE p.year = (SELECT MAX(year) FROM profitandloss p2 WHERE p2.company_id = p.company_id)
ORDER BY p.net_profit DESC
LIMIT 10;

-- 4. Companies with negative net_profit in their latest reported year
SELECT p.company_id, c.company_name, p.year, p.net_profit
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
WHERE p.year = (SELECT MAX(year) FROM profitandloss p2 WHERE p2.company_id = p.company_id)
  AND p.net_profit < 0;

-- 5. Average ROE by sector (latest year per company)
SELECT s.broad_sector, ROUND(AVG(c.roe_percentage), 2) AS avg_roe
FROM companies c
JOIN sectors s ON c.id = s.company_id
GROUP BY s.broad_sector
ORDER BY avg_roe DESC;

-- 6. Companies with highest debt-to-equity (latest financial_ratios year per company)
SELECT fr.company_id, c.company_name, fr.year, fr.debt_to_equity
FROM financial_ratios fr
JOIN companies c ON fr.company_id = c.id
WHERE fr.year = (SELECT MAX(year) FROM financial_ratios fr2 WHERE fr2.company_id = fr.company_id)
ORDER BY fr.debt_to_equity DESC
LIMIT 10;

-- 7. Stock price range (min/max close) per company over full history
SELECT company_id, MIN(close_price) AS min_close, MAX(close_price) AS max_close,
       ROUND(MAX(close_price) - MIN(close_price), 2) AS price_range
FROM stock_prices
GROUP BY company_id
ORDER BY price_range DESC
LIMIT 10;

-- 8. Companies by market cap category and average PE ratio
SELECT s.market_cap_category, COUNT(DISTINCT mc.company_id) AS company_count,
       ROUND(AVG(mc.pe_ratio), 2) AS avg_pe_ratio
FROM market_cap mc
JOIN sectors s ON mc.company_id = s.company_id
GROUP BY s.market_cap_category
ORDER BY avg_pe_ratio DESC;

-- 9. Peer group membership — companies grouped with their benchmark peer
SELECT pg.peer_group_name, c.company_name, pg.is_benchmark
FROM peer_groups pg
JOIN companies c ON pg.company_id = c.id
ORDER BY pg.peer_group_name, pg.is_benchmark DESC;

-- 10. Balance sheet growth check — total_assets year-over-year change for a sample company
SELECT company_id, year, total_assets,
       total_assets - LAG(total_assets) OVER (PARTITION BY company_id ORDER BY year) AS yoy_asset_change
FROM balancesheet
WHERE company_id = 'RELIANCE'
ORDER BY year;