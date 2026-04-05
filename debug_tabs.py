"""Debug tab selection."""

import asyncio
from browser_controller import BrowserController


async def main():
    browser = BrowserController()
    await browser.connect()

    print("=== All tabs ===")
    for ctx in browser._browser.contexts:
        for page in ctx.pages:
            print(f"  {page.url}")

    await browser.close()


asyncio.run(main())
