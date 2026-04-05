"""Quick test of ezto fallback."""

import asyncio
from browser_controller import BrowserController


async def main():
    browser = BrowserController(url_keywords=["ezto.mheducation"])
    await browser.connect()

    # Test the fallback directly
    from question_parser import QuestionParser

    parser = QuestionParser(browser)

    # Skip normal extraction, go straight to fallback
    result = await parser._extract_ezto_fallback()
    if result:
        print(f"SUCCESS: {result.question_type}")
        print(f"Question: {result.question_text}")
        print(f"Options: {result.options}")
    else:
        print("FAILED: fallback returned None")

    await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
