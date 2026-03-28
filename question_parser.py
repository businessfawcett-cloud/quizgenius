"""Question parser — extracts question text and answer options from the McGraw Hill DOM."""

from __future__ import annotations
import asyncio
import re
from dataclasses import dataclass, field
from typing import Optional, List
from config import MAX_RETRIES, RETRY_DELAY, setup_logging

logger = setup_logging()


@dataclass
class ParsedQuestion:
    """Structured representation of a quiz question."""

    question_type: str  # e.g. "True or False", "Multiple Choice"
    question_text: str  # The actual question body
    options: list[str]  # Available answer choices
    progress_current: int = 0  # e.g. 15
    progress_total: int = 0  # e.g. 40
    fill_blank_input_ids: Optional[List[str]] = field(
        default_factory=list
    )  # IDs of fill-in-blank input fields

    def __post_init__(self):
        if self.fill_blank_input_ids is None:
            self.fill_blank_input_ids = []


class QuestionParser:
    """Extracts structured question data from a McGraw Hill Connect page."""

    # CSS selectors tuned for McGraw Hill Connect quiz pages.
    # Multiple fallbacks are tried in order so we survive minor DOM changes.
    SELECTORS = {
        "question_type": [
            ".probe-header",  # McGraw Hill probe header
            ".dlc_question",  # question type label area
            "h2",  # question type heading
        ],
        "question_text": [
            ".prompt",  # McGraw Hill question prompt
            ".dlc_question",  # fallback question container
            "legend",  # fieldset-based forms
            "[role='main']",  # main content area
        ],
        "options": [
            ".choiceText",  # McGraw Hill answer text
            ".printable-option",  # clickable choice row
            ".choice-row",  # choice row container
            "[data-choice-id]",  # ordering choice IDs
            ".ordering-choice",  # ordering choices
            ".sortable-item",  # sortable items
        ],
        "progress": [
            "[aria-label='Assignment Progress']",
        ],
        "fill_blank_input": [
            "input.fitb-input",  # fill in the blank input
            "input[id^='fitbTesting_response']",  # fill in the blank input IDs
        ],
        "fill_blank_question": [
            "Fill in the Blank",  # question type indicator
        ],
    }

    def __init__(self, browser):
        self.browser = browser  # BrowserController instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def parse(self) -> ParsedQuestion:
        """Parse the current page with retry logic."""
        last_error: Exception | None = None

        # Wait for page to be fully loaded
        try:
            await self.browser.page.wait_for_load_state("networkidle", timeout=10000)
            await asyncio.sleep(2)  # Extra wait for dynamic content
        except Exception:
            pass  # Continue anyway

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                question = await self._extract()

                # For fill-in-the-blank questions, we don't need options
                is_fill_blank = (
                    question.fill_blank_input_ids
                    and len(question.fill_blank_input_ids) > 0
                )

                if question.question_text and (question.options or is_fill_blank):
                    logger.info(
                        "Parsed question %d/%d: %s",
                        question.progress_current,
                        question.progress_total,
                        question.question_text[:80],
                    )
                    return question
                raise ValueError("Empty question text or no options found.")
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Parse attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc
                )
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)

        raise RuntimeError(
            f"Failed to parse question after {MAX_RETRIES} attempts: {last_error}"
        )

    # ------------------------------------------------------------------
    # Internal extraction
    # ------------------------------------------------------------------
    async def _extract(self) -> ParsedQuestion:
        """Try every selector group and assemble a ParsedQuestion."""
        question_type = await self._try_selectors(self.SELECTORS["question_type"])
        question_text = await self._try_selectors(self.SELECTORS["question_text"])

        # First check if it's an ordering question (needs special handling)
        body_text = ""
        try:
            body_text = await self.browser.get_text("body")
        except:
            pass

        is_ordering = (
            "ordering" in (question_text + body_text).lower()
            or "rank" in (question_text + body_text).lower()
            or "click and drag" in (question_text + body_text).lower()
        )

        if is_ordering:
            # Extract ordering options directly
            options = await self._extract_ordering_options()
            progress_current, progress_total = await self._parse_progress()

            return ParsedQuestion(
                question_type="Ordering Question",
                question_text=question_text,
                options=options,
                progress_current=progress_current,
                progress_total=progress_total,
                fill_blank_input_ids=[],
            )

        # Normal flow for non-ordering questions
        options = await self._try_option_selectors()
        progress_current, progress_total = await self._parse_progress()

        # Check for matching questions BEFORE checking for empty options
        # (matching questions need special handling - drag and drop)
        if not options:
            body_check = ""
            try:
                body_check = await self.browser.get_text("body")
            except:
                pass

            if (
                "matching" in (question_text + body_check).lower()
                or "drag and drop" in (question_text + body_check).lower()
            ):
                # Extract matching options from body text
                options = await self._extract_matching_options(
                    question_text, body_check
                )
                if options:
                    logger.info(
                        f"Extracted {len(options)} matching options from body text"
                    )
                    question_type = "Matching Question"

        # Check for fill-in-the-blank questions
        fill_blank_input_ids = await self._extract_fill_blank_inputs()

        # Detect fill-in-the-blank from question type text
        qt_lower = question_type.lower()
        if "fill" in qt_lower and "blank" in qt_lower:
            question_type = "Fill in the Blank"

        # Also check main content for the fill-in-blank indicator
        if not fill_blank_input_ids:
            main_text = await self._try_selectors(["[role='main']"])
            if "fill" in main_text.lower() and "blank" in main_text.lower():
                question_type = "Fill in the Blank"
                fill_blank_input_ids = await self._extract_fill_blank_inputs()

        # Clean up the question type string
        question_type = question_type or "Unknown"
        qt_lower = question_type.lower()

        # Also get body text for additional detection
        body_text = ""
        try:
            body_text = await self.browser.get_text("body")
        except:
            pass

        # Check for matching questions (drag and drop)
        if (
            "matching" in qt_lower
            or "pair each" in qt_lower
            or "match each" in qt_lower
        ):
            question_type = "Matching Question"
        elif "drag and drop" in (question_text + body_text).lower():
            question_type = "Matching Question"
        elif "drag and drop application" in (question_text + body_text).lower():
            question_type = "Matching Question"
        elif "true" in qt_lower or "false" in qt_lower:
            question_type = "True or False"
        elif "select" in qt_lower or "all that apply" in qt_lower:
            question_type = "Multiple Select"
        elif "multiple" in qt_lower:
            question_type = "Multiple Choice"
        elif (
            "ordering" in qt_lower
            or "rank" in qt_lower
            or "drag" in qt_lower
            or "ordering question" in (question_text + body_text).lower()
        ):
            question_type = "Ordering Question"
            # Extract ordering options
            if not options:
                options = await self._extract_ordering_options()
        elif (
            "short answer" in (question_text + body_text).lower()
            or "type your answer" in (question_text + body_text).lower()
        ):
            question_type = "Short Answer"
        elif (
            "essay" in (question_text + body_text).lower()
            or "explain in detail" in (question_text + body_text).lower()
        ):
            question_type = "Essay Question"

        return ParsedQuestion(
            question_type=question_type,
            question_text=question_text,
            options=options,
            progress_current=progress_current,
            progress_total=progress_total,
            fill_blank_input_ids=fill_blank_input_ids,
        )

    async def _extract_matching_options(
        self, question_text: str, body_text: str
    ) -> list[str]:
        """Extract options from matching question body text."""
        options = []

        if not body_text:
            return options

        import re

        lines = body_text.split("\n")

        target_names = set()
        target_matches = re.findall(r"([^\n]+?)\s+drop zone \d+ of \d+", body_text)
        for match in target_matches:
            match = match.strip()
            if match and len(match) > 2:
                target_names.add(match)

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
                "matching question",
                "drag and drop",
                "match the",
                "skip to",
                "exit",
                "reading mode",
                "question mode",
                "progress",
                "concepts completed",
                "due",
                "estimated time",
            ]
            if any(phrase in line.lower() for phrase in skip_phrases):
                continue
            if any(
                line.lower() == t.lower() or line.lower() in t.lower()
                for t in target_names
            ):
                continue
            if line and len(line) > 10 and len(line) < 100:
                options.append(line)

        unique_options = list(dict.fromkeys(options))
        return unique_options

    async def _extract_fill_blank_inputs(self) -> list[str]:
        """Extract fill-in-the-blank input field IDs."""
        input_ids = []

        # Try to find fill-in-the-blank input fields
        for sel in ["input.fitb-input", "input[id^='fitbTesting_response']"]:
            try:
                elements = await self.browser.page.query_selector_all(sel)
                for el in elements:
                    try:
                        # Check if visible
                        is_visible = await el.is_visible()
                        if is_visible:
                            input_id = await el.get_attribute("id")
                            if input_id:
                                input_ids.append(input_id)
                    except Exception:
                        continue
            except Exception:
                continue

        return input_ids

    async def _extract_ordering_options(self) -> list[str]:
        """Extract ordering/ranking options from drag-and-drop questions."""
        options = []

        # Try to find ordering/choice elements
        selectors = [
            ".choice-item",
            ".ordering-choice",
            "[data-choice-id]",
            ".drag-item",
            ".sortable-item",
        ]

        for sel in selectors:
            try:
                elements = await self.browser.page.query_selector_all(sel)
                if elements:
                    for el in elements:
                        try:
                            text = await el.inner_text()
                            if text and text.strip():
                                options.append(text.strip())
                        except Exception:
                            continue
                    if options:
                        logger.info(f"Found {len(options)} ordering options")
                        return options
            except Exception:
                continue

        # Fallback: look for text patterns like "Choice 1 of 4"
        try:
            body = await self.browser.get_text("body", timeout=5000)
            if body:
                import re

                # Match patterns like "Choice 1 of 4. Thermic effect of food"
                matches = re.findall(r"Choice \d+ of \d+\.\s*([^\n]+)", body)
                if matches:
                    options = [m.strip() for m in matches]
                    logger.info(f"Found {len(options)} ordering options from body text")
                    return options
        except Exception:
            pass

        return options

    async def _try_selectors(self, selectors: list[str]) -> str:
        """Return text from the first selector that matches an element."""
        for sel in selectors:
            try:
                text = await self.browser.get_text(sel, timeout=3_000)
                if text:
                    return text
            except Exception:
                continue
        return ""

    async def _try_option_selectors(self) -> list[str]:
        """Return answer texts from the first working option selector."""
        for sel in self.SELECTORS["options"]:
            try:
                texts = await self.browser.get_all_texts(sel)
                # Filter out blanks and navigation labels
                filtered = [
                    t
                    for t in texts
                    if t
                    and t.lower()
                    not in (
                        "next",
                        "previous",
                        "submit",
                        "skip",
                        "need help?",
                        "rate your confidence",
                    )
                ]
                if filtered:
                    # Deduplicate while preserving order
                    seen = set()
                    unique = []
                    for t in filtered:
                        if t.lower() not in seen:
                            seen.add(t.lower())
                            unique.append(t)
                    return unique
            except Exception:
                continue
        return []

    async def _parse_progress(self) -> tuple[int, int]:
        """Extract 'X of Y Concepts completed' progress numbers."""
        for sel in self.SELECTORS["progress"]:
            try:
                text = await self.browser.get_text(sel, timeout=3_000)
                match = re.search(r"(\d+)\s+of\s+(\d+)", text)
                if match:
                    return int(match.group(1)), int(match.group(2))
            except Exception:
                continue

        # Fallback: search the entire page body
        try:
            body = await self.browser.get_text("body", timeout=5_000)
            match = re.search(r"(\d+)\s+of\s+(\d+)\s+Concepts", body)
            if match:
                return int(match.group(1)), int(match.group(2))
        except Exception:
            pass

        return 0, 0
