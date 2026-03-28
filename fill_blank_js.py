#!/usr/bin/env python3
"""Fill in the blank question - try JS approach"""

import asyncio
from browser_controller import BrowserController


async def fill_blank_js():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    print("Page title:", await browser.page.title())

    # Use JavaScript to find and fill the input
    # Try to find any editable input
    result = await browser.page.evaluate("""
        () => {
            // Find all input elements
            const inputs = document.querySelectorAll('input');
            const results = [];
            for (let inp of inputs) {
                results.push({
                    type: inp.type,
                    id: inp.id,
                    name: inp.name,
                    class: inp.className,
                    visible: inp.offsetParent !== null
                });
            }
            return results;
        }
    """)

    print("Input elements found:", result)

    # Try to fill using JavaScript
    await browser.page.evaluate("""
        () => {
            // Try to find the input field
            const inputs = document.querySelectorAll('input');
            for (let inp of inputs) {
                if (inp.type === 'text' || inp.type === '' || !inp.type) {
                    if (inp.offsetParent !== null) {  // visible
                        console.log('Found visible input:', inp);
                        inp.value = 'bomb calorimeter';
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                        inp.dispatchEvent(new Event('change', { bubbles: true }));
                        return 'Filled: ' + inp.value;
                    }
                }
            }
            return 'No visible text input found';
        }
    """)

    await asyncio.sleep(2)

    # Try clicking through
    print("\nTrying to find and click buttons...")

    # Get all buttons
    buttons = await browser.page.evaluate("""
        () => {
            const btns = document.querySelectorAll('button');
            const results = [];
            for (let btn of btns) {
                if (btn.offsetParent !== null) {
                    results.push({
                        text: btn.innerText?.trim(),
                        visible: true
                    });
                }
            }
            return results;
        }
    """)
    print("Visible buttons:", buttons)

    await browser.close()


if __name__ == "__main__":
    asyncio.run(fill_blank_js())
