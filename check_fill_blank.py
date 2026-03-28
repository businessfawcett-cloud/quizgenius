#!/usr/bin/env python3
"""Check fill in blank question and try to answer"""

import asyncio
from browser_controller import BrowserController


async def check_fill_blank():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    print("Page title:", await browser.page.title())

    # Look for input fields
    inputs = await browser.page.query_selector_all("input")
    print(f"Found {len(inputs)} input elements")

    # Look for textareas
    textareas = await browser.page.query_selector_all("textarea")
    print(f"Found {len(textareas)} textarea elements")

    # Try to find any button
    buttons = await browser.page.query_selector_all("button")
    print(f"Found {len(buttons)} button elements")
    for btn in buttons[:10]:
        try:
            text = await btn.inner_text()
            print(f"  Button: {text}")
        except:
            pass

    # Get full page text
    text = await browser.page.inner_text("[role='main']")
    print("\nPage content:")
    print(text[:500])

    await browser.close()


if __name__ == "__main__":
    asyncio.run(check_fill_blank())
