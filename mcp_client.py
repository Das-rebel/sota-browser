#!/usr/bin/env python3
"""
PI Browser MCP Client
Connects to the SOTA Browser MCP server and provides tools for PI.

Usage:
    python3 mcp_client.py
    
Or configure in PI's MCP settings to connect to http://localhost:9377
"""

import asyncio
import base64
import json
import os
import sys
from typing import Optional

import httpx

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_HOST = os.environ.get("MCP_BROWSER_HOST", "http://localhost:9377")
API_KEY = os.environ.get("MCP_BROWSER_API_KEY", os.environ.get("CAMOFOX_API_KEY", ""))

# =============================================================================
# MCP Tools Definition
# =============================================================================

TOOLS = [
    {
        "name": "browser_create_session",
        "description": "Create a new isolated browser session for a user. Each session has its own cookies, storage, and proxy settings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Unique identifier for the user/session owner"
                },
                "headless": {
                    "type": "boolean",
                    "description": "Run browser in headless mode (default: true)",
                    "default": True
                },
                "proxy": {
                    "type": "string",
                    "description": "Proxy URL (e.g., socks5://127.0.0.1:1080)"
                },
                "viewport_width": {
                    "type": "integer",
                    "description": "Viewport width in pixels",
                    "default": 1920
                },
                "viewport_height": {
                    "type": "integer",
                    "description": "Viewport height in pixels",
                    "default": 1080
                }
            },
            "required": ["user_id"]
        }
    },
    {
        "name": "browser_create_tab",
        "description": "Create a new tab in an existing browser session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID from browser_create_session"
                }
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "browser_navigate",
        "description": "Navigate a tab to a URL. Returns page info including URL, title, and HTTP status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID"
                },
                "tab_id": {
                    "type": "string",
                    "description": "The tab ID"
                },
                "url": {
                    "type": "string",
                    "description": "URL to navigate to (https://...)"
                }
            },
            "required": ["session_id", "tab_id", "url"]
        }
    },
    {
        "name": "browser_snapshot",
        "description": "Get an accessibility tree snapshot of the current page. Includes element refs (e1, e2, e3...) for reliable clicking/typeing. Returns the page tree, text content, and interactive elements.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID"
                },
                "tab_id": {
                    "type": "string",
                    "description": "The tab ID"
                },
                "screenshot": {
                    "type": "boolean",
                    "description": "Include base64 screenshot (default: false)"
                },
                "max_nodes": {
                    "type": "integer",
                    "description": "Maximum tree nodes (default: 500)"
                }
            },
            "required": ["session_id", "tab_id"]
        }
    },
    {
        "name": "browser_click",
        "description": "Click an element on the page. Use selector (CSS), ref (e1, e2...), or x/y coordinates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID"
                },
                "tab_id": {
                    "type": "string",
                    "description": "The tab ID"
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector to click"
                },
                "ref": {
                    "type": "string",
                    "description": "Element reference from browser_snapshot (e.g., e5)"
                },
                "x": {
                    "type": "number",
                    "description": "X coordinate if using absolute positioning"
                },
                "y": {
                    "type": "number",
                    "description": "Y coordinate if using absolute positioning"
                }
            },
            "required": ["session_id", "tab_id"]
        }
    },
    {
        "name": "browser_type",
        "description": "Type text into an element (textbox, search field, etc.).",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID"
                },
                "tab_id": {
                    "type": "string",
                    "description": "The tab ID"
                },
                "text": {
                    "type": "string",
                    "description": "Text to type"
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector for the input element"
                },
                "ref": {
                    "type": "string",
                    "description": "Element reference from browser_snapshot"
                }
            },
            "required": ["session_id", "tab_id", "text"]
        }
    },
    {
        "name": "browser_scroll",
        "description": "Scroll the page up or down.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID"
                },
                "tab_id": {
                    "type": "string",
                    "description": "The tab ID"
                },
                "dx": {
                    "type": "number",
                    "description": "Horizontal scroll delta in pixels",
                    "default": 0
                },
                "dy": {
                    "type": "number",
                    "description": "Vertical scroll delta in pixels (negative = up, positive = down)",
                    "default": -300
                }
            },
            "required": ["session_id", "tab_id"]
        }
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current page.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID"
                },
                "tab_id": {
                    "type": "string",
                    "description": "The tab ID"
                },
                "full": {
                    "type": "boolean",
                    "description": "Capture entire page, not just viewport",
                    "default": False
                },
                "path": {
                    "type": "string",
                    "description": "File path to save screenshot"
                }
            },
            "required": ["session_id", "tab_id"]
        }
    },
    {
        "name": "browser_evaluate",
        "description": "Execute arbitrary JavaScript in the page context. Useful for extracting data, interacting with complex widgets, or automating dynamic content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID"
                },
                "tab_id": {
                    "type": "string",
                    "description": "The tab ID"
                },
                "script": {
                    "type": "string",
                    "description": "JavaScript code to execute (can be multi-line)"
                }
            },
            "required": ["session_id", "tab_id", "script"]
        }
    },
    {
        "name": "browser_list_tabs",
        "description": "List all open tabs in a session.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID"
                }
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "browser_close_tab",
        "description": "Close a specific tab.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID"
                },
                "tab_id": {
                    "type": "string",
                    "description": "The tab ID to close"
                }
            },
            "required": ["session_id", "tab_id"]
        }
    },
    {
        "name": "browser_import_cookies",
        "description": "Import browser cookies (e.g., from authenticated sessions). Accepts cookies in Netscape format or as a list of cookie objects.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID"
                },
                "cookies": {
                    "type": "array",
                    "description": "List of cookie objects with name, value, domain, path, secure, expires"
                }
            },
            "required": ["session_id", "cookies"]
        }
    },
    {
        "name": "browser_close_session",
        "description": "Close a browser session and all its tabs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID to close"
                }
            },
            "required": ["session_id"]
        }
    },
    {
        "name": "browser_fetch",
        "description": "Fetch a URL using Scrapling's adaptive parsing engine with anti-detection capabilities. Better than direct HTTP for JavaScript-heavy sites.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch"
                },
                "selectors": {
                    "type": "array",
                    "description": "CSS selectors to extract (results are adaptive to page changes)"
                },
                "proxy": {
                    "type": "string",
                    "description": "Proxy URL"
                },
                "headless": {
                    "type": "boolean",
                    "description": "Use headless browser (default: true)"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_extract",
        "description": "Extract structured data from a URL using a JSON schema. Maps schema fields to CSS selectors for reliable extraction.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to extract from"
                },
                "schema": {
                    "type": "object",
                    "description": "JSON schema mapping field names to CSS selectors"
                }
            },
            "required": ["url", "schema"]
        }
    }
]

# =============================================================================
# MCP Client Implementation
# =============================================================================

class BrowserMCPClient:
    """HTTP-based MCP client for browser automation."""
    
    def __init__(self, host: str = DEFAULT_HOST, api_key: str = None):
        self.host = host.rstrip("/")
        self.api_key = api_key or API_KEY
        self.headers = {}
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key
    
    def _headers(self, extra: dict = None) -> dict:
        h = {**self.headers}
        if extra:
            h.update(extra)
        return h
    
    async def _request(self, method: str, path: str, **kwargs) -> dict:
        async with httpx.AsyncClient(base_url=self.host) as client:
            resp = await client.request(
                method,
                path,
                headers=self._headers(kwargs.pop("headers", None)),
                **kwargs
            )
            resp.raise_for_status()
            return resp.json()
    
    # --- Session Management ---
    
    async def create_session(self, user_id: str, **options) -> dict:
        """Create a new browser session."""
        return await self._request("POST", "/sessions", json={
            "user_id": user_id,
            **options
        })
    
    async def list_sessions(self) -> dict:
        """List all active sessions."""
        return await self._request("GET", "/sessions")
    
    async def get_session(self, session_id: str) -> dict:
        """Get session details."""
        return await self._request("GET", f"/sessions/{session_id}")
    
    async def close_session(self, session_id: str) -> dict:
        """Close a session."""
        return await self._request("DELETE", f"/sessions/{session_id}")
    
    # --- Tab Management ---
    
    async def create_tab(self, session_id: str) -> dict:
        """Create a new tab."""
        return await self._request("POST", f"/sessions/{session_id}/tabs")
    
    async def list_tabs(self, session_id: str) -> dict:
        """List tabs in a session."""
        return await self._request("GET", f"/sessions/{session_id}/tabs")
    
    async def navigate(self, session_id: str, tab_id: str, url: str) -> dict:
        """Navigate to URL."""
        return await self._request("POST", f"/sessions/{session_id}/tabs/{tab_id}/navigate", json={"url": url})
    
    async def close_tab(self, session_id: str, tab_id: str) -> dict:
        """Close a tab."""
        return await self._request("DELETE", f"/sessions/{session_id}/tabs/{tab_id}")
    
    # --- Page Interaction ---
    
    async def snapshot(self, session_id: str, tab_id: str, 
                       screenshot: bool = False, max_nodes: int = 500) -> dict:
        """Get page snapshot."""
        return await self._request("GET", f"/sessions/{session_id}/tabs/{tab_id}/snapshot",
                                  params={"screenshot": screenshot, "max_nodes": max_nodes})
    
    async def click(self, session_id: str, tab_id: str, 
                    selector: str = None, ref: str = None, x: float = None, y: float = None) -> dict:
        """Click element."""
        return await self._request("POST", f"/sessions/{session_id}/tabs/{tab_id}/click", json={
            "selector": selector, "ref": ref, "x": x, "y": y
        })
    
    async def type_text(self, session_id: str, tab_id: str,
                        text: str, selector: str = None, ref: str = None) -> dict:
        """Type text."""
        return await self._request("POST", f"/sessions/{session_id}/tabs/{tab_id}/type", json={
            "text": text, "selector": selector, "ref": ref
        })
    
    async def scroll(self, session_id: str, tab_id: str, dx: float = 0, dy: float = -300) -> dict:
        """Scroll page."""
        return await self._request("POST", f"/sessions/{session_id}/tabs/{tab_id}/scroll", json={
            "dx": dx, "dy": dy
        })
    
    async def screenshot(self, session_id: str, tab_id: str, 
                         full: bool = False, path: str = None) -> dict:
        """Take screenshot."""
        params = {"full": full}
        return await self._request("GET", f"/sessions/{session_id}/tabs/{tab_id}/screenshot", params=params)
    
    async def evaluate(self, session_id: str, tab_id: str, script: str) -> dict:
        """Execute JavaScript."""
        return await self._request("POST", f"/sessions/{session_id}/tabs/{tab_id}/evaluate", json={
            "script": script
        })
    
    # --- Cookies ---
    
    async def import_cookies(self, session_id: str, cookies: list) -> dict:
        """Import cookies."""
        return await self._request("POST", f"/sessions/{session_id}/cookies", json={"cookies": cookies})
    
    # --- Scraping ---
    
    async def fetch(self, url: str, selectors: list = None, proxy: str = None, headless: bool = True) -> dict:
        """Fetch URL with Scrapling."""
        return await self._request("POST", "/fetch", json={
            "url": url, "selectors": selectors or [], "proxy": proxy, "headless": headless
        })
    
    async def extract(self, url: str, schema: dict) -> dict:
        """Extract structured data."""
        return await self._request("POST", "/extract", json={"url": url, "schema": schema})
    
    # --- Health ---
    
    async def health(self) -> dict:
        """Health check."""
        return await self._request("GET", "/health")
    
    # --- MCP Protocol ---
    
    async def list_tools(self) -> list:
        """Return MCP tools manifest."""
        return TOOLS
    
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool by name with arguments."""
        method_map = {
            "browser_create_session": lambda: self.create_session(**arguments),
            "browser_create_tab": lambda: self.create_tab(**arguments),
            "browser_navigate": lambda: self.navigate(**arguments),
            "browser_snapshot": lambda: self.snapshot(**arguments),
            "browser_click": lambda: self.click(**arguments),
            "browser_type": lambda: self.type_text(**arguments),
            "browser_scroll": lambda: self.scroll(**arguments),
            "browser_screenshot": lambda: self.screenshot(**arguments),
            "browser_evaluate": lambda: self.evaluate(**arguments),
            "browser_list_tabs": lambda: self.list_tabs(**arguments),
            "browser_close_tab": lambda: self.close_tab(**arguments),
            "browser_import_cookies": lambda: self.import_cookies(**arguments),
            "browser_close_session": lambda: self.close_session(**arguments),
            "browser_fetch": lambda: self.fetch(**arguments),
            "browser_extract": lambda: self.extract(**arguments),
        }
        
        if tool_name not in method_map:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        return await method_map[tool_name]()

# =============================================================================
# PI Integration Helper
# =============================================================================

async def demo_workflow():
    """Demonstrate a typical browser automation workflow."""
    client = BrowserMCPClient()
    
    print("Creating session...")
    session = await client.create_session(user_id="pi-demo", headless=True)
    print(f"  Session ID: {session['id']}")
    
    print("\nCreating tab...")
    tab = await client.create_tab(session_id=session['id'])
    print(f"  Tab ID: {tab['id']}")
    
    print("\nNavigating to example.com...")
    info = await client.navigate(session_id=session['id'], tab_id=tab['id'], url="https://example.com")
    print(f"  Title: {info.get('title', 'N/A')}")
    
    print("\nGetting snapshot...")
    snap = await client.snapshot(session_id=session['id'], tab_id=tab['id'])
    print(f"  Elements found: {len(snap.get('elements', {}))}")
    print(f"  Tree nodes: {len(snap.get('tree', []))}")
    
    print("\nTaking screenshot...")
    shot = await client.screenshot(session_id=session['id'], tab_id=tab['id'])
    if shot.get("base64"):
        print(f"  Screenshot: {len(shot['base64'])} bytes (base64)")
    
    print("\nClosing session...")
    await client.close_session(session['id'])
    print("  Done!")

if __name__ == "__main__":
    print("=== SOTA Browser MCP Client ===\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        asyncio.run(demo_workflow())
    else:
        # Print configuration info
        print(f"Server: {DEFAULT_HOST}")
        print(f"API Key: {'Set' if API_KEY else 'Not set (anonymous)'}")
        print(f"\nTools available: {len(TOOLS)}")
        print("\nConfigure PI to connect to this MCP server:")
        print(f"  MCP_HOST={DEFAULT_HOST}")
        print("  MCP_BROWSER_API_KEY=<your-key>")
        print("\nOr run: python3 -m uvicorn src.server:app --reload")