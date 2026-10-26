#!/usr/bin/env python3
"""Amazon Intelligence Suite - Master Orchestrator & Daily Digest Generator.
Runs all 4 intelligence tools, executes AI synthesis with Google Gemini,
and generates the unified daily intelligence digest.
Author: Tarik Islam (github.com/tarikk786786)
Website: https://tarikislam.in
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.db import get_db
from core.gemini import generate_insight
from tools import niche_finder, rank_tracker, review_analyzer, trends_tracker

REPORTS_DIR = ROOT / "reports"


def run_all_tools(delay: float = 2.0) -> dict:
    print("=" * 70)
    print("🚀 AMAZON INTELLIGENCE SUITE — DAILY MASTER RUN")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()} (UTC)")
    print("=" * 70)

    start_time = time.time()

    # 1. Rank Tracker
    print("\n[1/4] Running Keyword Rank Tracking...")
    try:
        rank_data = rank_tracker.cmd_run(delay=delay)
        rank_tracker.cmd_report()
    except Exception as exc:
        print(f"⚠️ Rank Tracker encountered error: {exc}")
        rank_data = []

    # 2. Niche Finder
    print("\n[2/4] Running Blue-Ocean Niche Scan...")
    try:
        niche_data = niche_finder.cmd_run(delay=delay)
        niche_finder.cmd_report()
    except Exception as exc:
        print(f"⚠️ Niche Finder encountered error: {exc}")
        niche_data = []

    # 3. Google Trends
    print("\n[3/4] Running Google Trends Momentum Tracking...")
    try:
        trends_data = trends_tracker.cmd_run(delay=delay)
        trends_tracker.cmd_report()
    except Exception as exc:
        print(f"⚠️ Trends Tracker encountered error: {exc}")
        trends_data = []

    # 4. Review Analyzer
    print("\n[4/4] Running Customer Review & Sentiment Mining...")
    try:
        review_data = review_analyzer.cmd_run(delay=delay)
        review_analyzer.cmd_report()
    except Exception as exc:
        print(f"⚠️ Review Analyzer encountered error: {exc}")
        review_data = []

    # Generate Unified Digest + AI Brief
    print("\n🧠 Generating Unified Intelligence Digest & Gemini AI Brief...")
    digest = generate_unified_digest()

    elapsed = round(time.time() - start_time, 1)
    print(f"\n🎉 ALL SYSTEMS COMPLETED in {elapsed}s! Report written to reports/latest.md")
    return {
        "rank_checks": len(rank_data),
        "niches": len(niche_data),
        "trends": len(trends_data),
        "reviews": len(review_data),
        "elapsed_seconds": elapsed
    }


def generate_unified_digest() -> str:
    conn = get_db()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()

    # Fetch snapshot metrics
    rank_count = conn.execute("SELECT COUNT(*) FROM rank_checks").fetchone()[0]
    opp_count = conn.execute("SELECT COUNT(*) FROM niches WHERE is_opportunity = 1").fetchone()[0]
    rising_trends = conn.execute("SELECT COUNT(*) FROM trends WHERE trend_direction = 'RISING'").fetchone()[0]
    avg_score = conn.execute("SELECT ROUND(AVG(avg_rating), 2) FROM review_stats").fetchone()[0] or 0.0

    # Fetch top ranked targets
    top_ranks = conn.execute("""
        SELECT asin, keyword, domain, position, organic_position, sponsored
        FROM rank_checks ORDER BY checked_at DESC LIMIT 10
    """).fetchall()

    # Fetch top blue ocean niches
    top_niches = conn.execute("""
        SELECT niche_title, marketplace_id, search_volume_t90, brand_count, score, minimum_price, maximum_price
        FROM niches WHERE is_opportunity = 1 ORDER BY score DESC LIMIT 5
    """).fetchall()

    # Fetch rising trends
    top_trends = conn.execute("""
        SELECT keyword, region, average_interest, latest_interest, trend_direction
        FROM trends ORDER BY latest_interest DESC LIMIT 5
    """).fetchall()

    # Synthesize AI Brief prompt
    ai_prompt = f"""
You are an expert Amazon seller strategist and E-Commerce growth consultant.
Analyze today's ({today}) marketplace scan metrics and provide:
1. Executive Brief: A concise 3-sentence summary of opportunities, risks, and ranking shifts.
2. Action Recommendations: 3 specific, high-priority actions for the seller today.

Data points:
- Total keywords checked: {rank_count}
- High-demand Blue-Ocean niches spotted: {opp_count}
- Rising Google search trends: {rising_trends}
- Average product portfolio rating: {avg_score} / 5.0
- Recent niches: {[t[0] for t in top_niches[:3]]}
- Top trending keywords: {[t[0] for t in top_trends[:3]]}
"""
    ai_summary = generate_insight(ai_prompt)

    # Save to ai_insights
    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO ai_insights (insight_date, summary, action_items, created_at)
        VALUES (?, ?, ?, ?)
    """, (today, ai_summary, "", now_iso))
    conn.commit()

    # Build Markdown
    lines = [
        f"# 🛰️ Amazon Intelligence Suite — Unified Daily Digest",
        f"**Date:** {today} | **Author:** [Tarik Islam](https://tarikislam.in) | **GitHub:** [@tarikk786786](https://github.com/tarikk786786)",
        "",
        "> Automated daily intelligence covering Amazon Keyword Rankings, Blue-Ocean Niches, Google Trends, and Customer Voice of Customer sentiment.",
        "",
        "## 🤖 Gemini AI Executive Brief",
        "",
        ai_summary,
        "",
        "---",
        "",
        "## 📊 KPI Dashboard Snapshot",
        "",
        f"- 🎯 **Tracked Keywords Scanned:** `{rank_count}`",
        f"- 💎 **Blue-Ocean Niches Identified:** `{opp_count}`",
        f"- 🚀 **Rising Search Trends:** `{rising_trends}`",
        f"- ⭐ **Portfolio Average Rating:** `{avg_score} / 5.0`",
        "",
        "---",
        "",
        "## 🔍 Latest Keyword Rankings",
        "",
        "| ASIN | Keyword | Market | Total Rank | Organic Rank | Type |",
        "|---|---|---|---|---|---|",
    ]

    for asin, kw, domain, pos, org, spon in top_ranks:
        t_type = "📢 Sponsored" if spon else "🌿 Organic"
        lines.append(f"| `{asin}` | **{kw}** | {domain} | {pos or '-'} | {org or '-'} | {t_type} |")

    lines += [
        "",
        "---",
        "",
        "## 🌊 Top Blue-Ocean Niche Opportunities",
        "",
        "| Niche Title | Market | Search Vol (90d) | Brands | Opportunity Score | Price Range |",
        "|---|---|---|---|---|---|",
    ]

    for title, market, sv, brands, score, min_p, max_p in top_niches:
        curr = "₹" if market == "A21TJRUUN4KGV" else "$"
        lines.append(f"| **{title}** | `{market}` | {sv:,} | {brands} | **`{score}`** | {curr}{int(min_p or 0)} - {curr}{int(max_p or 0)} |")

    lines += [
        "",
        "---",
        "",
        "## 📈 High-Momentum Google Trends",
        "",
        "| Keyword | Region | Average Interest | Latest Interest | Velocity |",
        "|---|---|---|---|---|",
    ]

    for kw, reg, avg_i, latest_i, direct in top_trends:
        lines.append(f"| **{kw}** | {reg} | {avg_i} | {latest_i} | **{direct}** |")

    lines += [
        "",
        "---",
        "*Automated report generated by [Amazon Intelligence Suite](https://github.com/tarikk786786/amazon-intelligence-suite) · Powered by Pangolinfo & Google Gemini AI.*"
    ]

    digest_content = "\n".join(lines) + "\n"
    (REPORTS_DIR / f"{today}.md").write_text(digest_content, encoding="utf-8")
    (REPORTS_DIR / "latest.md").write_text(digest_content, encoding="utf-8")
    return digest_content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon Intelligence Suite Master Runner")
    parser.add_argument("command", choices=["run", "digest"], nargs="?", default="run")
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    if args.command == "run":
        run_all_tools(args.delay)
    elif args.command == "digest":
        print(generate_unified_digest())
