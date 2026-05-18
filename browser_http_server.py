#!/usr/bin/env python3
"""
Standalone HTTP Browser Server
A lightweight HTTP server that exposes browser automation via simple REST API.
Used by enhancv_browse.py for PRO plan Enhancv automation.

Start: python3 browser_http_server.py [--port 9377]
"""

import asyncio
import base64
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import parse_qs

# Try to use built-in HTTP server first
try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading
    USE_BUILTIN = True
except ImportError:
    USE_BUILTIN = False

# Fallback to asyncio if needed
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Playwright
try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# =============================================================================
# Browser Manager (simplified from mcp_server.py)
# =============================================================================

class SimpleBrowserManager:
    """Simplified browser manager for HTTP server."""
    
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self.sessions: Dict[str, dict] = {}
        self._lock = asyncio.Lock()
    
    async def start(self):
        self._playwright = await async_playwright().start()
        
        # Check for existing Chrome
        cdp_url = os.environ.get("CHROME_CDP_URL", "")
        if cdp_url:
            try:
                self._browser = await self._playwright.chromium.connect_over_cdp(cdp_url, timeout=20000)
                print("[browser-http] Connected to existing Chrome via CDP")
                return
            except Exception as e:
                print(f"[browser-http] CDP connection failed: {e}, launching fresh browser")
        
        # Launch fresh browser
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        print("[browser-http] Browser launched (headless)")
    
    async def create_session(self, user_id: str) -> Dict[str, Any]:
        """Create a new browser session."""
        async with self._lock:
            session_id = str(uuid.uuid4())
            
            context = await self._browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            self.sessions[session_id] = {
                "context": context,
                "page": page,
                "user_id": user_id
            }
            
            return {"session_id": session_id, "tab_id": session_id}
    
    async def close_session(self, session_id: str) -> Dict[str, Any]:
        """Close a session."""
        async with self._lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                await session["page"].close()
                await session["context"].close()
                del self.sessions[session_id]
                return {"success": True}
            return {"error": "Session not found"}
    
    async def navigate(self, session_id: str, url: str) -> Dict[str, Any]:
        """Navigate to URL."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        page = self.sessions[session_id]["page"]
        try:
            response = await page.goto(url, wait_until="networkidle", timeout=30000)
            return {
                "url": page.url,
                "title": await page.title(),
                "status": response.status if response else None
            }
        except Exception as e:
            return {"error": str(e), "url": page.url}
    
    async def snapshot(self, session_id: str, screenshot: bool = False) -> Dict[str, Any]:
        """Get page snapshot."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        page = self.sessions[session_id]["page"]
        
        # Get accessibility tree
        tree = await page.accessibility.snapshot()
        
        result = {
            "url": page.url,
            "title": await page.title(),
            "tree": tree,
            "text": await page.inner_text("body")
        }
        
        if screenshot:
            img = await page.screenshot()
            result["screenshot"] = base64.b64encode(img).decode()
        
        return result
    
    async def click(self, session_id: str, selector: str = None, ref: str = None, x: float = None, y: float = None) -> Dict[str, Any]:
        """Click element."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        page = self.sessions[session_id]["page"]
        
        try:
            if x is not None and y is not None:
                await page.mouse.click(x, y)
            elif selector:
                await page.click(selector)
            else:
                return {"error": "Need selector or coordinates"}
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}
    
    async def type_text(self, session_id: str, text: str, selector: str = None) -> Dict[str, Any]:
        """Type text."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        page = self.sessions[session_id]["page"]
        
        try:
            if selector:
                await page.fill(selector, text)
            else:
                await page.keyboard.type(text)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}
    
    async def evaluate(self, session_id: str, script: str) -> Dict[str, Any]:
        """Execute JavaScript."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        page = self.sessions[session_id]["page"]
        
        try:
            result = await page.evaluate(script)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}
    
    async def scroll(self, session_id: str, dx: float = 0, dy: float = -300) -> Dict[str, Any]:
        """Scroll page."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        page = self.sessions[session_id]["page"]
        
        try:
            if dx or dy:
                await page.evaluate(f"window.scrollBy({dx}, {dy})")
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}
    
    async def press_key(self, session_id: str, key: str) -> Dict[str, Any]:
        """Press key."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        page = self.sessions[session_id]["page"]
        
        try:
            await page.keyboard.press(key)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}
    
    async def screenshot(self, session_id: str, full: bool = False) -> Dict[str, Any]:
        """Take screenshot."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        page = self.sessions[session_id]["page"]
        
        try:
            img = await page.screenshot(full_page=full)
            return {"base64": base64.b64encode(img).decode()}
        except Exception as e:
            return {"error": str(e)}
    
    async def list_tabs(self, session_id: str) -> Dict[str, Any]:
        """List tabs."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        # For simplicity, each session is one tab
        return {"tabs": [{"tab_id": session_id, "url": self.sessions[session_id]["page"].url}]}
    
    async def close_tab(self, session_id: str, tab_id: str) -> Dict[str, Any]:
        """Close tab (same as close session for now)."""
        return await self.close_session(session_id)
    
    async def import_cookies(self, session_id: str, cookies: list) -> Dict[str, Any]:
        """Import cookies."""
        if session_id not in self.sessions:
            return {"error": "Session not found"}
        
        context = self.sessions[session_id]["context"]
        
        try:
            for cookie in cookies:
                await context.add_cookies([{
                    "name": cookie.get("name"),
                    "value": cookie.get("value"),
                    "domain": cookie.get("domain", ".enhancv.com"),
                    "path": cookie.get("path", "/"),
                    "secure": cookie.get("secure", True),
                    "httpOnly": cookie.get("isHttpOnly", False),
                }])
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}
    
    async def wait(self, session_id: str, seconds: float = 1) -> Dict[str, Any]:
        """Wait."""
        await asyncio.sleep(seconds)
        return {"success": True}
    
    async def shutdown(self):
        """Shutdown browser."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()


# =============================================================================
# HTTP Request Handler
# =============================================================================

browser_manager: Optional[SimpleBrowserManager] = None
executor = ThreadPoolExecutor(max_workers=4)


class BrowserHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for browser automation API."""
    
    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length:
            return json.loads(self.rfile.read(content_length))
        return {}
    
    async def _async_handle(self, method: str, path: str, query: dict, body: dict):
        global browser_manager
        
        # Parse path
        parts = path.strip("/").split("/")
        
        # Health check
        if path == "/health":
            return {"status": "ok", "sessions": len(browser_manager.sessions) if browser_manager else 0}
        
        # CORS preflight
        if method == "OPTIONS":
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        
        # API routes
        if len(parts) < 2:
            return {"error": "Invalid path"}
        
        resource = parts[0]
        action_parts = parts[1:]
        
        if resource == "sessions":
            if method == "POST":
                # Create session
                user_id = body.get("user_id", "anonymous")
                result = await browser_manager.create_session(user_id)
                return result
            
            elif len(action_parts) >= 1:
                session_id = action_parts[0]
                
                if method == "DELETE":
                    return await browser_manager.close_session(session_id)
                
                # Tab operations
                if len(action_parts) >= 2:
                    operation = action_parts[1]
                    
                    if operation == "navigate" and method == "POST":
                        url = body.get("url")
                        if url:
                            return await browser_manager.navigate(session_id, url)
                        return {"error": "url required"}
                    
                    elif operation == "snapshot" and method == "GET":
                        screenshot = query.get("screenshot", ["false"])[0].lower() == "true"
                        return await browser_manager.snapshot(session_id, screenshot)
                    
                    elif operation == "click" and method == "POST":
                        return await browser_manager.click(
                            session_id,
                            selector=body.get("selector"),
                            x=body.get("x"),
                            y=body.get("y")
                        )
                    
                    elif operation == "type" and method == "POST":
                        text = body.get("text")
                        selector = body.get("selector")
                        if text:
                            return await browser_manager.type_text(session_id, text, selector)
                        return {"error": "text required"}
                    
                    elif operation == "evaluate" and method == "POST":
                        script = body.get("script")
                        if script:
                            return await browser_manager.evaluate(session_id, script)
                        return {"error": "script required"}
                    
                    elif operation == "scroll" and method == "POST":
                        return await browser_manager.scroll(
                            session_id,
                            dx=body.get("dx", 0),
                            dy=body.get("dy", -300)
                        )
                    
                    elif operation == "screenshot" and method == "GET":
                        full = query.get("full", ["false"])[0].lower() == "true"
                        return await browser_manager.screenshot(session_id, full)
                    
                    elif operation == "press_key" and method == "POST":
                        key = body.get("key")
                        if key:
                            return await browser_manager.press_key(session_id, key)
                        return {"error": "key required"}
                    
                    elif operation == "wait" and method == "POST":
                        seconds = body.get("seconds", 1)
                        return await browser_manager.wait(session_id, seconds)
                    
                    elif operation == "cookies" and method == "POST":
                        cookies = body.get("cookies", [])
                        return await browser_manager.import_cookies(session_id, cookies)
                    
                    elif operation == "tabs" and method == "GET":
                        return await browser_manager.list_tabs(session_id)
                
                return await browser_manager.snapshot(session_id)
        
        return {"error": "Unknown endpoint"}
    
    def do_GET(self):
        query = parse_qs(self.path.split("?")[1] if "?" in self.path else "")
        path = self.path.split("?")[0]
        
        # Run async handler in thread pool
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self._async_handle("GET", path, query, {}))
            if result is not None:
                self._send_json(result)
        finally:
            loop.close()
    
    def do_POST(self):
        body = self._read_json()
        query = parse_qs(self.path.split("?")[1] if "?" in self.path else "")
        path = self.path.split("?")[0]
        
        # Determine method from body or default to POST
        method = body.pop("_method", "POST")
        
        # Run async handler in thread pool
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self._async_handle(method, path, query, body))
            if result is not None:
                self._send_json(result)
        finally:
            loop.close()
    
    def do_DELETE(self):
        body = self._read_json()
        query = parse_qs(self.path.split("?")[1] if "?" in self.path else "")
        path = self.path.split("?")[0]
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self._async_handle("DELETE", path, query, body))
            if result is not None:
                self._send_json(result)
        finally:
            loop.close()
    
    def log_message(self, format, *args):
        # Suppress log noise
        if "health" not in args[0]:
            print(f"[browser-http] {args[0]}")


async def main(port: int = 9377):
    global browser_manager
    
    print(f"Starting Browser HTTP Server on port {port}...")
    
    # Initialize browser
    browser_manager = SimpleBrowserManager()
    await browser_manager.start()
    
    # Start HTTP server
    server = HTTPServer(("0.0.0.0", port), BrowserHTTPHandler)
    print(f"Browser HTTP Server ready at http://localhost:{port}")
    print(f"  GET  /health                    - Health check")
    print(f"  POST /sessions                  - Create session")
    print(f"  POST /sessions/:id/navigate     - Navigate")
    print(f"  GET  /sessions/:id/snapshot     - Get page snapshot")
    print(f"  POST /sessions/:id/click        - Click element")
    print(f"  POST /sessions/:id/type         - Type text")
    print(f"  POST /sessions/:id/evaluate     - Run JavaScript")
    print(f"  POST /sessions/:id/screenshot   - Take screenshot")
    print(f"  DELETE /sessions/:id           - Close session")
    print()
    
    try:
        await asyncio.Event().wait()  # Run forever
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await browser_manager.shutdown()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Browser HTTP Server")
    parser.add_argument("--port", "-p", type=int, default=9377)
    args = parser.parse_args()
    
    asyncio.run(main(args.port))
