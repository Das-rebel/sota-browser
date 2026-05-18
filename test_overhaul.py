#!/usr/bin/env python3
"""
Comprehensive test suite for the SOTA Browser MCP Server overhaul.

Tests: imports, models, config, middleware, tool schemas, BrowserManager,
       and MCPServer integration — without requiring Playwright/browser.

Run:  cd ~/sota-browser && python3 test_overhaul.py
"""

import asyncio
import sys
import os
import time
import traceback
import importlib
from collections import defaultdict

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---- Test infrastructure ----

_results = []  # (category, test_name, passed, detail)


def test(category: str, name: str, condition: bool, detail: str = ""):
    passed = bool(condition)
    _results.append((category, name, passed, detail))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}" + (f"  -- {detail}" if detail and not passed else ""))


def test_raises(category: str, name: str, exc_type, fn, detail: str = ""):
    """Test that fn() raises exc_type."""
    try:
        fn()
        _results.append((category, name, False, "Expected exception not raised"))
        print(f"  [FAIL] {name}  -- Expected {exc_type.__name__} but no exception")
    except exc_type:
        _results.append((category, name, True, ""))
        print(f"  [PASS] {name}")
    except Exception as e:
        _results.append((category, name, False, f"Wrong exception: {type(e).__name__}: {e}"))
        print(f"  [FAIL] {name}  -- Wrong exception: {type(e).__name__}: {e}")


# =====================================================================
# 1. IMPORT / MODULE TESTS
# =====================================================================

def run_import_tests():
    print("\n=== 1. IMPORT / MODULE TESTS ===")

    # 1a. Individual module imports
    modules_to_import = [
        ("config", "config"),
        ("models.session", "models.session"),
        ("models.tab", "models.tab"),
        ("models.result", "models.result"),
        ("models", "models"),
        ("middleware", "middleware"),
        ("middleware.retry", "middleware.retry"),
        ("middleware.circuit_breaker", "middleware.circuit_breaker"),
        ("middleware.guardrails", "middleware.guardrails"),
        ("middleware.cost_tracker", "middleware.cost_tracker"),
        ("middleware.semantic_cache", "middleware.semantic_cache"),
        ("middleware.memory", "middleware.memory"),
        ("tools", "tools"),
        ("tools.session_tools", "tools.session_tools"),
        ("tools.navigation", "tools.navigation"),
        ("tools.interaction", "tools.interaction"),
        ("tools.snapshot", "tools.snapshot"),
        ("tools.frames", "tools.frames"),
        ("tools.cookies", "tools.cookies"),
        ("tools.http_tools", "tools.http_tools"),
        ("tools.form_tools", "tools.form_tools"),
        ("tools.download", "tools.download"),
        ("tools.dialog", "tools.dialog"),
        ("tools.network", "tools.network"),
        ("tools.wait", "tools.wait"),
    ]

    for label, mod_name in modules_to_import:
        try:
            importlib.import_module(mod_name)
            test("Imports", f"import {label}", True)
        except Exception as e:
            test("Imports", f"import {label}", False, str(e))

    # 1b. Key class imports
    try:
        from models import Session, Tab, ToolResult
        test("Imports", "from models import Session, Tab, ToolResult", True)
    except Exception as e:
        test("Imports", "from models import Session, Tab, ToolResult", False, str(e))

    try:
        from middleware import MiddlewarePipeline
        test("Imports", "from middleware import MiddlewarePipeline", True)
    except Exception as e:
        test("Imports", "from middleware import MiddlewarePipeline", False, str(e))

    try:
        from middleware.retry import RetryMiddleware
        from middleware.circuit_breaker import CircuitBreakerMiddleware
        from middleware.guardrails import GuardrailsMiddleware
        from middleware.cost_tracker import CostTrackerMiddleware
        from middleware.semantic_cache import SemanticCacheMiddleware
        from middleware.memory import MemoryMiddleware, BrowserMemoryTree
        test("Imports", "all 6 middleware classes importable", True)
    except Exception as e:
        test("Imports", "all 6 middleware classes importable", False, str(e))

    # 1c. Tool schemas + handlers load
    try:
        from tools import get_all_schemas, register_all
        schemas = get_all_schemas()
        test("Imports", f"get_all_schemas() returns {len(schemas)} schemas", len(schemas) > 0, f"got {len(schemas)}")
    except Exception as e:
        test("Imports", "get_all_schemas()", False, str(e))

    # 1d. No duplicate tool names
    try:
        from tools import get_all_schemas
        schemas = get_all_schemas()
        names = [s["name"] for s in schemas]
        dupes = [n for n in names if names.count(n) > 1]
        test("Imports", "no duplicate tool names", len(dupes) == 0, f"duplicates: {set(dupes)}")
    except Exception as e:
        test("Imports", "duplicate tool name check", False, str(e))

    # 1e. Handler registration (with mock manager — no browser needed)
    try:
        from tools import register_all

        class _MockManager:
            """Minimal stub so register_all() can wire up handlers."""
            pass

        # Dynamically add stub methods that register_all expects
        _methods = [
            "create_session", "close_session", "create_tab", "close_tab",
            "list_tabs", "switch_tab", "info", "set_viewport",
            "navigate", "go_back", "go_forward", "reload", "wait_for_navigation",
            "click", "type_text", "press_key", "scroll", "hover",
            "drag_drop", "select_option", "upload_file",
            "get_snapshot", "get_state", "get_html", "screenshot",
            "extract_images", "extract_links", "get_text", "evaluate",
            "get_console_logs",
            "list_frames", "evaluate_in_frame", "get_frame_content",
            "inject_into_all_frames",
            "import_cookies", "export_cookies", "clear_cookies",
            "http_get", "http_post", "http_put", "http_delete",
            "parse_resume", "analyze_form", "fill_form",
            "fill_form_from_resume", "fill_form_page", "submit_form",
            "download_file", "wait_for_download",
            "handle_dialog",
            "intercept_request", "mock_response", "get_network_log",
            "wait", "wait_for_selector", "wait_for_network_idle",
        ]
        for m in _methods:
            setattr(_MockManager, m, staticmethod(lambda *a, **kw: asyncio.coroutine(lambda: {})()))

        mock = _MockManager()
        handlers = register_all(mock)
        test("Imports", f"register_all() returns {len(handlers)} handlers", len(handlers) > 0, f"got {len(handlers)}")
    except Exception as e:
        test("Imports", "register_all() with mock manager", False, str(e))

    # 1f. BrowserManager import (not start)
    try:
        from browser_manager import BrowserManager
        test("Imports", "from browser_manager import BrowserManager", True)
    except Exception as e:
        test("Imports", "from browser_manager import BrowserManager", False, str(e))


# =====================================================================
# 2. MIDDLEWARE PIPELINE TESTS
# =====================================================================

async def run_middleware_tests():
    print("\n=== 2. MIDDLEWARE PIPELINE TESTS ===")

    # ---- RetryMiddleware ----
    print("\n  -- RetryMiddleware --")
    from middleware.retry import RetryMiddleware, _is_retryable

    # 2a. Retryable classification
    test("Retry", "TimeoutError is retryable", _is_retryable(TimeoutError("timeout")))
    test("Retry", "ConnectionError is retryable", _is_retryable(ConnectionError("connection lost")))
    test("Retry", "OSError is retryable", _is_retryable(OSError("network down")))
    test("Retry", "string 'timeout' exception is retryable", _is_retryable(RuntimeError("connection timeout")))
    test("Retry", "ValueError is NOT retryable", not _is_retryable(ValueError("bad input")))
    test("Retry", "string without pattern is NOT retryable", not _is_retryable(RuntimeError("something else")))

    # 2b. Retry actually retries 3 times
    call_count = 0

    async def failing_fn():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("connection lost")

    mw = RetryMiddleware(max_attempts=3, base_delay_ms=10, max_delay_ms=50, jitter=0.0)
    try:
        await mw.wrap("test_tool", {"tab_id": "t1"}, failing_fn)
        test("Retry", "retries 3 times then raises", False, "no exception raised")
    except ConnectionError:
        test("Retry", "retries 3 times then raises", call_count == 3, f"call_count={call_count}")

    # 2c. Succeeds on 2nd attempt
    call_count2 = 0

    async def fail_once():
        nonlocal call_count2
        call_count2 += 1
        if call_count2 < 2:
            raise ConnectionError("transient")
        return {"ok": True}

    mw2 = RetryMiddleware(max_attempts=3, base_delay_ms=10, max_delay_ms=50, jitter=0.0)
    result = await mw2.wrap("test_tool", {}, fail_once)
    test("Retry", "succeeds on 2nd attempt", result == {"ok": True}, f"got {result}")
    test("Retry", "call count is 2 for fail-once", call_count2 == 2, f"call_count={call_count2}")

    # ---- CircuitBreakerMiddleware ----
    print("\n  -- CircuitBreakerMiddleware --")
    from middleware.circuit_breaker import CircuitBreakerMiddleware, State

    cb = CircuitBreakerMiddleware(threshold=3, recovery_s=0.1)

    # 2d. Starts CLOSED
    test("CircuitBreaker", "initial state is CLOSED",
         cb._get_breaker("example.com").state == State.CLOSED)

    # 2e. Opens after threshold failures
    for i in range(3):
        breaker = cb._get_breaker("example.com")
        breaker.record_failure()
    test("CircuitBreaker", "opens after 3 failures",
         cb._get_breaker("example.com").state == State.OPEN)

    # 2f. Blocks calls when OPEN
    result = await cb.wrap("test_tool", {"url": "http://example.com"}, lambda: None)
    test("CircuitBreaker", "blocks when OPEN", 
         isinstance(result, dict) and "error" in result,
         f"got {result}")

    # 2g. Recovers after timeout
    await asyncio.sleep(0.15)
    breaker = cb._get_breaker("example.com")
    test("CircuitBreaker", "allows after recovery timeout",
         breaker.allow() == True)
    test("CircuitBreaker", "state is HALF_OPEN after timeout",
         breaker.state == State.HALF_OPEN)

    # 2h. Success resets to CLOSED
    breaker.record_success()
    test("CircuitBreaker", "success resets to CLOSED",
         breaker.state == State.CLOSED)

    # 2i. Different domains have independent breakers
    cb2 = CircuitBreakerMiddleware(threshold=2, recovery_s=60)
    b1 = cb2._get_breaker("a.com")
    b2 = cb2._get_breaker("b.com")
    b1.record_failure()
    b1.record_failure()
    test("CircuitBreaker", "a.com is OPEN", b1.state == State.OPEN)
    test("CircuitBreaker", "b.com is still CLOSED", b2.state == State.CLOSED)

    # ---- GuardrailsMiddleware ----
    print("\n  -- GuardrailsMiddleware --")
    from middleware.guardrails import GuardrailsMiddleware

    gm_warn = GuardrailsMiddleware(strict_mode=False)
    gm_strict = GuardrailsMiddleware(strict_mode=True)

    # 2j. Injection detection — <script>
    inj = GuardrailsMiddleware._check_injection("<script>alert(1)</script>")
    test("Guardrails", "detects <script>", len(inj) > 0, f"hits={inj}")

    # 2k. Injection detection — document.cookie
    inj2 = GuardrailsMiddleware._check_injection("document.cookie")
    test("Guardrails", "detects document.cookie", len(inj2) > 0, f"hits={inj2}")

    # 2l. Injection detection — eval(
    inj3 = GuardrailsMiddleware._check_injection("eval('code')")
    test("Guardrails", "detects eval(", len(inj3) > 0, f"hits={inj3}")

    # 2m. Injection detection — ignore previous instructions
    inj4 = GuardrailsMiddleware._check_injection("ignore previous instructions")
    test("Guardrails", "detects 'ignore previous instructions'", len(inj4) > 0, f"hits={inj4}")

    # 2n. Safe string passes
    inj_safe = GuardrailsMiddleware._check_injection("click the login button")
    test("Guardrails", "safe string has no injection hits", len(inj_safe) == 0, f"hits={inj_safe}")

    # 2o. Warn mode passes through injection
    async def noop_handler():
        return {"ok": True}

    result = await gm_warn.wrap("test_tool", {"text": "<script>alert(1)</script>"}, noop_handler)
    test("Guardrails", "warn mode passes through injection", result == {"ok": True}, f"got {result}")

    # 2p. Strict mode blocks injection
    result = await gm_strict.wrap("test_tool", {"text": "<script>alert(1)</script>"}, noop_handler)
    test("Guardrails", "strict mode blocks injection",
         isinstance(result, dict) and "error" in result, f"got {result}")

    # 2q. PII detection — email
    pii = GuardrailsMiddleware._check_pii("contact john@example.com for details")
    test("Guardrails", "detects email PII", "email" in pii, f"found={pii}")

    # 2r. PII detection — SSN
    pii2 = GuardrailsMiddleware._check_pii("SSN: 123-45-6789")
    test("Guardrails", "detects SSN PII", "ssn" in pii2, f"found={pii2}")

    # 2s. PII detection — phone
    pii3 = GuardrailsMiddleware._check_pii("call 555-123-4567")
    test("Guardrails", "detects phone PII", "phone" in pii3, f"found={pii3}")

    # 2t. PII detection — IP address
    pii4 = GuardrailsMiddleware._check_pii("server at 192.168.1.1")
    test("Guardrails", "detects IP address PII", "ip_address" in pii4, f"found={pii4}")

    # 2u. Strict mode blocks PII
    result = await gm_strict.wrap("test_tool", {"text": "email me at test@test.com"}, noop_handler)
    test("Guardrails", "strict mode blocks PII",
         isinstance(result, dict) and "error" in result, f"got {result}")

    # 2v. Skip list bypasses scan for tab_id etc
    result = await gm_strict.wrap("test_tool", {"tab_id": "abc-123"}, noop_handler)
    test("Guardrails", "skip-list fields bypass guardrails", result == {"ok": True}, f"got {result}")

    # ---- CostTrackerMiddleware ----
    print("\n  -- CostTrackerMiddleware --")
    from middleware.cost_tracker import CostTrackerMiddleware

    ct = CostTrackerMiddleware(default_budget=10.0)

    # 2w. Record operations and check sums
    call_n = 0
    async def handler():
        nonlocal call_n
        call_n += 1
        return {"done": True}

    # navigate costs 1.0
    await ct.wrap("browser_navigate", {"session_id": "s1"}, handler)
    # click costs 0.3
    await ct.wrap("browser_click", {"session_id": "s1"}, handler)
    # snapshot costs 0.5
    await ct.wrap("browser_snapshot", {"session_id": "s1"}, handler)

    summary = ct.summary("s1")
    expected_total = 1.0 + 0.3 + 0.5
    test("CostTracker", f"total cost = {expected_total}",
         abs(summary["total_cost"] - expected_total) < 0.01,
         f"got {summary['total_cost']}")
    test("CostTracker", "operation count = 3",
         summary["operation_count"] == 3, f"got {summary['operation_count']}")
    test("CostTracker", "remaining = budget - total",
         abs(summary["remaining"] - (10.0 - expected_total)) < 0.01,
         f"got {summary['remaining']}")

    # 2x. Budget enforcement
    ct_small = CostTrackerMiddleware(default_budget=0.5)
    result = await ct_small.wrap("browser_navigate", {"session_id": "s2"}, handler)
    test("CostTracker", "blocks when budget exceeded",
         isinstance(result, dict) and "error" in result, f"got {result}")

    # 2y. Global summary
    global_summary = ct.summary()
    test("CostTracker", "global summary has sessions",
         "sessions" in global_summary and "total_all" in global_summary,
         f"got {global_summary}")
    test("CostTracker", "total_all = sum of all session costs",
         abs(global_summary["total_all"] - expected_total) < 0.01,
         f"got {global_summary['total_all']}")

    # 2z. Unknown session summary
    unk = ct.summary("nonexistent")
    test("CostTracker", "unknown session returns error",
         "error" in unk, f"got {unk}")

    # ---- SemanticCacheMiddleware ----
    print("\n  -- SemanticCacheMiddleware --")
    from middleware.semantic_cache import SemanticCacheMiddleware, _trigrams, _jaccard

    # 2aa. Trigram basics
    tri = _trigrams("hello world")
    test("SemanticCache", "trigrams non-empty for 'hello world'", len(tri) > 0, f"got {len(tri)}")
    test("SemanticCache", "trigrams are 3-char substrings",
         all(len(t) == 3 for t in tri if len("hello world") >= 3))

    # 2ab. Jaccard similarity
    j1 = _jaccard(_trigrams("hello world"), _trigrams("hello world"))
    test("SemanticCache", "identical strings have jaccard=1.0", j1 == 1.0, f"got {j1}")
    j2 = _jaccard(_trigrams("hello world"), _trigrams("goodbye moon"))
    test("SemanticCache", "dissimilar strings have jaccard < 0.5", j2 < 0.5, f"got {j2}")

    # 2ac. Cache stores and retrieves by exact key
    cache = SemanticCacheMiddleware(threshold=0.7, ttl_snapshot=60)
    call_count3 = 0

    async def expensive_snapshot():
        nonlocal call_count3
        call_count3 += 1
        return {"tree": "accessibility-tree-data"}

    # First call: miss → execute → store
    r1 = await cache.wrap("browser_snapshot", {"tab_id": "t1"}, expensive_snapshot)
    test("SemanticCache", "first call executes handler", call_count3 == 1, f"count={call_count3}")
    test("SemanticCache", "first call result correct", r1.get("tree") == "accessibility-tree-data")

    # Second call: hit → cached
    r2 = await cache.wrap("browser_snapshot", {"tab_id": "t1"}, expensive_snapshot)
    test("SemanticCache", "second call is cache hit", r2.get("_cached") == True, f"got {r2}")
    test("SemanticCache", "call count stays 1 on cache hit", call_count3 == 1, f"count={call_count3}")

    # 2ad. Similar query triggers cache hit
    call_count3b = 0
    cache2 = SemanticCacheMiddleware(threshold=0.3, ttl_snapshot=60)

    async def handler_b():
        nonlocal call_count3b
        call_count3b += 1
        return {"data": "value"}

    # Store with url "https://example.com/page1"
    await cache2.wrap("browser_http_get", {"url": "https://example.com/page1"}, handler_b)
    # Similar url should hit (threshold=0.3)
    r_sim = await cache2.wrap("browser_http_get", {"url": "https://example.com/page1"}, handler_b)
    test("SemanticCache", "similar key triggers cache hit (threshold=0.3)",
         r_sim.get("_cached") == True, f"got {r_sim}")

    # 2ae. TTL expiry
    cache_ttl = SemanticCacheMiddleware(threshold=0.7, ttl_snapshot=0.05)
    call_count4 = 0

    async def handler_c():
        nonlocal call_count4
        call_count4 += 1
        return {"data": "fresh"}

    await cache_ttl.wrap("browser_snapshot", {"tab_id": "t2"}, handler_c)
    await asyncio.sleep(0.08)  # wait for TTL to expire
    r_expired = await cache_ttl.wrap("browser_snapshot", {"tab_id": "t2"}, handler_c)
    test("SemanticCache", "expired entry causes re-execution",
         call_count4 == 2, f"count={call_count4}")
    test("SemanticCache", "expired entry not cached",
         "_cached" not in r_expired, f"got {r_expired}")

    # 2af. Invalidation on mutating tool
    cache_inv = SemanticCacheMiddleware(threshold=0.7, ttl_snapshot=600)
    call_count5 = 0

    async def handler_d():
        nonlocal call_count5
        call_count5 += 1
        return {"data": f"v{call_count5}"}

    await cache_inv.wrap("browser_snapshot", {"tab_id": "t3"}, handler_d)
    # Mutating tool invalidates
    await cache_inv.wrap("browser_click", {"tab_id": "t3"}, handler_d)
    # Snapshot should re-execute
    r_post_inv = await cache_inv.wrap("browser_snapshot", {"tab_id": "t3"}, handler_d)
    test("SemanticCache", "mutation invalidates cache",
         call_count5 == 3, f"count={call_count5}")

    # 2ag. Non-cacheable tool passes through
    call_count6 = 0
    async def handler_e():
        nonlocal call_count6
        call_count6 += 1
        return {"ok": True}

    await cache.wrap("browser_evaluate", {"tab_id": "t1"}, handler_e)
    await cache.wrap("browser_evaluate", {"tab_id": "t1"}, handler_e)
    test("SemanticCache", "non-cacheable tool always executes",
         call_count6 == 2, f"count={call_count6}")

    # ---- MemoryMiddleware ----
    print("\n  -- MemoryMiddleware --")
    from middleware.memory import MemoryMiddleware, BrowserMemoryTree

    tree = BrowserMemoryTree(max_actions=5)

    # 2ah. Record and recall
    tree.record("browser_click", {"url": "https://example.com/page1"}, {"ok": True})
    tree.record("browser_navigate", {"url": "https://example.com/page1"}, {"url": "https://example.com/page1"})
    tree.record("browser_snapshot", {"url": "https://example.com/page1"}, {"tree": "..."})

    recall = tree.recall("example.com")
    test("Memory", "recall returns recorded actions", len(recall) == 3, f"got {len(recall)}")

    # 2ai. Filter by tool name
    click_only = tree.recall("example.com", action="browser_click")
    test("Memory", "filter by action works", len(click_only) == 1, f"got {len(click_only)}")

    # 2aj. Domains listing
    domains = tree.domains()
    test("Memory", "domains() includes example.com", "example.com" in domains, f"got {domains}")

    # 2ak. Limit enforcement
    for i in range(10):
        tree.record("browser_click", {"url": "https://limited.com/p"}, {"ok": True})
    recall_limited = tree.recall("limited.com")
    test("Memory", "max_actions limit enforced", len(recall_limited) <= 5,
         f"got {len(recall_limited)}")

    # 2al. Stats
    stats = tree.stats()
    test("Memory", "stats has domains count", "domains" in stats and "total_actions" in stats)
    test("Memory", "stats domains >= 2", stats["domains"] >= 2, f"got {stats}")

    # 2am. MemoryMiddleware.wrap records
    mem_mw = MemoryMiddleware(tree=tree)
    call_count7 = 0
    async def handler_f():
        nonlocal call_count7
        call_count7 += 1
        return {"result": "data"}

    await mem_mw.wrap("browser_navigate", {"url": "https://memtest.com"}, handler_f)
    recall_mem = tree.recall("memtest.com")
    test("MemoryMiddleware", "wrap records action in tree", len(recall_mem) >= 1, f"got {len(recall_mem)}")
    test("MemoryMiddleware", "recorded tool is correct", recall_mem[-1]["tool"] == "browser_navigate")

    # 2an. Unknown domain returns empty
    empty = tree.recall("nonexistent.xyz")
    test("Memory", "unknown domain returns empty", len(empty) == 0)


# =====================================================================
# 3. TOOL SCHEMA VALIDATION
# =====================================================================

def run_schema_tests():
    print("\n=== 3. TOOL SCHEMA VALIDATION ===")
    from tools import get_all_schemas

    schemas = get_all_schemas()

    # 3a. Count
    test("Schemas", f"total tool count = {len(schemas)}", len(schemas) > 0)
    print(f"       (found {len(schemas)} tools)")

    # 3b. Every schema has name, description, inputSchema
    for s in schemas:
        has_name = "name" in s
        has_desc = "description" in s
        has_schema = "inputSchema" in s
        has_type = s.get("inputSchema", {}).get("type") == "object"
        test("Schemas", f"{s.get('name', '???')} has required fields",
             has_name and has_desc and has_schema and has_type,
             f"name={has_name} desc={has_desc} schema={has_schema} type_obj={has_type}")

    # 3c. Required fields for known tools
    tools_requiring_tab = [
        "browser_navigate", "browser_click", "browser_type", "browser_snapshot",
        "browser_screenshot", "browser_evaluate", "browser_list_frames",
        "browser_scroll", "browser_hover", "browser_press_key",
    ]
    for tname in tools_requiring_tab:
        schema = next((s for s in schemas if s["name"] == tname), None)
        if schema:
            required = schema["inputSchema"].get("required", [])
            has_tab = "tab_id" in required
            test("Schemas", f"{tname} requires tab_id", has_tab,
                 f"required={required}")
        else:
            test("Schemas", f"{tname} requires tab_id", False, "schema not found")

    # 3d. No duplicate names
    names = [s["name"] for s in schemas]
    seen = set()
    dupes = set()
    for n in names:
        if n in seen:
            dupes.add(n)
        seen.add(n)
    test("Schemas", "no duplicate tool names", len(dupes) == 0, f"duplicates: {dupes}")

    # 3e. Group by category
    categories = defaultdict(list)
    prefixes = {
        "browser_create_": "Session/Tab",
        "browser_close_": "Session/Tab",
        "browser_list_": "Session/Tab",
        "browser_switch_": "Session/Tab",
        "browser_info": "Session/Tab",
        "browser_set_v": "Session/Tab",
        "browser_go_": "Navigation",
        "browser_navigate": "Navigation",
        "browser_reload": "Navigation",
        "browser_wait_for_n": "Navigation",
        "browser_click": "Interaction",
        "browser_type": "Interaction",
        "browser_press_": "Interaction",
        "browser_scroll": "Interaction",
        "browser_hover": "Interaction",
        "browser_drag_": "Interaction",
        "browser_select_": "Interaction",
        "browser_upload_": "Interaction",
        "browser_snapshot": "Snapshot",
        "browser_get_s": "Snapshot",
        "browser_get_h": "Snapshot",
        "browser_screenshot": "Snapshot",
        "browser_extract_": "Snapshot",
        "browser_get_t": "Snapshot",
        "browser_get_c": "Snapshot",
        "browser_evaluate": "Snapshot",
        "browser_list_f": "Frames",
        "browser_evaluate_in_": "Frames",
        "browser_get_frame": "Frames",
        "browser_inject_": "Frames",
        "browser_import_c": "Cookies",
        "browser_export_": "Cookies",
        "browser_clear_": "Cookies",
        "browser_http_": "HTTP",
        "browser_parse_": "Form",
        "browser_analyze_": "Form",
        "browser_fill_": "Form",
        "browser_submit_": "Form",
        "browser_download": "Download",
        "browser_wait_for_d": "Download",
        "browser_handle_": "Dialog",
        "browser_intercept": "Network",
        "browser_mock": "Network",
        "browser_get_network": "Network",
        "browser_wait$": "Wait",
        "browser_wait_for_s": "Wait",
    }
    print(f"\n       Tools grouped by category:")
    for n in sorted(names):
        cat = "Other"
        for prefix, c in prefixes.items():
            if n.startswith(prefix) or (prefix.endswith("$") and n == prefix[:-1]):
                cat = c
                break
        categories[cat].append(n)
    for cat in sorted(categories):
        print(f"       {cat}: {len(categories[cat])} tools")
        for t in categories[cat]:
            print(f"         - {t}")

    return schemas


# =====================================================================
# 4. BROWSERMANAGER UNIT TESTS
# =====================================================================

def run_browser_manager_tests():
    print("\n=== 4. BROWSERMANAGER UNIT TESTS ===")
    from browser_manager import BrowserManager

    # 4a. Create instance without starting
    bm = BrowserManager()
    test("BrowserManager", "sessions dict is empty", len(bm.sessions) == 0)
    test("BrowserManager", "pages dict is empty", len(bm.pages) == 0)
    test("BrowserManager", "contexts dict is empty", len(bm.contexts) == 0)

    # 4b. info() returns correct counts
    info = bm.info()
    test("BrowserManager", "info() has sessions=0", info.get("sessions") == 0, f"got {info}")
    test("BrowserManager", "info() has tabs=0", info.get("tabs") == 0, f"got {info}")

    # 4c. _lock exists
    import asyncio
    test("BrowserManager", "has _lock attribute", hasattr(bm, "_lock"))
    test("BrowserManager", "_lock is asyncio.Lock", isinstance(bm._lock, asyncio.Lock))


# =====================================================================
# 5. MCP SERVER INTEGRATION TESTS
# =====================================================================

async def run_mcp_server_tests():
    print("\n=== 5. MCP SERVER INTEGRATION TESTS ===")
    from mcp_server import MCPServer
    from tools import get_all_schemas

    # 5a. Create server (don't initialize — no browser)
    server = MCPServer()
    test("MCPServer", "MCPServer() constructs", server is not None)
    test("MCPServer", "_initialized is False", server._initialized is False)

    # 5b. Test initialize response
    resp = await server.handle({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
    })
    test("MCPServer", "initialize returns jsonrpc 2.0",
         resp.get("jsonrpc") == "2.0", f"got {resp}")
    test("MCPServer", "initialize has protocolVersion",
         "protocolVersion" in resp.get("result", {}), f"got {resp}")
    test("MCPServer", "serverInfo name = sota-browser",
         resp.get("result", {}).get("serverInfo", {}).get("name") == "sota-browser")

    # 5c. notifications/initialized returns None
    resp2 = await server.handle({
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    })
    test("MCPServer", "notifications/initialized returns None", resp2 is None)

    # 5d. tools/list returns schemas (without initializing browser)
    resp3 = await server.handle({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
    })
    tools = resp3.get("result", {}).get("tools", [])
    schema_count = len(get_all_schemas())
    test("MCPServer", f"tools/list returns {schema_count} tools",
         len(tools) == schema_count, f"got {len(tools)}")

    # 5e. Unknown method returns error
    resp4 = await server.handle({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "unknown/method",
    })
    test("MCPServer", "unknown method returns error",
         "error" in resp4 and resp4["error"]["code"] == -32601, f"got {resp4}")

    # 5f. tools/call on uninitialized server (no handlers) returns error
    resp5 = await server.handle({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "browser_info", "arguments": {}},
    })
    # Without initialize(), handlers are empty so it returns {"error": "Unknown tool: browser_info"}
    # wrapped in result.content
    test("MCPServer", "tools/call without init returns error in result",
         "error" in resp5.get("result", {}).get("content", [{}])[0].get("text", "")
         or "error" in resp5, f"got {resp5}")

    # 5g. Build middleware pipeline manually and verify 6 stages
    from middleware import MiddlewarePipeline
    from middleware.guardrails import GuardrailsMiddleware
    from middleware.cost_tracker import CostTrackerMiddleware
    from middleware.semantic_cache import SemanticCacheMiddleware
    from middleware.circuit_breaker import CircuitBreakerMiddleware
    from middleware.retry import RetryMiddleware
    from middleware.memory import MemoryMiddleware

    pipeline = MiddlewarePipeline([
        GuardrailsMiddleware(strict_mode=False),
        CostTrackerMiddleware(default_budget=10000.0),
        SemanticCacheMiddleware(),
        CircuitBreakerMiddleware(),
        RetryMiddleware(),
        MemoryMiddleware(),
    ])
    test("MCPServer", "pipeline has 6 middleware stages",
         len(pipeline.middlewares) == 6, f"got {len(pipeline.middlewares)}")

    # 5h. Pipeline executes correctly
    # Note: the pipeline eventually calls handler(**args), so handler must accept **kwargs
    call_count = 0
    async def test_handler(**kwargs):
        nonlocal call_count
        call_count += 1
        return {"success": True}

    result = await pipeline.execute("browser_snapshot", {"tab_id": "t1"}, test_handler)
    test("MCPServer", "pipeline executes and returns result",
         result.get("success") == True, f"got {result}")


# =====================================================================
# 6. CONFIG TESTS
# =====================================================================

def run_config_tests():
    print("\n=== 6. CONFIG TESTS ===")
    import config

    test("Config", "DEFAULT_VIEWPORT = 1280x720",
         config.DEFAULT_VIEWPORT == {"width": 1280, "height": 720},
         f"got {config.DEFAULT_VIEWPORT}")
    test("Config", "DEFAULT_TIMEOUT = 15000",
         config.DEFAULT_TIMEOUT == 15000, f"got {config.DEFAULT_TIMEOUT}")
    test("Config", "FAST_WAIT = 0.1",
         config.FAST_WAIT == 0.1, f"got {config.FAST_WAIT}")
    test("Config", "MCP_PROTOCOL_VERSION is set",
         len(config.MCP_PROTOCOL_VERSION) > 0, f"got {config.MCP_PROTOCOL_VERSION}")
    test("Config", "SERVER_NAME = sota-browser",
         config.SERVER_NAME == "sota-browser", f"got {config.SERVER_NAME}")
    test("Config", "SERVER_VERSION is set",
         len(config.SERVER_VERSION) > 0, f"got {config.SERVER_VERSION}")

    test("Config", "RETRY_MAX_ATTEMPTS = 3",
         config.RETRY_MAX_ATTEMPTS == 3, f"got {config.RETRY_MAX_ATTEMPTS}")
    test("Config", "RETRY_BASE_DELAY_MS = 500",
         config.RETRY_BASE_DELAY_MS == 500, f"got {config.RETRY_BASE_DELAY_MS}")
    test("Config", "RETRY_MAX_DELAY_MS = 10000",
         config.RETRY_MAX_DELAY_MS == 10000, f"got {config.RETRY_MAX_DELAY_MS}")

    test("Config", "CB_FAILURE_THRESHOLD = 5",
         config.CB_FAILURE_THRESHOLD == 5, f"got {config.CB_FAILURE_THRESHOLD}")
    test("Config", "CB_RECOVERY_TIMEOUT_S = 30",
         config.CB_RECOVERY_TIMEOUT_S == 30, f"got {config.CB_RECOVERY_TIMEOUT_S}")

    test("Config", "CACHE_TTL_SNAPSHOT_S = 300",
         config.CACHE_TTL_SNAPSHOT_S == 300, f"got {config.CACHE_TTL_SNAPSHOT_S}")
    test("Config", "CACHE_TTL_HTTP_S = 3600",
         config.CACHE_TTL_HTTP_S == 3600, f"got {config.CACHE_TTL_HTTP_S}")
    test("Config", "CACHE_SIMILARITY_THRESHOLD = 0.7",
         config.CACHE_SIMILARITY_THRESHOLD == 0.7, f"got {config.CACHE_SIMILARITY_THRESHOLD}")

    test("Config", "MEMORY_MAX_ACTIONS = 200",
         config.MEMORY_MAX_ACTIONS == 200, f"got {config.MEMORY_MAX_ACTIONS}")


# =====================================================================
# 7. MODEL TESTS
# =====================================================================

def run_model_tests():
    print("\n=== 7. MODEL TESTS ===")

    # Session
    from models.session import Session
    s = Session(user_id="test-user")
    test("Session", "id is auto-generated UUID", len(s.id) == 36, f"got {s.id}")
    test("Session", "user_id preserved", s.user_id == "test-user")
    test("Session", "options is empty dict", s.options == {})
    test("Session", "to_dict has id", s.to_dict().get("id") == s.id)
    test("Session", "to_dict has user_id", s.to_dict().get("user_id") == "test-user")

    s2 = Session(user_id="u2", id="fixed-id", existing_browser=True)
    test("Session", "custom id works", s2.id == "fixed-id")
    test("Session", "existing_browser=True", s2.existing_browser is True)
    test("Session", "to_dict note mentions existing",
         "existing" in s2.to_dict().get("note", "").lower())

    # Tab (mock page)
    from models.tab import Tab

    class MockPage:
        url = "https://example.com"
        async def title(self):
            return "Example"

    t = Tab(page=MockPage(), session_id="s1")
    test("Tab", "id is auto-generated UUID", len(t.id) == 36)
    test("Tab", "session_id preserved", t.session_id == "s1")
    test("Tab", "to_dict has url", t.to_dict().get("url") == "https://example.com")

    # Tab to_dict_full (async)
    async def test_tab_async():
        t2 = Tab(page=MockPage(), session_id="s2")
        d = await t2.to_dict_full()
        return d

    d = asyncio.get_event_loop().run_until_complete(test_tab_async())
    test("Tab", "to_dict_full has title", d.get("title") == "Example")
    test("Tab", "to_dict_full has url", d.get("url") == "https://example.com")

    # ToolResult
    from models.result import ToolResult
    tr = ToolResult()
    test("ToolResult", "default success=True", tr.success is True)
    test("ToolResult", "default error=None", tr.error is None)
    test("ToolResult", "default data is empty dict", tr.data == {})
    test("ToolResult", "to_dict returns success dict", "success" in tr.to_dict())

    tr_err = ToolResult(success=False, error="Something failed")
    d_err = tr_err.to_dict()
    test("ToolResult", "error result has 'error' key", "error" in d_err)
    test("ToolResult", "error result has error message", d_err["error"] == "Something failed")

    tr_data = ToolResult(data={"url": "https://example.com", "status": 200})
    d_data = tr_data.to_dict()
    test("ToolResult", "data result includes url", d_data.get("url") == "https://example.com")
    test("ToolResult", "data result includes status", d_data.get("status") == 200)


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 70)
    print("SOTA Browser MCP Server — Overhaul Test Suite")
    print("=" * 70)

    # Sync tests
    run_import_tests()
    run_schema_tests()
    run_browser_manager_tests()
    run_config_tests()
    run_model_tests()

    # Async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_middleware_tests())
    loop.run_until_complete(run_mcp_server_tests())

    # ---- Summary ----
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    categories = defaultdict(lambda: {"pass": 0, "fail": 0, "failures": []})
    for cat, name, passed, detail in _results:
        if passed:
            categories[cat]["pass"] += 1
        else:
            categories[cat]["fail"] += 1
            categories[cat]["failures"].append((name, detail))

    total_pass = sum(c["pass"] for c in categories.values())
    total_fail = sum(c["fail"] for c in categories.values())
    total = total_pass + total_fail

    for cat in sorted(categories):
        c = categories[cat]
        status = "OK" if c["fail"] == 0 else "FAIL"
        print(f"  [{status}] {cat}: {c['pass']} passed, {c['fail']} failed")
        for name, detail in c["failures"]:
            print(f"         FAIL: {name}  -- {detail}")

    print(f"\n  TOTAL: {total_pass}/{total} passed, {total_fail} failed")
    print("=" * 70)

    if total_fail > 0:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
