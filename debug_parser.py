#!/usr/bin/env python3
"""Debug parser to see what's happening"""

import asyncio
from browser_controller import BrowserController
from question_parser import QuestionParser


async def debug_parser():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    parser = QuestionParser(browser)

    print("Page title:", await browser.page.title())

    # Try to get question type
    selectors = [".probe-header", ".dlc_question", "h2", "[role='main']"]

    for sel in selectors:
        try:
            text = await browser.get_text(sel, timeout=3000)
            if text:
                print(f"\n{sel}:")
                print(text[:200])
        except Exception as e:
            print(f"{sel}: Error - {e}")

    # Try to get options
    print("\n--- Options ---")
    option_selectors = [".choiceText", ".printable-option", ".choice-row"]
    for sel in option_selectors:
        try:
            texts = await browser.get_all_texts(sel)
            if texts:
                print(f"{sel}: {texts}")
        except Exception as e:
            print(f"{sel}: Error - {e}")

    # Try to get fill in blank inputs
    print("\n--- Fill in blank inputs ---")
    fb_selectors = ["input.fitb-input", "input[id^='fitbTesting_response']"]
    for sel in fb_selectors:
        try:
            elements = await browser.page.query_selector_all(sel)
            print(f"{sel}: Found {len(elements)}")
            for el in elements[:3]:
                is_visible = await el.is_visible()
                input_id = await el.get_attribute("id")
                print(f"  ID: {input_id}, visible: {is_visible}")
        except Exception as e:
            print(f"{sel}: Error - {e}")

    await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_parser())
