"""Diagnostic script — dumps the page HTML so we can see the real DOM structure."""

import asyncio
from browser_controller import BrowserController


async def main():
    browser = BrowserController()
    await browser.connect()

    # Dump the full page text to see what's there
    body_text = await browser.get_text("body", timeout=10_000)
    print("=== PAGE TEXT ===")
    print(body_text[:3000])
    print("=== END ===")

    # Dump the HTML to a file for inspection
    html = await browser.page_content()
    with open("page_dump.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("\nFull HTML saved to page_dump.html")

    await browser.close()


asyncio.run(main())
