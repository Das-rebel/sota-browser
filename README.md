# SOTA Browser MCP Server

**56 tools. 6 middleware stages. Modular architecture. Zero external dependencies beyond Playwright.**

A standalone, production-grade browser automation MCP server. Independent project — works with any MCP client (PI, Claude Desktop, Cursor, etc.).

## What's New in v2.0

- **56 tools** (was 33) — hover, drag-drop, file upload, network interception, downloads, dialogs, cookie export, and more
- **6-stage middleware pipeline** — guardrails, cost tracking, semantic cache, circuit breaker, retry, memory
- **Modular architecture** — 21 files across `tools/`, `middleware/`, `models/` (was a single 650-line monolith)
- **213 tests passing**

## Features

### Browser Control
- CDP-based automation via Playwright (connect to existing Chrome or launch headless)
- Isolated sessions with own cookies, storage, viewport
- Stable element refs (e1, e2, e3...) for reliable interaction
- Accessibility tree snapshots (~90% smaller than raw HTML)
- Anti-detection: removes `webdriver` indicators, spoofed fingerprints

### Middleware Pipeline
Every tool call passes through 6 stages:
1. **Guardrails** — 17-pattern injection detection + PII redaction
2. **Cost Tracker** — per-session cost tracking + budget enforcement
3. **Semantic Cache** — trigram Jaccard similarity (no embedding API needed)
4. **Circuit Breaker** — per-domain failure tracking (CLOSED→OPEN→HALF_OPEN)
5. **Retry** — exponential backoff with jitter
6. **Memory** — contextual recall of past interactions per domain

## Installation

```bash
git clone https://github.com/Das-rebel/sota-browser.git
cd sota-browser
pip install -r requirements.txt
playwright install chromium
```

## Usage

### MCP Stdio Mode

```bash
python3 mcp_server.py
```

Configure in your MCP client:
```json
{
  "mcpServers": {
    "sota-browser": {
      "command": "python3",
      "args": ["/path/to/sota-browser/mcp_server.py"]
    }
  }
}
```

### HTTP REST Mode

```bash
python3 browser_http_server.py
# Server starts on http://localhost:9377
```

### Connect to Existing Chrome

```bash
# Start Chrome with remote debugging
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Run with CDP
CHROME_CDP_URL=http://localhost:9222 python3 mcp_server.py
```

## Tools (56 total)

### Session & Tab Management (8)

| Tool | Description |
|------|-------------|
| `browser_create_session` | Create isolated browser session (with proxy, UA, timezone, locale) |
| `browser_close_session` | Close session and all tabs |
| `browser_create_tab` | Open new tab (optionally navigate to URL) |
| `browser_close_tab` | Close specific tab |
| `browser_list_tabs` | List all tabs in session |
| `browser_switch_tab` | Switch to tab by index |
| `browser_info` | Server status (sessions, tabs, version) |
| `browser_set_viewport` | Resize viewport for a tab |

### Navigation (6)

| Tool | Description |
|------|-------------|
| `browser_navigate` | Navigate to URL |
| `browser_go_back` | Navigate back in history |
| `browser_go_forward` | Navigate forward in history |
| `browser_reload` | Reload current page |
| `browser_wait_for_navigation` | Wait for URL change or pattern match |
| `browser_wait_for_selector` | Wait for element to appear |

### Interaction (8)

| Tool | Description |
|------|-------------|
| `browser_click` | Click by selector/ref/coordinates |
| `browser_type` | Type text into element |
| `browser_hover` | Hover over element |
| `browser_drag_drop` | Drag and drop between elements |
| `browser_press_key` | Press keyboard key |
| `browser_scroll` | Scroll page by delta |
| `browser_select_option` | Select option in `<select>` dropdown |
| `browser_upload_file` | Upload file to `<input type="file">` |

### Snapshot & Extraction (8)

| Tool | Description |
|------|-------------|
| `browser_snapshot` | Accessibility tree + element refs + optional screenshot |
| `browser_get_state` | Indexed clickable elements with bounding boxes |
| `browser_get_html` | Raw HTML of page or element |
| `browser_get_text` | Lightweight text-only extraction |
| `browser_screenshot` | Capture screenshot (viewport or full-page) |
| `browser_extract_images` | Extract all `<img>` src/alt/dimensions |
| `browser_extract_links` | Extract all `<a>` hrefs + text |
| `browser_get_console_logs` | Capture console messages |

### Frames & IFrames (5)

| Tool | Description |
|------|-------------|
| `browser_list_frames` | List all frames with URLs and origins |
| `browser_evaluate` | Execute JS (main frame or specific frame) |
| `browser_evaluate_in_frame` | Execute JS in frame by URL match |
| `browser_get_frame_content` | Get HTML from specific frame |
| `browser_inject_all_frames` | Run JS in ALL frames, collect results |

### Network Interception (4)

| Tool | Description |
|------|-------------|
| `browser_intercept_request` | Block/modify/mock network requests |
| `browser_mock_response` | Return canned response for URL pattern |
| `browser_get_network_log` | Get all intercepted request/response pairs |
| `browser_wait_for_network_idle` | Wait until no network activity |

### Downloads (3)

| Tool | Description |
|------|-------------|
| `browser_download_file` | Download file by clicking trigger |
| `browser_wait_for_download` | Wait for download to complete |
| `browser_handle_dialog` | Accept/dismiss JS dialogs |

### Cookies (3)

| Tool | Description |
|------|-------------|
| `browser_import_cookies` | Import cookies into session |
| `browser_export_cookies` | Export current session cookies |
| `browser_clear_cookies` | Clear all session cookies |

### Wait & Timing (3)

| Tool | Description |
|------|-------------|
| `browser_wait` | Explicit wait (fixed seconds) |
| `browser_wait_for_selector` | Wait for element to appear/disappear |
| `browser_wait_for_network_idle` | Wait for network quiescence |

### HTTP Direct (4)

| Tool | Description |
|------|-------------|
| `browser_http_get` | Direct HTTP GET (no browser) |
| `browser_http_post` | Direct HTTP POST |
| `browser_http_put` | Direct HTTP PUT |
| `browser_http_delete` | Direct HTTP DELETE |

### Form Engine (6)

| Tool | Description |
|------|-------------|
| `browser_parse_resume` | Parse plain-text resume into structured profile |
| `browser_analyze_form` | Detect form type + fields + buttons |
| `browser_fill_form` | Fill form from profile dict |
| `browser_fill_form_from_resume` | One-shot: parse resume + fill form |
| `browser_fill_form_page` | Fill + click Next for multi-page forms |
| `browser_submit_form` | Auto-detect and click Submit |

**Supported form types:** Google Forms, Greenhouse, Workday, Lever, Material UI, Ant Design, standard HTML. **50+ semantic field types** recognized.

## Architecture

```
sota-browser/
├── mcp_server.py              # Entry point — JSON-RPC stdio (163 lines)
├── browser_http_server.py     # Entry point — HTTP REST
├── browser_manager.py         # Core: browser lifecycle, sessions, tabs
├── config.py                  # Constants (timeouts, viewports)
├── form_engine.py             # Rule-based form filler (no LLM)
├── tools/                     # 13 tool modules
│   ├── navigation.py          # navigate, go_back, go_forward, reload, waits
│   ├── interaction.py         # click, type, hover, drag_drop, press_key, scroll, select, upload
│   ├── snapshot.py            # snapshot, get_state, get_html, screenshot, extract_*, get_text
│   ├── frames.py              # list_frames, evaluate_in_frame, get_frame_content, inject_all
│   ├── network.py             # intercept_request, mock_response, get_network_log, wait_idle
│   ├── download.py            # download_file, wait_for_download
│   ├── dialog.py              # handle_dialog
│   ├── cookies.py             # import, export, clear cookies
│   ├── session_tools.py       # create/close session, tabs, info, viewport
│   ├── http_tools.py          # http_get, http_post, http_put, http_delete
│   ├── form_tools.py          # parse_resume, analyze_form, fill_form, submit
│   └── wait.py                # wait, wait_for_selector, wait_for_network_idle
├── middleware/                 # 6 middleware stages
│   ├── guardrails.py          # Injection detection + PII redaction
│   ├── cost_tracker.py        # Per-session cost tracking + budget
│   ├── semantic_cache.py      # Trigram Jaccard cache (no embedding API)
│   ├── circuit_breaker.py     # Per-domain failure tracking
│   ├── retry.py               # Exponential backoff + jitter
│   └── memory.py              # BrowserMemoryTree for contextual recall
├── models/                    # Data classes
│   ├── session.py             # Session (id, context, metadata, cost)
│   ├── tab.py                 # Tab (id, page, session_id)
│   └── result.py              # ToolResult (success, data, error_type)
├── mcp_client.py              # Python client library
├── Dockerfile                 # Container deployment
├── requirements.txt           # Python dependencies
└── pyproject.toml             # Project metadata
```

## Testing

```bash
python3 test_overhaul.py
# 213 tests across 15 categories, all passing
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROME_CDP_URL` | (none) | Connect to existing Chrome via CDP WebSocket |
| `BH_HEADLESS` | `true` | Run headless vs headed browser |
| `BH_DEBUG_CLICKS` | `false` | Show click overlays |

## License

MIT
