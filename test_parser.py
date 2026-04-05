"""Test the parser on the current ezto quiz page."""

import asyncio
from browser_controller import BrowserController
from question_parser import QuestionParser


async def main():
    browser = BrowserController(url_keywords=["ezto.mheducation"])
    await browser.connect()

    parser = QuestionParser(browser)

    print("\n=== PARSING ===")
    try:
        q = await parser.parse()
        print(f"Type: {q.question_type}")
        print(f"Question: {q.question_text}")
        print(f"Options: {q.options}")
        print(f"Progress: {q.progress_current}/{q.progress_total}")
    except Exception as e:
        print(f"Error: {e}")

    await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
