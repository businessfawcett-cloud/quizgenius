"""Debug script to see what's on the ezto quiz page."""

import asyncio
from browser_controller import BrowserController


async def main():
    browser = BrowserController(url_keywords=["ezto.mheducation"])
    await browser.connect()

    print("\n=== PAGE URL ===")
    print(browser.page.url)

    print("\n=== BODY TEXT (first 5000 chars) ===")
    try:
        body = await browser.get_text("body", timeout=5000)
        print(body[:5000])
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== LOOKING FOR QUESTION ELEMENTS ===")
    selectors = [
        ".question",
        ".prompt",
        ".question-text",
        "[class*='question']",
        "h1",
        "h2",
        "h3",
    ]
    for sel in selectors:
        try:
            count = await browser.get_element_count(sel)
            if count > 0:
                print(f"  {sel}: {count} elements")
                texts = await browser.get_all_texts(sel)
                for t in texts[:3]:
                    print(f"    - {t[:100]}")
        except:
            pass

    await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
