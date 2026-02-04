-- Basic sanity checks (run in any SQLite client)
-- 1) Row counts
SELECT 'dim_customer' AS table_name, COUNT(*) AS rows FROM dim_customer
UNION ALL
SELECT 'dim_product', COUNT(*) FROM dim_product
UNION ALL
SELECT 'dim_date', COUNT(*) FROM dim_date
UNION ALL
SELECT 'fact_order_line', COUNT(*) FROM fact_order_line;

-- 2) Revenue should be non-negative
SELECT COUNT(*) AS negative_revenue_rows
FROM fact_order_line
WHERE revenue < 0;

-- 3) On-time ship rate (order-level)
WITH order_level AS (
  SELECT
    order_id,
    MAX(is_cancelled) AS is_cancelled,
    MAX(on_time_ship) AS on_time_ship
  FROM fact_order_line
  GROUP BY order_id
)
SELECT
  AVG(CASE WHEN is_cancelled = 0 THEN on_time_ship ELSE NULL END) AS on_time_ship_rate
FROM order_level;

-- 4) Cycle time (delivered only)
WITH order_level AS (
  SELECT
    order_id,
    MAX(is_cancelled) AS is_cancelled,
    AVG(cycle_time_days) AS cycle_time_days
  FROM fact_order_line
  GROUP BY order_id
)
SELECT AVG(cycle_time_days) AS avg_cycle_time_days
FROM order_level
WHERE is_cancelled = 0 AND cycle_time_days IS NOT NULL;
