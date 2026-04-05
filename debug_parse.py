"""Debug parse flow."""

import asyncio
from browser_controller import BrowserController
from question_parser import QuestionParser


async def test():
    browser = BrowserController(url_keywords=["ezto.mheducation"])
    await browser.connect()

    url = browser.page.url.lower()
    print("URL:", url)
    print("Is ezto:", "ezto.mheducation" in url)

    # Wait for page to be ready
    await asyncio.sleep(1)

    parser = QuestionParser(browser)

    print("\n=== Testing _extract ===")
    try:
        q = await parser._extract()
        print("Question:", q.question_text[:50] if q.question_text else None)
        print("Options:", len(q.options))
    except Exception as e:
        print("_extract error:", e)

    print("\n=== Testing fallback ===")
    try:
        q = await parser._extract_ezto_fallback()
        if q:
            print("Question:", q.question_text[:50])
            print("Options:", len(q.options))
        else:
            print("Fallback returned None")
    except Exception as e:
        print("Fallback error:", e)

    await browser.close()


asyncio.run(test())
