#!/usr/bin/env python3
"""Debug current page state"""

import asyncio
from browser_controller import BrowserController


async def check_current_page():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    print("Page title:", await browser.page.title())
    print("Page URL:", browser.page.url)

    # Get question text
    try:
        text = await browser.page.inner_text("[role='main']")
        print("\nMain content:")
        print(text[:500])
    except Exception as e:
        print(f"Error getting main content: {e}")

    await browser.close()


if __name__ == "__main__":
    asyncio.run(check_current_page())
