#!/usr/bin/env python3
"""Fill in the blank question"""

import asyncio
from browser_controller import BrowserController


async def fill_blank():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    print("Page title:", await browser.page.title())

    # Get question text
    text = await browser.page.inner_text("[role='main']")
    print("Question:", text[:300])

    # Find text input fields (type="text")
    text_inputs = await browser.page.query_selector_all("input[type='text']")
    print(f"\nFound {len(text_inputs)} text input fields")

    # Try to type in each input
    for i, inp in enumerate(text_inputs):
        try:
            # Check if visible
            is_visible = await inp.is_visible()
            if is_visible:
                print(f"Input {i} is visible")
                await inp.fill("bomb calorimeter")
                print(f"Filled input {i} with answer")
                break
        except Exception as e:
            print(f"Input {i}: {e}")

    # Wait a bit
    await asyncio.sleep(1)

    # Click confidence button (High)
    try:
        high_btn = await browser.page.query_selector("button:has-text('High')")
        if high_btn:
            await high_btn.click()
            print("Clicked High confidence button")
    except Exception as e:
        print(f"Error clicking confidence: {e}")

    await asyncio.sleep(1)

    # Look for Submit/Next button
    buttons = await browser.page.query_selector_all("button")
    for btn in buttons:
        try:
            text = await btn.inner_text()
            if text and ("Next" in text or "Submit" in text or "Continue" in text):
                print(f"Clicking button: {text}")
                await btn.click()
                break
        except:
            pass

    print("\nDone!")
    await browser.close()


if __name__ == "__main__":
    asyncio.run(fill_blank())
