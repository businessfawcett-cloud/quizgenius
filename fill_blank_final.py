#!/usr/bin/env python3
"""Fill in the blank question - final version"""

import asyncio
from browser_controller import BrowserController


async def fill_blank_final():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    print("Page title:", await browser.page.title())

    # Fill the fill-in-the-blank input
    await browser.page.fill("#fitbTesting_response0", "bomb calorimeter")
    print("Filled answer: bomb calorimeter")

    await asyncio.sleep(1)

    # Click High confidence button
    try:
        await browser.page.click("button:has-text('High')")
        print("Clicked High confidence")
    except Exception as e:
        print(f"Error clicking High: {e}")

    await asyncio.sleep(1)

    # Click Next button
    try:
        await browser.page.click("button:has-text('Next')")
        print("Clicked Next")
    except Exception as e:
        print(f"Error clicking Next: {e}")

    await asyncio.sleep(3)

    # Check new page state
    print("\nNew page title:", await browser.page.title())

    await browser.close()


if __name__ == "__main__":
    asyncio.run(fill_blank_final())
