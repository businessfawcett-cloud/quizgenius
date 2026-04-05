"""Debug option clicking on ezto page."""

import asyncio
from browser_controller import BrowserController


async def main():
    browser = BrowserController(url_keywords=["ezto.mheducation"])
    await browser.connect()

    await asyncio.sleep(2)

    print("=== Looking for option elements ===")
    selectors = [
        "input[type='radio']",
        "input[type='checkbox']",
        ".choice",
        ".option",
        "[role='radio']",
        "label",
        ".answer-option",
    ]

    for sel in selectors:
        try:
            count = await browser.get_element_count(sel)
            if count > 0:
                print(f"\n{sel}: {count} elements")
                # Try to get text or value
                els = await browser.page.query_selector_all(sel)
                for el in els[:5]:
                    try:
                        text = await el.inner_text()
                        value = await el.get_attribute("value")
                        print(f"  text={text[:30]}, value={value}")
                    except:
                        pass
        except Exception as e:
            print(f"  Error: {e}")

    print("\n=== All inputs ===")
    try:
        inputs = await browser.page.query_selector_all("input")
        for inp in inputs[:10]:
            try:
                inp_type = await inp.get_attribute("type")
                value = await inp.get_attribute("value")
                name = await inp.get_attribute("name")
                print(f"  type={inp_type}, value={value}, name={name}")
            except:
                pass
    except Exception as e:
        print(f"Error: {e}")

    await browser.close()


asyncio.run(main())
