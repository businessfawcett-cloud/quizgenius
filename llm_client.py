"""LLM client — sends questions to the Groq API and returns the predicted answer."""

from __future__ import annotations
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

logger = None


def setup_logger():
    global logger
    if logger is None:
        import logging

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        logger = logging.getLogger("mcgrawhill_bot")
    return logger


setup_logger()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_RETRIES = 5
RETRY_DELAY = 2


class LLMClient:
    """Async client for the Groq chat completions API."""

    def __init__(self):
        self._headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

    async def get_answer(
        self,
        question_text: str,
        options: list[str],
        question_type: str = "",
        learned_context: str = "",
    ) -> str:
        """Send the question to the LLM and return the chosen answer string."""
        prompt = self._build_prompt(
            question_text, options, question_type, learned_context
        )
        logger.debug("LLM prompt:\n%s", prompt)

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                raw = await self._call_api(prompt, options=options)
                answer = raw.strip().strip('"').strip("'").strip(".")
                import re

                answer = re.sub(r"^[\d]+[\.\)]\s*", "", answer)
                answer = re.sub(r"^[A-Za-z][\.\)]\s*", "", answer)
                answer = self._extract_best_option(answer, options)
                logger.info("LLM answered: %s", answer)
                return answer
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc
                )
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY * attempt
                    if "429" in str(exc):
                        delay = max(delay, 5)
                    await asyncio.sleep(delay)

        raise RuntimeError(f"LLM failed after {MAX_RETRIES} attempts: {last_error}")

    async def get_multiple_answers(
        self,
        question_text: str,
        options: list[str],
        question_type: str = "",
        learned_context: str = "",
    ) -> list[str]:
        """For multi-select questions — return a list of matching option strings."""
        import re

        # NEW APPROACH: Ask LLM to evaluate EACH option as True/False
        # This is more reliable than asking for a list
        correct_options = []

        for opt in options:
            # Ask about each option individually
            eval_prompt = (
                f"{LLMClient.COURSE_CONTEXT}\n\n"
                f"Question: {question_text}\n\n"
                f"Option: {opt}\n\n"
                f"Is this option CORRECT? Answer with just TRUE or FALSE.\n"
            )

            try:
                raw = await self._call_api(eval_prompt)
                raw_lower = raw.lower().strip()

                # Check if LLM says this option is true/correct
                if "true" in raw_lower and "false" not in raw_lower.split("true")[0]:
                    correct_options.append(opt)
                    logger.debug(f"Option marked TRUE: {opt}")
                elif raw_lower.startswith("true"):
                    correct_options.append(opt)
                    logger.debug(f"Option marked TRUE: {opt}")
            except Exception as e:
                logger.debug(f"Failed to evaluate option: {e}")

        if len(correct_options) >= 2:
            logger.info(f"Multi-select (evaluated): {correct_options}")
            return correct_options

        # Fallback: Try the original prompt approach
        prompt = self._build_prompt(
            question_text, options, question_type, learned_context
        )
        logger.debug("LLM prompt (multi):\n%s", prompt)

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                raw = await self._call_api(prompt, options=options)
                logger.debug("LLM raw response:\n%s", raw)

                result = []

                # Strategy 1: Check each line for option matches
                lines = raw.strip().splitlines()
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Clean the line
                    line = re.sub(r"^[\d\-\*]+[\.\:\)\-\s]+", "", line)
                    line = (
                        line.strip().strip('"').strip("'").strip(",").strip(".").strip()
                    )

                    if not line or len(line) < 2:
                        continue

                    # Match against options
                    for opt in options:
                        opt_lower = opt.lower().strip()
                        line_lower = line.lower().strip()

                        if (
                            opt_lower == line_lower
                            or opt_lower in line_lower
                            or line_lower in opt_lower
                        ):
                            if opt not in result:
                                result.append(opt)

                # Strategy 2: If we got < 2 results, scan the ENTIRE response for ALL options
                if len(result) < 2:
                    result = []  # Reset
                    full_response = raw.lower()

                    for opt in options:
                        opt_lower = opt.lower().strip()
                        # Check if option text appears in response
                        if opt_lower in full_response:
                            if opt not in result:
                                result.append(opt)
                                logger.debug(f"Found option in full response: {opt}")

                # Strategy 3: Look for comma/AND/OR separated lists in the raw response
                if len(result) < 2:
                    result = []
                    # Find all text that looks like a list
                    # Replace common separators with newlines
                    cleaned = raw.lower()
                    cleaned = re.sub(
                        r",\s*(?=[a-z])", "\n", cleaned
                    )  # comma -> newline
                    cleaned = re.sub(
                        r"\s+and\s+(?=[a-z])", "\n", cleaned
                    )  # and -> newline
                    cleaned = re.sub(
                        r"\s+or\s+(?=[a-z])", "\n", cleaned
                    )  # or -> newline
                    cleaned = re.sub(
                        r";\s*(?=[a-z])", "\n", cleaned
                    )  # semicolon -> newline

                    lines = cleaned.splitlines()
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue

                        for opt in options:
                            opt_lower = opt.lower().strip()
                            if opt_lower in line.lower():
                                if opt not in result:
                                    result.append(opt)

                # Deduplicate while preserving order
                result = list(dict.fromkeys(result))

                if len(result) >= 1:
                    logger.info("LLM multi-answers: %s", result)
                    return result

                raise ValueError("No answers parsed from multi-select response.")
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "LLM multi attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc
                )
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY * attempt
                    if "429" in str(exc):
                        delay = max(delay, 5)
                    await asyncio.sleep(delay)

        raise RuntimeError(
            f"LLM multi failed after {MAX_RETRIES} attempts: {last_error}"
        )

    @staticmethod
    def _extract_best_option(answer: str, options: list[str]) -> str:
        """If the LLM returned verbose text, find which option it refers to."""
        answer_lower = answer.lower().strip()
        for opt in options:
            if opt.lower().strip() == answer_lower:
                return opt
        for opt in options:
            if opt.lower().strip() in answer_lower:
                return opt
        for opt in options:
            if answer_lower in opt.lower():
                return opt
        return answer

    COURSE_CONTEXT = (
        "You are an expert nutrition science professor. "
        "This is a McGraw Hill Connect quiz for a college nutrition course.\n\n"
        "CRITICAL BLOOD & ANEMIA FACTS - Use these for all answers:\n\n"
        "BLOOD COMPONENTS:\n"
        "- Red blood cells (erythrocytes): transport oxygen & CO2\n"
        "- White blood cells (leukocytes): immune defense\n"
        "- Platelets: blood clotting\n"
        "- Plasma: fluid carrying nutrients, hormones, waste products\n\n"
        "HEMOGLOBIN:\n"
        "- Iron-containing protein in red blood cells\n"
        "- Carries oxygen from lungs to tissues\n"
        "- Carries CO2 from tissues to lungs\n"
        "- Each hemoglobin has 4 iron atoms\n\n"
        "IRON:\n"
        "- Essential for hemoglobin synthesis\n"
        "- Sources: red meat, poultry, beans, fortified cereals\n"
        "- RDA: 8mg men, 18mg women\n"
        "- Deficiency: iron-deficiency anemia (fatigue, weakness, pale skin)\n\n"
        "VITAMIN B-12:\n"
        "- Needed for red blood cell formation\n"
        "- Sources: meat, fish, poultry, dairy (NOT in plants)\n"
        "- RDA: 2.4 mcg/day\n"
        "- Deficiency: pernicious/macrocytic anemia (large abnormal RBCs)\n"
        "- Needed for nerve function\n\n"
        "FOLATE (Vitamin B-9):\n"
        "- Needed for DNA synthesis, red blood cells\n"
        "- Sources: leafy greens, beans, fortified grains\n"
        "- RDA: 400 mcg DFE/day\n"
        "- Deficiency: macrocytic anemia\n"
        "- Critical during pregnancy\n\n"
        "VITAMIN B-6:\n"
        "- Needed for hemoglobin synthesis\n"
        "- Sources: meat, fish, potatoes, bananas\n"
        "- RDA: 1.3-1.7 mg/day\n"
        "- Deficiency: sideroblastic anemia\n\n"
        "ANEMIA TYPES:\n"
        "- Iron-deficiency: low iron, small RBCs (microcytic)\n"
        "- B-12 deficiency: pernicious anemia, large RBCs (macrocytic)\n"
        "- Folate deficiency: macrocytic anemia\n"
        "- Hemolytic: RBCs destroyed prematurely\n"
        "- Aplastic: bone marrow doesn't make enough RBCs\n\n"
        "OTHER KEY FACTS:\n"
        "- Bone marrow produces all blood cells\n"
        "- Stem cells in bone marrow give rise to blood cells\n"
        "- Red blood cells live ~120 days\n"
        "- Multi-select: usually 2-4 correct answers; look for TRUE statements\n"
        "- Use EXACT option text in answers - match carefully!\n"
    )

    @staticmethod
    def _build_prompt(
        question_text: str,
        options: list[str],
        question_type: str,
        learned_context: str = "",
    ) -> str:
        """Format the question into a clear LLM prompt."""
        numbered = "\n".join(f"  {i + 1}. {opt}" for i, opt in enumerate(options))

        # Add learned context if available
        context_addon = ""
        if learned_context:
            context_addon = f"\n\n{learned_context}"

        is_multi = (
            "select" in question_type.lower()
            or "all that apply" in question_type.lower()
        )

        is_ordering = (
            "ordering" in question_type.lower() or "rank" in question_type.lower()
        )

        is_fill_blank = (
            "fill" in question_type.lower() and "blank" in question_type.lower()
        )

        if is_ordering:
            return (
                f"{LLMClient.COURSE_CONTEXT}{context_addon}\n\n"
                "This is an ORDERING/RANKING question — arrange items in the correct order.\n"
                "Respond with ONLY the options in correct order (1st to last), one per line. "
                "No explanation, no numbering. Use EXACT option text.\n\n"
                f"Question ({question_type}): {question_text}\n\n"
                f"Options:\n{numbered}\n\n"
                "Correct order (one per line, verbatim option text only):"
            )
        elif is_fill_blank:
            return (
                f"{LLMClient.COURSE_CONTEXT}{context_addon}\n\n"
                "This is a FILL-IN-THE-BLANK question.\n"
                "Provide a SHORT, CONCISE answer - just the keyword or term that fills the blank.\n"
                "Respond with ONLY the single word or short phrase (2-5 words max) that correctly fills the blank.\n"
                "NO full sentences. NO explanations. Just the answer term.\n\n"
                f"Question: {question_text}\n\n"
                "Short keyword answer:"
            )
        elif is_multi:
            # For multi-select, require listing ALL correct answers
            return (
                f"{LLMClient.COURSE_CONTEXT}{context_addon}\n\n"
                "⚠️ CRITICAL: MULTIPLE SELECT - LIST ALL CORRECT ANSWERS! ⚠️\n"
                "This question requires MULTIPLE answers (usually 2-4).\n"
                "Look for TRUE statements in the options.\n\n"
                f"Question: {question_text}\n\n"
                f"Options:\n{numbered}\n\n"
                "IMPORTANT: Put EACH correct answer on its OWN LINE. No commas, no 'and', no explanation.\n"
                "Example format (one answer per line):\n"
                "iron.\n"
                "thiamin.\n"
                "niacin.\n\n"
                "Your answer (each correct option on a separate line):\n"
            )
        else:
            return (
                f"{LLMClient.COURSE_CONTEXT}{context_addon}\n\n"
                "This is a standard quiz question. Read carefully and select the SINGLE best answer.\n"
                "Respond with ONLY the exact text of the correct answer option — "
                "nothing else. No explanation. No reasoning. No numbering.\n\n"
                f"Question ({question_type}): {question_text}\n\n"
                f"Options:\n{numbered}\n\n"
                "Correct answer (verbatim option text only):"
            )

    async def _call_api(self, prompt: str, options: list[str] | None = None) -> str:
        """Make a single request to the Groq completions endpoint."""
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert nutrition science professor. "
                        "Answer McGraw Hill quiz questions accurately. "
                        "Respond with EXACT answer text only. No explanations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 512,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=self._headers,
                json=payload,
            )
            resp.raise_for_status()

        data = resp.json()
        message = data["choices"][0]["message"]
        content = (message.get("content") or "").strip()

        logger.debug("LLM content: %s", content[:200] if content else "None")

        if not content:
            raise ValueError(f"No content in LLM response: {message}")

        if options:
            for opt in options:
                if opt.lower().strip() in content.lower():
                    return opt
                if content.lower().strip() in opt.lower():
                    return opt

        return content
