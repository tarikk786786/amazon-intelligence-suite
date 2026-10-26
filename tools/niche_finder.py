#!/usr/bin/env python3
"""Amazon Blue-Ocean Niche Finder - Opportunity Discovery.
Discovers high-demand, low-competition Amazon niches via Pangolinfo filter_niches API.
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

CONFIG_FILE = ROOT / "config" / "niches.json"
EXAMPLE_FILE = ROOT / "config" / "niches.example.json"
CSV_FILE = ROOT / "data" / "opportunities.csv"
REPORTS_DIR = ROOT / "reports" / "niches"

METRIC_FIELDS = [
    ("search_volume_t90", "searchVolumeT90", "search_volume_t90"),
    ("search_volume_t360", "searchVolumeT360", "search_volume_t360"),
    ("minimum_price", "minimumPrice", "minimum_price"),
    ("maximum_price", "maximumPrice", "maximum_price"),
    ("return_rate_t360", "returnRateT360", "return_rate_t360"),
    ("product_count", "productCount", "product_count"),
    ("brand_count", "brandCount", "brand_count"),
    ("selling_partner_count_t360", "sellingPartnerCountT360", "selling_partner_count_t360"),
    ("avg_review_rating", "avgReviewRating", "avg_review_rating"),
    ("avg_best_seller_rank", "avgBestSellerRank", "avg_best_seller_rank"),
    ("avg_review_count", "avgReviewCount", "avg_review_count"),
]


def _looks_like_niche(d: dict) -> bool:
    keys = {k.lower() for k in d.keys()}
    has_id = bool(keys & {"nicheid", "niche_id", "id", "nichetitle", "niche_title", "title"})
    has_metric = bool(keys & {"searchvolume", "search_volume", "searchvolumet90", "searchvolumet360", "price", "minimumprice", "minimum_price"})
    return has_id and has_metric


def _find_niche_list(node, depth: int = 0) -> list:
    if depth > 6 or node is None:
        return []
    if isinstance(node, dict):
        for value in node.values():
            if isinstance(value, list) and value and isinstance(value[0], dict) and _looks_like_niche(value[0]):
                return value
        for value in node.values():
            found = _find_niche_list(value, depth + 1)
            if found:
                return found
    if isinstance(node, list):
        for value in node:
            found = _find_niche_list(value, depth + 1)
            if found:
                return found
    return []


def extract_niche_list(payload: dict) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "results", "niches", "items"):
            v = payload.get(key)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        return _find_niche_list(payload)
    return []


def _get(d: dict, *names):
    low = {k.lower(): v for k, v in d.items()}
    for n in names:
        if n.lower() in low and low[n.lower()] not in (None, ""):
            return low[n.lower()]
    return None


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_niche(item: dict) -> dict:
    out = {
        "niche_id": _get(item, "nicheId", "niche_id", "id"),
        "niche_title": _get(item, "nicheTitle", "niche_title", "title", "name")
    }
    for col, *keys in METRIC_FIELDS:
        out[col] = _num(_get(item, *keys))
    return out


def blue_ocean_score(search_volume: float | None, competition: float | None) -> float:
    demand = search_volume or 0.0
    comp = competition or 0.0
    return round(demand / (comp + 1.0), 2)


def is_opportunity(metrics: dict, opp: dict) -> bool:
    sv = metrics.get("search_volume_t90") or 0
    if opp.get("min_search_volume_t90") and sv < opp["min_search_volume_t90"]:
        return False
    price = metrics.get("minimum_price")
    if opp.get("min_price") is not None and price is not None and price < opp["min_price"]:
        return False
    if opp.get("max_price") is not None and price is not None and price > opp["max_price"]:
        return False
    comp = metrics.get("brand_count") or metrics.get("selling_partner_count_t360") or 0
    if opp.get("max_brand_count") and comp > opp["max_brand_count"]:
        return False
    return True


def cmd_run(delay: float = 2.0) -> list[dict]:
    if not CONFIG_FILE.exists():
        if EXAMPLE_FILE.exists():
            CONFIG_FILE.write_text(EXAMPLE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            sys.exit(f"Niches config missing: {CONFIG_FILE}")

    queries = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    client = McpClient()
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    opportunities = []

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌊 Scanning Blue-Ocean Niches across {len(queries)} queries...")

    for query in queries:
        label = query.get("label", query.get("marketplace_id", "india-niche"))
        marketplace_id = query.get("marketplace_id", "A21TJRUUN4KGV") # India default
        filters = query.get("filters", {})
        opp = query.get("opportunity", {})

        arguments = {"marketplace_id": marketplace_id}
        if filters:
            arguments.update(filters)

        try:
            payload = client.call_tool("filter_niches", arguments)
        except McpError as exc:
            print(f"  ! Niche scan error for {label}: {exc}")
            time.sleep(delay)
            continue

        raw_list = extract_niche_list(payload)
        for item in raw_list:
            n = parse_niche(item)
            if not n.get("niche_id"):
                continue

            score = blue_ocean_score(n.get("search_volume_t90"), n.get("brand_count") or n.get("selling_partner_count_t360"))
            opp_flag = 1 if is_opportunity(n, opp) else 0

            row = {
                "niche_key": f"{marketplace_id}:{n['niche_id']}",
                "query_label": label,
                "marketplace_id": marketplace_id,
                "niche_id": str(n["niche_id"]),
                "niche_title": n.get("niche_title") or "Unnamed Niche",
                "search_volume_t90": n.get("search_volume_t90"),
                "search_volume_t360": n.get("search_volume_t360"),
                "minimum_price": n.get("minimum_price"),
                "maximum_price": n.get("maximum_price"),
                "return_rate_t360": n.get("return_rate_t360"),
                "product_count": n.get("product_count"),
                "brand_count": n.get("brand_count"),
                "selling_partner_count_t360": n.get("selling_partner_count_t360"),
                "avg_review_rating": n.get("avg_review_rating"),
                "avg_best_seller_rank": n.get("avg_best_seller_rank"),
                "avg_review_count": n.get("avg_review_count"),
                "score": score,
                "is_opportunity": opp_flag,
                "first_seen_at": now,
                "last_seen_at": now
            }

            conn.execute("""
                INSERT INTO niches
                (niche_key, query_label, marketplace_id, niche_id, niche_title,
                 search_volume_t90, search_volume_t360, minimum_price, maximum_price,
                 return_rate_t360, product_count, brand_count, selling_partner_count_t360,
                 avg_review_rating, avg_best_seller_rank, avg_review_count,
                 score, is_opportunity, first_seen_at, last_seen_at)
                VALUES (:niche_key, :query_label, :marketplace_id, :niche_id, :niche_title,
                        :search_volume_t90, :search_volume_t360, :minimum_price, :maximum_price,
                        :return_rate_t360, :product_count, :brand_count, :selling_partner_count_t360,
                        :avg_review_rating, :avg_best_seller_rank, :avg_review_count,
                        :score, :is_opportunity, :first_seen_at, :last_seen_at)
                ON CONFLICT(niche_key) DO UPDATE SET
                  niche_title=excluded.niche_title,
                  search_volume_t90=excluded.search_volume_t90,
                  score=excluded.score,
                  is_opportunity=excluded.is_opportunity,
                  last_seen_at=excluded.last_seen_at
            """, row)
            conn.commit()

            if opp_flag:
                opportunities.append(row)
                print(f"  💎 Opportunity: '{row['niche_title']}' (Score: {score}, Vol: {row['search_volume_t90']})")

        time.sleep(delay)

    # Export to CSV
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["niche_id", "title", "marketplace", "search_volume_t90", "brand_count", "price_range", "score", "is_opportunity"])
        for r in conn.execute("SELECT niche_id, niche_title, marketplace_id, search_volume_t90, brand_count, minimum_price || '-' || maximum_price, score, is_opportunity FROM niches ORDER BY score DESC LIMIT 200"):
            w.writerow(r)

    print(f"✅ Niche scan completed! Opportunities exported to {CSV_FILE}")
    return opportunities


def cmd_report() -> str:
    conn = get_db()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()

    opps = conn.execute("""
        SELECT niche_title, marketplace_id, search_volume_t90, brand_count,
               minimum_price, maximum_price, score, avg_review_rating
        FROM niches WHERE is_opportunity = 1 ORDER BY score DESC LIMIT 50
    """).fetchall()

    lines = [
        f"# Amazon Blue-Ocean Niche Report - {today}",
        "",
        "Generated by **Amazon Intelligence Suite** (Crafted by [tarikislam.in](https://tarikislam.in)).",
        "",
        "## Top Scored Opportunities (High Demand / Low Competition)",
        "",
        "| Niche Title | Market | 90d Search Vol | Brands | Price Range | Blue-Ocean Score | Avg Rating |",
        "|---|---|---|---|---|---|---|",
    ]

    for title, market, sv, brands, min_p, max_p, score, rating in opps:
        p_range = f"₹{int(min_p or 0)} - ₹{int(max_p or 0)}" if market == "A21TJRUUN4KGV" else f"${min_p or 0} - ${max_p or 0}"
        lines.append(f"| **{title}** | `{market}` | {sv:,} | {brands} | {p_range} | **`{score}`** | ⭐ {rating or '-'} |")

    report_content = "\n".join(lines) + "\n"
    (REPORTS_DIR / f"{today}.md").write_text(report_content, encoding="utf-8")
    (REPORTS_DIR / "latest.md").write_text(report_content, encoding="utf-8")
    return report_content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon Blue-Ocean Niche Finder")
    parser.add_argument("command", choices=["run", "report"], nargs="?", default="run")
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args.delay)
        cmd_report()
    elif args.command == "report":
        print(cmd_report())
