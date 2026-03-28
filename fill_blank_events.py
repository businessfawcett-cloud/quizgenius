#!/usr/bin/env python3
"""Fill in the blank question - with event triggering"""

import asyncio
from browser_controller import BrowserController


async def fill_blank_events():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    print("Page title:", await browser.page.title())

    # Fill the input
    await browser.page.fill("#fitbTesting_response0", "bomb calorimeter")
    print("Filled answer")

    # Trigger input and change events
    await browser.page.evaluate("""
        () => {
            const input = document.getElementById('fitbTesting_response0');
            if (input) {
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                input.dispatchEvent(new Event('blur', { bubbles: true }));
            }
        }
    """)
    print("Triggered events")

    await asyncio.sleep(2)

    # Check if button is enabled now
    is_disabled = await browser.page.evaluate("""
        () => {
            const btn = document.querySelector('[data-automation-id="confidence-buttons--high_confidence"]');
            return btn ? btn.disabled : 'not found';
        }
    """)
    print(f"High button disabled: {is_disabled}")

    # Try clicking using JavaScript
    await browser.page.evaluate("""
        () => {
            const btn = document.querySelector('[data-automation-id="confidence-buttons--high_confidence"]');
            if (btn && !btn.disabled) {
                btn.click();
            }
        }
    """)
    print("Clicked High via JS")

    await asyncio.sleep(2)

    # Check for Next button
    has_next = await browser.page.evaluate("""
        () => {
            const btns = document.querySelectorAll('button');
            for (let btn of btns) {
                if (btn.innerText.includes('Next') || btn.innerText.includes('Continue')) {
                    return btn.innerText;
                }
            }
            return 'none';
        }
    """)
    print(f"Next button: {has_next}")

    await browser.close()


if __name__ == "__main__":
    asyncio.run(fill_blank_events())
