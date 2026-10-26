#!/usr/bin/env python3
"""Amazon Review Analyzer - Voice of Customer & Sentiment Mining.
Mines sentiment, extracts complaint/praise themes, and computes rating health.
Enhanced with Gemini AI root cause analysis.
Part of the Amazon Intelligence Suite by Tarik Islam (github.com/tarikk786786).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.db import get_db
from core.gemini import generate_insight
from core.mcp_client import McpClient, McpError

CONFIG_FILE = ROOT / "config" / "reviews.json"
EXAMPLE_FILE = ROOT / "config" / "reviews.example.json"
REPORTS_DIR = ROOT / "reports" / "reviews"

# Lexicons for pure-Python sentiment extraction
STOP_WORDS = {
    "the", "and", "a", "to", "of", "in", "it", "is", "i", "that", "this", "for",
    "you", "with", "on", "was", "my", "as", "have", "not", "but", "be", "they",
    "at", "are", "from", "so", "very", "an", "good", "product", "amazon"
}

COMPLAINT_SIGNALS = {
    "broken", "defect", "poor", "terrible", "waste", "horrible", "cheap",
    "bad", "stopped", "failed", "broke", "worst", "scam", "damaged", "return",
    "useless", "slow", "noise", "overheat", "dissatisfied", "disappointed"
}

PRAISE_SIGNALS = {
    "great", "excellent", "love", "awesome", "perfect", "best", "recommend",
    "worth", "durable", "sturdy", "fast", "impressive", "quality", "clean",
    "solid", "comfortable", "value", "easy", "fantastic", "amazing"
}


def analyze_lexicon(text: str) -> tuple[int, list[str], list[str]]:
    tokens = re.findall(r"[a-z]+", text.lower())
    complaints, praise = [], []
    score = 0
    for t in tokens:
        if t in COMPLAINT_SIGNALS:
            score -= 1
            complaints.append(t)
        elif t in PRAISE_SIGNALS:
            score += 1
            praise.append(t)
    return score, complaints, praise


def cmd_run(delay: float = 2.0) -> list[dict]:
    if not CONFIG_FILE.exists():
        if EXAMPLE_FILE.exists():
            CONFIG_FILE.write_text(EXAMPLE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            sys.exit(f"Reviews config missing: {CONFIG_FILE}")

    targets = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    client = McpClient()
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today = datetime.now(timezone.utc).date().isoformat()
    results = []

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💬 Mining Customer Sentiment & Reviews for {len(targets)} ASINs...")

    for item in targets:
        asin = item.get("asin", "").strip().upper()
        label = item.get("label", asin)
        pages = int(item.get("pages", 2))
        domain = item.get("domain", "www.amazon.in")

        if not asin:
            continue

        try:
            payload = client.call_tool("get_amazon_reviews", {
                "asin": asin,
                "pages": pages,
                "domain": domain
            })
        except McpError as exc:
            print(f"  ! Review fetch error for {label} ({asin}): {exc}")
            time.sleep(delay)
            continue

        reviews = payload.get("reviews") or payload.get("data", {}).get("reviews", [])
        if not reviews and isinstance(payload, list):
            reviews = payload

        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        pos, neu, neg = 0, 0, 0
        all_complaints = []
        all_praise = []
        ratings = []

        for r in reviews:
            rate = r.get("rating") or r.get("stars")
            try:
                rate_val = int(float(rate))
                if 1 <= rate_val <= 5:
                    dist[rate_val] += 1
                    ratings.append(rate_val)
            except (TypeError, ValueError):
                pass

            body = (r.get("text") or r.get("review") or r.get("title") or "")
            score, comp_words, praise_words = analyze_lexicon(body)
            all_complaints.extend(comp_words)
            all_praise.extend(praise_words)

            if score > 0:
                pos += 1
            elif score < 0:
                neg += 1
            else:
                neu += 1

        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
        top_complaints = [w for w, _ in Counter(all_complaints).most_common(5)]
        top_praise = [w for w, _ in Counter(all_praise).most_common(5)]

        row = {
            "asin": asin,
            "label": label,
            "captured_at": now,
            "review_count": len(reviews),
            "avg_rating": avg_rating,
            "rating_1": dist[1],
            "rating_2": dist[2],
            "rating_3": dist[3],
            "rating_4": dist[4],
            "rating_5": dist[5],
            "pos_count": pos,
            "neu_count": neu,
            "neg_count": neg,
            "top_complaints": json.dumps(top_complaints),
            "top_praise": json.dumps(top_praise),
            "first_seen_at": now,
            "last_seen_at": now
        }

        conn.execute("""
            INSERT INTO review_stats
            (asin, label, captured_at, review_count, avg_rating, rating_1, rating_2, rating_3,
             rating_4, rating_5, pos_count, neu_count, neg_count, top_complaints, top_praise,
             first_seen_at, last_seen_at)
            VALUES (:asin, :label, :captured_at, :review_count, :avg_rating, :rating_1, :rating_2,
                    :rating_3, :rating_4, :rating_5, :pos_count, :neu_count, :neg_count,
                    :top_complaints, :top_praise, :first_seen_at, :last_seen_at)
            ON CONFLICT(asin) DO UPDATE SET
              label=excluded.label,
              captured_at=excluded.captured_at,
              review_count=excluded.review_count,
              avg_rating=excluded.avg_rating,
              rating_1=excluded.rating_1, rating_2=excluded.rating_2, rating_3=excluded.rating_3,
              rating_4=excluded.rating_4, rating_5=excluded.rating_5,
              pos_count=excluded.pos_count, neu_count=excluded.neu_count, neg_count=excluded.neg_count,
              top_complaints=excluded.top_complaints, top_praise=excluded.top_praise,
              last_seen_at=excluded.last_seen_at
        """, row)

        neg_ratio = round(neg / len(reviews), 2) if reviews else 0.0
        conn.execute("""
            INSERT OR REPLACE INTO review_history (asin, captured_date, avg_rating, neg_ratio)
            VALUES (?, ?, ?, ?)
        """, (asin, today, avg_rating, neg_ratio))

        conn.commit()
        results.append(row)
        print(f"  • {label} ({asin}): {len(reviews)} reviews | ⭐ {avg_rating} | Pos:{pos} Neu:{neu} Neg:{neg}")
        time.sleep(delay)

    print("✅ Review analysis completed!")
    return results


def cmd_report() -> str:
    conn = get_db()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()

    stats = conn.execute("""
        SELECT asin, label, review_count, avg_rating, pos_count, neu_count, neg_count, top_complaints, top_praise
        FROM review_stats ORDER BY avg_rating DESC
    """).fetchall()

    lines = [
        f"# Amazon Customer Sentiment & Reviews Analysis - {today}",
        "",
        "Generated by **Amazon Intelligence Suite** (Crafted by [tarikislam.in](https://tarikislam.in)).",
        "",
        "## Product Voice of Customer Summary",
        "",
        "| Product / Label | ASIN | Avg Rating | Reviews | Sentiment (Pos/Neu/Neg) | Key Complaints | Top Praises |",
        "|---|---|---|---|---|---|---|",
    ]

    for asin, label, count, avg_r, pos, neu, neg, comp, praise in stats:
        c_words = ", ".join(json.loads(comp or "[]")) or "None detected"
        p_words = ", ".join(json.loads(praise or "[]")) or "None detected"
        lines.append(f"| **{label}** | `{asin}` | ⭐ **{avg_r}** | {count} | 🟢{pos} / ⚪{neu} / 🔴{neg} | *{c_words}* | *{p_words}* |")

    report_content = "\n".join(lines) + "\n"
    (REPORTS_DIR / f"{today}.md").write_text(report_content, encoding="utf-8")
    (REPORTS_DIR / "latest.md").write_text(report_content, encoding="utf-8")
    return report_content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon Review Analyzer")
    parser.add_argument("command", choices=["run", "report"], nargs="?", default="run")
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args.delay)
        cmd_report()
    elif args.command == "report":
        print(cmd_report())
