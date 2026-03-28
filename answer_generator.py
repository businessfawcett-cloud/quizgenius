#!/usr/bin/env python3
"""
Reading Guide Answer Generator - Standalone Version
Generates answers for Canvas reading guide without browser connection
"""

import asyncio
import json
import logging
from typing import List, Tuple, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ReadingGuideGenerator:
    """Generate answers for Canvas reading guide"""

    def __init__(self):
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

    def format_answers_for_copying(self, answers: Dict[str, str]) -> str:
        """Format answers for easy copying to Google Docs"""
        result = []

        result.append("=== READING GUIDE ANSWERS - LESSON 7.3 ===\n")

        # Vocabulary section
        result.append("VOCABULARY TERMS:")
        result.append("-" * 50)

        for term, definition in self.vocab_terms:
            if term in answers:
                result.append(f"{term} - {answers[term]}")

        result.append("\n")

        # Questions section
        result.append("QUESTIONS:")
        result.append("-" * 50)

        for i, (_, question) in enumerate(self.questions):
            question_key = f"question_{i}"
            if question_key in answers:
                result.append(f"Q{i + 1}: {question}")
                result.append(f"A{i + 1}: {answers[question_key]}")
                result.append("")

        return "\n".join(result)

    def save_answers(self, answers: Dict[str, str]):
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

            # Also save formatted version for easy copying
            formatted = self.format_answers_for_copying(answers)
            with open("reading_guide_formatted.txt", "w", encoding="utf-8") as f:
                f.write(formatted)

            logger.info("Answers saved to:")
            logger.info("- reading_guide_answers.json (structured)")
            logger.info("- reading_guide_formatted.txt (formatted for copying)")

        except Exception as e:
            logger.error(f"Error saving answers: {e}")

    async def run(self):
        """Run the answer generation"""
        try:
            logger.info("=== Reading Guide Answer Generator ===")
            logger.info(
                "Lesson 7.3: A Second World War, 1937-1945 & The Recovery of Europe"
            )

            # Generate answers
            logger.info("Generating answers...")
            answers = await self.generate_answers()

            # Save answers
            await self.save_answers(answers)

            # Show summary
            logger.info("\n=== SUMMARY ===")
            logger.info(
                f"Vocabulary terms generated: {len([a for a in answers.keys() if a in [t[0] for t in self.vocab_terms]])}"
            )
            logger.info(
                f"Questions generated: {len([a for a in answers.keys() if a.startswith('question_')])}"
            )

            logger.info("\n=== INSTRUCTIONS ===")
            logger.info("1. Open your Google Docs")
            logger.info(
                "2. Copy the formatted content from reading_guide_formatted.txt"
            )
            logger.info("3. Paste into your documents")
            logger.info("4. Submit to Canvas")

            logger.info("\n🎉 Answers generated successfully!")

            return True

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return False


async def main():
    """Main function"""
    generator = ReadingGuideGenerator()
    success = await generator.run()

    if success:
        logger.info("✅ Task completed!")
    else:
        logger.error("❌ Task failed")


if __name__ == "__main__":
    asyncio.run(main())
