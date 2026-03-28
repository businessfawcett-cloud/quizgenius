"""Browser controller — connects to an existing Chrome session via CDP."""

import asyncio
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from config import CDP_ENDPOINT, CHROME_DEBUG_PORT, setup_logging

logger = setup_logging()


class BrowserController:
    """Manages connection to an existing Chrome browser and page interactions."""

    def __init__(self, url_keywords: list[str] | None = None):
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self.page: Page | None = None
        # Keywords to match in the tab URL (case-insensitive)
        self._url_keywords = url_keywords or [
            "mheducation",
            "mcgraw",
            "connect",
            "learning.mheducation",
        ]

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------
    async def connect(self):
        """Connect to Chrome via the Chrome DevTools Protocol."""
        logger.info("Connecting to Chrome on port %s …", CHROME_DEBUG_PORT)
        self._playwright = await async_playwright().start()

        try:
            self._browser = await self._playwright.chromium.connect_over_cdp(
                CDP_ENDPOINT
            )
            logger.info("Connected to Chrome successfully.")
        except Exception as exc:
            logger.error(
                "Could not connect to Chrome. Make sure Chrome is running with:\n"
                '  chrome.exe --remote-debugging-port=%s --user-data-dir="C:\\chrome-debug"\n'
                "Error: %s",
                CHROME_DEBUG_PORT,
                exc,
            )
            raise

        # Find the target tab across all contexts
        self.page = None
        for ctx in self._browser.contexts:
            for page in ctx.pages:
                url = page.url.lower()
                logger.info("Found tab: %s", page.url)
                if any(kw in url for kw in self._url_keywords):
                    self.page = page
                    self._context = ctx
                    logger.info("Attached to target page: %s", page.url)
                    break
            if self.page:
                break

        # Fallback: pick the first non-chrome:// page (or new-tab-page which is usable)
        if not self.page:
            for ctx in self._browser.contexts:
                for page in ctx.pages:
                    url = page.url
                    # Accept pages that aren't chrome:// system pages (except new-tab-page which is usable)
                    if (
                        not url.startswith("chrome://")
                        or url == "chrome://new-tab-page/"
                    ):
                        self.page = page
                        self._context = ctx
                        logger.info("Attached to fallback page: %s", page.url)
                        break
                if self.page:
                    break

        if not self.page:
            raise RuntimeError(
                "No suitable page found. Make sure McGraw Hill is open in Chrome."
            )

    # ------------------------------------------------------------------
    # Element interactions
    # ------------------------------------------------------------------
    async def click(self, selector: str, timeout: int = 10_000):
        """Click an element matched by *selector*."""
        logger.debug("Clicking: %s", selector)
        await self.page.click(selector, timeout=timeout)

    async def get_text(self, selector: str, timeout: int = 10_000) -> str:
        """Return the inner text of the first element matching *selector*."""
        element = await self.page.wait_for_selector(selector, timeout=timeout)
        return (await element.inner_text()).strip()

    async def get_all_texts(self, selector: str) -> list[str]:
        """Return inner text for every element matching *selector*."""
        elements = await self.page.query_selector_all(selector)
        return [((await el.inner_text()).strip()) for el in elements]

    async def get_element_count(self, selector: str) -> int:
        """Return how many elements match *selector*."""
        elements = await self.page.query_selector_all(selector)
        return len(elements)

    async def wait_for_navigation(self, timeout: int = 15_000):
        """Wait for the page to finish navigating."""
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except Exception:
            logger.warning("Navigation wait timed out — continuing anyway.")

    async def wait_for_selector(self, selector: str, timeout: int = 15_000):
        """Wait until *selector* appears in the DOM."""
        await self.page.wait_for_selector(selector, timeout=timeout)

    async def page_content(self) -> str:
        """Return the full HTML of the page."""
        return await self.page.content()

    async def evaluate(self, expression: str):
        """Run arbitrary JS in the page context."""
        return await self.page.evaluate(expression)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    async def close(self):
        """Disconnect from the browser (does NOT close Chrome)."""
        if self._playwright:
            await self._playwright.stop()
            logger.info("Disconnected from Chrome (browser left open).")
