-- Aurora KPI Views (rollup-optimized)
-- Usage: sqlite3 data/metrics.db < kpi_views.sql
-- Note: P95 aggregation across buckets uses a safe upper-bound approximation (MAX of per-bucket p95)

PRAGMA foreign_keys=ON;

-- 1) 1-hour KPI (uses rollup_1m)
CREATE VIEW IF NOT EXISTS v_kpi_1h AS
WITH win AS (
  SELECT * FROM rollup_1m
  WHERE bucket >= (strftime('%s','now') - 3600)
)
SELECT
  SUM(success_cnt) * 1.0 / NULLIF(SUM(success_cnt+blocked_cnt+error_cnt),0) AS success_rate,
  SUM(blocked_cnt) * 1.0 / NULLIF(SUM(success_cnt+blocked_cnt+error_cnt),0) AS blocked_rate,
  MAX(p95_latency) AS p95_latency_upper
FROM win;

-- 2) 24-hour KPI (uses rollup_5m)
CREATE VIEW IF NOT EXISTS v_kpi_24h AS
WITH win AS (
  SELECT * FROM rollup_5m
  WHERE bucket >= (strftime('%s','now') - 86400)
)
SELECT
  SUM(success_cnt) * 1.0 / NULLIF(SUM(success_cnt+blocked_cnt+error_cnt),0) AS success_rate,
  SUM(blocked_cnt) * 1.0 / NULLIF(SUM(success_cnt+blocked_cnt+error_cnt),0) AS blocked_rate,
  MAX(p95_latency) AS p95_latency_upper
FROM win;

-- 3) 7-day KPI (uses rollup_1h)
CREATE VIEW IF NOT EXISTS v_kpi_7d AS
WITH win AS (
  SELECT * FROM rollup_1h
  WHERE bucket >= (strftime('%s','now') - 7*86400)
)
SELECT
  SUM(success_cnt) * 1.0 / NULLIF(SUM(success_cnt+blocked_cnt+error_cnt),0) AS success_rate,
  SUM(blocked_cnt) * 1.0 / NULLIF(SUM(success_cnt+blocked_cnt+error_cnt),0) AS blocked_rate,
  MAX(p95_latency) AS p95_latency_upper
FROM win;

-- 4) Consent timeline (7d window; rollup-friendly via events table optional)
CREATE VIEW IF NOT EXISTS v_consent_7d AS
SELECT datetime(ts,'unixepoch') AS ts_utc,
       action,
       decision,
       risk,
       ttl_hours
FROM consent
WHERE ts >= (strftime('%s','now') - 7*86400)
ORDER BY ts ASC;

-- 5) Consent aggregates (24h)
CREATE VIEW IF NOT EXISTS v_consent_24h_agg AS
SELECT
  SUM(CASE WHEN decision='approved' THEN 1 ELSE 0 END) AS approved,
  SUM(CASE WHEN decision='denied' THEN 1 ELSE 0 END)   AS denied,
  SUM(CASE WHEN decision='expired' THEN 1 ELSE 0 END)  AS expired
FROM consent
WHERE ts >= (strftime('%s','now') - 86400);

-- 6) Error TopN (1h)
CREATE VIEW IF NOT EXISTS v_error_topn_1h AS
SELECT tool, err_code, COUNT(*) AS count
FROM events_raw
WHERE ts >= (strftime('%s','now') - 3600) AND outcome='error'
GROUP BY tool, err_code
ORDER BY count DESC;

PRAGMA optimize;