#!/usr/bin/env python3
"""Navigate through McGraw Hill questions"""

import asyncio
from browser_controller import BrowserController


async def navigate_questions():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    for i in range(20):  # Try 20 times
        print(f"\n=== Attempt {i + 1} ===")
        print("Page title:", await browser.page.title())

        # Check current URL
        print("URL:", browser.page.url)

        # Try to find and click Next Question button
        selectors = [
            "button:has-text('Next Question')",
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "[data-automation-id='next-button']",
        ]

        clicked = False
        for sel in selectors:
            try:
                btn = await browser.page.query_selector(sel)
                if btn:
                    await btn.click()
                    print(f"Clicked: {sel}")
                    clicked = True
                    await asyncio.sleep(2)
                    break
            except:
                pass

        if not clicked:
            print("No next button found, trying refresh...")
            await browser.page.reload()
            await asyncio.sleep(3)

        await asyncio.sleep(2)

    await browser.close()


if __name__ == "__main__":
    asyncio.run(navigate_questions())
