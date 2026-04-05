"""Debug parse flow - see where it hangs."""

import asyncio
from browser_controller import BrowserController
from question_parser import QuestionParser


async def test():
    browser = BrowserController(url_keywords=["ezto.mheducation"])
    await browser.connect()

    url = browser.page.url.lower()
    print("URL:", url)
    print("Is ezto:", "ezto.mheducation" in url)

    await asyncio.sleep(1)

    parser = QuestionParser(browser)

    # Test just the selectors first
    print("\n=== Testing question_type selectors ===")
    for sel in parser.SELECTORS["question_type"][:3]:
        try:
            text = await browser.get_text(sel, timeout=2000)
            print(f"  {sel}: {text[:50] if text else 'empty'}")
        except Exception as e:
            print(f"  {sel}: error - {e}")

    print("\n=== Testing question_text selectors ===")
    for sel in parser.SELECTORS["question_text"][:3]:
        try:
            text = await browser.get_text(sel, timeout=2000)
            print(f"  {sel}: {text[:50] if text else 'empty'}")
        except Exception as e:
            print(f"  {sel}: error - {e}")

    print("\n=== Testing option selectors ===")
    for sel in parser.SELECTORS["options"][:3]:
        try:
            count = await browser.get_element_count(sel)
            print(f"  {sel}: {count} elements")
        except Exception as e:
            print(f"  {sel}: error - {e}")

    await browser.close()


asyncio.run(test())
