// Amazon Intelligence Suite — Background Service Worker
// Author: Tarik Islam (github.com/tarikk786786 | tarikislam.in)

const MCP_URL = "https://mcp.pangolinfo.com/mcp";
const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36";

chrome.runtime.onInstalled.addListener(() => {
  console.log("Amazon Intelligence Suite Extension Installed!");
  // Set default config if empty
  chrome.storage.local.get(["geminiApiKey", "defaultMarketplace", "defaultZipcode"], (res) => {
    const defaults = {};
    if (!res.geminiApiKey) {
      defaults.geminiApiKey = "";
    }
    if (!res.defaultMarketplace) {
      defaults.defaultMarketplace = "www.amazon.in";
    }
    if (!res.defaultZipcode) {
      defaults.defaultZipcode = "110001";
    }
    chrome.storage.local.set(defaults);
  });
});

// Helper for Pangolinfo MCP JSON-RPC call
async function callMcpTool(token, toolName, args) {
  if (!token) {
    throw new Error("Pangolinfo Token not configured. Please open extension settings and add your PANGOLIN_TOKEN.");
  }

  // 1. Initialize session
  const initPayload = {
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "amazon-intel-extension", version: "1.0.0" }
    }
  };

  const initRes = await fetch(MCP_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json, text/event-stream",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify(initPayload)
  });

  const sessionId = initRes.headers.get("mcp-session-id");

  // 2. Execute tool
  const toolPayload = {
    jsonrpc: "2.0",
    id: 2,
    method: "tools/call",
    params: { name: toolName, arguments: args }
  };

  const headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "Authorization": `Bearer ${token}`
  };
  if (sessionId) headers["mcp-session-id"] = sessionId;

  const toolRes = await fetch(MCP_URL, {
    method: "POST",
    headers,
    body: JSON.stringify(toolPayload)
  });

  const text = await toolRes.text();
  let json = {};
  for (const line of text.split("\n")) {
    if (line.startsWith("data:")) {
      try {
        json = JSON.parse(line.replace("data:", "").trim());
        break;
      } catch (e) {}
    }
  }
  if (!json.result && text.startsWith("{")) {
    try { json = JSON.parse(text); } catch (e) {}
  }

  const result = json.result || {};
  const contents = result.content || [];
  for (const c of contents) {
    if (c.type === "text") {
      try { return JSON.parse(c.text); } catch (e) {}
    }
  }
  return result;
}

// Helper for Google Gemini API
async function callGemini(apiKey, prompt) {
  if (!apiKey) {
    throw new Error("Gemini API Key missing.");
  }
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.3, maxOutputTokens: 600 }
    })
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`Gemini Error (${resp.status}): ${err.slice(0, 150)}`);
  }

  const data = await resp.json();
  return data?.candidates?.[0]?.content?.parts?.[0]?.text || "No AI output generated.";
}

// Router for messages from popup & content scripts
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    try {
      const storage = await chrome.storage.local.get(["pangolinToken", "geminiApiKey", "defaultMarketplace", "defaultZipcode"]);
      const token = storage.pangolinToken || "";
      const apiKey = storage.geminiApiKey || "";

      switch (msg.action) {
        case "CHECK_RANK": {
          const res = await callMcpTool(token, "search_amazon", {
            keyword: msg.keyword,
            page: msg.page || 1,
            domain: msg.domain || storage.defaultMarketplace || "www.amazon.in",
            zipcode: msg.zipcode || storage.defaultZipcode || "110001"
          });
          sendResponse({ success: true, data: res });
          break;
        }

        case "FILTER_NICHES": {
          const res = await callMcpTool(token, "filter_niches", msg.params || {
            marketplace_id: "A21TJRUUN4KGV",
            search_volume_t90_min: 2500,
            sort_field: "searchVolumeT90",
            sort_order: "desc"
          });
          sendResponse({ success: true, data: res });
          break;
        }

        case "GET_TRENDS": {
          const res = await callMcpTool(token, "keyword_trends", {
            keywords: msg.keywords,
            region: msg.region || "IN",
            time_range: msg.time_range || "today 3-m",
            language: msg.language || "en-IN"
          });
          sendResponse({ success: true, data: res });
          break;
        }

        case "GET_REVIEWS": {
          const res = await callMcpTool(token, "get_amazon_reviews", {
            asin: msg.asin,
            pages: msg.pages || 2,
            domain: msg.domain || storage.defaultMarketplace || "www.amazon.in"
          });
          sendResponse({ success: true, data: res });
          break;
        }

        case "GEMINI_INSIGHT": {
          const answer = await callGemini(apiKey, msg.prompt);
          sendResponse({ success: true, insight: answer });
          break;
        }

        case "GET_SETTINGS": {
          sendResponse({ success: true, settings: storage });
          break;
        }

        default:
          sendResponse({ success: false, error: "Unknown action" });
      }
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
  })();
  return true; // Keep sendResponse async channel open
});
