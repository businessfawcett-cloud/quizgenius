"""Quick test of parser with ezto fix."""

import asyncio
from browser_controller import BrowserController
from question_parser import QuestionParser


async def main():
    browser = BrowserController(url_keywords=["ezto.mheducation"])
    await browser.connect()

    parser = QuestionParser(browser)
    q = await parser.parse()
    print(f"SUCCESS: {q.question_text[:80]}")
    print(f"Options: {len(q.options)}")
    for opt in q.options:
        print(f"  - {opt}")

    await browser.close()


asyncio.run(main())
