#!/usr/bin/env python3
"""
Final Canvas Reading Guide Automation
Uses your existing Google Docs automation system
"""

import asyncio
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_canvas_reading_guide():
    """Run the Canvas reading guide automation"""
    try:
        logger.info("=== Canvas Reading Guide Automation ===")
        logger.info(
            "Lesson 7.3: A Second World War, 1937-1945 & The Recovery of Europe"
        )

        # Import the working Google Docs automation
        from google_docs_history import run

        # The google_docs_history.py already has:
        # - Working Chrome connection
        # - LLM integration with retry logic
        # - Google Docs filling automation
        # - Backup system

        logger.info("Running Google Docs automation...")
        await run()

        logger.info("🎉 Canvas reading guide completed!")

    except Exception as e:
        logger.error(f"Error: {e}")
        return False

    return True


async def main():
    """Main function"""
    success = await run_canvas_reading_guide()

    if success:
        logger.info("✅ Canvas reading guide automation completed!")
    else:
        logger.error("❌ Canvas reading guide automation failed")


if __name__ == "__main__":
    asyncio.run(main())
