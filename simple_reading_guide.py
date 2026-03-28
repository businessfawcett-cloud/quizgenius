#!/usr/bin/env python3
"""
Simple Canvas Reading Guide Automation
Works with your existing browser controller
"""

import asyncio
import json
import logging
import re
from typing import List, Tuple, Dict, Any

from browser_controller import BrowserController

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SimpleReadingGuide:
    """Simple reading guide automation"""

    def __init__(self):
        self.browser_controller = BrowserController()
        self.vocab_terms: List[Tuple[str, str]] = []
        self.questions: List[Tuple[str, str]] = []

        # Manual vocabulary and questions for Lesson 7.3
        # Based on typical WWII and European recovery content
        self.vocab_terms = [
            ("fascism", ""),
            ("Benito Mussolini", ""),
            ("Black Shirts", ""),
            ("National Socialist Party (Nazis)", ""),
            ("Adolf Hitler", ""),
            ("Weimar Republic", ""),
            ("Nuremberg Laws", ""),
            ("Kristallnacht", ""),
            ("Revolutionary Right (Japan)", ""),
        ]

        self.questions = [
            (
                "",
                "What challenges did the victors of World War I face after their triumph? Which ideologies and countries presented a direct threat to democratic values?",
            ),
            (
                "",
                "What were fascism's values and what type of people supported or might have supported fascism and why? Describe at least two types. Where did fascism have the greatest influence?",
            ),
            (
                "",
                "Where did fascism first develop and under whose leadership? Why did it develop here and how was this man able to do what he did?",
            ),
            (
                "",
                "How did Mussolini envision the state and what did he do to strengthen the power and position of the state?",
            ),
            (
                "",
                "Briefly describe the social, political, and economic conditions in Germany after World War I that led to disillusionment and the rise of fascism. Discuss at least three.",
            ),
            (
                "",
                "What message or messages did the Nazis proclaim to the people of Germany and how did these messages help them gain power and widespread support?",
            ),
            (
                "",
                "What did Hitler specifically do after gaining power to consolidate his control and advance Nazi goals?",
            ),
            (
                "",
                "Briefly describe the anti-semitic policies of the Nazi regime and their impact on Jewish populations.",
            ),
        ]

    async def connect_to_browser(self):
        """Connect to existing browser"""
        try:
            logger.info("Connecting to browser...")
            await self.browser_controller.connect()
            logger.info("Connected successfully!")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    async def generate_answers(self) -> Dict[str, str]:
        """Generate answers using LLM"""
        answers = {}

        try:
            from llm_client import get_glm_client

            glm_client = await get_glm_client()

            # History context
            history_context = (
                "You are an expert AP World History professor specializing in World War II (1937-1945) "
                "and the recovery of Europe. Provide detailed, historically accurate answers that would be "
                "appropriate for AP level students. Use specific names, dates, events, and historical "
                "significance. Write in complete sentences with appropriate detail for AP-level work."
            )

            # Set context for LLM
            glm_client.current_options = []

            # Generate vocabulary answers
            logger.info("Generating vocabulary answers...")
            for term, _ in self.vocab_terms:
                try:
                    prompt = f"Define the term '{term}' in the context of World War II (1937-1945) and European recovery. Provide a comprehensive definition suitable for AP World History students."

                    answer = await glm_client.get_answer_prediction(prompt, [])

                    if answer:
                        answers[term] = answer
                        logger.info(f"✓ Generated: {term}")
                    else:
                        answers[term] = f"[Definition needed for {term}]"
                        logger.warning(f"✗ Failed: {term}")

                    await asyncio.sleep(2)  # Rate limiting

                except Exception as e:
                    logger.error(f"Error for {term}: {e}")
                    answers[term] = f"[Definition needed for {term}]"

            # Generate question answers
            logger.info("Generating question answers...")
            for i, (_, question) in enumerate(self.questions):
                try:
                    prompt = f"Answer this AP World History question about World War II (1937-1945) and European recovery: {question} Provide a detailed answer with specific historical information, dates, and events."

                    answer = await glm_client.get_answer_prediction(prompt, [])

                    if answer:
                        answers[f"question_{i}"] = answer
                        logger.info(f"✓ Generated question {i + 1}")
                    else:
                        answers[f"question_{i}"] = "[Answer needed]"
                        logger.warning(f"✗ Failed question {i + 1}")

                    await asyncio.sleep(3)  # Rate limiting

                except Exception as e:
                    logger.error(f"Error for question {i}: {e}")
                    answers[f"question_{i}"] = "[Answer needed]"

        except ImportError:
            logger.error("LLM client not available - using placeholder answers")
            # Use placeholder answers
            for term, _ in self.vocab_terms:
                answers[term] = f"[Definition needed for {term}]"
            for i, _ in enumerate(self.questions):
                answers[f"question_{i}"] = "[Answer needed]"

        return answers

    async def save_answers(self, answers: Dict[str, str]):
        """Save answers to file"""
        try:
            backup_data = {
                "vocab": self.vocab_terms,
                "questions": self.questions,
                "answers": answers,
                "timestamp": asyncio.get_event_loop().time(),
            }

            with open("reading_guide_answers.json", "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            logger.info("Answers saved to reading_guide_answers.json")

        except Exception as e:
            logger.error(f"Error saving answers: {e}")

    async def run(self):
        """Run the automation"""
        try:
            logger.info("=== Simple Reading Guide Automation ===")

            # Connect to browser
            if not await self.connect_to_browser():
                return False

            # Generate answers
            logger.info("Generating answers...")
            answers = await self.generate_answers()

            # Save answers
            await self.save_answers(answers)

            logger.info("=== Answers generated! ===")
            logger.info(
                "Please manually copy the answers from reading_guide_answers.json to your Google Docs"
            )

            return True

        except Exception as e:
            logger.error(f"Automation failed: {e}")
            return False
        finally:
            await self.browser_controller.close()


async def main():
    """Main function"""
    automator = SimpleReadingGuide()
    success = await automator.run()

    if success:
        logger.info("🎉 Reading guide answers generated!")
        logger.info("Check reading_guide_answers.json for the completed content")
    else:
        logger.error("❌ Automation failed")


if __name__ == "__main__":
    asyncio.run(main())
