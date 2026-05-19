# SOTA Browser MCP Server

```
█▀▀ █▀█ █▄ █ █▀▀ █▀█ █▀█ ▄▀█   █▀▀ █▀ █▀█ █▀█ █▄ █ █▀▀ █▀█
██▄ █▄█ █ ▀█ ██▄ █▀▄ █▀▄ █▀█   █▄█ ▄█ █▀▄ █▀▄ █ ▀█ ██▄ █▀▄
```

**56 tools · 6 middleware stages · Modular architecture · Zero external dependencies beyond Playwright**

A standalone, production-grade MCP (Model Context Protocol) server for browser automation.
Drop-in compatible with any MCP client — PI, Claude Desktop, Cursor, Roo Code, and more.

---

## Table of Contents

1. [What is this?](#what-is-this)
2. [Key Facts at a Glance](#key-facts-at-a-glance)
3. [Architecture](#architecture)
4. [Installation](#installation)
5. [Quick Start](#quick-start)
6. [Running Modes](#running-modes)
7. [The 56 Tools (Complete Reference)](#the-56-tools-complete-reference)
8. [Middleware Pipeline](#middleware-pipeline)
9. [Session & Tab Management](#session--tab-management)
10. [JavaScript & Frames](#javascript--frames)
11. [Network Interception & Mocking](#network-interception--mocking)
12. [Form Engine](#form-engine)
13. [HTTP Direct Tools](#http-direct-tools)
14. [Downloads & Dialogs](#downloads--dialogs)
15. [Cookies](#cookies)
16. [Error Handling](#error-handling)
17. [Anti-Detection](#anti-detection)
18. [Python Client Library](#python-client-library)
19. [Environment Variables](#environment-variables)
20. [File Structure](#file-structure)
21. [Testing](#testing)
22. [Performance Notes](#performance-notes)
23. [Changelog](#changelog)
24. [License](#license)

---

## What is this?

**SOTA Browser** is a modular MCP server that exposes browser automation capabilities as
JSON-RPC 2.0 tools over stdio. It is built on top of [Playwright](https://playwright.dev)
and adds a production-grade middleware pipeline on top of every tool call.

The server is designed to be **self-contained** — the only real external dependency is
Playwright itself. The middleware pipeline provides:

- **Guardrails** — injection detection + PII redaction
- **Cost tracking** — per-session budget enforcement
- **Semantic caching** — trigram Jaccard cache (no embedding API needed)
- **Circuit breaker** — per-domain failure tracking (CLOSED→OPEN→HALF_OPEN)
- **Retry** — exponential backoff with jitter
- **Memory** — per-domain action history for contextual recall

The tool set grew from 33 tools in v1.x to **56 tools** in v2.0, organized into 6
middleware stages.

---

## Key Facts at a Glance

| Property | Value |
|----------|-------|
| **Tools** | 56 |
| **Middleware stages** | 6 |
| **Files in project** | 21 modules |
| **Test suite** | 213 tests, all passing |
| **External dependencies** | `playwright>=1.40.0`, `httpx>=0.25.0` only |
| **Protocol** | JSON-RPC 2.0 over stdio (MCP) |
| **Browser engine** | Playwright Chromium (also supports existing Chrome via CDP) |
| **Python version** | 3.10+ |

---

## Architecture

### High-Level Request Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  MCP Client (PI / Claude Desktop / Cursor)                                 │
│  ───────────────────────────────────────────────────────────── JSON-RPC 2.0 │
│  stdin  ──→  mcp_server.py  ──→  MiddlewarePipeline  ──→  Tool Handler     │
│  stdout ←──                   ←──  (6 stages, outer→inner)  ←─  BrowserManager │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Middleware Pipeline (outer → inner execution order)

```
Request enters
      │
      ▼
┌─────────────────────────────────────────┐
│  Stage 1: GuardrailsMiddleware            │  ← Injection + PII scan (WARN or BLOCK)
│  Stage 2: CostTrackerMiddleware          │  ← Per-session cost + budget enforcement
│  Stage 3: SemanticCacheMiddleware       │  ← Trigram-Jaccard cache (read-only tools)
│  Stage 4: CircuitBreakerMiddleware      │  ← Per-domain CLOSED→OPEN→HALF_OPEN
│  Stage 5: RetryMiddleware               │  ← Exponential backoff + jitter
│  Stage 6: MemoryMiddleware              │  ← Per-domain BrowserMemoryTree recall
      │
      ▼
┌─────────────────────────────────────────┐
│  Tool Handler (tools/*.py)              │  ← Delegates to BrowserManager method
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│  BrowserManager (browser_manager.py)   │  ← Playwright page/context/session ops
└─────────────────────────────────────────┘
      │
      ▼
   Playwright Chromium
```

### Data Flow per Tool Call (example: `browser_navigate`)

```
1. JSON-RPC request received on stdin
2. MCPServer.handle() dispatches to _call_tool("browser_navigate", {tab_id, url})
3. MiddlewarePipeline.execute() wraps the call:
   a. GuardrailsMiddleware.wrap() — scans args for injection / PII
   b. CostTrackerMiddleware.wrap() — increments session cost counter
   c. SemanticCacheMiddleware.wrap() — invalidates cache for this tab (mutation)
   d. CircuitBreakerMiddleware.wrap() — checks if domain is OPEN, raises if so
   e. RetryMiddleware.wrap() — executes with exponential backoff on failure
   f. MemoryMiddleware.wrap() — records action in BrowserMemoryTree after success
4. Handler in tools/navigation.py calls manager.navigate(tab_id, url)
5. BrowserManager.navigate() calls page.goto() on the Playwright page
6. Result flows back up through the middleware stack
7. JSON-RPC response written to stdout
```

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Chrome/Chromium installed (or use the auto-installed Playwright browser)
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/Das-rebel/sota-browser.git
cd sota-browser

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install Chromium browser for Playwright
playwright install chromium

# 4. Verify the server starts
python3 mcp_server.py --help   # shows version info on stderr
```

### Supported Browsers

| Browser | Support | Notes |
|---------|---------|-------|
| Playwright Chromium (headless) | ✅ Default | Launched automatically |
| Playwright Chromium (headed) | ✅ | Set `BH_HEADLESS=false` |
| Existing Chrome via CDP | ✅ | Set `CHROME_CDP_URL` env var |
| Firefox | ⚙️ | Partial — not all tools tested |
| WebKit | ⚙️ | Partial — not all tools tested |

---

## Quick Start

### A. Run as MCP Stdio Server (recommended for PI agent)

```bash
python3 mcp_server.py
```

Then configure your MCP client. Example for PI:

```json
{
  "mcpServers": {
    "sota-browser": {
      "command": "python3",
      "args": ["/absolute/path/to/sota-browser/mcp_server.py"]
    }
  }
}
```

### B. Run as HTTP REST Server

```bash
python3 browser_http_server.py
# Server starts on http://localhost:9377
```

REST endpoints mirror the stdio tools. Useful for non-MCP clients or testing.

### C. Connect to Existing Chrome (CDP Mode)

If you already have Chrome open with remote debugging enabled:

```bash
# Terminal 1: Start Chrome with remote debugging
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-dev-profile

# Terminal 2: Run the MCP server pointing at the CDP socket
CHROME_CDP_URL=http://localhost:9222 python3 mcp_server.py
```

Or use the helper script:

```bash
./use-chrome-cdp.sh
```

### D. Docker Deployment

```bash
# Build the container
docker build -t sota-browser .

# Run (headless by default)
docker run -p 9377:9377 sota-browser

# Run with existing Chrome CDP
docker run -e CHROME_CDP_URL=http://host.docker.internal:9222 sota-browser
```

---

## Running Modes

### Stdio Mode (MCP)

```
python3 mcp_server.py
```

Communication: JSON-RPC 2.0 over stdin/stdout. Suitable for agent integrations.
This is the primary mode.

### HTTP REST Mode

```
python3 browser_http_server.py
```

Communication: HTTP REST. Suitable for web dashboards or non-MCP clients.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROME_CDP_URL` | _(none)_ | Connect to existing Chrome via CDP WebSocket |
| `BH_HEADLESS` | `true` | Run headless (`false` = headed/visible browser) |
| `BH_DEBUG_CLICKS` | `false` | Overlay click targets with red boxes for debugging |
| `MCP_LOG_LEVEL` | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## The 56 Tools (Complete Reference)

### Stage 1 — Session & Tab Management (8 tools)

These tools manage browser sessions (isolated Playwright BrowserContexts) and tabs.
They **bypass the middleware pipeline** because they operate at the session/tab level
and have no `tab_id` or `url` context.

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `browser_create_session` | Create an isolated session (own cookies, storage, viewport) | `user_id`, `width`, `height`, `proxy`, `user_agent`, `timezone`, `locale` |
| `browser_close_session` | Close a session and all its tabs | `session_id` |
| `browser_create_tab` | Open a new tab in a session | `session_id`, `url` (optional) |
| `browser_close_tab` | Close a specific tab | `tab_id` |
| `browser_list_tabs` | List all tabs in a session | `session_id` |
| `browser_switch_tab` | Switch to a tab by index | `tab_id`, `tab_index` |
| `browser_info` | Server status (sessions, tabs, version) | _(none)_ |
| `browser_set_viewport` | Resize viewport for a tab | `tab_id`, `width`, `height` |

**Example — session lifecycle:**

```python
# Create session → create tab → navigate → take screenshot → close
result = await mcp_call("browser_create_session", {"user_id": "alice"})
session_id = result["id"]

result = await mcp_call("browser_create_tab", {"session_id": session_id, "url": "https://example.com"})
tab_id = result["id"]

result = await mcp_call("browser_snapshot", {"tab_id": tab_id})
print(result["title"])   # "Example Domain"
print(result["text"])   # accessibility tree

await mcp_call("browser_close_session", {"session_id": session_id})
```

**Example — multi-tab workflow:**

```python
result = await mcp_call("browser_create_tab", {"session_id": session_id, "url": "https://news.ycombinator.com"})
tab1 = result["id"]

result = await mcp_call("browser_create_tab", {"session_id": session_id})  # blank tab
tab2 = result["id"]

result = await mcp_call("browser_list_tabs", {"session_id": session_id})
# [{url: "https://news.ycombinator.com", title: "Hacker News"}, {url: "about:blank", title: ""}]

# Switch to tab index 1 (the blank tab)
await mcp_call("browser_switch_tab", {"tab_id": tab1, "tab_index": 1})
```

### Stage 2 — Navigation (5 tools)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `browser_navigate` | Navigate to URL, returns status + title | `tab_id`, `url` |
| `browser_go_back` | Navigate back in history | `tab_id` |
| `browser_go_forward` | Navigate forward in history | `tab_id` |
| `browser_reload` | Reload the current page | `tab_id` |
| `browser_wait_for_navigation` | Wait for URL pattern or load state | `tab_id`, `url_pattern`, `timeout` |

**Example:**

```python
result = await mcp_call("browser_navigate", {"tab_id": tab_id, "url": "https://example.com"})
# {url: "https://example.com", title: "Example Domain", status: 200}

# Wait for SPA navigation
await mcp_call("browser_wait_for_navigation", {
    "tab_id": tab_id,
    "url_pattern": "**/dashboard/**",
    "timeout": 30000
})
```

### Stage 3 — Interaction (9 tools)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `browser_click` | Click by selector, element ref (`e1`), or coordinates | `tab_id`, `selector`\|`ref`\|`x,y` |
| `browser_type` | Type text into an element | `tab_id`, `text`, `selector`\|`ref` |
| `browser_hover` | Hover over an element | `tab_id`, `selector` |
| `browser_drag_drop` | Drag source element to target element | `tab_id`, `source`, `target` |
| `browser_press_key` | Press a keyboard key (Enter, Escape, etc.) | `tab_id`, `key`, `modifiers` |
| `browser_scroll` | Scroll the page by delta | `tab_id`, `dx`, `dy` |
| `browser_select_option` | Select an option in a `<select>` dropdown | `tab_id`, `selector`, `value` |
| `browser_upload_file` | Upload a file to `<input type="file">` | `tab_id`, `selector`, `paths` |
| `browser_set_viewport` | Resize viewport (also in Session stage) | `tab_id`, `width`, `height` |

**Clicking by element reference (stable across page changes):**

```python
# The snapshot returns element refs like "e1", "e2"...
result = await mcp_call("browser_snapshot", {"tab_id": tab_id})
# Elements: {e1: {role: "link", name: "Sign in", tag: "a"}, ...}

# Click by ref — works even if the page structure changes slightly
await mcp_call("browser_click", {"tab_id": tab_id, "ref": "e1"})

# Click by selector (CSS or Playwright selector)
await mcp_call("browser_click", {"tab_id": tab_id, "selector": "#submit-btn"})

# Click by absolute coordinates
await mcp_call("browser_click", {"tab_id": tab_id, "x": 640, "y": 360})
```

**Typing into a form:**

```python
await mcp_call("browser_type", {
    "tab_id": tab_id,
    "text": "hello@example.com",
    "selector": 'input[type="email"]'
})
await mcp_call("browser_press_key", {"tab_id": tab_id, "key": "Enter"})
```

**Scrolling:**

```python
# Scroll down 300px (default)
await mcp_call("browser_scroll", {"tab_id": tab_id})

# Scroll up 600px
await mcp_call("browser_scroll", {"tab_id": tab_id, "dx": 0, "dy": 600})

# Scroll right 200px
await mcp_call("browser_scroll", {"tab_id": tab_id, "dx": 200, "dy": 0})
```

### Stage 4 — JavaScript & Frames (5 tools)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `browser_evaluate` | Execute arbitrary JavaScript in the page | `tab_id`, `script`, `frame_index` (optional) |
| `browser_list_frames` | List all frames (main + iframes) with URLs | `tab_id` |
| `browser_evaluate_in_frame` | Execute JS in a specific frame by URL | `tab_id`, `script`, `frame_url_contains` |
| `browser_get_frame_content` | Get HTML from a specific iframe | `tab_id`, `frame_index`\|`frame_url_contains` |
| `browser_inject_all_frames` | Run the same JS in ALL frames, collect per-frame results | `tab_id`, `script` |

**Example — extracting data from a page:**

```python
result = await mcp_call("browser_evaluate", {
    "tab_id": tab_id,
    "script": """
        () => {
            const prices = Array.from(document.querySelectorAll('.price'))
                .map(el => el.textContent.trim());
            return { count: prices.length, prices };
        }
    """
})
```

**Example — reading Colab/Jupyter output via iframe:**

```python
# List all frames to find iframes
result = await mcp_call("browser_list_frames", {"tab_id": tab_id})
# {frames: [{index: 0, url: "https://colab.research.google.com/...", name: "", is_main: true},
#           {index: 1, url: "https://colab.googleusercontent.com/...", name: "frame_1", is_main: false}], total: 2}

# Get HTML from the second frame
result = await mcp_call("browser_get_frame_content", {"tab_id": tab_id, "frame_index": 1})

# Inject JS into all frames to read last 500 chars of output
result = await mcp_call("browser_inject_all_frames", {
    "tab_id": tab_id,
    "script": "document.body.innerText.slice(-500)"
})
# {results: [{frame_index: 0, url: "...", success: true, result: "..."},
#            {frame_index: 1, url: "...", success: true, result: "cell output..."}]}

# Capture console.log output from hidden frame
result = await mcp_call("browser_get_console_logs", {"tab_id": tab_id})
```

### Stage 5 — Snapshot & State (6 tools)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `browser_snapshot` | Accessibility tree + element refs + optional screenshot | `tab_id`, `include_screenshot` |
| `browser_get_state` | Indexed clickable elements with bounding boxes | `tab_id` |
| `browser_get_html` | Raw HTML of page or element | `tab_id`, `selector` (optional) |
| `browser_get_text` | Text content only (lightweight) | `tab_id`, `selector` (optional) |
| `browser_screenshot` | PNG screenshot (viewport or full-page) | `tab_id`, `full` |
| `browser_extract_images` | Extract all `<img>` src/alt/dimensions | `tab_id` |
| `browser_extract_links` | Extract all `<a href>` + text | `tab_id` |

**Snapshot vs Get State:**

```
browser_snapshot → gives you an accessibility tree with [role] labels.
                   Good for: understanding page structure, reading content.
                   Output: {tree: [...], elements: {e1: {...}}, text: "...", frames: [...]}

browser_get_state → gives you a flat list of INDEXED clickable elements with x,y coords.
                    Good for: programmatic clicking, UI automation.
                    Output: {elements: [{index: 1, role: "button", name: "Submit", x: 640, y: 360}], count: 12}
```

**Example — iterate over all clickable elements:**

```python
result = await mcp_call("browser_get_state", {"tab_id": tab_id})
for el in result["elements"]:
    print(f"[{el['index']}] {el['role']}: {el['name']} at ({el['x']}, {el['y']})")
# [1] link: "Privacy Policy" at (120, 480)
# [2] button: "Accept all cookies" at (640, 360)
# [3] input: "Email address" at (300, 200)
```

**Example — full-page screenshot:**

```python
result = await mcp_call("browser_screenshot", {"tab_id": tab_id, "full": True})
# result["base64"] contains the full-page PNG as base64
```

### Stage 6 — Network Interception (4 tools)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `browser_intercept_request` | Start intercepting requests matching a URL pattern | `tab_id`, `url_pattern` |
| `browser_mock_response` | Return a canned/mock response for matching URLs | `tab_id`, `url_pattern`, `body`, `status`, `content_type` |
| `browser_get_network_log` | Retrieve all intercepted request/response pairs | `tab_id` |
| `browser_wait_for_network_idle` | Wait until no network activity for N seconds | `tab_id`, `timeout` |

**Example — mocking an API response:**

```python
# Mock a JSON API endpoint
await mcp_call("browser_mock_response", {
    "tab_id": tab_id,
    "url_pattern": "**/api/user/**",
    "body": '{"id": 42, "name": "Alice", "plan": "pro"}',
    "status": 200,
    "content_type": "application/json"
})
```

**Example — intercepting requests:**

```python
await mcp_call("browser_intercept_request", {"tab_id": tab_id, "url_pattern": "**/analytics/**"})
# ... user browses ...
result = await mcp_call("browser_get_network_log", {"tab_id": tab_id})
print(result["count"])  # e.g. 5
for req in result["requests"]:
    print(req["url"], req["method"])
```

### Stage 7 — Downloads & Dialogs (4 tools)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `browser_download_file` | Trigger a file download (by click or direct URL) | `tab_id`, `trigger_selector`\|`url` |
| `browser_wait_for_download` | Wait for download to complete, returns file path | `download_id`, `path` (optional) |
| `browser_handle_dialog` | Accept or dismiss a JS dialog (alert/confirm/prompt) | `tab_id`, `action` ("accept"\|"dismiss"), `prompt_text` |
| `browser_wait` | Explicit sleep for a fixed number of seconds | `seconds` |

**Example — download workflow:**

```python
result = await mcp_call("browser_download_file", {
    "tab_id": tab_id,
    "trigger_selector": 'a[href*="/download/report.pdf"]'
})
download_id = result["download_id"]
filename = result["filename"]  # e.g. "report.pdf"

# Wait for download to finish
result = await mcp_call("browser_wait_for_download", {
    "download_id": download_id,
    "path": "/tmp/reports/"
})
print(result["path"])  # /tmp/reports/report.pdf
```

**Example — handling JS confirm dialog:**

```python
# Before clicking the button that triggers the confirm:
result = await mcp_call("browser_handle_dialog", {
    "tab_id": tab_id,
    "action": "accept",
    "prompt_text": ""
})
# Or dismiss:
await mcp_call("browser_handle_dialog", {"tab_id": tab_id, "action": "dismiss"})
```

### Stage 8 — Cookies (3 tools)

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `browser_import_cookies` | Import cookies into a session | `session_id`, `cookies` |
| `browser_export_cookies` | Export all cookies from a session | `session_id` |
| `browser_clear_cookies` | Clear all cookies for a session | `session_id` |

**Example — session persistence across restarts:**

```python
# After logging into a site, export cookies
result = await mcp_call("browser_export_cookies", {"session_id": session_id})
cookies = result["cookies"]  # list of {name, value, domain, path, secure, ...}

# Persist to file
import json
with open("/tmp/session_cookies.json", "w") as f:
    json.dump(cookies, f)

# Later: import cookies to restore session
with open("/tmp/session_cookies.json") as f:
    cookies = json.load(f)
await mcp_call("browser_import_cookies", {"session_id": session_id, "cookies": cookies})
```

**Cookie extraction for headless HTTP (Brave browser example):**

```bash
python3 extract_brave_cookies.py --domain github.com --output /tmp/gh_cookies.json
```

```python
# Then import into a session:
with open("/tmp/gh_cookies.json") as f:
    cookies = json.load(f)
await mcp_call("browser_import_cookies", {"session_id": session_id, "cookies": cookies})
```

### Stage 9 — HTTP Direct (4 tools)

These tools make direct HTTP requests **without opening a browser tab**.
Useful for API probing, headless fetches, and checking CDN availability.

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `browser_http_get` | HTTP GET (no browser) | `url`, `headers`, `timeout` |
| `browser_http_post` | HTTP POST (no browser) | `url`, `data`\|`json`, `headers`, `timeout` |
| `browser_http_put` | HTTP PUT (no browser) | `url`, `data`\|`json`, `headers`, `timeout` |
| `browser_http_delete` | HTTP DELETE (no browser) | `url`, `headers`, `timeout` |

**Example:**

```python
result = await mcp_call("browser_http_get", {
    "url": "https://api.example.com/status",
    "headers": {"Authorization": "Bearer token123"}
})
# {url: "...", status: 200, headers: {...}, content: "..."}
```

### Stage 10 — Form Engine (6 tools)

The form engine is a **rule-based** (no LLM required) system that understands 50+
semantic field types across Google Forms, Greenhouse, Workday, Lever, Material UI,
Ant Design, and standard HTML forms.

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `browser_parse_resume` | Parse a plain-text resume into a structured profile | `resume_text` |
| `browser_analyze_form` | Detect form type, fields, and buttons | `tab_id` |
| `browser_fill_form` | Fill form from a profile dict | `tab_id`, `profile`, `skip_types`, `fill_unmatched` |
| `browser_fill_form_from_resume` | One-shot: parse resume + fill form | `tab_id`, `resume_text`, `skip_types`, `fill_unmatched` |
| `browser_fill_form_page` | Fill + click Next for multi-page forms | `tab_id`, `profile`, `skip_types`, `fill_unmatched` |
| `browser_submit_form` | Auto-detect and click the submit button | `tab_id` |

**Supported semantic field types (50+):**

```
name, first_name, last_name, middle_name, full_name,
email, phone, phone_mobile, phone_work,
address, street, city, state, zip, country,
date_of_birth, gender, marital_status,
job_title, company, company_size, industry, linkedin_url, portfolio_url,
education, degree, major, graduation_year, school_name,
skills, language, hobby,
resume_file, cover_letter, salary, notice_period, ...
```

**Example — one-shot resume → job application:**

```python
with open("resume.txt") as f:
    resume_text = f.read()

result = await mcp_call("browser_fill_form_from_resume", {
    "tab_id": tab_id,
    "resume_text": resume_text,
    "skip_types": ["resume_file"],  # skip file upload
    "fill_unmatched": False        # don't fill unrecognized fields
})
print(result["form_type"])   # "greenhouse"
print(result["profile"])     # parsed profile dict
print(result["fill_result"])  # {filled: [...], skipped: [...], errors: [...]}
```

**Example — multi-page form:**

```python
# Fill page 1 and advance
result = await mcp_call("browser_fill_form_page", {
    "tab_id": tab_id,
    "profile": profile
})
# Navigate to page 2, fill, advance
result = await mcp_call("browser_fill_form_page", {
    "tab_id": tab_id,
    "profile": profile
})
# Submit on final page
await mcp_call("browser_submit_form", {"tab_id": tab_id})
```

---

## Middleware Pipeline

### Overview

Every tool call (except session-level tools) passes through 6 middleware stages,
registered in `mcp_server.py`:

```python
MiddlewarePipeline([
    GuardrailsMiddleware(strict_mode=False),
    CostTrackerMiddleware(default_budget=10000.0),
    SemanticCacheMiddleware(),
    CircuitBreakerMiddleware(),
    RetryMiddleware(),
    MemoryMiddleware(),
])
```

### Stage 1 — GuardrailsMiddleware

**Purpose:** Detect injection attacks and PII in tool arguments.

- **17 injection patterns** scanned: prompt injection (`ignore previous instructions`,
  `you are now`), HTML injection (`<script>`, `javascript:`), JS injection
  (`eval(`, `document.cookie`), prototype pollution (`__proto__`), and more.
- **5 PII patterns** detected: email, SSN, credit card, phone, IP address.
- **WARN mode (default):** logs warnings, allows the call.
- **STRICT mode:** blocks the call with an error response.

```python
# Strict mode — blocks injection attempts
GuardrailsMiddleware(strict_mode=True)
```

### Stage 2 — CostTrackerMiddleware

**Purpose:** Track resource usage per session and enforce budgets.

- Tracks calls per session, with a configurable budget.
- When budget is exceeded, returns an error instead of executing.
- Configurable via `default_budget` parameter (default: 10,000 units).

```python
CostTrackerMiddleware(default_budget=5000.0)
```

### Stage 3 — SemanticCacheMiddleware

**Purpose:** Cache read-only tool results using trigram Jaccard similarity.

- **No embedding API required** — uses character trigrams (n=3) and Jaccard similarity.
- Cacheable tools: `browser_snapshot`, `browser_get_state`, `browser_get_html`,
  `browser_get_text`, `browser_screenshot`, `browser_http_*`, `browser_extract_*`.
- **Mutating tools** (click, type, navigate, etc.) automatically invalidate the cache
  for the affected tab scope.
- TTL: 5 minutes for snapshots, 1 hour for HTTP tools.
- Similarity threshold: 0.7 (configurable).

```python
# Cache hit example
result = await mcp_call("browser_snapshot", {"tab_id": tab_id})
# result["_cached"] == True  ← indicates a cached response
```

### Stage 4 — CircuitBreakerMiddleware

**Purpose:** Prevent cascading failures by tracking per-domain failure rates.

States: **CLOSED → OPEN → HALF_OPEN**

```
CLOSED    (normal): every call proceeds. On failure → increment counter.
OPEN      (failing): calls are blocked with error "Circuit breaker OPEN for domain: X".
HALF_OPEN (probing): one test call allowed. Success → CLOSED. Failure → OPEN.
```

- Threshold: 5 consecutive failures (configurable).
- Recovery timeout: 30 seconds (configurable).
- Domain is extracted from `url`, `tab_id`, or `session_id` arguments.

```python
CircuitBreakerMiddleware(threshold=5, recovery_s=30.0)
```

### Stage 5 — RetryMiddleware

**Purpose:** Retry transient failures with exponential backoff + jitter.

- Retryable errors: `TimeoutError`, `ConnectionError`, `OSError`, and errors
  whose message contains `timeout`, `connection`, `network`, `disconnected`, `closed`.
- Exponential backoff: delay = `base_delay * 2^(attempt-1)`, capped at `max_delay`.
- Jitter: ±30% randomization to avoid thundering herd.
- Default: 3 attempts, 500ms base, 10s cap.

```python
RetryMiddleware(max_attempts=3, base_delay_ms=500, max_delay_ms=10000, jitter=0.3)
```

### Stage 6 — MemoryMiddleware

**Purpose:** Per-domain action history for contextual recall.

- `BrowserMemoryTree` stores the last 200 actions per domain.
- After every tool call, the result (success/failure) is recorded.
- Useful for agents that need to recall what actions were taken on a domain
  to avoid repeating steps or build on previous interactions.

```python
# After a series of interactions on example.com:
result = await mcp_call("browser_navigate", {"tab_id": tab_id, "url": "https://example.com"})
# ... several clicks and types ...
recall = memory_mw.tree.recall("example.com")
print(len(recall))  # e.g. 12
print(recall[-1])   # {tool: "browser_click", args_summary: {...}, success: True, timestamp: ...}
```

---

## Session & Tab Management

### Session Model

A **session** = one Playwright `BrowserContext`. Isolated from other sessions:
- Own cookies, localStorage, sessionStorage
- Own viewport, user agent, timezone, locale
- One or more **tabs** (Playwright `Page` objects)

```
Browser Process
  ├── Session A (context A)
  │     ├── Tab A1 (page)
  │     ├── Tab A2 (page)
  │     └── ...
  ├── Session B (context B)
  │     ├── Tab B1 (page)
  │     └── ...
  └── ...
```

### Creating Sessions with Custom Settings

```python
await mcp_call("browser_create_session", {
    "user_id": "alice",
    "width": 1920,
    "height": 1080,
    "proxy": "http://proxy.example.com:8080",     # optional
    "user_agent": "Mozilla/5.0 ... Chrome/122",   # optional
    "timezone": "America/Los_Angeles",            # optional
    "locale": "en-US",                            # optional
})
```

### Viewport

```python
# Default: 1280x720
await mcp_call("browser_set_viewport", {
    "tab_id": tab_id,
    "width": 1920,
    "height": 1080
})
```

---

## JavaScript & Frames

### Frame Architecture

Modern web pages have multiple frame layers:

```
Top-level page (main frame)
  ├── iframe (frame_index=1) — embedded content from same/different origin
  ├── iframe (frame_index=2) — another embed
  └── ...
    └── Nested iframe (frame_index=N) — iframe inside an iframe
```

### Listing Frames

```python
result = await mcp_call("browser_list_frames", {"tab_id": tab_id})
# {frames: [{index: 0, url: "https://app.com/", name: "", is_main: true},
#           {index: 1, url: "https://cdn.example.com/widget.html", name: "widget", is_main: false}],
#  total: 2}
```

### Injecting into All Frames Simultaneously

```python
# Read the output text from all frames — useful for Colab/Jupyter notebooks
result = await mcp_call("browser_inject_all_frames", {
    "tab_id": tab_id,
    "script": "document.body.innerText.slice(-500)"
})
# Results are returned per-frame with success/failure per frame.
```

### Capturing Console Logs from Hidden Frames

```python
# Set up console capture (first call initializes the JS logger)
result = await mcp_call("browser_get_console_logs", {"tab_id": tab_id})
# Subsequent calls return all captured console.log/error messages.
# Include `clear: True` to flush after reading.
```

---

## Network Interception & Mocking

### Architecture

```
Browser Tab
  └── Playwright Route Handler
        ├── If url_pattern matches:
        │     └── Return mock (canned response) OR
        │         Intercept and log request
        └── If no match:
              └── Pass through to real network
```

### Mocking a REST API

```python
await mcp_call("browser_mock_response", {
    "tab_id": tab_id,
    "url_pattern": "**/api/v1/products/**",
    "body": '[{"id": 1, "name": "Widget", "price": 9.99}]',
    "status": 200,
    "content_type": "application/json"
})

# Now every fetch/XHR to /api/v1/products/* returns the mock data
result = await mcp_call("browser_navigate", {
    "tab_id": tab_id,
    "url": "https://shop.example.com/products"
})
# The product list page will show the mocked data
```

### Logging All Requests

```python
# Start intercepting analytics calls
await mcp_call("browser_intercept_request", {
    "tab_id": tab_id,
    "url_pattern": "**/analytics/**"
})

# Browse the page...
# Then retrieve all logged requests
result = await mcp_call("browser_get_network_log", {"tab_id": tab_id})
for req in result["requests"]:
    print(req["timestamp"], req["method"], req["url"], req["resource_type"])
```

---

## Form Engine

### Architecture

```
browser_fill_form_from_resume
       │
       ▼
┌──────────────────┐
│  ResumeParser    │  ← Rule-based parser, no LLM needed
│  (form_engine.py)│     Parses: name, email, phone, education, etc.
└────────┬─────────┘
         │ profile dict
         ▼
┌──────────────────┐
│  FormScanner     │  ← Scans the DOM for form fields
│  (form_engine.py)│     Detects: field semantic types, form framework
└────────┬─────────┘
         │ analysis dict
         ▼
┌──────────────────┐
│  FormFiller      │  ← Fills fields by semantic type matching
│  (form_engine.py)│     50+ semantic types, handles Material UI / HTML
└──────────────────┘
```

### Form Type Detection

The `FormScanner` auto-detects:

| Detected Form Type | Notes |
|--------------------|-------|
| `google_forms` | Google Forms with `aria-label` based field mapping |
| `greenhouse` | Greenhouse.io job application forms |
| `workday` | Workday talent management forms |
| `lever` | Lever.co application forms |
| `material_ui` | Material Design React components |
| `ant_design` | Ant Design React components |
| `standard_html` | Generic HTML forms |

### Semantic Type System

Each form field is assigned a **semantic type** (e.g., `email`, `phone`, `degree`).
The `FormFiller` maps profile values to fields by semantic type:

```
Profile field         →  Form field (semantic match)
─────────────────────────────────────────────────────
alice@example.com     →  <input aria-label="Work email">
+1-555-123-4567      →  <input aria-label="Mobile phone">
Bachelor of Science  →  <select aria-label="Degree">
```

---

## HTTP Direct Tools

These tools bypass the browser entirely and make raw HTTP requests. Useful for:

- Health checks and API probing before navigating
- Headless data fetching (no browser overhead)
- Checking CDN availability
- Quick JSON API calls without loading a full page

```python
# Health check
result = await mcp_call("browser_http_get", {
    "url": "https://api.example.com/health"
})

# POST to a webhook
result = await mcp_call("browser_http_post", {
    "url": "https://hooks.example.com/trigger",
    "json": {"event": "signup", "user_id": "alice"}
})
```

---

## Downloads & Dialogs

### Download Flow

```
browser_download_file → triggers download (returns download_id)
browser_wait_for_download → waits for completion, saves to path
```

### Dialog Types Handled

| Dialog Type | `dtype` | Action |
|-------------|---------|--------|
| `alert` | `dialog.alert` | accept or dismiss |
| `confirm` | `dialog.confirm` | accept or dismiss |
| `prompt` | `dialog.prompt` | accept with text, or dismiss |
| `beforeunload` | `dialog.beforeunload` | accept or dismiss |

---

## Cookies

### Cookie Object Format

```python
{
    "name": "session_id",
    "value": "abc123...",
    "domain": ".example.com",
    "path": "/",
    "secure": True,
    # optional:
    "httpOnly": True,
    "sameSite": "Lax",
    "expires": "2025-12-31T23:59:59Z"
}
```

### Import/Export Example

```python
# Export after successful login
result = await mcp_call("browser_export_cookies", {"session_id": session_id})
save_cookies = result["cookies"]  # [{name, value, domain, ...}, ...]

# Another session restores the cookies
await mcp_call("browser_import_cookies", {"session_id": session_id2, "cookies": save_cookies})
```

### Brave Browser Cookie Extraction

```bash
python3 extract_brave_cookies.py --domain github.com --output /tmp/gh_cookies.json
```

This script extracts cookies from a running Brave browser profile for use with
`browser_import_cookies`. Useful for maintaining authenticated sessions across
headless automation runs.

---

## Error Handling

### Error Response Format

Every tool returns a consistent error format when something fails:

```python
{"error": "Human-readable error message"}
```

### HTTP Status Codes in Responses

| Scenario | HTTP Status |
|----------|-------------|
| Page loaded successfully | `200` |
| Page loaded (redirect) | `301`, `302` |
| Resource not found | `404` |
| Server error | `500` |

### Common Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `Tab not found` | `tab_id` is invalid or tab was closed | Re-create tab with `browser_create_tab` |
| `Session not found` | `session_id` is invalid | Re-create session |
| `Circuit breaker OPEN for domain: X` | Domain had too many failures | Wait 30s for recovery, or increase threshold |
| `Element not found: #selector` | Selector doesn't match any element | Use `browser_snapshot` to find correct selector |
| `Blocked by guardrails: injection patterns detected` | Strict guardrails mode, detected injection | Remove suspicious patterns from args |

---

## Anti-Detection

The server removes common `webdriver` and automation fingerprints:

```python
# Injected into every new context:
Object.defineProperty(navigator, 'webdriver', {get: () => false});
```

Additional browser launch arguments that reduce detection:

```
--disable-blink-features=AutomationControlled
--disable-features=IsolateOrigins,site-per-process
--no-sandbox
--disable-setuid-sandbox
--disable-dev-shm-usage
--disable-gpu
--disable-extensions
--disable-background-networking
--disable-default-apps
--disable-sync
--no-first-run
```

For more aggressive anti-detection, consider running headed (`BH_HEADLESS=false`)
with a real user profile, or using the existing Chrome CDP connection.

---

## Python Client Library

The `mcp_client.py` module provides a programmatic Python interface:

```python
from mcp_client import MCPClient

async def main():
    client = MCPClient()
    await client.connect()  # starts mcp_server.py as subprocess

    # Create session → tab → navigate → snapshot
    session = await client.call("browser_create_session", {"user_id": "test"})
    session_id = session["id"]

    tab = await client.call("browser_create_tab", {"session_id": session_id, "url": "https://example.com"})
    tab_id = tab["id"]

    result = await client.call("browser_snapshot", {"tab_id": tab_id})
    print(result["title"])

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### MCPClient API

| Method | Description |
|--------|-------------|
| `await client.connect()` | Start server subprocess and handshake |
| `await client.call(tool_name, args)` | Call a tool, returns result dict |
| `await client.close()` | Shut down server and close client |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROME_CDP_URL` | _(none)_ | Connect to existing Chrome via CDP |
| `BH_HEADLESS` | `true` | Run headless vs headed |
| `BH_DEBUG_CLICKS` | `false` | Show click overlays |
| `MCP_LOG_LEVEL` | `INFO` | Log verbosity |

---

## File Structure

```
sota-browser/
├── mcp_server.py                  # Entry point — JSON-RPC stdio (MCP protocol)
├── browser_http_server.py         # Entry point — HTTP REST mode
├── browser_manager.py             # Core: browser lifecycle, sessions, tabs, all page ops
├── config.py                      # Constants: timeouts, user-agent, middleware defaults
├── form_engine.py                 # Rule-based form parser + scanner + filler (no LLM)
├── middleware/                     # 6 middleware stages
│   ├── __init__.py
│   ├── guardrails.py              # 17-pattern injection detection + 5 PII patterns
│   ├── cost_tracker.py            # Per-session cost tracking + budget enforcement
│   ├── semantic_cache.py          # Trigram Jaccard cache (no embedding API)
│   ├── circuit_breaker.py         # Per-domain CLOSED→OPEN→HALF_OPEN state machine
│   ├── retry.py                   # Exponential backoff + jitter for transient failures
│   └── memory.py                  # BrowserMemoryTree: per-domain action history
├── models/                        # Data classes
│   ├── __init__.py
│   ├── session.py                 # Session dataclass
│   ├── tab.py                     # Tab dataclass
│   └── result.py                  # ToolResult dataclass
├── tools/                         # 13 tool modules, 56 tools total
│   ├── __init__.py                # get_all_schemas() + register_all(manager)
│   ├── session_tools.py           # 8 tools: create/close session/tab, list, switch, info, viewport
│   ├── navigation.py              # 5 tools: navigate, go_back, go_forward, reload, wait_navigation
│   ├── interaction.py            # 9 tools: click, type, hover, drag_drop, press_key, scroll, select, upload, viewport
│   ├── snapshot.py                # 7 tools: snapshot, get_state, get_html, get_text, screenshot, extract_images, extract_links
│   ├── frames.py                  # 5 tools: list_frames, evaluate_in_frame, get_frame_content, inject_all_frames, evaluate (frame support)
│   ├── cookies.py                 # 3 tools: import, export, clear cookies
│   ├── http_tools.py              # 4 tools: http_get, http_post, http_put, http_delete
│   ├── form_tools.py              # 6 tools: parse_resume, analyze_form, fill_form, fill_form_from_resume, fill_form_page, submit_form
│   ├── download.py                # 3 tools: download_file, wait_for_download
│   ├── dialog.py                  # 1 tool: handle_dialog
│   ├── network.py                # 4 tools: intercept_request, mock_response, get_network_log, wait_for_network_idle
│   └── wait.py                    # 3 tools: wait, wait_for_selector, wait_for_network_idle
├── mcp_client.py                  # Python client library for programmatic use
├── extract_brave_cookies.py       # Extract cookies from Brave browser for headless HTTP
├── Dockerfile                     # Container deployment
├── requirements.txt               # Python dependencies (playwright + httpx)
├── pyproject.toml                # Project metadata
├── CHANGELOG.md                  # Version history
└── README.md                     # This file
```

---

## Testing

### Run All Tests

```bash
python3 test_overhaul.py
# 213 tests across 15 categories, all passing
```

### Run Live E2E Tests

```bash
python3 test_live_e2e.py
# End-to-end browser tests (requires network access)
```

### Test Categories (213 total)

| Category | Count | Description |
|----------|-------|-------------|
| Session management | ~15 | Create/close sessions and tabs |
| Navigation | ~10 | Navigate, back, forward, reload |
| Interaction | ~20 | Click, type, hover, drag, key press |
| Snapshot | ~15 | Accessibility tree, elements, HTML |
| Frames | ~10 | Iframe listing, injection, content |
| Cookies | ~10 | Import/export/clear |
| HTTP direct | ~10 | GET/POST/PUT/DELETE |
| Form engine | ~20 | Resume parsing, form filling |
| Download | ~8 | File download flow |
| Dialog | ~5 | JS dialog handling |
| Network | ~12 | Mocking, interception |
| Wait | ~8 | Explicit waits, network idle |
| Circuit breaker | ~15 | State transitions |
| Semantic cache | ~20 | Cache hit/miss/invalidation |
| Memory | ~10 | Action recall |
| Guardrails | ~15 | Injection/PII detection |
| **Total** | **213** | **All passing** |

---

## Performance Notes

### Snapshot vs Raw HTML

The accessibility tree snapshot (`browser_snapshot`) is ~**90% smaller** than raw HTML
for typical web pages. Prefer `browser_snapshot` for reading content and `browser_get_state`
for finding click targets.

### Semantic Cache Impact

For read-only tools, the semantic cache avoids repeated Playwright page evaluations:

```
Without cache: ~200-500ms per browser_snapshot call
With cache:    ~1-5ms  per cached hit (Jaccard trigram lookup)
```

### Concurrent Tab Limits

Playwright's default limit is **half the CPU cores** for parallel page operations.
For I/O-bound browser automation, running 4-8 tabs in parallel is usually optimal.

### Session Isolation Cost

Each session creates a new Playwright `BrowserContext`, which consumes ~10-30MB
of memory. Close sessions when done to free resources.

---

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for the full version history. Key milestones:

| Version | Date | Highlights |
|---------|------|------------|
| v2.0 | 2025 | 56 tools, 6 middleware stages, modular architecture, 213 tests |
| v1.x | 2024 | 33 tools, monolithic mcp_server.py |

---

## License

MIT