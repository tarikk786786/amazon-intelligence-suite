#!/usr/bin/env python3
"""Google Trends Tracker - Automated Keyword Interest Monitoring.
Tracks trend velocity, rising/falling interest over time via Pangolinfo MCP API.
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

CONFIG_FILE = ROOT / "config" / "keywords.json"
EXAMPLE_FILE = ROOT / "config" / "keywords.example.json"
REPORTS_DIR = ROOT / "reports" / "trends"


def sparkline(numbers: list[float | int]) -> str:
    if not numbers:
        return ""
    bars = " ▂▃▄▅▆▇█"
    lo, hi = min(numbers), max(numbers)
    span = hi - lo
    if span == 0:
        return bars[3] * len(numbers)
    return "".join(bars[min(int((n - lo) / span * 7), 7)] for n in numbers)


def cmd_run(delay: float = 2.0) -> list[dict]:
    if not CONFIG_FILE.exists():
        if EXAMPLE_FILE.exists():
            CONFIG_FILE.write_text(EXAMPLE_FILE.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            sys.exit(f"Keywords config missing: {CONFIG_FILE}")

    groups = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    client = McpClient()
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results = []

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 📈 Checking Google Trends across {len(groups)} keyword groups...")

    for group in groups:
        label = group.get("label", "group")
        keywords = group.get("keywords", [])
        region = group.get("region", "IN") # India default
        time_range = group.get("time_range", "today 3-m")
        language = group.get("language", "en-IN")

        if not keywords:
            continue

        arguments = {
            "keywords": keywords,
            "region": region,
            "time_range": time_range,
            "language": language
        }

        try:
            payload = client.call_tool("keyword_trends", arguments)
        except McpError as exc:
            print(f"  ! Google Trends error for {label}: {exc}")
            time.sleep(delay)
            continue

        # Extract trend timelines
        timeline = payload.get("timeline") or payload.get("data", {}).get("timeline", [])
        for kw in keywords:
            points = []
            if isinstance(timeline, list):
                for pt in timeline:
                    val = pt.get(kw) or pt.get("values", {}).get(kw)
                    date_str = pt.get("date") or pt.get("time")
                    if val is not None and date_str:
                        try:
                            points.append((date_str, float(val)))
                        except ValueError:
                            pass

            avg_interest = round(sum(p[1] for p in points) / len(points), 1) if points else 0.0
            latest_interest = points[-1][1] if points else 0.0

            direction = "FLAT"
            if len(points) >= 3:
                recent_avg = sum(p[1] for p in points[-3:]) / 3
                first_avg = sum(p[1] for p in points[:3]) / 3
                if recent_avg > first_avg * 1.15:
                    direction = "RISING"
                elif recent_avg < first_avg * 0.85:
                    direction = "FALLING"

            trend_key = f"{region}:{time_range}:{kw}"
            row = {
                "trend_key": trend_key,
                "label": label,
                "region": region,
                "time_range": time_range,
                "keyword": kw,
                "average_interest": avg_interest,
                "latest_interest": latest_interest,
                "trend_direction": direction,
                "first_seen_at": now,
                "last_seen_at": now
            }

            conn.execute("""
                INSERT INTO trends
                (trend_key, label, region, time_range, keyword, average_interest, latest_interest, trend_direction, first_seen_at, last_seen_at)
                VALUES (:trend_key, :label, :region, :time_range, :keyword, :average_interest, :latest_interest, :trend_direction, :first_seen_at, :last_seen_at)
                ON CONFLICT(trend_key) DO UPDATE SET
                  average_interest=excluded.average_interest,
                  latest_interest=excluded.latest_interest,
                  trend_direction=excluded.trend_direction,
                  last_seen_at=excluded.last_seen_at
            """, row)

            for d, val in points:
                conn.execute("""
                    INSERT OR REPLACE INTO trend_points (trend_key, date, value)
                    VALUES (?, ?, ?)
                """, (trend_key, d, val))

            conn.commit()
            results.append(row)
            dir_icon = "🚀 RISING" if direction == "RISING" else ("📉 FALLING" if direction == "FALLING" else "➡️ STABLE")
            print(f"  • {kw} ({region}): Avg {avg_interest} | Latest {latest_interest} | {dir_icon}")

        time.sleep(delay)

    print("✅ Google Trends update complete!")
    return results


def cmd_report() -> str:
    conn = get_db()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()

    trends_list = conn.execute("""
        SELECT trend_key, label, region, keyword, average_interest, latest_interest, trend_direction
        FROM trends ORDER BY average_interest DESC LIMIT 50
    """).fetchall()

    lines = [
        f"# Google Trends Intelligence Report - {today}",
        "",
        "Generated by **Amazon Intelligence Suite** (Crafted by [tarikislam.in](https://tarikislam.in)).",
        "",
        "## Search Interest Velocity & Momentum",
        "",
        "| Keyword | Category | Region | Avg Interest | Latest | Velocity | Sparkline (Recent) |",
        "|---|---|---|---|---|---|---|",
    ]

    for key, label, region, kw, avg_i, latest_i, direct in trends_list:
        pts = conn.execute("SELECT value FROM trend_points WHERE trend_key = ? ORDER BY date DESC LIMIT 15", (key,)).fetchall()
        vals = [p[0] for p in reversed(pts)]
        spark = sparkline(vals) if vals else "-"
        icon = "🟢 RISING" if direct == "RISING" else ("🔴 FALLING" if direct == "FALLING" else "⚪ FLAT")
        lines.append(f"| **{kw}** | `{label}` | {region} | {avg_i} | {latest_i} | {icon} | `{spark}` |")

    report_content = "\n".join(lines) + "\n"
    (REPORTS_DIR / f"{today}.md").write_text(report_content, encoding="utf-8")
    (REPORTS_DIR / "latest.md").write_text(report_content, encoding="utf-8")
    return report_content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Trends Tracker")
    parser.add_argument("command", choices=["run", "report"], nargs="?", default="run")
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args.delay)
        cmd_report()
    elif args.command == "report":
        print(cmd_report())
