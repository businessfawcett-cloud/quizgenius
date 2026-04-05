import re

with open("D:/Mcgrawhill/question_parser.py", "r") as f:
    content = f.read()

old = """    # CSS selectors tuned for McGraw Hill Connect quiz pages.
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
    }"""

new = """    SELECTORS = {
        "question_type": [
            ".probe-header",
            ".dlc_question",
            "h2",
            ".question-type",
            "span.qz-type-label",
            "[class*='question-type']",
        ],
        "question_text": [
            ".prompt",
            ".dlc_question",
            "legend",
            "[role='main']",
            ".question-text",
            ".item-question",
            "div[class*='question-text']",
            ".assessment-question",
            "h3.pg-question",
            ".question-body",
        ],
        "options": [
            ".choiceText",
            ".printable-option",
            ".choice-row",
            "[data-choice-id]",
            ".ordering-choice",
            ".sortable-item",
            ".multiple-choice-option",
            ".answer-choice",
            ".choice",
            "label.choice-label",
            ".option-text",
            "div[class*='choice-item']",
            "ul.choices li",
            ".answer-container label",
            "div[class*='answer-option']",
            ".quiz-question-answer",
        ],
        "progress": [
            "[aria-label='Assignment Progress']",
            ".progress-indicator",
            ".question-counter",
            ".progress-text",
            "div[class*='progress']",
            ".quiz-progress",
        ],
        "fill_blank_input": [
            "input.fitb-input",
            "input[id^='fitbTesting_response']",
            "input[type='text'].fitb",
        ],
        "fill_blank_question": [
            "Fill in the Blank",
        ],
    }"""

if old in content:
    content = content.replace(old, new)
    with open("D:/Mcgrawhill/question_parser.py", "w") as f:
        f.write(content)
    print("Updated selectors!")
else:
    print("Old pattern not found")
