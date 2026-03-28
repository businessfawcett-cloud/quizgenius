#!/usr/bin/env python3
"""Navigate from reading mode back to questions"""

import asyncio
from browser_controller import BrowserController


async def navigate_to_questions():
    browser = BrowserController(url_keywords=["learning.mheducation.com"])
    await browser.connect()

    print("Page title:", await browser.page.title())

    # Look for buttons to exit reading mode
    buttons = await browser.page.evaluate("""
        () => {
            const btns = document.querySelectorAll('button, a');
            const results = [];
            for (let btn of btns) {
                if (btn.offsetParent !== null && btn.innerText) {
                    results.push({
                        text: btn.innerText.trim(),
                        tag: btn.tagName,
                        href: btn.href
                    });
                }
            }
            return results;
        }
    """)
    print("Buttons/Links:", buttons[:20])

    await browser.close()


if __name__ == "__main__":
    asyncio.run(navigate_to_questions())
