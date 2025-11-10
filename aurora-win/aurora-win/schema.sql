-- Aurora metrics.db initial schema
-- SQLite DDL
-- Run: sqlite3 data/metrics.db < schema.sql

PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

-- ============= raw events (immutable) =============
CREATE TABLE IF NOT EXISTS events_raw (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,                 -- unix epoch seconds (UTC)
  type TEXT NOT NULL,               -- task|tool|policy|consent|error|bandit|rag
  session_id TEXT,
  user TEXT,
  intent TEXT,
  plan_id TEXT,
  tool TEXT,
  outcome TEXT,                     -- success|blocked|error
  latency_ms INTEGER,
  err_code TEXT,
  risk TEXT,                        -- low|medium|high
  evidences INTEGER DEFAULT 0,      -- RAG evidence count
  args_hash TEXT                    -- sha256 of input args (PII-safe)
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events_raw(ts);
CREATE INDEX IF NOT EXISTS idx_events_type ON events_raw(type);
CREATE INDEX IF NOT EXISTS idx_events_tool ON events_raw(tool);
CREATE INDEX IF NOT EXISTS idx_events_outcome ON events_raw(outcome);

-- ============= consent events =============
CREATE TABLE IF NOT EXISTS consent (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  session_id TEXT,
  action TEXT,           -- e.g., mail.send
  decision TEXT,         -- approved|denied|expired
  risk TEXT,
  ttl_hours INTEGER
);
CREATE INDEX IF NOT EXISTS idx_consent_ts ON consent(ts);

-- ============= error summary =============
CREATE TABLE IF NOT EXISTS errors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  tool TEXT,
  err_code TEXT,
  message TEXT
);
CREATE INDEX IF NOT EXISTS idx_errors_ts ON errors(ts);

-- ============= bandit analytics =============
CREATE TABLE IF NOT EXISTS bandit (
  ts REAL PRIMARY KEY,   -- bucketed timestamp (e.g., per hour)
  avg_reward REAL
);

CREATE TABLE IF NOT EXISTS bandit_weights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  tool TEXT NOT NULL,
  weight REAL
);
CREATE INDEX IF NOT EXISTS idx_bandit_w_ts ON bandit_weights(ts);
CREATE INDEX IF NOT EXISTS idx_bandit_w_tool ON bandit_weights(tool);

-- ============= RAG hits =============
CREATE TABLE IF NOT EXISTS rag_hits (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  doc TEXT,
  chunk_idx INTEGER
);
CREATE INDEX IF NOT EXISTS idx_rag_hits_ts ON rag_hits(ts);

-- ============= rollups =============
CREATE TABLE IF NOT EXISTS rollup_1m (
  bucket REAL PRIMARY KEY,         -- floor(ts/60)*60
  success_cnt INTEGER,
  blocked_cnt INTEGER,
  error_cnt INTEGER,
  p95_latency INTEGER
);

CREATE TABLE IF NOT EXISTS rollup_5m (
  bucket REAL PRIMARY KEY,
  success_cnt INTEGER,
  blocked_cnt INTEGER,
  error_cnt INTEGER,
  p95_latency INTEGER
);

CREATE TABLE IF NOT EXISTS rollup_1h (
  bucket REAL PRIMARY KEY,
  success_cnt INTEGER,
  blocked_cnt INTEGER,
  error_cnt INTEGER,
  p95_latency INTEGER
);

-- ============= seed views (optional) =============
CREATE VIEW IF NOT EXISTS v_events_last_1h AS
SELECT * FROM events_raw WHERE ts >= (strftime('%s','now') - 3600);

-- ============= pragmas post =============
PRAGMA optimize;
