#!/usr/bin/env python3
"""
Enhancv Browser Automation Module
Uses sota-browser MCP to control Enhancv web app (PRO-compatible, no API needed).

Capabilities (PRO plan sufficient):
- Login to enhancv.com
- Get existing resume profile data
- Create new resume from structured data
- Export resume as PDF
- List all resumes

Uses browser session cookies to authenticate (no API key required).
Credentials stored securely via system keychain.

Usage:
    from enhancv_browse import EnhancvBrowser
    
    browser = EnhancvBrowser()
    browser.login()  # or use existing session
    profile = browser.get_profile()
    pdf_bytes = browser.export_pdf(resume_id="xxx")
"""

import asyncio
import base64
import json
import os
import sys
import keyring
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path

# Add parent dir for imports
sys.path.insert(0, str(Path(__file__).parent))

# Try to import MCP client (requires HTTP server)
try:
    from mcp_client import BrowserMCPClient
    HAS_MCP_CLIENT = True
except ImportError:
    HAS_MCP_CLIENT = False

# Try to import Playwright for direct mode
try:
    from playwright.async_api import async_playwright, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# Import ResumeParser from form_engine for data normalization
try:
    from form_engine import ResumeParser
    HAS_RESUME_PARSER = True
except ImportError:
    HAS_RESUME_PARSER = False

# =============================================================================
# Configuration
# =============================================================================

ENHANCV_BASE_URL = "https://enhancv.com"
ENHANCV_APP_URL = "https://app.enhancv.com"
ENHANCV_API_URL = "https://api.enhancv.com"

CREDENTIAL_SERVICE = "filly-enhancv"
SESSION_COOKIE_FILE = Path.home() / ".filly" / "enhancv_cookies.json"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class EnhancvProfile:
    """Parsed profile data from Enhancv.
    
    Compatible with ResumeParser output format.
    """
    # Basic info
    name: str = ""
    full_name: str = ""
    first_name: str = ""
    last_name: str = ""
    headline: str = ""
    summary: str = ""
    
    # Contact
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""
    
    # Experience & Education (compatible with ResumeParser format)
    experience: List[Dict] = field(default_factory=list)
    education: List[Dict] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    
    # Current positions (derived)
    current_title: str = ""
    current_company: str = ""
    highest_degree: str = ""
    school: str = ""
    
    # Raw data
    raw_json: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for form filling."""
        return {
            "name": self.full_name or self.name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "headline": self.headline,
            "summary": self.summary,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "linkedin": self.linkedin,
            "github": self.github,
            "website": self.website,
            "experience": self.experience,
            "education": self.education,
            "skills": self.skills,
            "languages": self.languages,
            "certifications": self.certifications,
            "current_title": self.current_title,
            "current_company": self.current_company,
            "highest_degree": self.highest_degree,
            "school": self.school,
        }
    
    @classmethod
    def from_resume_parser(cls, data: Dict) -> "EnhancvProfile":
        """Create from ResumeParser output."""
        profile = cls()
        profile.full_name = data.get("full_name", "")
        profile.first_name = data.get("first_name", "")
        profile.last_name = data.get("last_name", "")
        profile.name = f"{profile.first_name} {profile.last_name}".strip()
        profile.email = data.get("email", "")
        profile.phone = data.get("phone", "")
        profile.linkedin = data.get("linkedin", "")
        profile.github = data.get("github", "")
        profile.website = data.get("website", "")
        profile.experience = data.get("experience", [])
        profile.education = data.get("education", [])
        profile.skills = data.get("skills", [])
        profile.languages = data.get("languages", [])
        profile.current_title = data.get("current_title", "")
        profile.current_company = data.get("current_company", "")
        profile.highest_degree = data.get("highest_degree", "")
        profile.school = data.get("school", "")
        profile.raw_json = data
        return profile


@dataclass
class EnhancvResume:
    """Enhancv resume metadata."""
    id: str
    title: str
    created_at: str
    updated_at: str
    is_primary: bool = False


# =============================================================================
# Credential Management
# =============================================================================

class EnhancvCredentialStore:
    """Secure credential storage via system keychain."""
    
    @staticmethod
    def save(email: str, password: str) -> None:
        """Store credentials securely in system keychain."""
        keyring.set_password(CREDENTIAL_SERVICE, "email", email)
        keyring.set_password(CREDENTIAL_SERVICE, "password", password)
        # Also store in memory for session
        EnhancvCredentialStore._cached_creds = (email, password)
    
    @staticmethod
    def load() -> Optional[tuple[str, str]]:
        """Load credentials from keychain."""
        email = keyring.get_password(CREDENTIAL_SERVICE, "email")
        password = keyring.get_password(CREDENTIAL_SERVICE, "password")
        if email and password:
            EnhancvCredentialStore._cached_creds = (email, password)
            return (email, password)
        return None
    
    @staticmethod
    def clear() -> None:
        """Remove credentials from keychain."""
        try:
            keyring.delete_password(CREDENTIAL_SERVICE, "email")
            keyring.delete_password(CREDENTIAL_SERVICE, "password")
        except Exception:
            pass
        EnhancvCredentialStore._cached_creds = None
    
    @staticmethod
    def has_credentials() -> bool:
        """Check if credentials exist."""
        return EnhancvCredentialStore.load() is not None


# =============================================================================
# Cookie Management  
# =============================================================================

class CookieManager:
    """Manages session cookies for Enhancv browser sessions."""
    
    @staticmethod
    def save_cookies(session_id: str, cookies: List[Dict]) -> None:
        """Save cookies to file for reuse."""
        SESSION_COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSION_COOKIE_FILE, 'w') as f:
            json.dump({"session_id": session_id, "cookies": cookies}, f)
    
    @staticmethod
    def load_cookies() -> Optional[Dict]:
        """Load saved cookies if they exist."""
        if SESSION_COOKIE_FILE.exists():
            with open(SESSION_COOKIE_FILE, 'r') as f:
                return json.load(f)
        return None
    
    @staticmethod
    def clear_cookies() -> None:
        """Clear saved cookies."""
        if SESSION_COOKIE_FILE.exists():
            SESSION_COOKIE_FILE.unlink()


# =============================================================================
# Direct Playwright Adapter (no HTTP server needed)
# =============================================================================

class DirectBrowserAdapter:
    """
    Direct Playwright browser adapter.
    Used when HTTP MCP server is not available.
    """
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
    
    async def start(self):
        """Start browser."""
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright not installed. Run: pip install playwright")
        
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ]
        )
    
    async def create_session(self, user_id: str = "default") -> tuple:
        """Create session. Returns (session_id, tab_id)."""
        if not self._browser:
            await self.start()
        
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        self._page = await self._context.new_page()
        session_id = user_id
        return session_id, session_id
    
    async def navigate(self, url: str, timeout: int = 30000):
        """Navigate to URL."""
        response = await self._page.goto(url, wait_until="networkidle", timeout=timeout)
        return {
            "url": self._page.url,
            "title": await self._page.title(),
            "status": response.status if response else None
        }
    
    async def snapshot(self, screenshot: bool = False):
        """Get page snapshot."""
        tree = await self._page.accessibility.snapshot()
        result = {
            "url": self._page.url,
            "title": await self._page.title(),
            "tree": tree,
            "text": await self._page.inner_text("body")
        }
        if screenshot:
            img = await self._page.screenshot()
            result["screenshot"] = base64.b64encode(img).decode()
        return result
    
    async def click(self, selector: str = None, ref: str = None, x: float = None, y: float = None):
        """Click element."""
        if x is not None and y is not None:
            await self._page.mouse.click(x, y)
        elif selector:
            await self._page.click(selector)
        return {"success": True}
    
    async def type_text(self, text: str, selector: str = None):
        """Type text."""
        if selector:
            await self._page.fill(selector, text)
        else:
            await self._page.keyboard.type(text)
        return {"success": True}
    
    async def evaluate(self, script: str):
        """Execute JavaScript."""
        result = await self._page.evaluate(script)
        return {"result": result}
    
    async def scroll(self, dx: float = 0, dy: float = -300):
        """Scroll page."""
        await self._page.evaluate(f"window.scrollBy({dx}, {dy})")
        return {"success": True}
    
    async def press_key(self, key: str):
        """Press key."""
        await self._page.keyboard.press(key)
        return {"success": True}
    
    async def screenshot(self, full: bool = False):
        """Take screenshot."""
        img = await self._page.screenshot(full_page=full)
        return {"base64": base64.b64encode(img).decode()}
    
    async def import_cookies(self, cookies: List[Dict]):
        """Import cookies."""
        for cookie in cookies:
            await self._context.add_cookies([{
                "name": cookie.get("name"),
                "value": cookie.get("value"),
                "domain": cookie.get("domain", ".enhancv.com"),
                "path": cookie.get("path", "/"),
                "secure": cookie.get("secure", True),
            }])
        return {"success": True}
    
    async def wait(self, seconds: float = 1):
        """Wait."""
        await asyncio.sleep(seconds)
        return {"success": True}
    
    async def close_session(self):
        """Close session."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        return {"success": True}
    
    async def shutdown(self):
        """Shutdown browser."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()


# =============================================================================
# Main Enhancv Browser Class
# =============================================================================

class EnhancvBrowser:
    """
    Browser automation for Enhancv web app.
    Works with PRO plan - no API key or Business plan needed.
    
    Supports two modes:
    1. HTTP MCP mode - uses BrowserMCPClient to connect to HTTP server
    2. Direct mode - uses Playwright directly (no HTTP server needed)
    """
    
    def __init__(
        self, 
        mcp_host: str = None,
        mcp_api_key: str = None,
        headless: bool = True,
        user_id: str = "enhancv-user",
        use_direct: bool = None  # None = auto-detect
    ):
        """
        Initialize Enhancv browser automation.
        
        Args:
            mcp_host: MCP server host (default: http://localhost:9377)
            mcp_api_key: MCP API key if required
            headless: Run browser in headless mode
            user_id: Unique identifier for this user's browser session
            use_direct: Force direct Playwright mode (no HTTP server)
        """
        self.mcp_host = mcp_host or os.environ.get("MCP_BROWSER_HOST", "http://localhost:9377")
        self.mcp_api_key = mcp_api_key or os.environ.get("MCP_BROWSER_API_KEY", "")
        self.headless = headless
        self.user_id = user_id
        
        # Determine mode
        if use_direct is True:
            self._use_direct = True
        elif use_direct is False:
            self._use_direct = False
        else:
            # Auto-detect: try MCP, fall back to direct
            self._use_direct = not (HAS_MCP_CLIENT and HAS_PLAYWRIGHT)
        
        self._browser = None  # Direct adapter
        self._client = None  # MCP client
        
        self.session_id: Optional[str] = None
        self.tab_id: Optional[str] = None
        self._logged_in = False
    
    async def _get_browser(self) -> DirectBrowserAdapter:
        """Get or create direct browser adapter."""
        if self._browser is None:
            self._browser = DirectBrowserAdapter(headless=self.headless)
        return self._browser
    
    async def _get_client(self) -> BrowserMCPClient:
        """Get or create MCP client."""
        if self._client is None:
            self._client = BrowserMCPClient(
                host=self.mcp_host,
                api_key=self.mcp_api_key
            )
        return self._client
    
    # -------------------------------------------------------------------------
    # Session Management
    # -------------------------------------------------------------------------
    
    async def _ensure_session(self) -> tuple[str, str]:
        """Ensure we have an active browser session."""
        if not self.session_id:
            if self._use_direct:
                browser = await self._get_browser()
                self.session_id, self.tab_id = await browser.create_session(self.user_id)
            else:
                client = await self._get_client()
                result = await client.browser_create_session(
                    user_id=self.user_id,
                    headless=self.headless
                )
                self.session_id = result.get("session_id")
                
                # Create initial tab
                result = await client.browser_create_tab(self.session_id)
                tabs = result.get("tabs", [])
                self.tab_id = tabs[0].get("tab_id") if tabs else None
        
        return self.session_id, self.tab_id
    
    async def _navigate(self, url: str, timeout: int = 30000):
        """Navigate to URL."""
        if self._use_direct:
            browser = await self._get_browser()
            return await browser.navigate(url, timeout)
        else:
            client = await self._get_client()
            sid, tid = await self._ensure_session()
            return await client.browser_navigate(sid, tid, url)
    
    async def _snapshot(self, screenshot: bool = False):
        """Get page snapshot."""
        if self._use_direct:
            browser = await self._get_browser()
            return await browser.snapshot(screenshot)
        else:
            client = await self._get_client()
            sid, tid = await self._ensure_session()
            return await client.browser_snapshot(sid, tid, screenshot=screenshot)
    
    async def _click(self, selector: str = None, ref: str = None, x: float = None, y: float = None):
        """Click element."""
        if self._use_direct:
            browser = await self._get_browser()
            return await browser.click(selector=selector, x=x, y=y)
        else:
            client = await self._get_client()
            sid, tid = await self._ensure_session()
            return await client.browser_click(sid, tid, selector=selector, ref=ref, x=x, y=y)
    
    async def _type(self, text: str, selector: str = None, ref: str = None):
        """Type text."""
        if self._use_direct:
            browser = await self._get_browser()
            return await browser.type_text(text, selector)
        else:
            client = await self._get_client()
            sid, tid = await self._ensure_session()
            return await client.browser_type(sid, tid, text, selector=selector, ref=ref)
    
    async def _evaluate(self, script: str):
        """Execute JavaScript."""
        if self._use_direct:
            browser = await self._get_browser()
            return await browser.evaluate(script)
        else:
            client = await self._get_client()
            sid, tid = await self._ensure_session()
            return await client.browser_evaluate(sid, tid, script)
    
    async def _scroll(self, dx: float = 0, dy: float = -300):
        """Scroll page."""
        if self._use_direct:
            browser = await self._get_browser()
            return await browser.scroll(dx, dy)
        else:
            client = await self._get_client()
            sid, tid = await self._ensure_session()
            return await client.browser_scroll(sid, tid, dx=dx, dy=dy)
    
    async def _press_key(self, key: str):
        """Press key."""
        if self._use_direct:
            browser = await self._get_browser()
            return await browser.press_key(key)
        else:
            client = await self._get_client()
            sid, tid = await self._ensure_session()
            return await client.browser_press_key(sid, tid, key)
    
    async def _screenshot(self, full: bool = False):
        """Take screenshot."""
        if self._use_direct:
            browser = await self._get_browser()
            return await browser.screenshot(full)
        else:
            client = await self._get_client()
            sid, tid = await self._ensure_session()
            return await client.browser_screenshot(sid, tid, full=full)
    
    async def _import_cookies(self, cookies: List[Dict]):
        """Import cookies."""
        if self._use_direct:
            browser = await self._get_browser()
            return await browser.import_cookies(cookies)
        else:
            client = await self._get_client()
            sid, tid = await self._ensure_session()
            return await client.browser_import_cookies(sid, cookies)
    
    async def _wait(self, seconds: float = 1):
        """Wait."""
        if self._use_direct:
            browser = await self._get_browser()
            return await browser.wait(seconds)
        else:
            client = await self._get_client()
            sid, tid = await self._ensure_session()
            return await client.browser_wait(sid, tid, seconds)
    
    async def close(self):
        """Close the browser session."""
        if self._use_direct:
            if self._browser:
                await self._browser.close_session()
                await self._browser.shutdown()
                self._browser = None
        else:
            if self._client and self.session_id:
                await self._client.browser_close_session(self.session_id)
        self.session_id = None
        self.tab_id = None
        self._logged_in = False
    
    # -------------------------------------------------------------------------
    # Compatibility: expose 'client' property that delegates to either mode
    # This allows existing code using self.client.browser_* to work
    # -------------------------------------------------------------------------
    
    @property
    def client(self):
        """
        Compatibility property that returns a wrapper delegating to the correct mode.
        For direct mode, this returns self._browser_adapter.
        For MCP mode, this returns self._client.
        """
        return self
    
    # -------------------------------------------------------------------------
    # Cookie Import from Brave
    # -------------------------------------------------------------------------
    
    async def import_brave_cookies(self) -> bool:
        """
        Try to import cookies from Brave browser.
        Brave stores cookies in ~/Library/Application Support/BraveSoftware/Brave-Browser/
        
        Returns:
            True if cookies were imported and user is logged in
        """
        brave_cookie_path = (
            Path.home() / "Library" / "Application Support" 
            / "BraveSoftware" / "Brave-Browser" / "Default" / "Cookies"
        )
        
        if not brave_cookie_path.exists():
            print("Brave cookie database not found")
            return False
        
        # Note: Brave/Chrome cookies are encrypted with the user's keychain
        # We need to either:
        # 1. Use the system's keychain to decrypt (if same user)
        # 2. Export via Chrome DevTools Protocol
        # 3. Ask user to export cookies manually
        
        # For now, try to export via a script approach
        # This requires the user to have granted keychain access
        
        try:
            import sqlite3
            
            # Try to read the cookies database
            # Note: This may fail if cookies are encrypted
            conn = sqlite3.connect(str(brave_cookie_path))
            cursor = conn.cursor()
            
            # Note: Brave stores cookies with encrypted values in encrypted_value column.
            # For session cookies (non-persistent), we need to either:
            # 1. Use Chrome DevTools Protocol to export (requires browser connection)
            # 2. Have user export via Chrome settings manually
            # 3. Use loginsessioncookie approach
            
            # For now, try reading non-encrypted session cookies if any exist
            cursor.execute(
                "SELECT host_key, name, value, path, is_secure, expires_utc FROM cookies WHERE host_key LIKE '%enhancv%' AND encrypted_value = ''"
            )
            
            cookies = []
            for row in cursor.fetchall():
                cookies.append({
                    "domain": row[0],
                    "name": row[1],
                    "value": row[2],
                    "path": row[3],
                    "secure": bool(row[4]),
                    "expires": row[5]
                })
            
            conn.close()
            
            if cookies:
                session_id, tab_id = await self._ensure_session()
                await self._import_cookies(cookies)
                
                # Verify login by checking the session
                await self._navigate(ENHANCV_APP_URL)
                await asyncio.sleep(2)
                
                # Check if logged in
                snapshot = await self._snapshot()
                page_text = snapshot.get("text", "").lower()
                
                if "log in" not in page_text or "sign up" not in page_text:
                    self._logged_in = True
                    CookieManager.save_cookies(session_id, cookies)
                    return True
                    
        except Exception as e:
            print(f"Failed to import Brave cookies: {e}")
        
        return False
    
    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------
    
    async def login(self, email: str = None, password: str = None) -> bool:
        """
        Log into Enhancv.
        
        Args:
            email: Enhancv account email (stored in keychain if not provided)
            password: Enhancv account password (stored in keychain if not provided)
        
        Returns:
            True if login successful
        """
        # Get credentials if not provided
        if not email or not password:
            creds = EnhancvCredentialStore.load()
            if creds:
                email, password = creds
            else:
                raise ValueError(
                    "No credentials provided and none found in keychain. "
                    "Call EnhancvCredentialStore.save(email, password) first."
                )
        
        await self._ensure_session()
        
        # Navigate to login page
        await self._navigate(f"{ENHANCV_APP_URL}/login")
        await asyncio.sleep(2)
        
        # Take snapshot to see the page
        snapshot = await self._snapshot()
        
        # Find and fill email field
        # Common selectors for email input
        email_selectors = [
            "input[type='email']",
            "input[name='email']",
            "input[id='email']",
            "input[placeholder*='email' i]"
        ]
        
        for selector in email_selectors:
            try:
                await self._type(email, selector=selector)
                break
            except Exception:
                continue
        
        # Find and fill password field
        password_selectors = [
            "input[type='password']",
            "input[name='password']",
            "input[id='password']"
        ]
        
        for selector in password_selectors:
            try:
                await self._type(password, selector=selector)
                break
            except Exception:
                continue
        
        # Click login button
        login_selectors = [
            "button[type='submit']",
            "button:has-text('Log in')",
            "button:has-text('Sign in')",
            "button:has-text('Login')"
        ]
        
        for selector in login_selectors:
            try:
                await self._click(selector=selector)
                break
            except Exception:
                continue
        
        # Wait for navigation
        await asyncio.sleep(3)
        
        # Verify login
        snapshot = await self._snapshot()
        current_url = snapshot.get("url", "")
        
        if "login" not in current_url.lower():
            self._logged_in = True
            # Save cookies for next time
            # Note: We'd need to extract current cookies from session
            return True
        
        return False
    
    async def is_logged_in(self) -> bool:
        """Check if currently logged in by visiting the app."""
        if self._logged_in:
            return True
        
        try:
            await self._ensure_session()
            await self._navigate(ENHANCV_APP_URL)
            await asyncio.sleep(2)
            
            snapshot = await self._snapshot()
            page_text = snapshot.get("text", "").lower()
            current_url = snapshot.get("url", "")
            
            # If we're on app.enhancv.com and don't see login/signup, we're logged in
            if "app.enhancv.com" in current_url and "log in" not in page_text:
                self._logged_in = True
                return True
        except Exception:
            pass
        
        return False
    
    # -------------------------------------------------------------------------
    # Profile Operations
    # -------------------------------------------------------------------------
    
    async def get_profile(self) -> EnhancvProfile:
        """
        Get the user's Enhancv profile data.
        
        Navigates to the profile editor and extracts all profile fields.
        """
        if not await self.is_logged_in():
            raise Exception("Not logged in. Call login() first.")
        
        # Navigate to profile section
        await self._navigate(f"{ENHANCV_APP_URL}/profile")
        await asyncio.sleep(2)
        
        # Extract data using JavaScript
        script = """
        (function() {
            // Try multiple possible data sources
            const data = {};
            
            // 1. Check for Redux/NGRX store (common in React apps)
            const reduxState = window.__REDUX_DEVTOOLS_EXTENSION__?.getState?.();
            if (reduxState) {
                data.redux = reduxState;
            }
            
            // 2. Check for Next.js state
            const nextState = window.__NEXT_DATA__?.props?.pageProps;
            if (nextState) {
                data.next = nextState;
            }
            
            // 3. Try GraphQL cache
            const apolloClient = window.__APOLLO_CLIENT__ || window.apolloClient;
            if (apolloClient) {
                const cache = apolloClient.cache.extract();
                data.graphql = cache;
            }
            
            // 4. Fall back to DOM extraction
            const profile = {
                name: document.querySelector('[data-testid="name"], h1, .name')?.textContent?.trim(),
                headline: document.querySelector('[data-testid="headline"], .headline, h2')?.textContent?.trim(),
                summary: document.querySelector('[data-testid="summary"], .summary, .about')?.textContent?.trim(),
                email: document.querySelector('a[href^="mailto:"]')?.textContent?.trim(),
                phone: document.querySelector('a[href^="tel:"]')?.textContent?.trim(),
            };
            
            // Extract experience entries
            const experiences = [];
            document.querySelectorAll('.experience, [data-section="experience"], .work-history').forEach(el => {
                experiences.push({
                    title: el.querySelector('.title, h3')?.textContent?.trim(),
                    company: el.querySelector('.company, .employer')?.textContent?.trim(),
                    dates: el.querySelector('.dates, .date-range')?.textContent?.trim(),
                    description: el.querySelector('.description, .details')?.textContent?.trim()
                });
            });
            
            // Extract education entries
            const education = [];
            document.querySelectorAll('.education, [data-section="education"]').forEach(el => {
                education.push({
                    school: el.querySelector('.school, .institution')?.textContent?.trim(),
                    degree: el.querySelector('.degree, .field')?.textContent?.trim(),
                    dates: el.querySelector('.dates')?.textContent?.trim()
                });
            });
            
            // Extract skills
            const skills = [];
            document.querySelectorAll('.skill, [data-testid="skill"], .skills-list li').forEach(el => {
                const text = el.textContent?.trim();
                if (text) skills.push(text);
            });
            
            data.profile = profile;
            data.experiences = experiences;
            data.education = education;
            data.skills = skills;
            
            return data;
        })();
        """
        
        result = await self._evaluate(script)
        data = result.get("result", {})
        
        # Parse into EnhancvProfile
        profile = EnhancvProfile()
        
        if "profile" in data:
            p = data["profile"]
            profile.name = p.get("name", "")
            profile.headline = p.get("headline", "")
            profile.summary = p.get("summary", "")
            profile.email = p.get("email", "")
            profile.phone = p.get("phone", "")
        
        profile.experience = data.get("experiences", [])
        profile.education = data.get("education", [])
        profile.skills = data.get("skills", [])
        profile.raw_json = data
        
        # Normalize using ResumeParser if available
        if HAS_RESUME_PARSER:
            profile = self._normalize_with_resume_parser(profile)
        
        return profile
    
    def _normalize_with_resume_parser(self, profile: EnhancvProfile) -> EnhancvProfile:
        """
        Normalize profile data using ResumeParser.
        Converts raw scraped data into standardized format.
        """
        # Build text representation for ResumeParser
        text_parts = []
        
        if profile.name:
            text_parts.append(profile.name)
        if profile.headline:
            text_parts.append(profile.headline)
        if profile.summary:
            text_parts.append(profile.summary)
        if profile.email:
            text_parts.append(profile.email)
        if profile.phone:
            text_parts.append(profile.phone)
        
        # Add experience as text
        for exp in profile.experience:
            if exp.get("title"):
                text_parts.append(exp["title"])
            if exp.get("company"):
                text_parts.append(f"at {exp['company']}")
            if exp.get("dates"):
                text_parts.append(exp["dates"])
            if exp.get("description"):
                text_parts.append(exp["description"])
        
        # Add education as text
        for edu in profile.education:
            if edu.get("school"):
                text_parts.append(edu["school"])
            if edu.get("degree"):
                text_parts.append(edu["degree"])
            if edu.get("dates"):
                text_parts.append(edu["dates"])
        
        # Add skills
        text_parts.extend(profile.skills)
        
        combined_text = "\n".join(text_parts)
        
        try:
            parser = ResumeParser()
            # Run sync parse in async context
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                normalized = executor.submit(asyncio.run, parser.parse(combined_text))
                normalized_data = normalized.result()
            
            if normalized_data:
                # Merge normalized data back into profile
                if normalized_data.get("full_name"):
                    profile.full_name = normalized_data["full_name"]
                if normalized_data.get("first_name"):
                    profile.first_name = normalized_data["first_name"]
                if normalized_data.get("last_name"):
                    profile.last_name = normalized_data["last_name"]
                if normalized_data.get("email"):
                    profile.email = normalized_data["email"]
                if normalized_data.get("phone"):
                    profile.phone = normalized_data["phone"]
                if normalized_data.get("linkedin"):
                    profile.linkedin = normalized_data["linkedin"]
                if normalized_data.get("github"):
                    profile.github = normalized_data["github"]
                if normalized_data.get("website"):
                    profile.website = normalized_data["website"]
                if normalized_data.get("experience"):
                    profile.experience = normalized_data["experience"]
                if normalized_data.get("education"):
                    profile.education = normalized_data["education"]
                if normalized_data.get("skills"):
                    profile.skills = normalized_data["skills"]
                if normalized_data.get("languages"):
                    profile.languages = normalized_data["languages"]
                if normalized_data.get("current_title"):
                    profile.current_title = normalized_data["current_title"]
                if normalized_data.get("current_company"):
                    profile.current_company = normalized_data["current_company"]
                if normalized_data.get("highest_degree"):
                    profile.highest_degree = normalized_data["highest_degree"]
                if normalized_data.get("school"):
                    profile.school = normalized_data["school"]
        except Exception as e:
            print(f"ResumeParser normalization failed: {e}")
        
        return profile
    
    async def get_resumes(self) -> List[EnhancvResume]:
        """
        Get list of all resumes in the user's account.
        
        Returns:
            List of EnhancvResume objects
        """
        if not await self.is_logged_in():
            raise Exception("Not logged in. Call login() first.")
        
        await self._navigate(f"{ENHANCV_APP_URL}/resumes")
        await asyncio.sleep(2)
        
        # Extract resume list via JavaScript
        script = """
        (function() {
            const resumes = [];
            
            // Look for resume cards/list items
            document.querySelectorAll('[data-testid="resume-card"], .resume-card, .resume-item').forEach(el => {
                const id = el.id || el.dataset.resumeId || el.querySelector('[data-resume-id]')?.dataset.resumeId;
                const title = el.querySelector('h3, h4, .title')?.textContent?.trim();
                const dateEl = el.querySelector('.date, .updated, time');
                const created = dateEl?.textContent?.trim() || '';
                
                if (id && title) {
                    resumes.push({
                        id: id,
                        title: title,
                        created_at: created,
                        updated_at: created
                    });
                }
            });
            
            // If no cards found, try looking in a sidebar or list
            if (resumes.length === 0) {
                document.querySelectorAll('a[href*="/resume/"]').forEach(a => {
                    const href = a.getAttribute('href');
                    const match = href.match(/\\/resume\\/([^/]+)/);
                    if (match) {
                        resumes.push({
                            id: match[1],
                            title: a.textContent?.trim() || 'Untitled',
                            created_at: '',
                            updated_at: ''
                        });
                    }
                });
            }
            
            return resumes;
        })();
        """
        
        result = await self._evaluate(script)
        resume_data = result.get("result", [])
        
        return [
            EnhancvResume(
                id=r.get("id", ""),
                title=r.get("title", ""),
                created_at=r.get("created_at", ""),
                updated_at=r.get("updated_at", "")
            )
            for r in resume_data
        ]
    
    # -------------------------------------------------------------------------
    # Resume Creation
    # -------------------------------------------------------------------------
    
    async def create_resume(
        self, 
        profile: EnhancvProfile,
        title: str = "New Resume"
    ) -> str:
        """
        Create a new resume from profile data.
        
        Args:
            profile: EnhancvProfile object with all resume data
            title: Title for the new resume
        
        Returns:
            Resume ID of the created resume
        """
        if not await self.is_logged_in():
            raise Exception("Not logged in. Call login() first.")
        
        # Navigate to create new resume page
        await self._navigate(f"{ENHANCV_APP_URL}/resume/create")
        await asyncio.sleep(3)
        
        # Fill in basic info
        # This is highly dependent on Enhancv's current UI
        # These selectors will need to be updated as Enhancv changes
        
        # Name field
        try:
            await self._type(profile.name, selector="input[name='name'], #name-input")
        except Exception:
            pass
        
        # Headline/summary
        try:
            await self._type(profile.headline, selector="input[name='headline'], #headline, .headline-input")
        except Exception:
            pass
        
        # Summary/About
        try:
            await self._type(profile.summary, selector="textarea[name='summary'], #summary, .summary-textarea")
        except Exception:
            pass
        
        # Contact info
        if profile.email:
            try:
                await self._type(profile.email, selector="input[name='email'], #email")
            except Exception:
                pass
        
        # Add experience entries
        for exp in profile.experience:
            await self._add_experience(exp)
        
        # Add education entries
        for edu in profile.education:
            await self._add_education(edu)
        
        # Add skills
        for skill in profile.skills:
            await self._add_skill(skill)
        
        # Get the resume ID from URL
        snapshot = await self._snapshot()
        url = snapshot.get("url", "")
        
        # Extract resume ID from URL
        import re
        match = re.search(r'/resume/([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        
        return ""
    
    async def _add_experience(self, exp: Dict) -> None:
        """Add an experience entry to the resume being edited."""
        # Click "Add experience" button
        add_selectors = [
            "button:has-text('Add experience')",
            "button:has-text('Add Work')",
            "[data-testid='add-experience']",
            ".add-experience-btn"
        ]
        
        for selector in add_selectors:
            try:
                await self._click(selector=selector)
                break
            except Exception:
                continue
        
        await asyncio.sleep(1)
        
        # Fill experience fields
        if exp.get("title"):
            try:
                await self._type(exp["title"], selector="input[name='title'], #job-title")
            except Exception:
                pass
        
        if exp.get("company"):
            try:
                await self._type(exp["company"], selector="input[name='company'], #company")
            except Exception:
                pass
    
    async def _add_education(self, edu: Dict) -> None:
        """Add an education entry to the resume being edited."""
        add_selectors = [
            "button:has-text('Add education')",
            "button:has-text('Add School')",
            "[data-testid='add-education']"
        ]
        
        for selector in add_selectors:
            try:
                await self._click(selector=selector)
                break
            except Exception:
                continue
        
        await asyncio.sleep(1)
        
        if edu.get("school"):
            try:
                await self._type(edu["school"], selector="input[name='school'], #school")
            except Exception:
                pass
    
    async def _add_skill(self, skill: str) -> None:
        """Add a skill to the resume being edited."""
        try:
            await self._type(skill, selector="input[name='skills'], #skill-input, .skill-input")
            # Press Enter to add
            await self._press_key("Enter")
        except Exception:
            pass
    
    # -------------------------------------------------------------------------
    # PDF Export
    # -------------------------------------------------------------------------
    
    async def export_pdf(self, resume_id: str = None, output_path: str = None) -> bytes:
        """
        Export a resume as PDF.
        
        Args:
            resume_id: ID of resume to export (uses current if not provided)
            output_path: Optional path to save PDF
        
        Returns:
            PDF file as bytes
        """
        if not await self.is_logged_in():
            raise Exception("Not logged in. Call login() first.")
        
        if resume_id:
            await self._navigate(f"{ENHANCV_APP_URL}/resume/{resume_id}/edit")
            await asyncio.sleep(2)
        
        # Find and click export/PDF button
        export_selectors = [
            "button:has-text('Export PDF')",
            "button:has-text('Download PDF')",
            "[data-testid='export-pdf']",
            ".export-btn",
            "button:has-text('Export')",
            "a:has-text('PDF')"
        ]
        
        export_clicked = False
        for selector in export_selectors:
            try:
                await self._click(selector=selector)
                export_clicked = True
                break
            except Exception:
                continue
        
        if not export_clicked:
            # Try via menu
            menu_selectors = [
                "button:has-text('More')",
                "[data-testid='menu']",
                ".menu-btn"
            ]
            for selector in menu_selectors:
                try:
                    await self._click(selector=selector)
                    await asyncio.sleep(1)
                    # Try export again
                    for export_sel in export_selectors:
                        try:
                            await self._click(selector=export_sel)
                            export_clicked = True
                            break
                        except Exception:
                            continue
                    if export_clicked:
                        break
                except Exception:
                    continue
        
        # Wait for download
        await asyncio.sleep(3)
        
        # Try to find the downloaded file
        # sota-browser should handle downloads - check default download location
        download_dir = Path.home() / "Downloads"
        pdf_files = list(download_dir.glob("*.pdf"))
        
        if pdf_files:
            # Get most recent PDF
            latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)
            
            if output_path:
                import shutil
                shutil.copy(latest_pdf, output_path)
            
            with open(latest_pdf, "rb") as f:
                pdf_bytes = f.read()
            
            # Clean up downloaded file
            latest_pdf.unlink()
            
            return pdf_bytes
        
        # Alternative: try to capture via CDP (Chrome DevTools Protocol)
        # This requires more sophisticated browser handling
        
        raise Exception("Could not export PDF - download not detected")
    
    # -------------------------------------------------------------------------
    # High-Level Operations
    # -------------------------------------------------------------------------
    
    async def sync_to_profile(self, profile: EnhancvProfile) -> str:
        """
        Update the user's Enhancv profile with new data.
        Creates a new resume and returns its ID.
        """
        return await self.create_resume(profile, title=f"Resume - {profile.name}")
    
    async def full_sync(self, profile: EnhancvProfile) -> Dict[str, Any]:
        """
        Perform a full sync: get existing profile, update, export PDF.
        
        Returns dict with:
            - existing_profile: EnhancvProfile
            - new_resume_id: str  
            - pdf_bytes: bytes
        """
        # Get existing
        existing = await self.get_profile()
        
        # Create new resume
        new_id = await self.create_resume(profile)
        
        # Export PDF
        pdf_bytes = await self.export_pdf(new_id)
        
        return {
            "existing_profile": existing,
            "new_resume_id": new_id,
            "pdf_bytes": pdf_bytes
        }


# =============================================================================
# MCP Tool Wrapper
# =============================================================================

class EnhancvMCPAdapter:
    """
    Adapter to expose EnhancvBrowser as MCP tools.
    Can be registered with the FillY MCP server.
    """
    
    TOOLS = [
        {
            "name": "enhancv_login",
            "description": "Log into Enhancv with stored or provided credentials",
            "input_schema": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "password": {"type": "string"}
                }
            }
        },
        {
            "name": "enhancv_get_profile",
            "description": "Get the user's Enhancv profile data",
            "input_schema": {"type": "object", "properties": {} }
        },
        {
            "name": "enhancv_get_resumes",
            "description": "List all resumes in the user's Enhancv account",
            "input_schema": {"type": "object", "properties": {} }
        },
        {
            "name": "enhancv_create_resume",
            "description": "Create a new resume from structured profile data",
            "input_schema": {
                "type": "object",
                "properties": {
                    "profile_json": {"type": "string"},
                    "title": {"type": "string"}
                }
            }
        },
        {
            "name": "enhancv_export_pdf",
            "description": "Export a resume as PDF bytes",
            "input_schema": {
                "type": "object", 
                "properties": {
                    "resume_id": {"type": "string"}
                }
            }
        }
    ]
    
    def __init__(self):
        self.browser = EnhancvBrowser()
    
    async def handle_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Route tool call to appropriate method."""
        
        if tool_name == "enhancv_login":
            success = await self.browser.login(
                email=arguments.get("email"),
                password=arguments.get("password")
            )
            return {"success": success}
        
        elif tool_name == "enhancv_get_profile":
            profile = await self.browser.get_profile()
            return {
                "name": profile.name,
                "headline": profile.headline,
                "summary": profile.summary,
                "email": profile.email,
                "experience": profile.experience,
                "education": profile.education,
                "skills": profile.skills
            }
        
        elif tool_name == "enhancv_get_resumes":
            resumes = await self.browser.get_resumes()
            return {
                "resumes": [
                    {"id": r.id, "title": r.title, "created": r.created_at}
                    for r in resumes
                ]
            }
        
        elif tool_name == "enhancv_create_resume":
            import json
            profile_data = json.loads(arguments.get("profile_json", "{}"))
            profile = EnhancvProfile(**profile_data)
            resume_id = await self.browser.create_resume(
                profile, 
                title=arguments.get("title", "New Resume")
            )
            return {"resume_id": resume_id}
        
        elif tool_name == "enhancv_export_pdf":
            pdf_bytes = await self.browser.export_pdf(
                resume_id=arguments.get("resume_id")
            )
            # Return as base64
            return {"pdf_base64": base64.b64encode(pdf_bytes).decode()}
        
        return {"error": f"Unknown tool: {tool_name}"}


# =============================================================================
# CLI / Main
# =============================================================================

async def main():
    """CLI for testing Enhancv browser automation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhancv Browser Automation")
    parser.add_argument("--email", help="Enhancv email")
    parser.add_argument("--password", help="Enhancv password")
    parser.add_argument("--action", default="profile", 
                       choices=["login", "profile", "resumes", "create", "export"])
    parser.add_argument("--resume-id", help="Resume ID for export")
    parser.add_argument("--save-creds", action="store_true", help="Save credentials to keychain")
    
    args = parser.parse_args()
    
    browser = EnhancvBrowser()
    
    try:
        if args.save_creds and args.email and args.password:
            EnhancvCredentialStore.save(args.email, args.password)
            print("Credentials saved to keychain")
        
        if args.action == "login":
            success = await browser.login(args.email, args.password)
            print(f"Login successful: {success}")
        
        elif args.action == "profile":
            profile = await browser.get_profile()
            print(json.dumps({
                "name": profile.name,
                "headline": profile.headline,
                "summary": profile.summary[:100] + "..." if len(profile.summary) > 100 else profile.summary,
                "skills_count": len(profile.skills)
            }, indent=2))
        
        elif args.action == "resumes":
            resumes = await browser.get_resumes()
            print(f"Found {len(resumes)} resumes:")
            for r in resumes:
                print(f"  - {r.title} ({r.id})")
        
        elif args.action == "export":
            pdf_bytes = await browser.export_pdf(args.resume_id)
            output = f"enhancv_resume_{args.resume_id or 'current'}.pdf"
            with open(output, "wb") as f:
                f.write(pdf_bytes)
            print(f"Exported PDF to {output}")
    
    finally:
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
