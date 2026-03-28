#!/usr/bin/env python3
"""Debug buttons on fill in blank page"""

import asyncio
from browser_controller import BrowserController


async def debug_buttons():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    print("Page title:", await browser.page.title())

    # Get all buttons
    buttons = await browser.page.evaluate("""
        () => {
            const btns = document.querySelectorAll('button');
            const results = [];
            for (let btn of btns) {
                if (btn.offsetParent !== null) {
                    results.push({
                        text: btn.innerText?.trim(),
                        id: btn.id,
                        dataAuto: btn.getAttribute('data-automation-id'),
                        disabled: btn.disabled
                    });
                }
            }
            return results;
        }
    """)
    print("Visible buttons:")
    for btn in buttons:
        print(f"  {btn}")

    await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_buttons())
