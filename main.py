"""
QuizGenius - McGraw Hill Quiz Automation
"""

import asyncio
import sys
import time
import os
import requests
from config import setup_logging
from config import GROQ_API_KEY, CHROME_DEBUG_PORT
from browser_controller import BrowserController
from question_parser import QuestionParser
from llm_client import LLMClient
from decision_engine import DecisionEngine
from matching_handler import MatchingHandler
from short_answer_handler import ShortAnswerHandler
from essay_handler import EssayHandler
from self_learning import SelfLearning
from stats_tracker import record_quiz_completion, get_stats, load_stats, save_stats

logger = setup_logging()

QUESTION_DELAY = 6
MAX_STUCK_RETRIES = 2

API_BASE_URL = os.environ.get("API_BASE_URL", "https://your-app.onrender.com")


def print_header():
    print("\n" + "=" * 50)
    print("  QUIZGENIUS - AI Quiz Solver")
    print("=" * 50)


def print_step(num, text):
    print(f"  {num}. {text}")


def get_api_key_from_web(user_id):
    """Fetch API key from web backend."""
    try:
        resp = requests.post(
            f"{API_BASE_URL}/api/sync",
            json={"user_id": user_id, "action": "get_key"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("api_key")
    except Exception as e:
        logger.debug(f"Could not connect to web API: {e}")
    return None


def sync_quiz_results(user_id, questions, correct, score, time_taken):
    """Sync quiz results to web backend."""
    if not user_id:
        return
    try:
        requests.post(
            f"{API_BASE_URL}/api/sync",
            json={
                "user_id": user_id,
                "action": "record_quiz",
                "questions": questions,
                "correct": correct,
                "score": score,
                "time": time_taken,
            },
            timeout=10,
        )
    except Exception as e:
        logger.debug(f"Could not sync to web: {e}")


def get_api_key():
    """Get API key from user, .env file, or web account."""
    api_key = GROQ_API_KEY
    user_id = None

    if not api_key or api_key == "your_groq_api_key_here":
        print_header()
        print()
        print("  How would you like to connect?")
        print()
        print("  1. Enter API key directly")
        print("  2. Connect to your QuizGenius account")
        print()
        choice = input("  Enter choice (1 or 2): ").strip()

        if choice == "2":
            user_id = input("  Enter your user ID: ").strip()
            if user_id:
                api_key = get_api_key_from_web(user_id)
                if api_key:
                    print("  Connected to your account!")
                else:
                    print("  Could not fetch API key. Try entering directly.")
                    api_key = input("  Enter API key: ").strip()
        else:
            print()
            print("  Get one free at: https://console.groq.com/keys")
            print()
            api_key = input("  Enter API key: ").strip()

        if api_key:
            env_path = os.path.join(os.path.dirname(sys.executable), ".env")
            if os.path.exists(env_path):
                with open(env_path, "a") as f:
                    f.write(f"\nGROQ_API_KEY={api_key}\n")
                print("  API key saved for next time!")

    if not api_key:
        print("  ERROR: API key required. Get one at https://console.groq.com/keys")
        input("\nPress Enter to exit...")
        sys.exit(1)

    os.environ["GROQ_API_KEY"] = api_key
    return api_key, user_id


async def run():
    """Main automation loop."""
    print_header()
    print()
    print("  Starting up...")
    print()

    time.sleep(1.5)

    # Get API key
    api_key, user_id = get_api_key()
    print()
    print(f"  Connected! API key: {api_key[:10]}...")
    if user_id:
        print(f"  Linked to account!")
    print()

    browser = BrowserController()
    parser = QuestionParser(browser)
    llm = LLMClient()
    engine = DecisionEngine(browser)
    learner = SelfLearning()  # Initialize self-learning

    # Track stats
    start_time = time.time()
    correct_first_try = 0
    retries = 0

    logger.info(f"Self-learning ready. Known mistakes: {len(learner.wrong_answers)}")

    print()
    print("=" * 50)
    print("  NEXT STEPS:")
    print("=" * 50)
    print("  1. Chrome will open automatically")
    print("  2. Go to your McGraw Hill quiz in Chrome")
    print("  3. Wait for quiz to fully load")
    print("  4. Press ENTER when ready to start solving")
    print("=" * 50)
    print("  (Press ENTER or wait 3 seconds to continue...)")
    print("=" * 50)
    try:
        input()
    except:
        pass

    print()
    print("Opening Chrome...")
    import subprocess
    import os
    import socket

    def is_port_open(host, port, timeout=1):
        """Check if a port is open."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def wait_for_port(host, port, max_wait=30):
        """Wait for port to be available."""
        logger.info(f"Waiting for port {port} to be ready...")
        start = time.time()
        while time.time() - start < max_wait:
            if is_port_open(host, port):
                logger.info(f"Port {port} is ready!")
                return True
            time.sleep(1)
        return False

    chrome_opened = False
    try:
        # First try Chrome
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
        chrome_exe = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_exe = path
                break

        if chrome_exe:
            # Remove old user-data-dir if exists (might be locked)
            user_data_dir = r"C:\chrome-debug"
            if os.path.exists(user_data_dir):
                try:
                    import shutil

                    shutil.rmtree(user_data_dir, ignore_errors=True)
                except:
                    pass

            # Launch Chrome with fresh profile
            subprocess.Popen(
                f'"{chrome_exe}" --remote-debugging-port=9222 --user-data-dir="{user_data_dir}" --no-first-run --no-default-browser-check',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            chrome_opened = True
            logger.info("Chrome started! Waiting for debugging port...")
    except Exception as e:
        logger.info(f"Could not auto-open Chrome: {e}")

    # If Chrome didn't work, try Edge
    if not chrome_opened:
        try:
            edge_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ]
            for path in edge_paths:
                if os.path.exists(path):
                    user_data_dir = r"C:\edge-debug"
                    if os.path.exists(user_data_dir):
                        try:
                            import shutil

                            shutil.rmtree(user_data_dir, ignore_errors=True)
                        except:
                            pass

                    subprocess.Popen(
                        f'"{path}" --remote-debugging-port=9222 --user-data-dir="{user_data_dir}" --no-first-run --no-default-browser-check',
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    chrome_opened = True
                    logger.info("Edge started! Waiting for debugging port...")
                    break
        except Exception as e:
            logger.info(f"Could not auto-open Edge: {e}")

    # Wait for the debugging port to be ready
    if chrome_opened:
        if wait_for_port("127.0.0.1", 9222, max_wait=30):
            logger.info("Chrome/Edge debugging port is ready!")
            time.sleep(2)  # Extra wait for Chrome to fully initialize
        else:
            logger.warning("Debugging port not ready, will try to connect anyway...")

        print()
        print("=" * 50)
        print("  Chrome opened!")
        print("  1. Go to your McGraw Hill quiz")
        print("  2. Wait for it to load")
        print("  3. Press ENTER when ready (or wait 3 sec)")
        print("=" * 50)
        try:
            input()
        except:
            pass

    # Now try to connect
    try:
        await browser.connect()
        logger.info("Connected to Chrome!")
    except Exception as e:
        logger.error("Could not connect to browser.")
        logger.error("Please open Chrome or Edge manually with:")
        logger.error(
            "chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\\chrome-debug"
        )
        input("\nPress Enter to exit...")
        sys.exit(1)

    questions_answered = 0
    last_question_text = ""
    stuck_count = 0

    while True:
        # --- Step 1: Parse the current question ---
        try:
            question = await parser.parse()
        except RuntimeError as exc:
            # When parsing fails, check if we're on a wrong answer feedback page
            logger.warning(f"Parsing failed: {exc}")

            # Check for wrong answer feedback state
            if await engine.is_wrong_answer_state():
                logger.info("Detected wrong-answer feedback after parse failure")

                # Try wrong-answer recovery
                recovered = await engine.handle_wrong_answer_recovery()
                if not recovered:
                    recovered = await engine.handle_incorrect_feedback()

                if recovered:
                    stuck_count = 0
                    last_question_text = ""
                    await asyncio.sleep(QUESTION_DELAY)
                    continue

            logger.error("Parsing failed — checking if quiz advanced...".format(exc))

            # Try refreshing the page once
            try:
                logger.info("Refreshing page to recover...")
                await browser.page.reload()
                await asyncio.sleep(5)
                new_question = await parser.parse()
                if new_question.question_text:
                    logger.info("Recovered after refresh!")
                    question = new_question
                    stuck_count = 0
                    continue
            except:
                pass

            # Check if quiz might be complete
            try:
                body = await browser.get_text("body")
                if any(
                    text in body.lower()
                    for text in [
                        "completed",
                        "finished",
                        "great work",
                        "your performance",
                    ]
                ):
                    logger.info("Quiz appears to be complete!")
                    break
            except:
                pass

            logger.error("Parsing failed — quiz may be finished. %s", exc)
            break

        # Check if quiz is complete
        if (
            question.progress_current >= question.progress_total
            and question.progress_total > 0
        ):
            logger.info(
                "Quiz complete! %d/%d concepts done.",
                question.progress_current,
                question.progress_total,
            )
            break

        # Detect if we're stuck on the same question (wrong answer scenario)
        if question.question_text == last_question_text:
            stuck_count += 1
            retries += 1  # Track that we had to retry
            logger.info("Same question again (attempt %d).", stuck_count)

            if stuck_count >= MAX_STUCK_RETRIES:
                logger.warning(
                    "Stuck after %d attempts. Running wrong-answer recovery...",
                    stuck_count,
                )
                recovered = await engine.handle_wrong_answer_recovery()
                if recovered:
                    stuck_count = 0
                    last_question_text = ""
                    await asyncio.sleep(QUESTION_DELAY)
                    continue
                else:
                    logger.error("Recovery failed. Stopping.")
                    break
        else:
            stuck_count = 0
            last_question_text = question.question_text

        # --- Check if we're on a wrong-answer feedback page before trying to answer ---
        if await engine.is_wrong_answer_state():
            logger.info(
                "Detected wrong-answer feedback page — recording for learning..."
            )

            # Try to extract correct answer and record for learning
            try:
                body = await browser.get_text("body")
                correct = None
                import re

                # Multiple extraction strategies - try them all
                extracted_answers = []

                # Strategy 1: Look for "Correct Answer" followed by actual answer text
                # Pattern: "Correct Answer" on its own line, then actual answers
                match = re.search(r"Correct Answer\s*:\s*([^\n]+)", body, re.IGNORECASE)
                if match:
                    ans = match.group(1).strip()
                    if ans and len(ans) > 1 and ans.lower() != "question":
                        extracted_answers.append(ans)

                # Strategy 2: "Correct Answer" label, then answers below (common in McGraw Hill)
                if not extracted_answers:
                    # Find "Correct Answer" and get lines after it that look like answers
                    lines = body.split("\n")
                    found_correct_label = False
                    for i, line in enumerate(lines):
                        if re.search(r"^Correct Answer$", line.strip(), re.IGNORECASE):
                            found_correct_label = True
                            # Look at next few lines for answers
                            for j in range(i + 1, min(i + 6, len(lines))):
                                candidate = lines[j].strip()
                                # Skip UI elements
                                skip_patterns = [
                                    "next question",
                                    "continue",
                                    "reading",
                                    "opens in",
                                    "select a concept",
                                    "feedback",
                                    "©",
                                    "privacy",
                                    "terms",
                                    "rights",
                                    "reserved",
                                    "mcgraw",
                                    "hill",
                                    "need help",
                                    "review these",
                                    "concept resources",
                                    "rate your confidence",
                                    "your answer",
                                    "incorrect",
                                    "correct",
                                    "question",
                                ]
                                if (
                                    candidate
                                    and len(candidate) > 2
                                    and len(candidate) < 80
                                ):
                                    if not any(
                                        s in candidate.lower() for s in skip_patterns
                                    ):
                                        # Check if it matches one of our options
                                        for opt in question.options:
                                            if (
                                                opt.lower().strip() in candidate.lower()
                                                or candidate.lower() in opt.lower()
                                            ):
                                                extracted_answers.append(opt)
                                                break
                                        else:
                                            # Just add it if it looks like an answer
                                            if not any(
                                                c.isdigit()
                                                for c in candidate[:5]
                                                if c.isdigit()
                                            ):
                                                extracted_answers.append(candidate)
                            break

                # Strategy 3: Match directly against options - look for which options are highlighted/correct
                if not extracted_answers:
                    # Check if any option text appears right after "Correct Answer"
                    for opt in question.options:
                        # Look for option text near "Correct Answer"
                        pattern = re.escape(opt)
                        match = re.search(
                            rf"Correct Answer[^\n]*{pattern}", body, re.IGNORECASE
                        )
                        if match:
                            extracted_answers.append(opt)

                # Strategy 4: For fill-in-blank - extract from "Field X: answer" pattern
                if not extracted_answers:
                    matches = re.findall(r"Field \d+[:\s]*([^\n]+)", body)
                    for m in matches:
                        if m.strip() and len(m.strip()) > 1:
                            extracted_answers.append(m.strip())

                # Strategy 5: Look for highlighted/correct indicators
                if not extracted_answers:
                    # Look for text in green or bold that might indicate correct answer
                    green_matches = re.findall(
                        r"#[0-9a-fA-F]{6}|green|correct|✓.*?([A-Za-z ]+)",
                        body,
                        re.IGNORECASE,
                    )
                    for m in green_matches:
                        if len(m.strip()) > 2:
                            extracted_answers.append(m.strip())

                # Deduplicate and clean
                if extracted_answers:
                    # Try to match against our known options first
                    final_answers = []
                    for ans in extracted_answers:
                        ans_clean = ans.strip().strip(",").strip(".").strip()
                        # Check if this matches any option
                        matched = False
                        for opt in question.options:
                            if (
                                opt.lower().strip() == ans_clean.lower()
                                or ans_clean.lower() in opt.lower()
                                or opt.lower() in ans_clean.lower()
                            ):
                                if opt not in final_answers:
                                    final_answers.append(opt)
                                    matched = True
                                    break
                        if (
                            not matched
                            and ans_clean
                            and len(ans_clean) > 2
                            and len(ans_clean) < 60
                        ):
                            # Add non-matched candidate if it looks reasonable
                            if ans_clean.lower() not in [
                                x.lower() for x in final_answers
                            ]:
                                final_answers.append(ans_clean)

                    if final_answers:
                        correct = ", ".join(final_answers[:4])
                        logger.info(f"Extracted correct answers: {correct}")

                # Clean up final answer
                if correct and len(correct) > 1:
                    # Final cleanup
                    correct = correct.strip().strip(",").strip(".").strip()

                    learner.record_wrong_answer(
                        question.question_text,
                        question.question_type,
                        "our_answer_here",
                        correct,
                        question.options,
                    )
                    logger.info(f"Recorded correct answer: {correct}")
            except Exception as e:
                logger.debug(f"Failed to extract correct answer: {e}")

            # Try wrong-answer recovery first
            recovered = await engine.handle_wrong_answer_recovery()
            if recovered:
                stuck_count = 0
                last_question_text = ""
                await asyncio.sleep(QUESTION_DELAY)
                continue

            # If that didn't work, try the incorrect feedback handler
            recovered = await engine.handle_incorrect_feedback()
            if recovered:
                stuck_count = 0
                last_question_text = ""
                await asyncio.sleep(QUESTION_DELAY)
                continue

            logger.error("Recovery from feedback page failed. Stopping.")
            break

        # --- Step 2 & 3: Ask the LLM and click answers ---
        q_text_lower = question.question_text.lower() if question.question_text else ""

        # First check if we have a learned answer for this exact question
        learned_exact = learner.get_exact_answer(question.question_text)
        if learned_exact:
            logger.info(f"Using learned exact answer: {learned_exact}")

        # Only treat as multi-select if explicitly says "Multiple Select" in type
        is_multi_select = "multiple select" in question.question_type.lower()

        # Fill blank - but NOT if it has options (those are dropdowns/multi-select)
        is_fill_blank = (
            (
                "fill" in question.question_type.lower()
                and "blank" in question.question_type.lower()
            )
            or ("blank" in q_text_lower and not question.options)
            or ("______" in question.question_text and not question.options)
        )

        is_ordering = (
            "ordering" in question.question_type.lower()
            or "rank" in question.question_type.lower()
        )
        is_matching = (
            "matching" in question.question_type.lower()
            or "ordering" in question.question_type.lower()
            or "rank" in question.question_type.lower()
        )
        is_short_answer = "short answer" in question.question_type.lower()
        is_essay = "essay" in question.question_type.lower()

        if is_matching:
            # Matching/Ordering question handling (drag and drop)
            logger.info(f"Detected {question.question_type}")

            # Try to handle matching question with handler
            handler = MatchingHandler(browser, llm)
            handled = await handler.handle(question)

            if handled:
                await asyncio.sleep(2)
                await engine.submit_confidence_and_next()

                await asyncio.sleep(3)

                if await engine.is_wrong_answer_state():
                    logger.info("Wrong answer detected, recovering...")
                    await engine.handle_wrong_answer_recovery()
                    await asyncio.sleep(QUESTION_DELAY)
                    continue

                try:
                    new_q = await parser.parse()
                    if new_q.question_text != question.question_text:
                        questions_answered += 1
                        logger.info(f"=== Answered {questions_answered} ===")
                except:
                    pass
            else:
                logger.warning(
                    "Could not handle matching question. Attempting to advance..."
                )
                await engine.handle_wrong_answer_recovery()

            await asyncio.sleep(QUESTION_DELAY)
            continue

        elif is_short_answer:
            # Short answer question handling
            logger.info("Detected short answer question")

            handler = ShortAnswerHandler(browser, llm)
            handled = await handler.handle(question)

            if handled:
                await asyncio.sleep(2)
                await engine.submit_confidence_and_next()
                questions_answered += 1
                logger.info(
                    f"=== Answered {questions_answered} question(s) | Progress: {question.progress_current + 1}/{question.progress_total} ==="
                )
            else:
                logger.warning("Could not handle short answer question")

            await asyncio.sleep(QUESTION_DELAY)
            continue

        elif is_essay:
            # Essay question handling
            logger.info("Detected essay question")

            handler = EssayHandler(browser, llm)
            handled = await handler.handle(question)

            if handled:
                await asyncio.sleep(2)
                await engine.submit_confidence_and_next()
                questions_answered += 1
                logger.info(
                    f"=== Answered {questions_answered} question(s) | Progress: {question.progress_current + 1}/{question.progress_total} ==="
                )
            else:
                logger.warning("Could not handle essay question")

            await asyncio.sleep(QUESTION_DELAY)
            continue

        elif is_ordering:
            # Ordering question handling
            logger.info("Detected ordering question")

            # Get learned context for this question
            learned = learner.get_learned_corrections(question.question_text)
            learned_ctx = learner.get_prompt_context() if learned else ""

            # Get answer from LLM (should be the correct order)
            try:
                llm_answer = await llm.get_answer(
                    question.question_text,
                    question.options,
                    question.question_type,
                    learned_context=learned_ctx,
                )
            except RuntimeError as exc:
                logger.error("LLM failed — stopping. %s", exc)
                break

            # Handle the ordering
            ordered = await engine.handle_ordering_question(
                [llm_answer] + question.options
            )
            if not ordered:
                logger.warning("Could not handle ordering. Trying to proceed anyway.")

            # Wait and try to click next
            await asyncio.sleep(2)
            await engine.submit_confidence_and_next()

            questions_answered += 1
            logger.info(
                f"=== Answered {questions_answered} question(s) | Progress: {question.progress_current}/{question.progress_total} ==="
            )
            await asyncio.sleep(QUESTION_DELAY)
            continue

        elif is_fill_blank:
            # Fill-in-the-blank question handling
            logger.info("Detected fill-in-the-blank question")

            # First check if we have exact learned answer
            if learned_exact:
                llm_answer = learned_exact
                logger.info(f"Using learned fill-blank answer: {llm_answer}")
            else:
                # Get learned context for this question
                learned = learner.get_learned_corrections(question.question_text)
                learned_ctx = (
                    learner.get_prompt_context(question.question_text)
                    if learned
                    else ""
                )

                # Get answer from LLM
                try:
                    llm_answer = await llm.get_answer(
                        question.question_text,
                        question.options,
                        question.question_type,
                        learned_context=learned_ctx,
                    )
                except RuntimeError as exc:
                    logger.error("LLM failed — stopping. %s", exc)
                    break

            # Fill in the blank
            filled = await engine.fill_blank_answer(
                llm_answer, question.fill_blank_input_ids or []
            )
            if not filled:
                logger.warning("Could not fill blank. Trying to proceed anyway.")

            # Wait for input to be registered
            await asyncio.sleep(2)

            # Try to click confidence button and next
            await engine.submit_confidence_and_next()

            answered_count = questions_answered + 1
            logger.info(
                f"=== Answered {answered_count} question(s) | Progress: {question.progress_current}/{question.progress_total} ==="
            )
            await asyncio.sleep(QUESTION_DELAY)
            continue

        elif is_multi_select:
            # Multi-select: get all answers and click each one
            # First check if we have exact learned answer
            if learned_exact:
                # Parse the learned answer (may be comma-separated)
                answers = [a.strip() for a in learned_exact.split(",")]
                logger.info(f"Using learned multi-select answers: {answers}")
            else:
                # Get learned context for this question
                learned = learner.get_learned_corrections(question.question_text)
                learned_ctx = (
                    learner.get_prompt_context(question.question_text)
                    if learned
                    else ""
                )

                try:
                    answers = await llm.get_multiple_answers(
                        question.question_text,
                        question.options,
                        question.question_type,
                        learned_context=learned_ctx,
                    )
                except RuntimeError as exc:
                    # Multi-select failed - try single answer instead
                    logger.warning(
                        f"Multi-select failed: {exc}. Trying single answer..."
                    )
                try:
                    llm_answer = await llm.get_answer(
                        question.question_text,
                        question.options,
                        question.question_type,
                        learned_context=learned_ctx,
                    )
                    # Clean up answer - take first line only if multiple
                    llm_answer = llm_answer.split("\n")[0].strip()
                    clicked = await engine.select_answer(llm_answer, question.options)
                    if clicked:
                        await engine.submit_confidence_and_next()
                        questions_answered += 1
                        logger.info(
                            f"=== Answered {questions_answered} via fallback ==="
                        )
                        await asyncio.sleep(QUESTION_DELAY)
                        continue  # Skip the rest of multi-select code
                    else:
                        # Could not match, try first option
                        if question.options:
                            await engine.select_answer(
                                question.options[0], question.options
                            )
                            await engine.submit_confidence_and_next()
                            questions_answered += 1
                            logger.info("Used first option as fallback")
                        await asyncio.sleep(QUESTION_DELAY)
                        continue  # Skip the rest of multi-select code
                except Exception as e2:
                    logger.error(f"Single answer also failed: {e2}")
                    break

            logger.info(f"Multi-select answers: {answers}")
            any_clicked = False
            for ans in answers:
                clicked = await engine.select_answer(ans, question.options)
                if clicked:
                    any_clicked = True
                    await asyncio.sleep(0.5)  # brief pause between clicks

            if not any_clicked:
                logger.warning(
                    "Could not click any multi-select answer. Trying first option."
                )
                if question.options:
                    any_clicked = await engine.select_answer(
                        question.options[0], question.options
                    )

            if not any_clicked:
                # Click failed — if same question, try recovery instead of stopping
                if stuck_count > 0:
                    logger.warning(
                        "Click failed on repeated question — trying recovery."
                    )
                    recovered = await engine.handle_wrong_answer_recovery()
                    if recovered:
                        stuck_count = 0
                        last_question_text = ""
                        await asyncio.sleep(QUESTION_DELAY)
                        continue
                logger.error("Could not click any option. Stopping.")
                break
        else:
            # Single answer question
            # First check if we have exact learned answer
            if learned_exact:
                llm_answer = learned_exact
                logger.info(f"Using learned answer: {llm_answer}")
            else:
                # Get learned context for this question
                learned = learner.get_learned_corrections(question.question_text)
                learned_ctx = (
                    learner.get_prompt_context(question.question_text)
                    if learned
                    else ""
                )

                try:
                    llm_answer = await llm.get_answer(
                        question.question_text,
                        question.options,
                        question.question_type,
                        learned_context=learned_ctx,
                    )
                except RuntimeError as exc:
                    logger.error("LLM failed — stopping. %s", exc)
                    break

            clicked = await engine.select_answer(llm_answer, question.options)
            if not clicked:
                logger.warning(
                    "Could not click answer '%s'. Trying first option as fallback.",
                    llm_answer,
                )
                if question.options:
                    clicked = await engine.select_answer(
                        question.options[0], question.options
                    )

            if not clicked:
                # Click failed — if same question, try recovery instead of stopping
                if stuck_count > 0:
                    logger.warning(
                        "Click failed on repeated question — trying recovery."
                    )
                    recovered = await engine.handle_wrong_answer_recovery()
                    if recovered:
                        stuck_count = 0
                        last_question_text = ""
                        await asyncio.sleep(QUESTION_DELAY)
                        continue
                logger.error("Could not click any option. Stopping.")
                break

        # Short pause for the page to register the click
        await asyncio.sleep(1)

        # --- Step 4: Submit confidence and advance ---
        await engine.submit_confidence_and_next()

        # Track correct first try (if stuck_count was 0, we got it right first time)
        if stuck_count == 0:
            correct_first_try += 1

        questions_answered += 1
        logger.info(
            "=== Answered %d question(s) | Progress: %d/%d ===",
            questions_answered,
            question.progress_current + 1,
            question.progress_total,
        )

        # Wait for the next question to load
        await asyncio.sleep(QUESTION_DELAY)

    # --- Done ---
    elapsed_time = time.time() - start_time
    logger.info(
        "Finished. Total questions answered this session: %d", questions_answered
    )

    # Record stats
    if questions_answered > 0:
        stats = record_quiz_completion(
            questions_answered=questions_answered,
            correct_first_try=correct_first_try,
            time_taken_seconds=elapsed_time,
        )
        logger.info(
            f"Stats recorded: {stats['quizzes_completed']} quizzes, "
            f"{stats['questions_solved']} questions, {stats['average_score']}% avg score"
        )

        # Sync to web account if connected
        if user_id:
            score = stats.get("average_score", 0)
            sync_quiz_results(
                user_id, questions_answered, correct_first_try, score, int(elapsed_time)
            )
            logger.info("Results synced to your account!")
        logger.info(
            f"📊 Stats recorded: {stats['quizzes_completed']} quizzes, "
            f"{stats['questions_solved']} questions, {stats['average_score']}% avg score"
        )

    # Try to click "Complete Assignment" button
    try:
        await asyncio.sleep(2)
        # Look for complete assignment button
        complete_btn = await browser.page.query_selector(
            "button:has-text('Complete Assignment'), "
            "button:has-text('Submit'), "
            "button:has-text('Finish'), "
            "[data-automation-id*='complete'], "
            "[data-automation-id*='submit']"
        )
        if complete_btn:
            await complete_btn.click()
            logger.info("Clicked Complete Assignment button")
            await asyncio.sleep(3)

            # Parse results page for accuracy
            try:
                body = await browser.page.inner_text("body")
                import re

                # Look for "X% accuracy" pattern
                accuracy_match = re.search(r"(\d+)% accuracy", body, re.IGNORECASE)
                if accuracy_match:
                    real_accuracy = int(accuracy_match.group(1))
                    logger.info(f" Real accuracy from McGraw Hill: {real_accuracy}%")

                    # Update stats with real accuracy
                    stats = load_stats()
                    if stats["history"]:
                        stats["history"][-1]["score"] = real_accuracy
                        stats["average_score"] = real_accuracy
                        stats["correct_answers"] = int(
                            real_accuracy / 100 * stats["questions_solved"]
                        )
                        save_stats(stats)
                        logger.info(
                            f"📊 Updated stats with real accuracy: {real_accuracy}%"
                        )
            except Exception as e:
                logger.warning(f"Could not parse accuracy: {e}")
    except Exception as e:
        logger.warning(f"Could not click complete button: {e}")

    await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
    print("\n" + "=" * 50)
    print("  Done! Press Enter to close...")
    print("=" * 50 + "\n")
    input()
