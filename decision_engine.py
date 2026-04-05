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
        "button.btn-primary:has-text('Next')",
        "button.btn-primary:has-text('Submit')",
    ]

    # Check my work button (validates answer)
    CHECK_MY_WORK_SELECTORS = [
        "button:has-text('Check my work')",
        "[data-automation-id='check-answer']",
        "button.btn-primary:has-text('Check')",
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
        """Click Check My Work (if available), verify answer, then click Next."""

        # First check if we're in Check My Work mode - need to return to question first
        try:
            body = await self.browser.get_text("body")
            body_lower = body.lower()

            if "check my work" in body_lower and "return to question" in body_lower:
                logger.info(
                    "In Check My Work mode - returning to question to answer properly"
                )
                for sel in [
                    "button:has-text('Return to question')",
                    "a:has-text('Return to question')",
                ]:
                    try:
                        await self.browser.click(sel, timeout=5000)
                        logger.info("Clicked Return to question")
                        await asyncio.sleep(2)
                        return  # Will re-parse and re-answer
                    except:
                        continue
        except Exception:
            pass

        # Step 1: Try clicking "Check my work" button first
        check_work_clicked = False
        has_check_button = False

        for sel in self.CHECK_MY_WORK_SELECTORS:
            try:
                count = await self.browser.get_element_count(sel)
                if count > 0:
                    has_check_button = True
                    btn = await self.browser.page.query_selector(sel)
                    if btn:
                        is_disabled = await btn.get_attribute("disabled")
                        if is_disabled:
                            continue
                        await btn.click()
                        logger.info(f"Clicked Check My Work: {sel}")
                        await asyncio.sleep(2)
                        check_work_clicked = True
                        break
            except Exception:
                continue

        # If there's no Check My Work button, flag it and proceed
        if not has_check_button:
            logger.warning(
                "No 'Check my work' button found - flagging for manual review"
            )

        # Step 2: If Check My Work was clicked, verify answer correctness
        if check_work_clicked:
            try:
                body = await self.browser.get_text("body")
                body_lower = body.lower()

                # Check if we can determine if answer was correct
                if "correct" in body_lower and "incorrect" in body_lower:
                    if "incorrect" in body_lower or "wrong" in body_lower:
                        logger.warning(
                            "Answer appears to be INCORRECT - flagging for manual review"
                        )
                        for sel in [
                            "button:has-text('Return to question')",
                            "a:has-text('Return to')",
                        ]:
                            try:
                                await self.browser.click(sel, timeout=3000)
                                logger.info(
                                    "Returned to question after incorrect answer"
                                )
                                await asyncio.sleep(1)
                                return
                            except:
                                continue
                    else:
                        logger.info("Answer appears to be CORRECT")
                elif "correct" in body_lower:
                    logger.info("Answer appears to be CORRECT")
            except Exception as e:
                logger.debug(f"Could not verify answer: {e}")

        # Step 3: Click Next button to proceed
        for sel in self.NEXT_SELECTORS:
            try:
                count = await self.browser.get_element_count(sel)
                if count > 0:
                    buttons = await self.browser.page.query_selector_all(sel)
                    for btn in buttons:
                        try:
                            is_visible = await btn.is_visible()
                            if is_visible:
                                text = await btn.inner_text()
                                await btn.click()
                                logger.info(f"Clicked next: {sel} - '{text.strip()}'")
                                await asyncio.sleep(2)
                                return
                        except Exception:
                            continue
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
            body_lower = body_text.lower()

            # If "Check my work" is in the page, we're in verification mode - not wrong answer feedback
            if "check my work" in body_lower:
                return False

            # Check if we're on the feedback page (not the original question)
            feedback_indicators = [
                "select a concept resource to continue",
                "you must review a resource",
                "your answer incorrect",
                "before moving on, you must review",
            ]

            for indicator in feedback_indicators:
                if indicator in body_lower:
                    logger.debug("Wrong-answer indicator matched: '%s'", indicator)
                    return True

            # Check if there's a "Return to question" without "Check my work"
            if "return to question" in body_lower:
                return True

        except Exception:
            pass

        return False
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
        # For ezto format, try clicking by label text
        try:
            # Try label selector - labels contain option text
            labels = await self.browser.page.query_selector_all("label")
            for label in labels:
                try:
                    text = (await label.inner_text()).strip()
                    if (
                        option_text.lower() in text.lower()
                        or text.lower() in option_text.lower()
                    ):
                        await label.click()
                        logger.info(f"Clicked option via label: {text[:50]}")
                        return True
                except Exception:
                    continue
        except Exception:
            pass

        # Try clicking radio buttons directly
        try:
            radios = await self.browser.page.query_selector_all("input[type='radio']")
            for radio in radios:
                try:
                    await radio.click()
                    logger.info("Clicked radio button")
                    return True
                except Exception:
                    continue
        except Exception:
            pass

        # Strategy 1: use Playwright's text selector (partial match)
        try:
            # Try partial text matching
            words = option_text.split()[:3]  # First 3 words
            partial_text = " ".join(words)
            selector = f"text='{partial_text}'"
            await self.browser.click(selector, timeout=5_000)
            logger.debug("Clicked option via partial text selector.")
            return True
        except Exception:
            pass

        # Strategy 2: iterate option selectors and match inner text
        for sel in self.OPTION_SELECTORS:
            try:
                elements = await self.browser.page.query_selector_all(sel)
                for el in elements:
                    text = (await el.inner_text()).strip()
                    # Partial match
                    if (
                        option_text.lower() in text.lower()
                        or text.lower() in option_text.lower()
                    ):
                        await el.click()
                        logger.debug("Clicked option via selector '%s'.", sel)
                        return True
            except Exception:
                continue

        logger.error("Failed to click option: %s", option_text)
        return False
