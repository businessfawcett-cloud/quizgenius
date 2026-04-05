"""Debug what's on the page after parsing."""

import asyncio
from browser_controller import BrowserController


async def main():
    browser = BrowserController(url_keywords=["ezto.mheducation"])
    await browser.connect()

    await asyncio.sleep(2)

    body = await browser.get_text("body", timeout=3000)
    print("=== BODY TEXT ===")
    print(body[:2000])

    print("\n=== Checking for wrong-answer indicators ===")
    body_lower = body.lower()
    indicators = [
        "return to question",
        "select a concept resource to continue",
        "you must review a resource",
        "your answer incorrect",
        "before moving on, you must review",
    ]
    for ind in indicators:
        if ind in body_lower:
            print(f"  FOUND: {ind}")

    await browser.close()


asyncio.run(main())
