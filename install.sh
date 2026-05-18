#!/bin/bash
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "=== SOTA Browser MCP Installation ==="

# Create venv
[ ! -d "venv" ] && python3 -m venv venv
source venv/bin/activate

# Install deps
pip install --upgrade pip
pip install playwright httpx uvicorn fastapi pydantic

# Install browser
playwright install chromium

# Make executable
chmod +x mcp_server.py mcp_client.py

# Create data dirs
mkdir -p ~/.mcp-browser/{profiles,cookies,logs}

echo ""
echo "=== Installed ==="
echo "Run MCP server: python3 mcp_server.py"
echo "Run HTTP server: python3 -m uvicorn src.server:app --port 9377"
echo ""
echo "19 tools available:"
echo "  browser_create_session, browser_create_tab, browser_navigate"
echo "  browser_snapshot, browser_click, browser_type, browser_scroll"
echo "  browser_press_key, browser_wait, browser_screenshot, browser_evaluate"
echo "  browser_extract_images, browser_list_tabs, browser_close_tab"
echo "  browser_http_get, browser_import_cookies, browser_info"
echo "  browser_upload_file, browser_close_session"
