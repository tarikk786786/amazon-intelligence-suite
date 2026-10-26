#!/usr/bin/env python3
"""Unified Database Layer for Amazon Intelligence Suite.
Manages SQLite storage across rank tracking, niche finding, Google trends, and review analysis.
Author: Tarik Islam (github.com/tarikk786786)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DB_FILE = ROOT / "data" / "suite.db"

SCHEMA = """
-- 1. Keyword Rank Checks
CREATE TABLE IF NOT EXISTS rank_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  checked_at TEXT NOT NULL,
  asin TEXT NOT NULL,
  keyword TEXT NOT NULL,
  domain TEXT NOT NULL,
  zipcode TEXT,
  position INTEGER,
  organic_position INTEGER,
  page INTEGER,
  sponsored INTEGER DEFAULT 0,
  title TEXT,
  price TEXT,
  rating TEXT,
  pages_scanned INTEGER DEFAULT 1,
  is_competitor INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_rank_checks_asin_kw ON rank_checks(asin, keyword, checked_at);

-- 2. Blue-Ocean Niches
CREATE TABLE IF NOT EXISTS niches (
  niche_key TEXT PRIMARY KEY,
  query_label TEXT NOT NULL,
  marketplace_id TEXT NOT NULL,
  niche_id TEXT NOT NULL,
  niche_title TEXT,
  search_volume_t90 INTEGER,
  search_volume_t360 INTEGER,
  minimum_price REAL,
  maximum_price REAL,
  return_rate_t360 REAL,
  product_count INTEGER,
  brand_count INTEGER,
  selling_partner_count_t360 INTEGER,
  avg_review_rating REAL,
  avg_best_seller_rank INTEGER,
  avg_review_count INTEGER,
  score REAL,
  is_opportunity INTEGER DEFAULT 0,
  first_seen_at TEXT,
  last_seen_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_niches_opp ON niches(is_opportunity, score);

-- 3. Google Trends
CREATE TABLE IF NOT EXISTS trends (
  trend_key TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  region TEXT NOT NULL,
  time_range TEXT NOT NULL,
  keyword TEXT NOT NULL,
  average_interest REAL,
  latest_interest REAL,
  trend_direction TEXT,
  first_seen_at TEXT,
  last_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS trend_points (
  trend_key TEXT NOT NULL,
  date TEXT NOT NULL,
  value REAL,
  PRIMARY KEY (trend_key, date)
);

-- 4. Amazon Reviews Analysis
CREATE TABLE IF NOT EXISTS review_stats (
  asin TEXT PRIMARY KEY,
  label TEXT,
  captured_at TEXT NOT NULL,
  review_count INTEGER,
  avg_rating REAL,
  rating_1 INTEGER DEFAULT 0,
  rating_2 INTEGER DEFAULT 0,
  rating_3 INTEGER DEFAULT 0,
  rating_4 INTEGER DEFAULT 0,
  rating_5 INTEGER DEFAULT 0,
  pos_count INTEGER DEFAULT 0,
  neu_count INTEGER DEFAULT 0,
  neg_count INTEGER DEFAULT 0,
  top_complaints TEXT,
  top_praise TEXT,
  first_seen_at TEXT,
  last_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS review_history (
  asin TEXT NOT NULL,
  captured_date TEXT NOT NULL,
  avg_rating REAL,
  neg_ratio REAL,
  PRIMARY KEY (asin, captured_date)
);

-- 5. AI Daily Insights & Summaries
CREATE TABLE IF NOT EXISTS ai_insights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  insight_date TEXT NOT NULL UNIQUE,
  summary TEXT NOT NULL,
  action_items TEXT,
  created_at TEXT NOT NULL
);
"""


def get_db(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = db_path or DB_FILE
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    return conn
