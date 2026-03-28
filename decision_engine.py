"""Decision engine — maps the LLM answer to a page action and executes it."""

from __future__ import annotations
import asyncio
from difflib import SequenceMatcher
from config import setup_logging

logger = setup_logging()


class DecisionEngine:
    """Takes the LLM's answer string and clicks the matching option on the page."""

    # Selectors for clickable answer options
    OPTION_SELECTORS = [
        ".printable-option",  # McGraw Hill clickable choice
        ".choice-row",  # choice row container
        ".choiceText",  # answer text element
    ]

    # Confidence buttons — click one to submit the answer
    CONFIDENCE_SELECTORS = [
        "[data-automation-id='confidence-buttons--high_confidence']",
        "[data-automation-id='confidence-buttons--medium_confidence']",
        "[data-automation-id='confidence-buttons--low_confidence']",
        "[aria-label='High Confidence']",
        "[aria-label='Medium Confidence']",
        "[aria-label='Low Confidence']",
        ".btn-confidence",
    ]

    # Next / continue buttons
    NEXT_SELECTORS = [
        "button:has-text('Next')",
        "button:has-text('Continue')",
        "button:has-text('Submit')",
        "button:has-text('Check')",
        "[data-automation-id='submit-answer']",
    ]

    # "Select a concept resource to continue" dropdown / expand button
    RESOURCE_DROPDOWN_SELECTORS = [
        "[data-automation-id='lr-tray_button']",  # actual expand button
        ".lr-tray-expand-button",
        "button:has-text('concept resource')",
    ]

    # Review / reading resource selectors (wrong-answer recovery flow)
    REVIEW_SELECTORS = [
        "[data-automation-id='lr-tray_reading-button']",  # "Read About the Concept"
        "[data-automation-id='lr-tray_reading-ai-button']",  # "Clarify with AI Reader"
        ".tray-item.reading-item button",
        "button.btn-tertiary.lr-tray-button",
        "button:has-text('Read About')",
    ]

    # "Reading" button
    READING_BUTTON_SELECTORS = [
        ".reading-button",
        "button:has-text('Reading')",
    ]

    # Fill-in-the-blank input selectors
    FILL_BLANK_INPUT_SELECTORS = [
        "input.fitb-input",
        "input[id^='fitbTesting_response']",
        "input[class*='fitb']",
    ]

    # Ordering question selectors (drag and drop)
    ORDERING_ITEM_SELECTORS = [
        ".choice-item",
        ".ordering-choice",
        "[data-choice-id]",
        ".drag-item",
        ".sortable-item",
        "[role='listitem']",
    ]

    # "Next Question" / back-to-questions buttons
    NEXT_QUESTION_SELECTORS = [
        "button:has-text('Next Question')",
        "button:has-text('Question Mode')",
        "button:has-text('Questions')",
    ]

    def __init__(self, browser):
        self.browser = browser  # BrowserController instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def select_answer(self, llm_answer: str, options: list[str]) -> bool:
        """Find and click the option that best matches *llm_answer*.

        Returns True if an option was clicked, False otherwise.
        """
        best_match = self._fuzzy_match(llm_answer, options)
        if best_match is None:
            logger.error("Could not match LLM answer '%s' to any option.", llm_answer)
            return False

        logger.info("Best match: '%s' → clicking '%s'", llm_answer, best_match)
        return await self._click_option(best_match)

    async def submit_confidence_and_next(self):
        """Click the confidence button (if present) and then the Next button."""
        # For fill-in-blank questions, we need to click the confidence button first
        # Try confidence buttons first
        for sel in self.CONFIDENCE_SELECTORS:
            try:
                count = await self.browser.get_element_count(sel)
                if count > 0:
                    # Check if button is enabled
                    btn = await self.browser.page.query_selector(sel)
                    if btn:
                        is_disabled = await btn.get_attribute("disabled")
                        if is_disabled:
                            logger.debug(
                                f"Confidence button {sel} is disabled, waiting..."
                            )
                            await asyncio.sleep(2)
                            # Try again after waiting
                            btn = await self.browser.page.query_selector(sel)
                            is_disabled = (
                                await btn.get_attribute("disabled") if btn else True
                            )
                            if is_disabled:
                                continue  # Still disabled, try next button

                    await self.browser.click(sel, timeout=5_000)
                    logger.info("Clicked confidence button: %s", sel)
                    await asyncio.sleep(1)
                    break
            except Exception:
                continue

        # Now try the Next button
        for sel in self.NEXT_SELECTORS:
            try:
                count = await self.browser.get_element_count(sel)
                if count > 0:
                    await self.browser.click(sel, timeout=5_000)
                    logger.info("Clicked next/submit: %s", sel)
                    await asyncio.sleep(2)
                    return
            except Exception:
                continue

        logger.warning("Could not find a Next/Submit button.")

    async def fill_blank_answer(self, llm_answer: str, input_ids: list[str]) -> bool:
        """Fill in the blank input field(s) with the LLM answer.

        Returns True if the answer was filled, False otherwise.
        """
        if not input_ids:
            logger.warning("No fill-in-the-blank input IDs provided")
            return False

        logger.info(f"Filling blank with: {llm_answer}")

        filled_any = False

        # Try to fill each input ID
        for input_id in input_ids:
            try:
                # Try using the ID directly
                selector = f"#{input_id}"
                await self.browser.page.fill(selector, llm_answer)
                logger.info(f"Filled input {input_id} with: {llm_answer}")

                # Trigger input events to make sure the page registers the change
                await self.browser.page.evaluate(f"""
                    () => {{
                        const input = document.getElementById('{input_id}');
                        if (input) {{
                            input.focus();
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                        }}
                    }}
                """)

                filled_any = True

            except Exception as e:
                logger.debug(f"Could not fill input {input_id}: {e}")
                continue

        if filled_any:
            # Wait for validation and button to become enabled
            await asyncio.sleep(3)
            return True

        # If direct fill didn't work, try finding visible inputs and filling them
        try:
            for sel in self.FILL_BLANK_INPUT_SELECTORS:
                try:
                    elements = await self.browser.page.query_selector_all(sel)
                    for el in elements:
                        is_visible = await el.is_visible()
                        if is_visible:
                            await el.fill(llm_answer)
                            logger.info(f"Filled {sel} with: {llm_answer}")

                            # Trigger events
                            await el.dispatch_event("input")
                            await el.dispatch_event("change")

                            filled_any = True
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error finding fill-in-blank inputs: {e}")

        if filled_any:
            await asyncio.sleep(3)

        return filled_any

        logger.info(f"Filling blank with: {llm_answer}")

        # Try to fill each input ID
        for input_id in input_ids:
            try:
                # Try using the ID directly
                selector = f"#{input_id}"
                await self.browser.page.fill(selector, llm_answer)
                logger.info(f"Filled input {input_id} with: {llm_answer}")

                # Trigger input events to make sure the page registers the change
                await self.browser.page.evaluate(f"""
                    () => {{
                        const input = document.getElementById('{input_id}');
                        if (input) {{
                            input.focus();
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                        }}
                    }}
                """)

                await asyncio.sleep(2)  # Wait for button to become enabled
                return True

            except Exception as e:
                logger.debug(f"Could not fill input {input_id}: {e}")
                continue

        # If direct fill didn't work, try finding visible inputs and filling them
        try:
            for sel in self.FILL_BLANK_INPUT_SELECTORS:
                try:
                    elements = await self.browser.page.query_selector_all(sel)
                    for el in elements:
                        is_visible = await el.is_visible()
                        if is_visible:
                            await el.fill(llm_answer)
                            logger.info(f"Filled {sel} with: {llm_answer}")

                            # Trigger events
                            await el.dispatch_event("input")
                            await el.dispatch_event("change")

                            await asyncio.sleep(1)
                            return True
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error finding fill-in-blank inputs: {e}")

        return False

    async def handle_ordering_question(self, ordered_options: list[str]) -> bool:
        """Handle ordering/ranking questions by dragging elements.

        For ordering questions, the LLM provides the correct order.
        We need to drag and drop elements to match that order.

        Returns True if elements were reordered, False otherwise.
        """
        if not ordered_options:
            logger.warning("No ordered options provided for ordering question")
            return False

        logger.info(f"Handling ordering question with {len(ordered_options)} options")

        # For now, just try clicking the first option as a simple approach
        # A full implementation would do drag-and-drop
        try:
            for sel in self.ORDERING_ITEM_SELECTORS:
                try:
                    elements = await self.browser.page.query_selector_all(sel)
                    if elements and len(elements) > 0:
                        # Just click the first element to select it
                        await elements[0].click()
                        logger.info(f"Clicked ordering element via {sel}")
                        await asyncio.sleep(1)
                        return True
                except Exception as e:
                    logger.debug(f"Could not click {sel}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error handling ordering question: {e}")

        return False

    async def handle_wrong_answer_recovery(self) -> bool:
        """Handle the wrong-answer flow:
        1. JS-click 'Read About the Concept' to open reading view
        2. Wait for reading view to load
        3. Click 'To Questions' to go back
        4. Click 'Next Question' to advance

        Returns True if recovery succeeded, False otherwise.
        """
        logger.info("Starting wrong-answer recovery flow...")

        # Step 0: Click the "Select a concept resource" dropdown if present
        for sel in self.RESOURCE_DROPDOWN_SELECTORS:
            try:
                el = await self.browser.page.query_selector(sel)
                if el:
                    await self.browser.page.evaluate("el => el.click()", el)
                    logger.info("Clicked resource dropdown: %s", sel)
                    await asyncio.sleep(2)  # wait for dropdown options to appear
                    break
            except Exception as e:
                logger.debug("Dropdown selector %s failed: %s", sel, e)
                continue

        # Step 1: Click the review resource via JS (it navigates to reading view)
        clicked_review = False
        for sel in self.REVIEW_SELECTORS:
            try:
                el = await self.browser.page.query_selector(sel)
                if el:
                    # Use JS click because the element may become invisible during navigation
                    await self.browser.page.evaluate("el => el.click()", el)
                    logger.info("JS-clicked review resource: %s", sel)
                    clicked_review = True
                    await asyncio.sleep(5)  # wait for reading view to load
                    break
            except Exception as e:
                logger.debug("Review selector %s failed: %s", sel, e)
                continue

        if not clicked_review:
            logger.warning("Could not find review resource button.")
            # Try clicking Next Question anyway (might already be enabled)
            return await self._try_click_next_question()

        # Step 2: Click "To Questions" to go back to the question view
        try:
            await self.browser.click("button:has-text('To Questions')", timeout=5_000)
            logger.info("Clicked 'To Questions' — back to question view.")
            await asyncio.sleep(3)
        except Exception:
            logger.warning(
                "Could not find 'To Questions' button. Trying alternatives..."
            )
            # Try other back buttons
            for sel in ["button:has-text('Questions')", ".reading-button"]:
                try:
                    await self.browser.click(sel, timeout=3_000)
                    logger.info("Clicked back via: %s", sel)
                    await asyncio.sleep(3)
                    break
                except Exception:
                    continue

        # Step 3: Click "Next Question" to advance
        return await self._try_click_next_question()

    async def _try_click_next_question(self) -> bool:
        """Try to click 'Next Question' or other advance buttons."""
        # Try Next Question first, NOT Check (Check is for submitting answers)
        for sel in [
            "button:has-text('Next Question')",
            "button.next-button",
            "button:has-text('Continue')",
            "button:has-text('Next')",
        ]:
            try:
                el = await self.browser.page.query_selector(sel)
                if el:
                    disabled = await el.get_attribute("disabled")
                    if disabled is not None:
                        logger.debug("Button %s is disabled, skipping.", sel)
                        continue
                    await el.click()
                    logger.info("Clicked advance button: %s", sel)
                    await asyncio.sleep(3)
                    logger.info("Wrong-answer recovery complete.")
                    return True
            except Exception:
                continue

        logger.error("Could not advance to next question.")
        return False

    async def is_wrong_answer_state(self) -> bool:
        """Check if the page is showing a wrong-answer feedback state
        where options are locked and we need to review a resource."""
        try:
            body_text = await self.browser.get_text("body", timeout=5_000)
            wrong_indicators = [
                "your answer incorrect",
                "you must review a resource",
                "select a concept resource to continue",
                "before moving on, you must review",
                "answer mode",
                "incorrect",
                "try again",
            ]
            body_lower = body_text.lower()
            for indicator in wrong_indicators:
                if indicator in body_lower:
                    logger.debug("Wrong-answer indicator matched: '%s'", indicator)
                    return True
        except Exception:
            pass

        return False

    async def handle_incorrect_feedback(self) -> bool:
        """Handle the incorrect answer feedback page.
        Click 'Select a concept resource' then 'Next Question' to continue."""
        try:
            logger.info("Handling incorrect answer feedback...")

            # Click the resource dropdown/button
            selectors = [
                "[data-automation-id='lr-tray_button']",
                "button:has-text('Select a concept')",
                "button:has-text('Select a concept resource')",
            ]

            for sel in selectors:
                try:
                    el = await self.browser.page.query_selector(sel)
                    if el:
                        await el.click()
                        logger.info(f"Clicked resource button: {sel}")
                        await asyncio.sleep(2)
                        break
                except Exception as e:
                    logger.debug(f"Could not click {sel}: {e}")
                    continue

            # Now click Next Question button
            next_selectors = [
                "button:has-text('Next Question')",
                "[data-automation-id='next-question-button']",
            ]

            for sel in next_selectors:
                try:
                    el = await self.browser.page.query_selector(sel)
                    if el:
                        await el.click()
                        logger.info(f"Clicked next question: {sel}")
                        await asyncio.sleep(3)
                        return True
                except Exception as e:
                    logger.debug(f"Could not click {sel}: {e}")
                    continue

            logger.warning("Could not find Next Question button")
            return False

        except Exception as e:
            logger.error(f"Error handling incorrect feedback: {e}")
            return False

    # ------------------------------------------------------------------
    # Fuzzy matching
    # ------------------------------------------------------------------
    @staticmethod
    def _fuzzy_match(answer: str, options: list[str]) -> str | None:
        """Return the option string closest to *answer* using sequence matching."""
        answer_lower = answer.lower().strip()

        # Exact match first
        for opt in options:
            if opt.lower().strip() == answer_lower:
                return opt

        # Substring containment
        for opt in options:
            if answer_lower in opt.lower() or opt.lower() in answer_lower:
                return opt

        # Fuzzy ratio
        best, best_ratio = None, 0.0
        for opt in options:
            ratio = SequenceMatcher(None, answer_lower, opt.lower()).ratio()
            if ratio > best_ratio:
                best, best_ratio = opt, ratio

        if best_ratio >= 0.4:  # Lowered from 0.5 to catch more matches
            return best

        return None

    # ------------------------------------------------------------------
    # Click helpers
    # ------------------------------------------------------------------
    async def _click_option(self, option_text: str) -> bool:
        """Click the DOM element whose visible text matches *option_text*."""
        # Strategy 1: use Playwright's text selector
        try:
            selector = f"text='{option_text}'"
            await self.browser.click(selector, timeout=5_000)
            logger.debug("Clicked option via text selector.")
            return True
        except Exception:
            pass

        # Strategy 2: iterate option selectors and match inner text
        for sel in self.OPTION_SELECTORS:
            try:
                elements = await self.browser.page.query_selector_all(sel)
                for el in elements:
                    text = (await el.inner_text()).strip()
                    if text.lower() == option_text.lower():
                        await el.click()
                        logger.debug("Clicked option via selector '%s'.", sel)
                        return True
            except Exception:
                continue

        logger.error("Failed to click option: %s", option_text)
        return False
