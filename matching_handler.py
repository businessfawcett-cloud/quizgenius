"""Matching question handler - drag and drop automation."""

from __future__ import annotations
import asyncio
from config import setup_logging

logger = setup_logging()


class MatchingHandler:
    """Handles matching/drag-and-drop questions."""

    SOURCE_SELECTORS = [
        "[draggable='true']",
        ".draggable-item",
        ".drag-item",
        ".match-source",
        ".ordering-choice",
        "[data-choice-id]",
        ".sortable-item",
        "[data-automation-id*='ordering']",
    ]

    TARGET_SELECTORS = [
        ".drop-zone",
        ".matching-target",
        "[data-drop-zone]",
        ".ordering-target",
        ".dropzone",
        ".sortable-placeholder",
    ]

    # Ordering/ranking specific selectors
    ORDER_ITEM_SELECTORS = [
        ".ordering-choice",
        ".choice-item",
        "[data-choice-id]",
        ".sortable-item",
        "[data-automation-id*='choice']",
        "li[role='listitem']",
    ]

    def __init__(self, browser, llm_client):
        self.browser = browser
        self.llm = llm_client

    async def detect_matching(
        self, question_text: str = "", body_text: str = ""
    ) -> bool:
        """Check if current question is a matching/drag-drop question."""
        indicators = [
            "drag and drop",
            "drag and drop application",
            "pair each",
            "match each",
            "match the following",
            "pair the following",
            "pair each type",
            "match each type",
            "ordering question",
            "rank the following",
            "click and drag",
            "drag on elements",
            "drag and drop application",
        ]

        combined = (question_text + " " + body_text).lower()
        return any(ind in combined for ind in indicators)

    async def _extract_sources(self) -> list[str]:
        """Extract draggable source items from left column."""
        sources = []
        page = self.browser.page

        for selector in self.SOURCE_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    for el in elements:
                        try:
                            text = (await el.inner_text()).strip()
                            if text and len(text) > 0:
                                sources.append(text)
                        except Exception:
                            continue
                    if sources:
                        logger.info(
                            f"Found {len(sources)} sources with selector: {selector}"
                        )
                        return sources
            except Exception:
                continue

        # Fallback: extract from page body text - better filtering
        try:
            body = await self.browser.get_text("body")
            if body:
                import re

                lines = body.split("\n")
                for line in lines:
                    line = line.strip()
                    skip_phrases = [
                        "drop zone",
                        "empty",
                        "need help",
                        "review these",
                        "concept resources",
                        "rate your confidence",
                        "submit your answer",
                        "©",
                        "privacy",
                        "terms",
                        "rights reserved",
                        "mcgraw",
                        "hill",
                        "skip to",
                        "exit assignment",
                        "reading mode",
                        "question mode",
                        "progress",
                        "concepts completed",
                        "due",
                        "estimated time",
                        "instructions",
                        "time check",
                        "match the",
                        "drag and drop",
                        "matching question",
                        "high",
                        "medium",
                        "low",
                        "read about",
                        "dragging over",
                        "droppable",
                    ]
                    if any(phrase in line.lower() for phrase in skip_phrases):
                        continue
                    # Skip if line matches a known target (these are titles, not draggable items)
                    target_ignore = [
                        "cell-mediated immunity",
                        "antibody-mediated immunity",
                    ]
                    if any(line.lower() == t for t in target_ignore):
                        continue
                    # Only include medium-length text items (definitions) - these are the actual draggables
                    if line and len(line) > 20 and len(line) < 95:
                        sources.append(line)
        except Exception:
            pass

        logger.warning(f"Extracted {len(sources)} sources (may include noise)")
        return sources[:10]

    async def _extract_targets(self) -> list[str]:
        """Extract drop zone targets from right column."""
        targets = []
        page = self.browser.page

        for selector in self.TARGET_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    for el in elements:
                        try:
                            text = (await el.inner_text()).strip()
                            if text and len(text) > 0:
                                targets.append(text)
                        except Exception:
                            continue
                    if targets:
                        logger.info(
                            f"Found {len(targets)} targets with selector: {selector}"
                        )
                        return targets
            except Exception:
                continue

        # Fallback: extract target names from body text
        try:
            body = await self.browser.get_text("body")
            if body:
                import re

                unique_targets = []

                # Strategy: In "Match the word with its definition", the TARGETS are the WORDS
                # These are typically:
                # 1. Single words or short phrases at the start of lines
                # 2. Words that appear BEFORE "drop zone" OR at the start of lines
                # 3. NOT the long definition sentences

                lines = body.split("\n")

                for line in lines:
                    line = line.strip()

                    # Skip if too short or too long (target terms should be short)
                    if len(line) < 2 or len(line) > 30:
                        continue

                    # Skip UI elements
                    skip_patterns = [
                        "drop zone",
                        "empty",
                        "need help",
                        "review these",
                        "concept resources",
                        "rate your confidence",
                        "submit",
                        "©",
                        "privacy",
                        "terms",
                        "rights",
                        "mcgraw",
                        "hill",
                        "skip to",
                        "exit",
                        "reading mode",
                        "question mode",
                        "progress",
                        "concepts",
                        "due",
                        "estimated",
                        "instructions",
                        "high",
                        "medium",
                        "low",
                        "reading",
                        "match the",
                        "most appropriate",
                        "time check",
                        "read about",
                        "confidence",
                    ]
                    if any(skip in line.lower() for skip in skip_patterns):
                        continue

                    # Target terms are usually:
                    # - Single words (like "Antigen", "Antibody", "Macrophage")
                    # - Short 2-3 word phrases
                    # - NOT sentences with verbs
                    if len(line) <= 25 and line[0].isupper():
                        # Must NOT contain common definition words
                        if not any(
                            word in line.lower()
                            for word in [
                                " is ",
                                " are ",
                                " can ",
                                " that ",
                                " which ",
                                " and ",
                                " or ",
                            ]
                        ):
                            if line not in unique_targets:
                                unique_targets.append(line)

                if unique_targets:
                    logger.info(
                        f"Extracted {len(unique_targets)} unique targets from body text"
                    )
                    return unique_targets[:8]
        except Exception as e:
            logger.debug(f"Error extracting targets from body: {e}")

        logger.warning(f"Extracted {len(targets)} targets")
        return targets[:10]

    async def _drag_to_target(self, source_text: str, target_text: str) -> bool:
        """Drag a source element to its target zone."""
        page = self.browser.page
        source_escaped = source_text.replace("'", "\\'")
        target_escaped = target_text.replace("'", "\\'")

        # Method 1: Try clicking source then target (select-style matching)
        try:
            # Find all clickable elements and look for source
            source_el = page.locator(f"text={source_text}").first
            target_el = page.locator(f"text={target_text}").first

            # Check if these elements exist and are visible
            if await source_el.count() > 0 and await target_el.count() > 0:
                # Try clicking source first
                await source_el.click()
                await asyncio.sleep(0.5)
                # Then click target
                await target_el.click()
                logger.info(f"Click-select '{source_text}' → '{target_text}'")
                await asyncio.sleep(0.5)
                return True
        except Exception as e:
            logger.debug(f"Click-select failed: {e}")

        # Method 2: Full JS drag with proper element finding
        try:
            result = await page.evaluate(f"""
                async () => {{
                    // Find source element - look for text anywhere in element
                    let source = null;
                    let target = null;
                    
                    // Search all elements for matching text
                    const allElements = document.querySelectorAll('*');
                    for (let el of allElements) {{
                        if (el.textContent && el.textContent.includes('{source_escaped}')) {{
                            // Check if this element is draggable or parent is
                            if (el.getAttribute('draggable') === 'true' || 
                                el.closest('[draggable="true"]')) {{
                                source = el.closest('[draggable="true"]') || el;
                            }}
                        }}
                        if (el.textContent && el.textContent.includes('{target_escaped}')) {{
                            // Look for drop zone nearby
                            target = el;
                        }}
                    }}
                    
                    if (!source || !target) {{
                        // Try finding by role or data attributes
                        for (let el of allElements) {{
                            if (el.getAttribute('role') === 'listitem' || 
                                el.classList.contains('draggable') ||
                                el.classList.contains('choice')) {{
                                if (el.textContent && el.textContent.includes('{source_escaped}')) {{
                                    source = el;
                                }}
                            }}
                            if (el.classList.contains('drop-zone') || 
                                el.getAttribute('data-drop-zone')) {{
                                if (el.textContent && el.textContent.includes('{target_escaped}')) {{
                                    target = el;
                                }}
                            }}
                        }}
                    }}
                    
                    if (!source || !target) {{
                        return false;
                    }}
                    
                    // Get bounding rectangles
                    const sourceRect = source.getBoundingClientRect();
                    const targetRect = target.getBoundingClientRect();
                    
                    // Simulate drag events
                    const dt = new DataTransfer();
                    
                    source.dispatchEvent(new DragEvent('dragstart', {{
                        bubbles: true,
                        cancelable: true,
                        dataTransfer: dt
                    }}));
                    
                    target.dispatchEvent(new DragEvent('dragover', {{
                        bubbles: true,
                        cancelable: true,
                        dataTransfer: dt
                    }}));
                    
                    target.dispatchEvent(new DragEvent('drop', {{
                        bubbles: true,
                        cancelable: true,
                        dataTransfer: dt
                    }}));
                    
                    return true;
                }}
            """)
            if result:
                logger.info(f"JS full drag '{source_text}' → '{target_text}'")
                await asyncio.sleep(0.5)
                return True
        except Exception as e:
            logger.debug(f"JS full drag failed: {e}")

        # Method 3: Native Playwright drag with trial
        try:
            source_locator = page.locator(f"text={source_text}").first
            target_locator = page.locator(f"text={target_text}").first

            await source_locator.drag_to(target_locator, force=True, timeout=5000)
            logger.info(f"Native drag_to '{source_text}' → '{target_text}'")
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.debug(f"Native drag_to failed: {e}")
            if result:
                logger.info(f"JS drag '{source_text}' → '{target_text}'")
                await asyncio.sleep(0.5)
                return True
        except Exception as e:
            logger.debug(f"JS drag failed: {e}")

        # Method 3: Click-based approach - click source, then click target (for select-style matching)
        try:
            # Try clicking source to select
            source_el = page.locator(f"text={source_text}").first
            await source_el.click(timeout=3000)
            await asyncio.sleep(0.3)

            # Try clicking target to place
            target_el = page.locator(f"text={target_text}").first
            await target_el.click(timeout=3000)
            logger.info(f"Click-based selection '{source_text}' → '{target_text}'")
            await asyncio.sleep(0.5)
            return True
        except Exception as e:
            logger.debug(f"Click-based failed: {e}")

        # Method 4: Manual mouse-based drag with longer steps
        try:
            source = await page.query_selector(f"text={source_text}")
            target = await page.query_selector(f"text={target_text}")

            if not source or not target:
                logger.warning(f"Could not find source or target element")
                return False

            source_box = await source.bounding_box()
            target_box = await target.bounding_box()

            if not source_box or not target_box:
                logger.warning(f"Could not get bounding boxes")
                return False

            # Perform manual drag with more steps and hold
            await page.mouse.move(
                source_box["x"] + source_box["width"] / 2,
                source_box["y"] + source_box["height"] / 2,
            )
            await page.mouse.down()
            await asyncio.sleep(0.2)

            # Move in multiple steps toward target
            for i in range(5):
                await page.mouse.move(
                    source_box["x"] + (target_box["x"] - source_box["x"]) * (i + 1) / 5,
                    source_box["y"] + (target_box["y"] - source_box["y"]) * (i + 1) / 5,
                    steps=2,
                )
                await asyncio.sleep(0.2)

            await page.mouse.up()
            await asyncio.sleep(0.3)

            logger.info(f"Manual drag '{source_text}' → '{target_text}'")
            return True

        except Exception as e:
            logger.error(f"Manual drag also failed: {e}")
            return False

    async def get_matching_pairs(
        self, question_text: str, sources: list, targets: list
    ) -> list[tuple]:
        """Ask LLM to determine correct source→target pairs."""

        prompt = f"""You are matching items in a McGraw Hill quiz.

Question: {question_text}

Items to match (drag these):
{chr(10).join(f"- {s}" for s in sources)}

Target options (drop zones):
{chr(10).join(f"- {t}" for t in targets)}

Determine the correct matches. Respond with each match on a new line in format:
SOURCE → TARGET

Example format:
muscle → 73%
adipose → 10-20%
bone → 20%

Correct matches (one per line):"""

        try:
            response = await self.llm._call_api(prompt)

            # Parse response into (source, target) tuples
            matches = []
            for line in response.strip().splitlines():
                line = line.strip()
                if not line:
                    continue

                # Handle both arrow types
                if "→" in line:
                    parts = line.split("→")
                elif "->" in line:
                    parts = line.split("->")
                else:
                    continue

                if len(parts) == 2:
                    source = parts[0].strip()
                    target = parts[1].strip()

                    # Match to actual source/target texts
                    matched_source = self._match_text(source, sources)
                    matched_target = self._match_text(target, targets)

                    if matched_source and matched_target:
                        matches.append((matched_source, matched_target))

            logger.info(f"LLM provided {len(matches)} matching pairs")
            return matches

        except Exception as e:
            logger.error(f"LLM matching failed: {e}")
            return []

    def _match_text(self, text: str, options: list) -> str:
        """Match LLM response to actual option text."""
        text_lower = text.lower().strip()

        for opt in options:
            if opt.lower().strip() == text_lower:
                return opt
            if text_lower in opt.lower():
                return opt
            if opt.lower() in text_lower:
                return opt

        return text if text in options else ""

    async def handle(self, question) -> bool:
        """Handle a matching question - extract, map, and drag."""
        logger.info("Handling matching question...")

        # Get page content for detection
        try:
            body_text = await self.browser.get_text("body")
        except:
            body_text = ""

        # Extract sources and targets
        sources = await self._extract_sources()
        targets = await self._extract_targets()

        if not sources or not targets:
            logger.warning("Could not extract sources or targets for matching question")
            return False

        logger.info(f"Sources: {sources}")
        logger.info(f"Targets: {targets}")

        # Get correct mappings from LLM
        mappings = await self.get_matching_pairs(
            question.question_text, sources, targets
        )

        if not mappings:
            logger.warning("No mappings from LLM, attempting manual matching")
            # Fallback: just click sources in order
            mappings = list(zip(sources[: len(targets)], targets))

        # Drag each source to correct target
        success_count = 0
        for source, target in mappings:
            if await self._drag_to_target(source, target):
                success_count += 1
            await asyncio.sleep(0.5)

        logger.info(f"Successfully dragged {success_count}/{len(mappings)} pairs")
        return success_count > 0

    async def _extract_ordering_options(self) -> list[str]:
        """Extract ordering/ranking options from the page."""
        page = self.browser.page
        options = []

        # Method 1: Look for Choice X of Y patterns in text
        try:
            body = await page.inner_text("body")
            if body:
                import re

                # Match patterns like "Choice 1 of 4. Salt added at the table"
                matches = re.findall(r"Choice \d+ of \d+\.\s*([^\n]+)", body)
                options = [m.strip() for m in matches if m.strip()]
                if options:
                    logger.info(f"Found {len(options)} ordering options from body text")
                    return options
        except Exception as e:
            logger.debug(f"Error extracting ordering from body: {e}")

        # Method 2: Look for ordering choice elements
        for selector in self.ORDER_ITEM_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                if elements:
                    for el in elements:
                        try:
                            text = (await el.inner_text()).strip()
                            if text and len(text) > 2:
                                options.append(text)
                        except:
                            continue
                    if options:
                        logger.info(f"Found {len(options)} ordering options")
                        return options
            except:
                continue

        return options

    async def handle_ordering(self, question) -> bool:
        """Handle ordering/ranking questions - determine correct order and drag."""
        logger.info("Handling ordering question...")

        # Extract the ordering options
        options = await self._extract_ordering_options()

        if not options:
            logger.warning("Could not extract ordering options")
            return False

        # Clean up options (remove "toggle button" suffix)
        clean_options = []
        for opt in options:
            clean = opt.replace(" toggle button", "").replace(" toggle", "").strip()
            clean_options.append(clean)

        logger.info(f"Found ordering options: {clean_options}")

        # Ask LLM for the correct order
        prompt = f"""You are ordering items in a McGraw Hill quiz.

Question: {question.question_text}

Items to order (rank from MOST to LEAST important):
{chr(10).join(f"{i + 1}. {opt}" for i, opt in enumerate(clean_options))}

Respond with ONLY the items in correct order, one per line, using the exact text from above:"""

        try:
            response = await self.llm._call_api(prompt)

            # Parse the response to get ordered list
            ordered = []
            for line in response.strip().splitlines():
                line = line.strip()
                if line:
                    # Match line to an option
                    matched = self._match_text(line, clean_options)
                    if matched and matched not in ordered:
                        ordered.append(matched)

            logger.info(f"LLM ordered: {ordered}")

            if not ordered:
                logger.warning("LLM returned empty order, trying fallback")
                ordered = clean_options

        except Exception as e:
            logger.error(f"LLM ordering failed: {e}")
            ordered = clean_options

        # Now drag elements to reorder
        return await self._perform_ordering_drag(clean_options, ordered)

    async def _perform_ordering_drag(
        self, options: list[str], correct_order: list[str]
    ) -> bool:
        """Actually drag elements to match the correct order."""
        page = self.browser.page

        # Try to find draggable ordering elements
        drag_selectors = [
            ".ordering-choice",
            ".choice-item",
            "[data-choice-id]",
            ".sortable-item",
            ".drag-item",
            "[role='listitem']",
            "li.item",
            ".rank-item",
        ]

        elements = None
        for sel in drag_selectors:
            try:
                elements = await page.query_selector_all(sel)
                if elements and len(elements) >= len(options):
                    logger.info(
                        f"Found {len(elements)} draggable elements with selector: {sel}"
                    )
                    break
            except:
                continue

        if not elements or len(elements) < len(options):
            logger.warning("Could not find draggable ordering elements")
            return False

        # Get current order from DOM
        current_order = []
        for el in elements:
            text = (await el.inner_text()).strip()
            clean = text.replace(" toggle button", "").replace(" toggle", "").strip()
            current_order.append(clean)

        logger.info(f"Current DOM order: {current_order}")
        logger.info(f"Target correct order: {correct_order}")

        # Perform drag-and-drop to reorder
        # Strategy: drag each item from its current position to target position
        try:
            for target_idx, target_text in enumerate(correct_order):
                # Find where this item currently is
                current_idx = None
                for i, curr_text in enumerate(current_order):
                    if (
                        target_text.lower() in curr_text.lower()
                        or curr_text.lower() in target_text.lower()
                    ):
                        current_idx = i
                        break

                if current_idx is None:
                    logger.warning(f"Could not find {target_text} in current order")
                    continue

                if current_idx == target_idx:
                    continue  # Already in correct position

                # Drag from current_idx to target_idx
                source_el = elements[current_idx]
                target_el = elements[target_idx]

                source_box = await source_el.bounding_box()
                target_box = await target_el.bounding_box()

                if not source_box or not target_box:
                    logger.warning(f"Could not get bounding boxes for drag")
                    continue

                # Perform drag
                await page.mouse.move(
                    source_box["x"] + source_box["width"] / 2,
                    source_box["y"] + source_box["height"] / 2,
                )
                await page.mouse.down()
                await asyncio.sleep(0.2)

                # Move to target position (slightly above to drop in place)
                await page.mouse.move(
                    target_box["x"] + target_box["width"] / 2,
                    target_box["y"] + target_box["height"] / 2,
                    steps=10,
                )
                await asyncio.sleep(0.2)
                await page.mouse.up()

                logger.info(
                    f"Dragged '{target_text}' from pos {current_idx} to {target_idx}"
                )

                # Update our tracking of current order
                current_order.pop(current_idx)
                current_order.insert(target_idx, target_text)

                # Re-fetch elements after drag
                elements = None
                for sel in drag_selectors:
                    try:
                        elements = await page.query_selector_all(sel)
                        if elements and len(elements) >= len(options):
                            break
                    except:
                        continue

                if not elements:
                    break

                await asyncio.sleep(0.5)

            logger.info("Drag-and-drop ordering completed")
            return True

        except Exception as e:
            logger.error(f"Error during ordering drag: {e}")
            return False
