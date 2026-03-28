#!/usr/bin/env python3
"""
Test Chrome connection for Google Docs automation
"""

import asyncio
import sys
import logging

# Add current directory to path
sys.path.append(".")

from browser_controller import BrowserController

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_chrome_connection():
    """Test connection to Chrome browser"""
    try:
        logger.info("Testing Chrome connection...")

        browser_controller = BrowserController()

        # Try to connect to Chrome
        await browser_controller.connect()

        logger.info("✅ Successfully connected to Chrome browser!")

        # Get page content to verify connection
        page_content = await browser_controller.page_content()
        logger.info(
            f"✅ Connected successfully! Page loaded: {len(page_content)} characters"
        )

        await browser_controller.close()
        return True

    except Exception as e:
        logger.error(f"❌ Failed to connect to Chrome browser: {e}")
        logger.info(
            "Make sure Chrome is running with: chrome.exe --remote-debugging-port=9222"
        )
        return False


if __name__ == "__main__":
    success = asyncio.run(test_chrome_connection())
    sys.exit(0 if success else 1)
