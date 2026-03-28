"""Short answer question handler - text input automation."""

from __future__ import annotations
import asyncio
from config import setup_logging

logger = setup_logging()


class ShortAnswerHandler:
    """Handles short answer questions (text input)."""

    INPUT_SELECTORS = [
        "input[type='text']",
        "input:not([type])",
        "input.short-answer-input",
        "input[type='text'].form-control",
        "textarea.short-answer",
        "input.answer-input",
    ]

    def __init__(self, browser, llm_client):
        self.browser = browser
        self.llm = llm_client

    async def detect_short_answer(
        self, question_text: str = "", body_text: str = ""
    ) -> bool:
        """Check if current question is a short answer question."""
        # Short answer indicators
        short_answer_indicators = [
            "short answer",
            "type your answer",
            "type here",
            "your answer:",
            "enter your answer",
            "provide your answer",
            "fill in your answer",
        ]

        # Essay indicators (to exclude)
        essay_indicators = [
            "essay",
            "explain in detail",
            "describe in detail",
            "discuss in detail",
            "write a paragraph",
        ]

        combined = (question_text + " " + body_text).lower()

        # Check for essay first (exclude)
        for ind in essay_indicators:
            if ind in combined:
                return False

        # Check for short answer
        for ind in short_answer_indicators:
            if ind in combined:
                return True

        # Also check for input fields without "fill in the blank"
        if "fill" in combined and "blank" in combined:
            return False  # Already handled by fill-blank handler

        return False

    async def _extract_input_field(self) -> str | None:
        """Extract the input field selector or ID."""
        page = self.browser.page

        for selector in self.INPUT_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    is_visible = await el.is_visible()
                    if is_visible:
                        # Get ID or name for filling
                        el_id = await el.get_attribute("id")
                        el_name = await el.get_attribute("name")
                        el_class = await el.get_attribute("class")

                        logger.debug(
                            f"Found input: id={el_id}, name={el_name}, class={el_class}"
                        )

                        if el_id:
                            return f"#{el_id}"
                        elif el_name:
                            return f"[name='{el_name}']"
            except Exception:
                continue

        return None

    async def _fill_input(self, selector: str, answer: str) -> bool:
        """Fill the input field with the answer."""
        page = self.browser.page

        try:
            # Fill the input
            await page.fill(selector, answer)
            logger.info(f"Filled short answer input with: {answer[:50]}...")

            # Trigger input events
            await page.evaluate(f"""
                () => {{
                    const input = document.querySelector('{selector}');
                    if (input) {{
                        input.focus();
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}
                }}
            """)

            return True

        except Exception as e:
            logger.error(f"Failed to fill input: {e}")
            return False

    async def _generate_answer(self, question_text: str, question_type: str) -> str:
        """Generate a short answer using the LLM."""

        prompt = f"""You are answering a McGraw Hill quiz question.

Question: {question_text}

Provide a SHORT, CONCISE answer (1-2 sentences maximum, 1-2 short phrases).
Focus on the key point. Be precise and to the point.

Short answer:"""

        try:
            response = await self.llm._call_api(prompt)

            # Clean up response
            answer = response.strip().strip('"').strip("'").strip(".")

            # Limit length for short answer
            if len(answer) > 200:
                answer = answer[:200]

            logger.info(f"Generated short answer: {answer[:50]}...")
            return answer

        except Exception as e:
            logger.error(f"LLM answer generation failed: {e}")
            return ""

    async def handle(self, question) -> bool:
        """Handle a short answer question."""
        logger.info("Handling short answer question...")

        # Get the input field
        selector = await self._extract_input_field()

        if not selector:
            logger.warning("Could not find short answer input field")
            return False

        logger.info(f"Found input field: {selector}")

        # Generate answer from LLM
        answer = await self._generate_answer(
            question.question_text, question.question_type
        )

        if not answer:
            logger.error("No answer generated from LLM")
            return False

        # Fill the input
        success = await self._fill_input(selector, answer)

        if success:
            # Wait for input to be registered
            await asyncio.sleep(2)

        return success
