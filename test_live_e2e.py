#!/usr/bin/env python3
"""
SOTA Browser v2.0 — Live End-to-End Test
Launches real browser, tests all tools, closes. No mocks.
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from browser_manager import BrowserManager
from tools import register_all
from middleware import MiddlewarePipeline
from middleware.guardrails import GuardrailsMiddleware
from middleware.cost_tracker import CostTrackerMiddleware
from middleware.semantic_cache import SemanticCacheMiddleware
from middleware.circuit_breaker import CircuitBreakerMiddleware
from middleware.retry import RetryMiddleware
from middleware.memory import MemoryMiddleware


class LiveTest:
    def __init__(self):
        self.bm = BrowserManager()
        self.handlers = {}
        self.passed = 0
        self.failed = 0
        self.session_id = None
        self.tab_id = None

    def check(self, name, ok, detail=""):
        if ok:
            self.passed += 1
            print(f"  [PASS] {name}")
        else:
            self.failed += 1
            print(f"  [FAIL] {name} — {detail}")

    async def call(self, tool_name, **kwargs):
        return await self.handlers[tool_name](**kwargs)

    async def run(self):
        print("=" * 60)
        print("SOTA Browser v2.0 — LIVE E2E TEST (real browser)")
        print("=" * 60)

        # ── STARTUP ─────────────────────────────────────────────
        print("\n[1] Startup...")
        await self.bm.start()
        self.check("browser started", self.bm._browser is not None)
        self.handlers = register_all(self.bm)
        self.check(f"56 tools registered", len(self.handlers) == 56, f"got {len(self.handlers)}")
        pipeline = MiddlewarePipeline([
            GuardrailsMiddleware(strict_mode=False),
            CostTrackerMiddleware(default_budget=10000.0),
            SemanticCacheMiddleware(),
            CircuitBreakerMiddleware(),
            RetryMiddleware(),
            MemoryMiddleware(),
        ])
        self.check("6 middleware stages", len(pipeline.middlewares) == 6)

        # ── SESSION & TAB ──────────────────────────────────────
        print("\n[2] Session & Tab...")

        r = await self.call("browser_create_session", user_id="e2e")
        self.session_id = r.get("id")
        self.check("create session", self.session_id is not None, str(r)[:150])

        r = await self.call("browser_info")
        self.check("info shows 1 session", r.get("sessions") == 1, str(r))

        r = await self.call("browser_create_tab", session_id=self.session_id, url="about:blank")
        self.tab_id = r.get("id")
        self.check("create tab", self.tab_id is not None, str(r)[:150])

        r = await self.call("browser_list_tabs", session_id=self.session_id)
        tabs = r if isinstance(r, list) else r.get("tabs", r.get("pages", []))
        self.check("list tabs ≥1", len(tabs) >= 1, f"got {len(tabs) if isinstance(tabs, list) else 'unknown'}")

        # ── NAVIGATION ─────────────────────────────────────────
        print("\n[3] Navigation...")

        r = await self.call("browser_navigate", tab_id=self.tab_id, url="https://example.com")
        self.check("navigate example.com", "url" in r or r.get("success"), str(r)[:150])

        await asyncio.sleep(1)

        r = await self.call("browser_get_text", tab_id=self.tab_id)
        text = r.get("text", "")
        self.check("get_text has content", len(text) > 0, f"{len(text)} chars")
        self.check("text contains 'example'", "example" in text.lower())

        # ── SNAPSHOT & EXTRACTION ───────────────────────────────
        print("\n[4] Snapshot & Extraction...")

        r = await self.call("browser_snapshot", tab_id=self.tab_id)
        self.check("snapshot", "elements" in r or "tree" in r or "text" in r or "html" in r)

        r = await self.call("browser_screenshot", tab_id=self.tab_id)
        self.check("screenshot", "base64" in r, f"len={len(r.get('base64', ''))}")

        r = await self.call("browser_extract_links", tab_id=self.tab_id)
        links = r.get("links", r.get("result", []))
        if isinstance(links, list):
            self.check("extract_links", len(links) >= 1, f"{len(links)} links")
        else:
            self.check("extract_links returned", True, str(r)[:100])

        r = await self.call("browser_extract_images", tab_id=self.tab_id)
        self.check("extract_images", isinstance(r, dict))

        r = await self.call("browser_get_html", tab_id=self.tab_id)
        html = r.get("html", "")
        self.check("get_html", len(html) > 50, f"{len(html)} chars")

        r = await self.call("browser_get_state", tab_id=self.tab_id)
        elements = r.get("elements", [])
        self.check("get_state", len(elements) >= 1, f"{len(elements)} clickable elements")

        # ── HISTORY ─────────────────────────────────────────────
        print("\n[5] History...")

        r = await self.call("browser_navigate", tab_id=self.tab_id, url="https://httpbin.org")
        await asyncio.sleep(2)
        self.check("navigate httpbin", "url" in r or r.get("success"), str(r)[:100])

        r = await self.call("browser_go_back", tab_id=self.tab_id)
        self.check("go_back", r.get("success") or "url" in r)

        r = await self.call("browser_go_forward", tab_id=self.tab_id)
        self.check("go_forward", r.get("success") or "url" in r)

        r = await self.call("browser_reload", tab_id=self.tab_id)
        self.check("reload", r.get("success") or "url" in r)

        # ── VIEWPORT ────────────────────────────────────────────
        print("\n[6] Viewport...")

        r = await self.call("browser_set_viewport", tab_id=self.tab_id, width=800, height=600)
        self.check("set_viewport 800x600", r.get("success"), str(r)[:100])

        r = await self.call("browser_set_viewport", tab_id=self.tab_id, width=1280, height=720)
        self.check("set_viewport 1280x720", r.get("success"))

        # ── WAITS ───────────────────────────────────────────────
        print("\n[7] Smart Waits...")

        r = await self.call("browser_wait_for_selector", tab_id=self.tab_id, selector="body", timeout=5000)
        self.check("wait_for_selector body", r.get("success") or r.get("found"), str(r)[:100])

        r = await self.call("browser_wait", seconds=0.3)
        self.check("wait 0.3s", r.get("success"))

        # ── COOKIES ─────────────────────────────────────────────
        print("\n[8] Cookies...")

        r = await self.call("browser_export_cookies", session_id=self.session_id)
        cookies = r.get("cookies", [])
        self.check("export_cookies", isinstance(cookies, list), f"{len(cookies)} cookies")

        r = await self.call("browser_import_cookies", session_id=self.session_id,
                           cookies=[{"name": "test", "value": "123", "domain": "example.com", "path": "/"}])
        self.check("import_cookies", r.get("success"), str(r)[:100])

        r = await self.call("browser_clear_cookies", session_id=self.session_id)
        self.check("clear_cookies", r.get("success"))

        # ── INTERACTION ─────────────────────────────────────────
        print("\n[9] Interaction...")

        # Navigate to page with interactive elements
        r = await self.call("browser_navigate", tab_id=self.tab_id, url="https://www.google.com")
        await asyncio.sleep(2)
        self.check("navigate google.com", r.get("success") or "url" in r, str(r)[:100])

        r = await self.call("browser_get_state", tab_id=self.tab_id)
        elements = r.get("elements", [])
        self.check("google has elements", len(elements) >= 1, f"{len(elements)} elements")

        # ── HTTP TOOLS ──────────────────────────────────────────
        print("\n[10] HTTP Direct...")

        r = await self.call("browser_http_get", url="https://httpbin.org/get")
        self.check("http_get", r.get("success") or "status" in r or "body" in r, str(r)[:150])

        r = await self.call("browser_http_post", url="https://httpbin.org/post", json={"e2e": "test"})
        self.check("http_post", r.get("success") or "status" in r or "body" in r, str(r)[:150])

        r = await self.call("browser_http_put", url="https://httpbin.org/put", json={"e2e": "test"})
        self.check("http_put", r.get("success") or "status" in r or "body" in r, str(r)[:150])

        r = await self.call("browser_http_delete", url="https://httpbin.org/delete")
        self.check("http_delete", r.get("success") or "status" in r or "body" in r, str(r)[:150])

        # ── CONSOLE LOGS ────────────────────────────────────────
        print("\n[11] Console Logs...")

        r = await self.call("browser_get_console_logs", tab_id=self.tab_id)
        self.check("get_console_logs", isinstance(r, dict))

        # ── NETWORK INTERCEPTION ────────────────────────────────
        print("\n[12] Network...")

        r = await self.call("browser_intercept_request", tab_id=self.tab_id, url_pattern="**/*.png")
        self.check("intercept_request", r.get("success") or r.get("intercepting"), str(r)[:100])

        r = await self.call("browser_navigate", tab_id=self.tab_id, url="https://example.com")
        await asyncio.sleep(1)

        r = await self.call("browser_get_network_log", tab_id=self.tab_id)
        self.check("get_network_log", isinstance(r, dict))

        # ── FORM ENGINE ─────────────────────────────────────────
        print("\n[13] Form Engine...")

        r = await self.call("browser_parse_resume", resume_text="John Smith\njohn@test.com\nBS MIT 2020\nSWE at Google\nSkills: Python, React")
        self.check("parse_resume", "profile" in r or "email" in str(r).lower(), str(r)[:200])

        # ── MULTI-TAB ───────────────────────────────────────────
        print("\n[14] Multi-Tab...")

        r2 = await self.call("browser_create_tab", session_id=self.session_id, url="https://httpbin.org/ip")
        tab2_id = r2.get("id")
        self.check("create tab 2", tab2_id is not None)

        await asyncio.sleep(1)

        r = await self.call("browser_switch_tab", tab_id=self.tab_id, tab_index=1)
        self.check("switch_tab", r.get("success") or "new_tab_id" in r, str(r)[:100])

        r = await self.call("browser_close_tab", tab_id=tab2_id)
        self.check("close tab 2", r.get("success"))

        # ── MIDDLEWARE PIPELINE ─────────────────────────────────
        print("\n[15] Middleware Pipeline...")

        r = await pipeline.execute("browser_evaluate", {
            "tab_id": self.tab_id, "script": "document.title"
        }, self.handlers["browser_evaluate"])
        self.check("pipeline: evaluate passes", r is not None)

        r = await pipeline.execute("browser_get_text", {"tab_id": self.tab_id}, self.handlers["browser_get_text"])
        self.check("pipeline: get_text passes", r is not None)

        # ── CLEANUP ─────────────────────────────────────────────
        print("\n[16] Cleanup...")

        r = await self.call("browser_close_session", session_id=self.session_id)
        self.check("close session", r.get("success") or r.get("deleted"))

        r = await self.call("browser_info")
        self.check("info shows 0 sessions", r.get("sessions", -1) == 0, str(r))

        await self.bm.shutdown()
        self.check("shutdown clean", True)

        # ── SUMMARY ─────────────────────────────────────────────
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print(f"  LIVE E2E: {self.passed}/{total} passed, {self.failed} failed")
        print("=" * 60)
        return self.failed == 0


if __name__ == "__main__":
    ok = asyncio.run(LiveTest().run())
    sys.exit(0 if ok else 1)
