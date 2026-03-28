"""Essay question handler - longer text input automation."""

from __future__ import annotations
import asyncio
from config import setup_logging

logger = setup_logging()


class EssayHandler:
    """Handles essay questions (longer text input)."""

    TEXTAREA_SELECTORS = [
        "textarea",
        "textarea.essay-input",
        "textarea.form-control",
        "textarea[id*='essay']",
        "textarea.response-textarea",
        "div[contenteditable='true']",
    ]

    def __init__(self, browser, llm_client):
        self.browser = browser
        self.llm = llm_client

    async def detect_essay(self, question_text: str = "", body_text: str = "") -> bool:
        """Check if current question is an essay question."""
        essay_indicators = [
            "essay",
            "explain in detail",
            "describe in detail",
            "discuss in detail",
            "write a paragraph",
            "provide a detailed response",
            "explain your reasoning",
            "explain why",
            "describe how",
            "discuss the",
            "short essay",
        ]

        combined = (question_text + " " + body_text).lower()

        for ind in essay_indicators:
            if ind in combined:
                return True

        return False

    async def _extract_textarea(self) -> str | None:
        """Extract the textarea selector or ID."""
        page = self.browser.page

        for selector in self.TEXTAREA_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    is_visible = await el.is_visible()
                    if is_visible:
                        el_id = await el.get_attribute("id")
                        el_name = await el.get_attribute("name")

                        logger.debug(f"Found textarea: id={el_id}, name={el_name}")

                        if el_id:
                            return f"#{el_id}"
                        elif el_name:
                            return f"[name='{el_name}']"
            except Exception:
                continue

        return None

    async def _fill_textarea(self, selector: str, answer: str) -> bool:
        """Fill the textarea with the essay answer."""
        page = self.browser.page

        try:
            # Clear existing content first
            await page.fill(selector, "")

            # Fill with essay content
            await page.fill(selector, answer)
            logger.info(f"Filled essay textarea with {len(answer)} characters")

            # Trigger input events
            await page.evaluate(f"""
                () => {{
                    const textarea = document.querySelector('{selector}');
                    if (textarea) {{
                        textarea.focus();
                        textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}
            """)

            return True

        except Exception as e:
            logger.error(f"Failed to fill textarea: {e}")
            return False

    async def _generate_essay(self, question_text: str, question_type: str) -> str:
        """Generate an essay response using the LLM."""

        prompt = f"""You are answering an essay question on a McGraw Hill quiz.

Question: {question_text}

Write a well-structured essay response (2-3 paragraphs). 
Include:
- A clear introduction
- Key points explaining your answer
- A brief conclusion

Be thorough but concise. This is for a quiz so keep it focused.
 
Essay:"""

        try:
            response = await self.llm._call_api(prompt)

            # Clean up response
            essay = response.strip().strip('"').strip("'").strip(".")

            # Limit length for essay (but allow reasonable length)
            if len(essay) > 2000:
                essay = essay[:2000]

            logger.info(f"Generated essay with {len(essay)} characters")
            return essay

        except Exception as e:
            logger.error(f"LLM essay generation failed: {e}")
            return ""

    async def handle(self, question) -> bool:
        """Handle an essay question."""
        logger.info("Handling essay question...")

        # Get the textarea
        selector = await self._extract_textarea()

        if not selector:
            logger.warning("Could not find essay textarea")
            return False

        logger.info(f"Found textarea: {selector}")

        # Generate essay from LLM
        essay = await self._generate_essay(
            question.question_text, question.question_type
        )

        if not essay:
            logger.error("No essay generated from LLM")
            return False

        # Fill the textarea
        success = await self._fill_textarea(selector, essay)

        if success:
            # Wait for input to be registered
            await asyncio.sleep(2)

        return success
