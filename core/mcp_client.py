#!/usr/bin/env python3
"""Unified Pangolinfo MCP Streamable-HTTP Client.

Talks JSON-RPC 2.0 to the Pangolinfo MCP Server (https://mcp.pangolinfo.com/mcp)
Zero external dependencies: uses Python 3.10+ standard library urllib only.
Author: Tarik Islam (github.com/tarikk786786)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

MCP_URL = os.environ.get("PANGOLIN_MCP_URL", "https://mcp.pangolinfo.com/mcp")
MCP_PROTOCOL_VERSION = "2024-11-05"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class McpError(RuntimeError):
    pass


class McpClient:
    """Talks JSON-RPC to the Pangolinfo MCP server over streamable-HTTP."""

    def __init__(self, token: Optional[str] = None, url: str = MCP_URL, timeout: int = 90) -> None:
        self.token = token or os.environ.get("PANGOLIN_TOKEN") or os.environ.get("PANGOLINFO_API_KEY", "")
        self.url = url
        self.timeout = timeout
        self.session_id: Optional[str] = None
        self._next_id = 0
        self._initialized = False

    def _post(self, payload: dict) -> dict:
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        req.add_header("User-Agent", USER_AGENT)
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        if self.session_id:
            req.add_header("mcp-session-id", self.session_id)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                sid = resp.headers.get("mcp-session-id")
                if sid:
                    self.session_id = sid
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", "replace")[:300]
            raise McpError(f"HTTP {exc.code} from MCP server: {err_body}") from exc
        except urllib.error.URLError as exc:
            raise McpError(f"MCP server unreachable: {exc}") from exc

        if not raw.strip():
            return {}

        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                try:
                    return json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw_text": raw}

    def initialize(self) -> None:
        self._next_id += 1
        self._post({
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "amazon-intelligence-suite", "version": "1.0.0"},
            },
        })
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        self._initialized = True

    def call_tool(self, name: str, arguments: dict) -> dict:
        if not self._initialized:
            self.initialize()
        self._next_id += 1
        resp = self._post({
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        if "error" in resp:
            raise McpError(f"JSON-RPC error: {resp['error']}")

        result = resp.get("result", {})
        texts = [c.get("text", "") for c in result.get("content", []) if c.get("type") == "text"]
        if result.get("isError"):
            raise McpError("tool error: " + (" ".join(texts)[:300] or "unknown"))

        for text in texts:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue

        return result
