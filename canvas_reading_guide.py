#!/usr/bin/env python3
"""
Canvas Reading Guide Automation for World History AP
Automatically completes vocabulary and questions from Google Docs
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


class CanvasReadingGuideAutomator:
    """Automates completion of Canvas reading guide assignments"""

    def __init__(self, doc_urls: List[str]):
        self.doc_urls = doc_urls
        self.browser_controller = BrowserController(url_keywords=["docs.google.com"])
        self.vocab_terms: List[Tuple[str, str]] = []
        self.questions: List[Tuple[str, str]] = []

        # History context for this specific assignment
        self.history_context = (
            "You are an expert AP World History professor specializing in World War II (1937-1945) "
            "and the recovery of Europe. Provide detailed, historically accurate answers that would be "
            "appropriate for AP level students. Use specific names, dates, events, and historical "
            "significance. Write in complete sentences with appropriate detail for AP-level work."
        )

    async def extract_content_from_docs(self) -> bool:
        """Extract vocabulary terms and questions from Google Docs"""
        try:
            logger.info("Connecting to browser...")
            await self.browser_controller.connect()

            for doc_url in self.doc_urls:
                logger.info(f"Processing document: {doc_url}")
                await self.browser_controller.page.goto(doc_url)
                await asyncio.sleep(2)  # Wait for document to load

                # Get document content
                content = await self.browser_controller.page_content()

                # Extract vocabulary and questions
                self._parse_document_content(content)

            logger.info(f"Extracted {len(self.vocab_terms)} vocabulary terms")
            logger.info(f"Extracted {len(self.questions)} questions")

            return True

        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return False

    def _parse_document_content(self, content: str):
        """Parse document content to extract vocabulary and questions"""
        lines = content.split("\n")

        current_section = None
        current_question = ""

        for line in lines:
            line = line.strip()

            # Skip empty lines and common headers
            if not line or line.lower() in [
                "vocabulary",
                "questions",
                "reading guide",
                "lesson 7.3",
            ]:
                continue

            # Detect vocabulary terms (usually followed by dash or colon)
            if re.match(r"^[A-Z][a-zA-Z\s]+(?:\s*[-:]\s*)?$", line):
                # This looks like a vocabulary term
                term = line.split("-")[0].split(":")[0].strip()
                if term and len(term) > 2:
                    self.vocab_terms.append((term, ""))
                    current_section = "vocab"
                    continue

            # Detect question patterns
            if re.match(r"^[A-Z].*[?.]$", line) and len(line) > 20:
                # This looks like a question
                if current_section == "vocab" and current_question:
                    # Save the previous vocab definition
                    if self.vocab_terms:
                        self.vocab_terms[-1] = (
                            self.vocab_terms[-1][0],
                            current_question.strip(),
                        )
                    current_question = ""

                current_question = line
                current_section = "question"
                self.questions.append(("", line))
                continue

            # If we're in a question and this line continues it
            if current_section == "question" and current_question and line:
                current_question += " " + line

            # If we're in vocab and this is the definition
            if (
                current_section == "vocab"
                and line
                and not line.startswith("-")
                and not line.startswith(":")
            ):
                if self.vocab_terms:
                    self.vocab_terms[-1] = (self.vocab_terms[-1][0], line.strip())
                current_question = ""

        # Handle last vocab definition
        if current_section == "vocab" and current_question and self.vocab_terms:
            self.vocab_terms[-1] = (self.vocab_terms[-1][0], current_question.strip())

    async def generate_answers(self) -> Dict[str, str]:
        """Generate answers for vocabulary and questions"""
        answers = {}

        # Import LLM client
        try:
            from llm_client import get_glm_client

            glm_client = await get_glm_client()

            # Generate vocabulary answers
            logger.info("Generating vocabulary answers...")
            for term, _ in self.vocab_terms:
                try:
                    prompt = f"Define the term '{term}' in the context of World War II (1937-1945) and European recovery. Provide a comprehensive definition suitable for AP World History students."

                    glm_client.current_options = []
                    answer = await glm_client.get_answer_prediction(prompt, [])

                    if answer:
                        answers[term] = answer
                        logger.info(f"Generated answer for: {term}")
                    else:
                        answers[term] = f"[Definition needed for {term}]"
                        logger.warning(f"Failed to generate answer for: {term}")

                    await asyncio.sleep(2)  # Rate limiting

                except Exception as e:
                    logger.error(f"Error generating answer for {term}: {e}")
                    answers[term] = f"[Definition needed for {term}]"

            # Generate question answers
            logger.info("Generating question answers...")
            for _, question in self.questions:
                try:
                    prompt = f"Answer this AP World History question about World War II (1937-1945) and European recovery: {question} Provide a detailed answer with specific historical information, dates, and events."

                    glm_client.current_options = []
                    answer = await glm_client.get_answer_prediction(prompt, [])

                    if answer:
                        # Use question as key (or first few words)
                        question_key = question[:50]  # First 50 chars as unique key
                        answers[question_key] = answer
                        logger.info(
                            f"Generated answer for question: {question[:50]}..."
                        )
                    else:
                        answers[question] = "[Answer needed]"
                        logger.warning(
                            f"Failed to generate answer for: {question[:50]}..."
                        )

                    await asyncio.sleep(3)  # Rate limiting

                except Exception as e:
                    logger.error(f"Error generating answer for question: {e}")
                    answers[question] = "[Answer needed]"

        except ImportError:
            logger.error("LLM client not available")
            # Generate placeholder answers
            for term, _ in self.vocab_terms:
                answers[term] = f"[Definition needed for {term}]"
            for _, question in self.questions:
                answers[question] = "[Answer needed]"

        return answers

    async def fill_documents(self, answers: Dict[str, str]):
        """Fill the Google Docs with generated answers"""
        try:
            logger.info("Filling documents with answers...")

            for doc_url in self.doc_urls:
                logger.info(f"Filling document: {doc_url}")
                await self.browser_controller.page.goto(doc_url)
                await asyncio.sleep(2)

                # Focus on document
                await self._focus_document()

                # Fill vocabulary terms
                logger.info("Filling vocabulary terms...")
                for term, definition in self.vocab_terms:
                    if term in answers:
                        await self._fill_vocab_term(term, answers[term])
                        await asyncio.sleep(0.5)

                # Fill questions
                logger.info("Filling questions...")
                for _, question in self.questions:
                    question_key = question[:50]
                    if question_key in answers:
                        await self._fill_question_answer(
                            question, answers[question_key]
                        )
                        await asyncio.sleep(0.5)

            logger.info("Documents filled successfully!")

        except Exception as e:
            logger.error(f"Error filling documents: {e}")

    async def _focus_document(self):
        """Focus on the Google Docs editor"""
        try:
            # Try to click on the editor
            editor = await self.browser_controller.page.query_selector(
                ".kix-appview-editor"
            )
            if editor:
                await editor.click()
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning(f"Error focusing document: {e}")

async def _fill_vocab_term(self, term: str, definition: str):
        """Fill a vocabulary term definition"""
        try:
            # Focus on document first
            await self.browser_controller.page.keyboard.press('Control+f')
            await asyncio.sleep(1)
            
            # Type the term to search for
            await self.browser_controller.page.keyboard.type(term)
            await asyncio.sleep(1)
            
            # Navigate to the term
            await self.browser_controller.page.keyboard.press('Enter')
            await asyncio.sleep(0.5)
            
            # Move to end of line and add definition
            await self.browser_controller.page.keyboard.press('End')
            await asyncio.sleep(0.5)
            await self.browser_controller.page.keyboard.type(f" - {definition}")
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error filling vocab term {term}: {e}")

async def _fill_question_answer(self, question: str, answer: str):
        """Fill a question answer"""
        try:
            # Focus on document first
            await self.browser_controller.page.keyboard.press('Control+f')
            await asyncio.sleep(1)
            
            # Type the question to search for
            await self.browser_controller.page.keyboard.type(question[:20])  # First 20 chars
            await asyncio.sleep(1)
            
            # Navigate to the question
            await self.browser_controller.page.keyboard.press('Enter')
            await asyncio.sleep(0.5)
            
            # Move to next line and type answer
            await self.browser_controller.page.keyboard.press('Enter')
            await asyncio.sleep(0.5)
            await self.browser_controller.page.keyboard.type(answer)
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error filling question answer: {e}")

    async def save_backup(self, answers: Dict[str, str]):
        """Save answers to backup file"""
        try:
            backup_data = {
                "vocab": self.vocab_terms,
                "questions": self.questions,
                "answers": answers,
                "timestamp": asyncio.get_event_loop().time(),
            }

            with open("reading_guide_backup.json", "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)

            logger.info("Backup saved to reading_guide_backup.json")

        except Exception as e:
            logger.error(f"Error saving backup: {e}")

    async def run_automation(self):
        """Run the complete automation"""
        try:
            logger.info("=== Canvas Reading Guide Automation ===")

            # Step 1: Extract content from docs
            if not await self.extract_content_from_docs():
                logger.error("Failed to extract content from documents")
                return False

            # Step 2: Generate answers
            answers = await self.generate_answers()

            # Step 3: Save backup
            await self.save_backup(answers)

            # Step 4: Fill documents
            await self.fill_documents(answers)

            logger.info("=== Automation completed successfully! ===")
            return True

        except Exception as e:
            logger.error(f"Automation failed: {e}")
            return False
        finally:
            await self.browser_controller.close()


async def main():
    """Main function"""
    # Your Google Doc URLs
    doc_urls = [
        "https://docs.google.com/document/d/1oA65prdJ5grqL8FZu4z2KkkgV_cJJNvz3NaQZ3s8Ed4/edit",
        "https://docs.google.com/document/d/1Jtj7BpE171_JzdcVwCKvmvb_247VUG5B1LPelTzg2tA/edit",
    ]

    automator = CanvasReadingGuideAutomator(doc_urls)
    success = await automator.run_automation()

    if success:
        logger.info("🎉 Reading guide completed successfully!")
    else:
        logger.error("❌ Reading guide automation failed")


if __name__ == "__main__":
    asyncio.run(main())
