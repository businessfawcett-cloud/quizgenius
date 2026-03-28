#!/usr/bin/env python3
"""Handle incorrect answer feedback"""

import asyncio
from browser_controller import BrowserController


async def handle_feedback():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    print("Page title:", await browser.page.title())

    # Click on a resource
    buttons = await browser.page.evaluate("""
        () => {
            const btns = document.querySelectorAll('button');
            const results = [];
            for (let btn of btns) {
                if (btn.offsetParent !== null && btn.innerText) {
                    results.push({
                        text: btn.innerText.trim(),
                        id: btn.id,
                        dataAuto: btn.getAttribute('data-automation-id')
                    });
                }
            }
            return results;
        }
    """)
    print("Buttons:", buttons)

    # Click something to continue
    await browser.page.click("button:has-text('Select a concept')")
    await asyncio.sleep(2)

    print("After clicking:")
    print("Page title:", await browser.page.title())

    await browser.close()


if __name__ == "__main__":
    asyncio.run(handle_feedback())
