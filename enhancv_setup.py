#!/usr/bin/env python3
"""
Setup script for Enhancv browser automation.

This script helps users:
1. Extract cookies from their Brave browser session
2. Store credentials securely in keychain
3. Test the connection to Enhancv

Usage:
    python3 enhancv_setup.py --action setup
    python3 enhancv_setup.py --action test
    python3 enhancv_setup.py --action extract-cookies
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from enhancv_browse import (
    EnhancvBrowser,
    EnhancvCredentialStore,
    CookieManager,
    EnhancvProfile
)
from extract_brave_cookies import extract_cookies_for_domain, export_netscape_format


async def setup(credentials: tuple[str, str] = None):
    """Interactive setup for Enhancv automation."""
    print("=" * 60)
    print("Enhancv Browser Automation Setup")
    print("=" * 60)
    
    if not credentials:
        print("\n📝 Enter your Enhancv credentials (stored in macOS Keychain):")
        email = input("Email: ").strip()
        password = input("Password: ").strip()
        
        if not email or not password:
            print("❌ Credentials required for setup")
            return False
        
        credentials = (email, password)
    
    # Save credentials
    EnhancvCredentialStore.save(credentials[0], credentials[1])
    print("✅ Credentials saved to Keychain")
    
    # Try to extract cookies from Brave
    print("\n🔍 Checking for existing Brave browser session...")
    cookies = extract_cookies_for_domain("enhancv.com")
    
    if cookies:
        print(f"   Found {len(cookies)} cookies from Brave")
        
        # Save cookies
        CookieManager.save_cookies("brave-import", cookies)
        print("✅ Cookies saved for session reuse")
    else:
        print("   No cookies found - will use credential login")
    
    # Test connection
    print("\n🧪 Testing connection...")
    success = await test_connection()
    
    if success:
        print("\n✅ Setup complete!")
        print("   You can now use enhancv_browse.py to automate Enhancv")
    else:
        print("\n⚠️  Setup completed but connection test failed")
        print("   Try running: python3 enhancv_setup.py --action test")
    
    return success


async def test_connection():
    """Test connection to Enhancv."""
    browser = EnhancvBrowser(headless=True, use_direct=True)  # Use direct mode
    
    try:
        # Check if we can load cookies
        saved_cookies = CookieManager.load_cookies()
        
        if saved_cookies:
            print("   Found saved cookies, importing...")
            await browser._ensure_session()
            # Would need to implement cookie import in browser
            # For now, fall back to login
        
        # Try login
        if EnhancvCredentialStore.has_credentials():
            print("   Attempting login...")
            success = await browser.login()
            if success:
                print("   ✅ Logged in successfully")
                
                # Get profile
                print("   Fetching profile...")
                profile = await browser.get_profile()
                print(f"   👤 {profile.name or profile.full_name or 'No name'}")
                print(f"   📧 {profile.email or 'No email'}")
                print(f"   💼 {len(profile.experience)} experience entries")
                print(f"   🎓 {len(profile.education)} education entries")
                print(f"   🛠️  {len(profile.skills)} skills")
                
                return True
            else:
                print("   ❌ Login failed")
                return False
        else:
            print("   ⚠️  No credentials found")
            print("   Run: python3 enhancv_setup.py --action setup")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    finally:
        await browser.close()


async def extract_cookies():
    """Extract cookies from Brave and save them."""
    print("🔍 Extracting cookies from Brave browser...")
    
    cookies = extract_cookies_for_domain("enhancv.com")
    
    if not cookies:
        print("❌ No cookies found")
        print("   Make sure you're logged into Enhancv in Brave browser")
        return False
    
    print(f"✅ Found {len(cookies)} cookies")
    
    # Save to file
    CookieManager.save_cookies("brave-import", cookies)
    
    # Also export in netscape format for reference
    netscape_format = export_netscape_format(cookies)
    output_file = Path.home() / ".filly" / "enhancv_cookies.txt"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(netscape_format)
    
    print(f"✅ Cookies saved to {output_file}")
    return True


async def get_profile():
    """Get and display the user's Enhancv profile."""
    browser = EnhancvBrowser(use_direct=True)
    
    try:
        logged_in = await browser.login()
        if not logged_in:
            print("❌ Login failed")
            return
        
        profile = await browser.get_profile()
        
        print("\n📋 Enhancv Profile:")
        print("-" * 40)
        print(f"Name:     {profile.name or profile.full_name}")
        print(f"Email:    {profile.email}")
        print(f"Phone:    {profile.phone}")
        print(f"Location: {profile.location}")
        print(f"LinkedIn: {profile.linkedin}")
        print(f"Headline: {profile.headline}")
        print(f"\nSummary:\n{profile.summary[:200]}..." if profile.summary else "")
        
        print(f"\nExperience ({len(profile.experience)}):")
        for exp in profile.experience[:3]:
            print(f"  • {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')}")
        
        print(f"\nEducation ({len(profile.education)}):")
        for edu in profile.education[:3]:
            print(f"  • {edu.get('degree', 'N/A')} at {edu.get('school', 'N/A')}")
        
        print(f"\nSkills ({len(profile.skills)}):")
        print(f"  {', '.join(profile.skills[:10])}")
        
        return profile
        
    finally:
        await browser.close()



async def list_resumes():
    """List all resumes in the user's Enhancv account."""
    browser = EnhancvBrowser(use_direct=True)
    
    try:
        logged_in = await browser.login()
        if not logged_in:
            print("❌ Login failed")
            return
        
        resumes = await browser.get_resumes()
        
        print(f"\n📄 Found {len(resumes)} resumes:")
        print("-" * 40)
        
        for r in resumes:
            print(f"  • {r.title} (ID: {r.id})")
            print(f"    Created: {r.created_at}")
            print(f"    Updated: {r.updated_at}")
            print()
        
        return resumes
        
    finally:
        await browser.close()



async def export_pdf(resume_id: str = None, output_path: str = None):
    """Export a resume as PDF."""
    browser = EnhancvBrowser(use_direct=True)
    
    try:
        logged_in = await browser.login()
        if not logged_in:
            print("❌ Login failed")
            return
        
        if not resume_id:
            # List resumes first
            resumes = await browser.get_resumes()
            if resumes:
                resume_id = resumes[0].id
                print(f"Exporting first resume: {resumes[0].title}")
            else:
                print("❌ No resumes found")
                return
        
        pdf_bytes = await browser.export_pdf(resume_id)
        
        if output_path:
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
            print(f"✅ PDF saved to {output_path}")
        else:
            output = f"enhancv_resume_{resume_id}.pdf"
            with open(output, "wb") as f:
                f.write(pdf_bytes)
            print(f"✅ PDF saved to {output}")
        
        return pdf_bytes
        
    finally:
        await browser.close()


def main():
    parser = argparse.ArgumentParser(description="Enhancv Browser Automation Setup")
    parser.add_argument("--action", "-a", 
                       choices=["setup", "test", "extract-cookies", "profile", "resumes", "export-pdf"],
                       default="test",
                       help="Action to perform")
    parser.add_argument("--email", help="Enhancv email")
    parser.add_argument("--password", help="Enhancv password")
    parser.add_argument("--resume-id", help="Resume ID for PDF export")
    parser.add_argument("--output", "-o", help="Output path for PDF export")
    
    args = parser.parse_args()
    
    credentials = (args.email, args.password) if args.email and args.password else None
    
    if args.action == "setup":
        asyncio.run(setup(credentials))
    elif args.action == "test":
        asyncio.run(test_connection())
    elif args.action == "extract-cookies":
        asyncio.run(extract_cookies())
    elif args.action == "profile":
        asyncio.run(get_profile())
    elif args.action == "resumes":
        asyncio.run(list_resumes())
    elif args.action == "export-pdf":
        asyncio.run(export_pdf(args.resume_id, args.output))


if __name__ == "__main__":
    main()
