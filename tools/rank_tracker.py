#!/usr/bin/env python3
"""Amazon Keyword Rank Tracker - Enhanced for Amazon India & Global Marketplaces.
Part of the Amazon Intelligence Suite by Tarik Islam (github.com/tarikk786786).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
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
from core.mcp_client import McpClient, McpError

CONFIG_FILE = ROOT / "config" / "targets.json"
EXAMPLE_FILE = ROOT / "config" / "targets.example.json"
CSV_FILE = ROOT / "data" / "ranks.csv"
REPORTS_DIR = ROOT / "reports" / "ranks"


def _find_results_container(node, depth: int = 0) -> dict | None:
    if depth > 6:
        return None
    if isinstance(node, dict):
        results = node.get("results")
        if isinstance(results, list) and results and isinstance(results[0], dict) and "asin" in results[0]:
            return node
        for value in node.values():
            found = _find_results_container(value, depth + 1)
            if found:
                return found
    if isinstance(node, list):
        for value in node:
            found = _find_results_container(value, depth + 1)
            if found:
                return found
    return None


def search_amazon_page(client: McpClient, keyword: str, page: int, domain: str = "www.amazon.in", zipcode: str = "110001") -> tuple[list[dict], dict]:
    payload = client.call_tool("search_amazon", {
        "keyword": keyword,
        "page": page,
        "domain": domain,
        "zipcode": zipcode
    })
    container = _find_results_container(payload)
    if not container:
        return [], {}
    return container.get("results", []), container


def item_rank(item: dict, fallback: int) -> int:
    try:
        return int(item.get("rank"))
    except (TypeError, ValueError):
        return fallback


def item_sponsored(item: dict) -> bool:
    for key in ("sponsored", "is_sponsored", "isSponsored", "ad", "is_ad"):
        if item.get(key) in (True, 1, "1", "true", "True"):
            return True
    badge = str(item.get("badge", "") or item.get("label", "")).lower()
    return "sponsored" in badge


def item_text(item: dict, *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def locate_asin(items: list[dict], target_asin: str) -> dict | None:
    organic_counter = 0
    for index, item in enumerate(items, start=1):
        sponsored = item_sponsored(item)
        if not sponsored:
            organic_counter += 1
        if str(item.get("asin", "")).strip().upper() == target_asin.strip().upper():
            return {
                "position": item_rank(item, index),
                "organic_position": None if sponsored else organic_counter,
                "sponsored": 1 if sponsored else 0,
                "title": item_text(item, "title", "name"),
                "price": item_text(item, "price", "price_text", "display_price"),
                "rating": item_text(item, "rating", "star", "stars", "score"),
            }
    return None


def cmd_run(delay: float = 2.0) -> list[dict]:
    if not CONFIG_FILE.exists():
        if EXAMPLE_FILE.exists():
            CONFIG_FILE.write_text(EXAMPLE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            sys.exit(f"Target config missing: {CONFIG_FILE}")

    targets = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    client = McpClient()
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results = []

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Starting Keyword Rank Check across {len(targets)} targets...")

    for target in targets:
        asin = target["asin"].strip().upper()
        domain = target.get("domain", "www.amazon.in")
        zipcode = target.get("zipcode", "110001")
        pages = int(target.get("pages", 2))
        is_competitor = 1 if target.get("is_competitor") else 0

        for keyword in target.get("keywords", []):
            hit = None
            hit_page = None
            scanned = 0
            for page in range(1, pages + 1):
                try:
                    items, _ = search_amazon_page(client, keyword, page, domain, zipcode)
                except McpError as exc:
                    time.sleep(3)
                    try:
                        items, _ = search_amazon_page(client, keyword, page, domain, zipcode)
                    except McpError:
                        break
                scanned = page
                if items:
                    hit = locate_asin(items, asin)
                    if hit:
                        hit_page = page
                        break
                if page < pages:
                    time.sleep(delay)

            row = {
                "checked_at": now,
                "asin": asin,
                "keyword": keyword,
                "domain": domain,
                "zipcode": zipcode,
                "position": hit["position"] if hit else None,
                "organic_position": hit["organic_position"] if hit else None,
                "page": hit_page,
                "sponsored": hit["sponsored"] if hit else 0,
                "title": hit["title"] if hit else None,
                "price": hit["price"] if hit else None,
                "rating": hit["rating"] if hit else None,
                "pages_scanned": scanned,
                "is_competitor": is_competitor
            }
            conn.execute("""
                INSERT INTO rank_checks
                (checked_at, asin, keyword, domain, zipcode, position, organic_position,
                 page, sponsored, title, price, rating, pages_scanned, is_competitor)
                VALUES (:checked_at, :asin, :keyword, :domain, :zipcode, :position,
                        :organic_position, :page, :sponsored, :title, :price, :rating,
                        :pages_scanned, :is_competitor)
            """, row)
            conn.commit()
            results.append(row)

            status = f"Rank {hit['position']} (Page {hit_page})" if hit else f"Not in top {scanned} page(s)"
            print(f"  • {asin} | '{keyword}': {status}")
            time.sleep(delay)

    # Export to CSV
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["checked_at", "asin", "keyword", "domain", "position", "organic_position", "page", "sponsored", "title", "price", "rating", "is_competitor"])
        for r in conn.execute("SELECT checked_at, asin, keyword, domain, position, organic_position, page, sponsored, title, price, rating, is_competitor FROM rank_checks ORDER BY checked_at DESC LIMIT 500"):
            w.writerow(r)

    print(f"✅ Rank check completed! Saved to database and {CSV_FILE}")
    return results


def cmd_report() -> str:
    conn = get_db()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()

    pairs = conn.execute("SELECT DISTINCT asin, keyword, domain FROM rank_checks ORDER BY asin, keyword").fetchall()
    if not pairs:
        return "No rank checks recorded yet."

    lines = [
        f"# Amazon Keyword Rank Intelligence Report - {today}",
        "",
        "Generated by **Amazon Intelligence Suite** (Crafted by [tarikislam.in](https://tarikislam.in)).",
        "",
        "## Latest Rankings & Movements",
        "",
        "| ASIN | Keyword | Market | Latest Rank | Organic | Prev Rank | Delta | 30d Best | 30d Worst |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for asin, keyword, domain in pairs:
        hist = conn.execute("""
            SELECT position, organic_position, checked_at FROM rank_checks
            WHERE asin = ? AND keyword = ? AND domain = ? AND position IS NOT NULL
            ORDER BY checked_at DESC LIMIT 30
        """, (asin, keyword, domain)).fetchall()

        latest = hist[0][0] if hist else None
        latest_org = hist[0][1] if hist and hist[0][1] is not None else "-"
        prev = hist[1][0] if len(hist) > 1 else None

        delta = "-"
        if latest is not None and prev is not None:
            diff = prev - latest
            delta = f"🟢 +{diff}" if diff > 0 else (f"🔴 {diff}" if diff < 0 else "⚪ 0")

        positions = [p[0] for p in hist]
        best = min(positions) if positions else "-"
        worst = max(positions) if positions else "-"

        lines.append(f"| `{asin}` | **{keyword}** | {domain} | {latest or '-'} | {latest_org} | {prev or '-'} | {delta} | {best} | {worst} |")

    report_content = "\n".join(lines) + "\n"
    (REPORTS_DIR / f"{today}.md").write_text(report_content, encoding="utf-8")
    (REPORTS_DIR / "latest.md").write_text(report_content, encoding="utf-8")
    return report_content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon Keyword Rank Tracker")
    parser.add_argument("command", choices=["run", "report", "history"], nargs="?", default="run")
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args.delay)
        cmd_report()
    elif args.command == "report":
        print(cmd_report())
