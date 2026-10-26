# 🛰️ Amazon Intelligence Suite
### All-in-One E-Commerce SEO, Niche Discovery, Trends & Review Mining Platform

[![Daily Automation](https://github.com/tarikk786786/amazon-intelligence-suite/actions/workflows/daily.yml/badge.svg)](https://github.com/tarikk786786/amazon-intelligence-suite/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Author: Tarik Islam](https://img.shields.io/badge/Crafted%20by-tarikislam.in-purple)](https://tarikislam.in)

**Amazon Intelligence Suite** is a unified, self-hosted, cloud-automated intelligence system that combines and elevates all four tools from [pangolinfoapi](https://github.com/pangolinfoapi) into a single, high-performance monorepo:
1. 📊 **Amazon Keyword Rank Tracker**: Tracks organic vs. sponsored ASIN rankings across Amazon India (`amazon.in`) and global marketplaces.
2. 🌊 **Blue-Ocean Niche Finder**: Discovers low-competition, high-demand niches using real Amazon marketplace data scored by blue-ocean ratio.
3. 📈 **Google Trends Velocity Tracker**: Monitors search interest trajectories, velocity, and sparkline trends across configurable keyword clusters.
4. 💬 **Customer Review & Sentiment Analyzer**: Mines review themes, extracts top complaints and praise, and measures sentiment health.
5. 🤖 **Gemini AI Daily Brief**: Synthesizes the daily findings into an executive 3-sentence summary and 3 actionable seller recommendations.

---

## 🏛️ Architecture & Directory Layout

```
amazon-intelligence-suite/
│
├── .github/
│   └── workflows/
│       └── daily.yml             # Cloud runner executing daily at 00:30 UTC (06:00 AM IST)
│
├── core/
│   ├── mcp_client.py             # Streamable-HTTP JSON-RPC client for Pangolinfo MCP
│   ├── db.py                     # Unified SQLite database layer (WAL mode)
│   └── gemini.py                 # Zero-dependency Google Gemini API client
│
├── tools/
│   ├── rank_tracker.py           # Tool 1: Amazon Keyword Rank Tracker
│   ├── niche_finder.py           # Tool 2: Blue-Ocean Niche Finder
│   ├── trends_tracker.py         # Tool 3: Google Trends Tracker
│   └── review_analyzer.py        # Tool 4: Amazon Review Sentiment Analyzer
│
├── config/
│   ├── targets.json              # Configured ASINs, keywords & marketplaces
│   ├── niches.json               # Niche filters, minimum volume & price ranges
│   ├── keywords.json             # Google Trends clusters & geographical regions
│   └── reviews.json              # Products monitored for customer sentiment
│
├── data/                         # Persistent intelligence database & CSV exports
│   ├── suite.db                  # Unified SQLite database
│   ├── ranks.csv                 # Exported historical keyword ranks
│   └── opportunities.csv         # Exported top blue-ocean niches
│
├── reports/                      # Daily markdown digests and historical reports
│   ├── latest.md                 # Daily unified executive report
│   ├── ranks/                    # Rank tracker breakdowns
│   ├── niches/                   # Niche finder reports
│   ├── trends/                   # Google Trends reports
│   └── reviews/                  # Review sentiment summaries
│
├── main.py                       # Master orchestrator & runner
├── appinfo11.txt                 # Centralized configuration & credential record
├── requirements.txt              # Standard library only (zero required external deps)
└── README.md                     # Documentation
```

---

## 🚀 Key Advantages Over Original Repositories

| Dimension | Original pangolinfoapi Repos | Amazon Intelligence Suite |
|---|---|---|
| **Repository Structure** | 4 fragmented repositories | **1 unified monorepo** with shared data and models |
| **Marketplace Focus** | US only (`amazon.com`) | **Amazon India default** (`amazon.in`, `A21TJRUUN4KGV`, INR) + Global support |
| **Database Architecture** | 4 disconnected SQLite files | **1 central SQLite DB** (`data/suite.db`) linking all metrics |
| **Automation** | 4 separate cron jobs running at different times | **1 synchronized daily pipeline** producing a unified digest |
| **AI Intelligence** | None (Raw data only) | **Google Gemini AI** executive synthesis & strategic action plan |
| **Competitor Tracking** | No competitor labeling | **Side-by-side ASIN vs. competitor benchmarking** |
| **Dependencies** | Python standard library | **Python standard library (Zero third-party pip dependencies required)** |

---

## ⚙️ Configuration & Environment Variables

All credentials are documented in [appinfo11.txt](file:///c:/Users/tarik/Downloads/Leads/amazon-intelligence-suite/appinfo11.txt):

| Variable | Description | Required? |
|---|---|---|
| `PANGOLIN_TOKEN` | Free Pangolinfo MCP API token ([tool.pangolinfo.com](https://tool.pangolinfo.com)) | Required for live data |
| `GEMINI_API_KEY` | Google AI Studio developer API key for AI briefs | Recommended |
| `PANGOLIN_MCP_URL` | Pangolinfo MCP endpoint (Default: `https://mcp.pangolinfo.com/mcp`) | Optional |

---

## 💻 Local Usage & Commands

Run any tool individually or trigger the complete suite:

```bash
# 1. Run the entire master suite (all 4 tools + AI brief + daily digest)
python main.py run

# 2. Re-generate the daily digest report without re-fetching
python main.py digest

# 3. Run individual tools on demand
python tools/rank_tracker.py run
python tools/niche_finder.py run
python tools/trends_tracker.py run
python tools/review_analyzer.py run
```

---

## ☁️ GitHub Actions Automated Setup

1. Push this repository to GitHub under your account (`tarikk786786/amazon-intelligence-suite`).
2. Navigate to **Settings → Secrets and variables → Actions**.
3. Add two Repository Secrets:
   - `PANGOLIN_TOKEN` = `<your token from tool.pangolinfo.com>`
   - `GEMINI_API_KEY` = `<your Google Gemini API key>`
4. Go to **Actions** tab → Enable workflows → Click **Run workflow** to test immediately.
5. The suite will run **every morning at 06:00 AM IST (00:30 UTC)** on autopilot and auto-commit fresh data and markdown reports!

---

## 📄 License & Attribution

- Built and crafted with ❤️ by **[Tarik Islam](https://tarikislam.in)**.
- Data powered by the **Pangolinfo MCP API** & **Google Gemini AI**.
- Released under the **MIT License**.
