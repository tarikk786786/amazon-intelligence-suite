# 🛰️ Amazon Intelligence Pro — Chrome Extension (Manifest V3)
### In-Browser Real-Time Amazon Keyword Rank Tracker, Blue-Ocean Niche Finder, Google Trends & Review Sentiment Analyzer

**Author:** [Tarik Islam](https://tarikislam.in) | **GitHub:** [@tarikk786786](https://github.com/tarikk786786)

A Manifest V3 Google Chrome Extension that brings the full power of the [Pangolinfo MCP Suite](https://pangolinfoapi.github.io/) and **Google Gemini AI** directly inside your Chrome browser.

---

## ⚡ How to Install in Chrome ("Load Unpacked")

1. Open Google Chrome.
2. Navigate to `chrome://extensions` in the address bar.
3. Ensure **Developer mode** toggle in the top-right corner is **ON** (enabled).
4. Click the **"Load unpacked"** button in the top-left corner.
5. In the file explorer dialog, select this exact folder:
   ```
   C:\Users\tarik\Downloads\Leads\AmazonIntelligenceExtension
   ```
6. The extension will instantly load with its icon in your extensions toolbar!
7. Click the **Extension Icon** or open **Options (⚙️)** to verify your credentials.

---

## 🛠️ Features Included

1. **🎯 Real-Time Keyword Rank Tracker**:
   - Query live keyword search results on Amazon India (`amazon.in`) and Amazon US.
   - Instantly shows organic position vs. sponsored ad placement.
2. **🌊 Blue-Ocean Niche Finder**:
   - Filter high-demand, low-competition niches using 90-day search volume and brand competition metrics.
3. **📈 Google Trends Velocity**:
   - Check trend trajectory and interest levels for target search terms.
4. **💬 Customer Review Sentiment Miner**:
   - Mines sentiment themes and integrates Google Gemini AI for instant customer feedback summaries.
5. **🌿 In-SERP Live Badges**:
   - Injects real-time organic rank badges (`#1`, `#2`...) and sponsored tags directly over product images on Amazon search pages.
   - Floating Heads-Up Display (HUD) showing SERP composition.

---

## 📁 Directory Structure

```
AmazonIntelligenceExtension/
├── manifest.json            # Chrome Manifest V3 declaration
├── icons/                   # 16px, 32px, 48px, 128px PNG icons
├── popup/                   # Extension popup UI (HTML/CSS/JS)
├── scripts/                 # Service worker background.js & content.js
├── options/                 # Configuration & settings page
├── styles/                  # In-SERP content styling
├── appinfo11.txt            # Centralized configuration & credentials
└── README.md                # Installation and documentation guide
```

---

## 🔑 Credentials Reference

Pre-configured to support your **Google Gemini API Key** (configured in Options).
Add your free **Pangolinfo API Token** in the extension options page from [tool.pangolinfo.com](https://tool.pangolinfo.com).
