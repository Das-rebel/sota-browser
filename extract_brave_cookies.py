#!/usr/bin/env python3
"""
Extract session cookies from Brave browser for Enhancv.
Uses SQLite to read Brave's cookie database.

Note: Brave/Chrome cookies are encrypted with the user's keychain.
This script works if:
1. The keychain is unlocked (user recently logged in)
2. We're running as the same user

For better security, users should export cookies manually from Brave DevTools.
"""

import sqlite3
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional


def get_brave_cookie_path() -> Path:
    """Get path to Brave's cookie database."""
    return (
        Path.home() / "Library" / "Application Support" 
        / "BraveSoftware" / "Brave-Browser" / "Default" / "Cookies"
    )


def extract_cookies_for_domain(domain: str = "enhancv.com") -> List[Dict]:
    """
    Extract cookies for a specific domain from Brave browser.
    
    Args:
        domain: Domain to extract cookies for (default: enhancv.com)
    
    Returns:
        List of cookie dictionaries in Netscape format
    """
    cookie_path = get_brave_cookie_path()
    
    if not cookie_path.exists():
        print(f"Brave cookie database not found at {cookie_path}")
        return []
    
    # Copy the database to avoid locking issues
    import tempfile
    import shutil
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        shutil.copy(str(cookie_path), tmp.name)
        tmp_path = tmp.name
    
    try:
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()
        
        # Query for enhancv cookies (only non-encrypted ones)
        # Note: Chrome/Brave encrypts cookies using the system's keychain, so only
        # some cookies (likely from extensions or non-secure contexts) are readable
        cursor.execute("""
            SELECT host_key, name, value, path, is_secure, expires_utc
            FROM cookies 
            WHERE host_key LIKE ? AND encrypted_value = ''
            ORDER BY creation_utc DESC
        """, (f"%{domain}%",))
        
        cookies = []
        for row in cursor.fetchall():
            cookies.append({
                "domain": row[0],
                "name": row[1],
                "value": row[2],
                "path": row[3],
                "secure": bool(row[4]),
                "expires": row[5],
                "isSecure": bool(row[4]),
                "isHttpOnly": False  # Not available in this query
            })
        
        conn.close()
        
    finally:
        os.unlink(tmp_path)
    
    return cookies


def export_netscape_format(cookies: List[Dict]) -> str:
    """
    Export cookies in Netscape format for browser-import tools.
    Format: domain\tinclude_subdomains\tpath\tsecure\texpires\tname\tvalue
    """
    lines = ["# Netscape HTTP Cookie File"]
    
    for c in cookies:
        # Determine if this is a domain cookie (starts with .)
        include_subdomains = "TRUE" if c["domain"].startswith(".") else "FALSE"
        secure = "TRUE" if c["secure"] else "FALSE"
        expires = str(c["expires"]) if c["expires"] else "0"
        path = c["path"] or "/"
        
        line = f"{c['domain']}\t{include_subdomains}\t{path}\t{secure}\t{expires}\t{c['name']}\t{c['value']}"
        lines.append(line)
    
    return "\n".join(lines)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract cookies from Brave browser")
    parser.add_argument("--domain", default="enhancv.com", help="Domain to extract cookies for")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--format", choices=["json", "netscape"], default="json",
                       help="Output format")
    
    args = parser.parse_args()
    
    cookies = extract_cookies_for_domain(args.domain)
    
    if not cookies:
        print(f"No cookies found for {args.domain}")
        print("Make sure you're logged into Brave and have visited the site.")
        sys.exit(1)
    
    print(f"Found {len(cookies)} cookies for {args.domain}")
    
    if args.format == "json":
        output = json.dumps(cookies, indent=2)
    else:
        output = export_netscape_format(cookies)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
