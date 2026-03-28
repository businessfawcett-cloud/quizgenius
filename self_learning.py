"""Self-learning system - learns from wrong answers to improve accuracy."""

import json
import os
from datetime import datetime
from pathlib import Path

LEARNING_FILE = "wrong_answers.json"


class SelfLearning:
    def __init__(self):
        self.wrong_answers = self._load_wrong_answers()

    def _load_wrong_answers(self) -> dict:
        """Load previous wrong answers from file."""
        if os.path.exists(LEARNING_FILE):
            try:
                with open(LEARNING_FILE, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_wrong_answers(self):
        """Save wrong answers to file."""
        with open(LEARNING_FILE, "w") as f:
            json.dump(self.wrong_answers, f, indent=2)

    def record_wrong_answer(
        self,
        question_text: str,
        question_type: str,
        our_answer: str,
        correct_answer: str,
        options: list = None,
    ):
        """Record a wrong answer for learning."""
        # Create a simple hash of the question for comparison
        q_hash = str(hash(question_text.lower().strip()[:100]))

        self.wrong_answers[q_hash] = {
            "question": question_text[:500],
            "type": question_type,
            "our_answer": our_answer,
            "correct_answer": correct_answer,
            "options": options[:20] if options else [],
            "timestamp": datetime.now().isoformat(),
            "times_wrong": self.wrong_answers.get(q_hash, {}).get("times_wrong", 0) + 1,
        }

        self._save_wrong_answers()
        print(f"📚 Recorded wrong answer. Total learned: {len(self.wrong_answers)}")

    def get_learned_corrections(self, question_text: str) -> dict | None:
        """Get learned correction for a similar question."""
        q_lower = question_text.lower().strip()

        # Exact match only - don't do partial matching to avoid wrong answers
        # Partial matching is too error-prone
        return None

    def get_prompt_context(self, current_question: str = "") -> str:
        """Get context string for LLM prompts about learned corrections."""
        if not self.wrong_answers:
            return ""

        # Only use exact match for learned answers
        q_hash = str(hash(current_question.lower().strip()[:100]))
        if q_hash in self.wrong_answers:
            return f"\n\n📚 LEARNED ANSWER: {self.wrong_answers[q_hash]['correct_answer']}\n"

        return ""

        # Otherwise show recent corrections
        for key, data in list(self.wrong_answers.items())[-3:]:  # Last 3
            context += f"- Question: {data['question'][:80]}...\n"
            context += f"  Correct answer: {data['correct_answer']}\n"

        return context

    def get_exact_answer(self, question_text: str) -> str | None:
        """Get exact learned answer for a question if we have it."""
        # Try exact match first
        q_hash = str(hash(question_text.lower().strip()[:100]))
        if q_hash in self.wrong_answers:
            answer = self.wrong_answers[q_hash]["correct_answer"]
            # Filter out bad answers
            if answer and len(answer) > 2 and answer.lower() != "question":
                if not any(
                    bad in answer.lower()
                    for bad in [
                        "next question",
                        "continue",
                        "reading",
                        "feedback",
                        "opens in",
                    ]
                ):
                    return answer

        # Try partial match
        best = self.get_learned_corrections(question_text)
        if best:
            answer = best["correct_answer"]
            # Filter out bad answers
            if answer and len(answer) > 2 and answer.lower() != "question":
                if not any(
                    bad in answer.lower()
                    for bad in [
                        "next question",
                        "continue",
                        "reading",
                        "feedback",
                        "opens in",
                    ]
                ):
                    return answer

        return None

    def analyze_mistakes(self) -> str:
        """Analyze common patterns in wrong answers."""
        if len(self.wrong_answers) < 3:
            return "Not enough data to analyze patterns yet."

        # Simple analysis
        analysis = "📊 MISTAKE ANALYSIS:\n"
        analysis += f"Total wrong answers recorded: {len(self.wrong_answers)}\n\n"

        # Group by question type
        by_type = {}
        for data in self.wrong_answers.values():
            qtype = data.get("type", "Unknown")
            if qtype not in by_type:
                by_type[qtype] = []
            by_type[qtype].append(data)

        analysis += "By question type:\n"
        for qtype, entries in by_type.items():
            analysis += f"  - {qtype}: {len(entries)} mistakes\n"

        return analysis
