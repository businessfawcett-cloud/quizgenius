"""Debug the ezto fallback parsing."""

import asyncio
import re
from browser_controller import BrowserController
from question_parser import QuestionParser


async def main():
    browser = BrowserController(url_keywords=["ezto.mheducation"])
    await browser.connect()

    body = await browser.get_text("body", timeout=5000)
    lines = [line.strip() for line in body.split("\n") if line.strip()]

    skip_phrases = [
        "skip to main content",
        "answer",
        "saved",
        "help",
        "opens in a new window",
        "save & exit",
        "submit",
        "item",
        "points",
        "skipped",
        "ebook",
        "print",
        "references",
        "check my work",
        "check my work button is now disabled",
        "prev",
        "next",
        "visit question map",
        "question map",
        "total",
    ]

    question_text = ""
    options = []
    in_options = False

    print("=== FILTERED LINES ===")
    for line in lines:
        line_lower = line.lower()
        if any(phrase in line_lower for phrase in skip_phrases):
            continue
        print(f"  {line}")

    print("\n=== AFTER FILTERING ===")
    for line in lines:
        line_lower = line.lower()
        if any(phrase in line_lower for phrase in skip_phrases):
            if "multiple" in line_lower and "choice" in line_lower:
                print(f"Found type: {line}")
            in_options = False
            continue

        if re.match(r"^Q\d+[\.\):]", line):
            question_text = line
            in_options = True
            print(f"Question: {line}")
            continue

        if question_text and len(line) > 10 and len(line) < 200:
            options.append(line)
            print(f"Option: {line}")

    print(f"\nQuestion: {question_text}")
    print(f"Options: {options}")

    await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
