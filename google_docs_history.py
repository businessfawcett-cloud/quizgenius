"""
Google Docs Study Guide Filler — History
=========================================
Generates answers for a history study guide via LLM, then fills them
into a Google Doc using keyboard automation (Find → navigate → paste).

Usage:
    1. Chrome must be running with --remote-debugging-port=9222
    2. Have the Google Doc open in a tab
    3. Run:  python google_docs_history.py
"""

import asyncio
import json
import httpx
from config import (
    GLM_API_KEY,
    GLM_API_URL,
    GLM_MODEL,
    MAX_RETRIES,
    RETRY_DELAY,
    setup_logging,
)
from browser_controller import BrowserController

logger = setup_logging()

# ---------------------------------------------------------------------------
# Course context for the LLM
# ---------------------------------------------------------------------------
HISTORY_CONTEXT = (
    "You are an expert world history professor. This is a study guide for a lesson on "
    "'Democracy Denied: Comparing Italy, Germany, and Japan' covering the rise of "
    "authoritarian regimes in the interwar period (1920s-1930s) and their connection "
    "to World War I conditions. Use textbook-standard, historically accurate answers. "
    "Be specific with names, dates, and events. Write at a college student level."
)

# ---------------------------------------------------------------------------
# Study guide structure
# ---------------------------------------------------------------------------

# (term_name, marker text in the doc to search for)
VOCAB_TERMS = [
    ("fascism", "fascism -"),
    ("Benito Mussolini", "Benito Mussolini -"),
    ("Black Shirts", "Black Shirts -"),
    ("National Socialist Party (Nazis)", "National Socialist Party (Nazis) -"),
    ("Adolf Hitler", "Adolf Hitler -"),
    ("Weimar Republic", "Weimar Republic -"),
    ("Nuremberg Laws", "Nuremberg Laws -"),
    ("Kristallnacht", "Kristallnacht -"),
    ("Revolutionary Right (Japan)", "Revolutionary Right (Japan) -"),
]

# (unique end-of-question marker for Ctrl+F, full question text for the LLM)
QUESTIONS = [
    (
        "direct threat to democratic values?",
        "What challenges did the victors of World War I face after their triumph? "
        "Which ideologies and countries presented a direct threat to democratic values?",
    ),
    (
        "greatest influence?",
        "What were fascism's values and what type of people supported or might have "
        "supported fascism and why? Describe at least two types. Where did fascism "
        "have the greatest influence?",
    ),
    (
        "able to do what he did?",
        "Where did fascism first develop and under whose leadership? Why did it "
        "develop here and how was this man able to do what he did?",
    ),
    (
        "power and position of the state?",
        "How did Mussolini envision the state and what did he do to strengthen the "
        "power and position of the state?",
    ),
    (
        "Discuss at least three.",
        "Briefly describe the social, political, and economic conditions in Germany "
        "after World War I that led to disillusionment and the rise of fascism. "
        "Discuss at least three.",
    ),
    (
        "gain power and widespread support?",
        "What message or messages did the Nazis proclaim to the people of Germany and "
        "how did the Nazis eventually gain power and widespread support?",
    ),
    (
        "support of millions of Germans?",
        "What did Hitler specifically do after gaining power and how did these policies "
        "and actions win the support of millions of Germans?",
    ),
    (
        "targeted for special discrimination?",
        "Briefly describe the anti-semitic policies of the Nazis. Why were Jews "
        "targeted for special discrimination?",
    ),
    (
        "Nazi views on the German nation?",
        "Briefly describe Nazi attitudes toward gender and sexuality. What did these "
        "attitudes reveal about Nazi views on the German nation?",
    ),
    (
        "How was Japan different?",
        "In what ways was Japan similar to Italy and Germany in the first half of the "
        "1900s? How was Japan different?",
    ),
    (
        "at least two specific examples.",
        "Why were the 1920s seen as a time of developing a democratic and Western "
        "society in Japan? Describe at least two specific examples.",
    ),
    (
        "respond to these disturbances?",
        "What social and economic issues, however, erupted into riots or generated "
        "tension during this period? How did the elites respond to these disturbances?",
    ),
    (
        "how did they respond?",
        "What event had the greatest impact in the rise of a more authoritarian system "
        "in Japan? How specifically did this event affect the people of Japan and how "
        "did they respond?",
    ),
    (
        "Germany and Italy?",
        "Why did a major fascist party not develop in Japan during the 20s and 30s "
        "like it had in Germany and Italy?",
    ),
    (
        "a more right-wing focus?",
        "What role did the military play in the Japanese government during the 1930s? "
        "What policies were put into place that demonstrated a more right-wing focus?",
    ),
    (
        "support these harsh ideologies?",
        "Briefly describe the similarities in the rise of and support for "
        "authoritarianism in Japan as the people also did in Germany. Why specifically "
        "did the Japanese support these harsh ideologies?",
    ),
]

# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------


async def call_llm(prompt: str) -> str:
    """Single LLM API call with retry logic."""
    headers = {
        "Authorization": f"Bearer {GLM_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/history-study-bot",
        "X-Title": "History Study Guide Bot",
    }
    payload = {
        "model": GLM_MODEL,
        "messages": [
            {"role": "system", "content": HISTORY_CONTEXT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(GLM_API_URL, headers=headers, json=payload)
                resp.raise_for_status()
            data = resp.json()
            content = (data["choices"][0]["message"].get("content") or "").strip()
            if content:
                return content
            reasoning = (data["choices"][0]["message"].get("reasoning") or "").strip()
            if reasoning:
                lines = [l.strip() for l in reasoning.splitlines() if l.strip()]
                return lines[-1] if lines else reasoning
            raise ValueError("Empty LLM response")
        except Exception as exc:
            logger.warning("LLM attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc)
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY * attempt
                if "429" in str(exc):
                    delay = max(delay, 10)
                await asyncio.sleep(delay)

    raise RuntimeError("LLM failed after all retries")


async def generate_vocab(term: str) -> str:
    """Generate a 1-2 sentence vocabulary definition."""
    return await call_llm(
        f"Write 1-2 detailed sentences defining '{term}' and explaining its importance "
        f"in the context of the rise of authoritarianism in Italy, Germany, and Japan "
        f"during the interwar period (1920s-1930s). Do NOT start with the term name — "
        f"just write the definition directly. Be concise but thorough."
    )


async def generate_answer(question: str) -> str:
    """Generate a 2-3 sentence answer to a study guide question."""
    return await call_llm(
        f"Answer this question in 2-3 complete sentences with detailed explanations "
        f"and specific historical examples. Do not restate the question.\n\n"
        f"Question: {question}"
    )


# ---------------------------------------------------------------------------
# Google Docs keyboard automation
# ---------------------------------------------------------------------------


async def click_in_doc(page):
    """Click in the Google Docs editor to ensure focus."""
    editor = await page.query_selector(".kix-appview-editor")
    if editor:
        box = await editor.bounding_box()
        if box:
            # Click in the middle of the editor
            await page.mouse.click(
                box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            )
            await asyncio.sleep(0.5)
            return
    # Fallback: click the page content area
    page_el = await page.query_selector(".kix-page")
    if page_el:
        await page_el.click()
        await asyncio.sleep(0.5)


async def paste_text(page, text: str):
    """Paste text into Google Docs via clipboard."""
    # Copy text to clipboard using a hidden textarea
    await page.evaluate(
        """text => {
        const el = document.createElement("textarea");
        el.value = text;
        el.style.position = "fixed";
        el.style.left = "-9999px";
        document.body.appendChild(el);
        el.select();
        document.execCommand("copy");
        el.remove();
    }""",
        text,
    )
    await asyncio.sleep(0.3)
    await page.keyboard.press("Control+v")
    await asyncio.sleep(0.8)


async def find_in_doc(page, search_text: str):
    """Use Ctrl+F to find text in Google Docs. Returns True if found."""
    await page.keyboard.press("Control+f")
    await asyncio.sleep(1)

    # Clear the find bar and type search text
    await page.keyboard.press("Control+a")
    await asyncio.sleep(0.1)
    await page.keyboard.type(search_text, delay=10)
    await asyncio.sleep(0.8)

    # Press Enter to trigger the search
    await page.keyboard.press("Enter")
    await asyncio.sleep(0.5)

    # Close find bar — cursor stays at found position
    await page.keyboard.press("Escape")
    await asyncio.sleep(0.5)


async def fill_vocab_term(page, marker: str, definition: str):
    """Fill in a vocabulary definition after its marker (e.g., 'fascism -')."""
    logger.info("Filling vocab: %s", marker)
    await find_in_doc(page, marker)

    # After find+escape: the matched text is selected.
    # Press End to go to end of line (deselects and moves cursor to EOL).
    await page.keyboard.press("End")
    await asyncio.sleep(0.2)

    # Type a space then paste the definition
    await paste_text(page, " " + definition)
    logger.info("Done: %s", marker)


async def fill_question_answer(page, marker: str, answer: str):
    """Fill in a question answer. Finds the end of the question, moves down to
    the blank answer area, and pastes the answer."""
    logger.info("Filling question: ...%s", marker[:40])
    await find_in_doc(page, marker)

    # After find+escape: cursor is at end-of-question marker.
    # Press End to ensure we're at end of line.
    await page.keyboard.press("End")
    await asyncio.sleep(0.2)

    # Move down to the blank line after the question
    await page.keyboard.press("ArrowDown")
    await asyncio.sleep(0.2)

    # Go to start of that line (it should be blank)
    await page.keyboard.press("Home")
    await asyncio.sleep(0.2)

    # Paste the answer
    await paste_text(page, answer)
    logger.info("Done: ...%s", marker[:40])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run():
    logger.info("=== History Study Guide Filler ===")

    # --- Phase 1: Generate all answers ---
    logger.info(
        "Phase 1: Generating answers via LLM (this may take a while due to rate limits)..."
    )

    vocab_results = []
    for term, marker in VOCAB_TERMS:
        try:
            definition = await generate_vocab(term)
            vocab_results.append((marker, definition))
            logger.info("Vocab done: %s", term)
            # Add delay to avoid rate limits
            await asyncio.sleep(2)
        except Exception as e:
            logger.error("Vocab FAILED for %s: %s", term, e)
            vocab_results.append((marker, f"[Definition needed for {term}]"))

    question_results = []
    for marker, full_question in QUESTIONS:
        try:
            answer = await generate_answer(full_question)
            question_results.append((marker, answer))
            logger.info("Question done: %s...", full_question[:50])
            # Add delay to avoid rate limits
            await asyncio.sleep(3)
        except Exception as e:
            logger.error("Question FAILED: %s", e)
            question_results.append((marker, "[Answer needed]"))

    # Save answers to file as backup
    backup = {
        "vocab": [(m, d) for m, d in vocab_results],
        "questions": [(m, a) for m, a in question_results],
    }
    with open("history_answers_backup.json", "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=2, ensure_ascii=False)
    logger.info("Answers backed up to history_answers_backup.json")

    # --- Phase 2: Fill in the Google Doc ---
    logger.info("Phase 2: Filling in Google Doc...")

    browser = BrowserController(url_keywords=["docs.google.com"])
    await browser.connect()
    page = browser.page

    # Focus in the document
    await click_in_doc(page)

    # Fill vocabulary definitions
    logger.info("--- Filling vocabulary ---")
    for marker, definition in vocab_results:
        try:
            await fill_vocab_term(page, marker, definition)
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error("Failed to fill vocab '%s': %s", marker, e)

    # Fill question answers
    logger.info("--- Filling questions ---")
    for marker, answer in question_results:
        try:
            await fill_question_answer(page, marker, answer)
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error("Failed to fill question '%s': %s", marker, e)

    logger.info("=== Done! All answers filled in. ===")
    await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
