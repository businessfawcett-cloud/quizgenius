#!/usr/bin/env python3
"""Debug script to see what's on the McGraw Hill page"""

import asyncio
from browser_controller import BrowserController


async def debug_page():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    # Get page content
    content = await browser.page.content()

    # Save HTML to file
    with open("page_debug.html", "w", encoding="utf-8") as f:
        f.write(content)

    print("Page title:", await browser.page.title())
    print("Page URL:", browser.page.url)

    # Try to find question elements
    selectors = [
        "[data-automation-id='question-prompt']",
        ".question-text",
        ".question-prompt",
        "[role='main']",
        "h2",
        "h3",
    ]

    for sel in selectors:
        try:
            els = await browser.page.query_selector_all(sel)
            if els:
                print(f"\nFound {len(els)} elements for selector: {sel}")
                for i, el in enumerate(els[:3]):
                    text = await el.inner_text()
                    print(f"  {i}: {text[:100]}...")
        except Exception as e:
            print(f"Error with {sel}: {e}")

    # Take screenshot
    await browser.page.screenshot("page_debug.png")
    print("\nScreenshot saved to page_debug.png")
    print("HTML saved to page_debug.html")

    await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_page())
