"""Debug buttons on ezto page."""

import asyncio
from browser_controller import BrowserController


async def main():
    browser = BrowserController(url_keywords=["ezto.mheducation"])
    await browser.connect()

    await asyncio.sleep(2)

    print("=== Looking for Next/Submit buttons ===")
    selectors = [
        "button:has-text('Next')",
        "button:has-text('Continue')",
        "button:has-text('Submit')",
        "a:has-text('Next')",
        "a:has-text('Continue')",
        "[data-automation-id]",
        "button",
        "a",
    ]

    for sel in selectors:
        try:
            count = await browser.get_element_count(sel)
            if count > 0:
                texts = await browser.get_all_texts(sel)
                print(f"\n{sel}: {count} elements")
                for t in texts[:5]:
                    if t.strip():
                        print(f"  - {t.strip()[:50]}")
        except Exception as e:
            pass

    print("\n=== All links ===")
    try:
        links = await browser.page.query_selector_all("a")
        for link in links[:15]:
            try:
                text = await link.inner_text()
                href = await link.get_attribute("href")
                if text.strip():
                    print(f"  {text.strip()[:40]} -> {href}")
            except:
                pass
    except Exception as e:
        print(f"Error: {e}")

    await browser.close()


asyncio.run(main())
