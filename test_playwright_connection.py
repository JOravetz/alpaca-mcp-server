#!/usr/bin/env python3
"""
Test script to verify Playwright MCP server connection
Run this after restarting Claude Code
"""

def test_playwright_connection():
    """Instructions for testing Playwright MCP connection"""
    
    print("=" * 60)
    print("PLAYWRIGHT MCP SERVER CONNECTION TEST")
    print("=" * 60)
    print()
    print("📋 Steps to verify Playwright MCP server connection:")
    print()
    print("1. Exit Claude Code by pressing 'Esc'")
    print()
    print("2. Restart Claude Code by running: claude")
    print()
    print("3. Once Claude Code restarts, run the /mcp command")
    print()
    print("4. You should see 'playwright' listed as connected")
    print()
    print("5. You can then use Playwright tools like:")
    print("   - browser_navigate: Navigate to a URL")
    print("   - browser_screenshot: Take a screenshot")
    print("   - browser_click: Click on elements")
    print("   - browser_fill: Fill in forms")
    print("   - browser_evaluate: Execute JavaScript")
    print()
    print("=" * 60)
    print("Example usage after connection:")
    print("=" * 60)
    print()
    print("Ask Claude to:")
    print("'Navigate to google.com and take a screenshot'")
    print("'Fill in a search form and submit it'")
    print("'Extract data from a webpage'")
    print()

if __name__ == "__main__":
    test_playwright_connection()