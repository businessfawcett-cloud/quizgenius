"""Stats tracker for QuizGenius - tracks quiz performance."""

import json
import os
from datetime import datetime
from pathlib import Path

STATS_FILE = Path(__file__).parent / "stats.json"


def load_stats() -> dict:
    """Load stats from file."""
    if not STATS_FILE.exists():
        return {
            "quizzes_completed": 0,
            "questions_solved": 0,
            "total_attempts": 0,
            "correct_answers": 0,
            "average_score": 0.0,
            "time_saved_minutes": 0,
            "history": [],
        }
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "quizzes_completed": 0,
            "questions_solved": 0,
            "total_attempts": 0,
            "correct_answers": 0,
            "average_score": 0.0,
            "time_saved_minutes": 0,
            "history": [],
        }


def save_stats(stats: dict):
    """Save stats to file."""
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)


def record_quiz_completion(
    questions_answered: int,
    correct_first_try: int,
    time_taken_seconds: float,
):
    """Record a completed quiz."""
    stats = load_stats()

    # Estimate time saved (assume 2 min per question if doing manually)
    manual_time = questions_answered * 2 * 60  # in seconds
    time_saved = max(0, manual_time - time_taken_seconds)

    # Calculate score (correct first try / total questions)
    score = (
        (correct_first_try / questions_answered * 100) if questions_answered > 0 else 0
    )

    # Update totals
    stats["quizzes_completed"] += 1
    stats["questions_solved"] += questions_answered
    stats["total_attempts"] += questions_answered
    stats["correct_answers"] += correct_first_try
    stats["time_saved_minutes"] += int(time_saved / 60)

    # Update average score
    if stats["quizzes_completed"] > 0:
        stats["average_score"] = round(
            (stats["correct_answers"] / stats["questions_solved"] * 100), 1
        )

    # Add to history
    stats["history"].append(
        {
            "date": datetime.now().isoformat(),
            "questions": questions_answered,
            "correct_first_try": correct_first_try,
            "score": round(score, 1),
            "time_saved_minutes": int(time_saved / 60),
        }
    )

    # Keep only last 20 history items
    stats["history"] = stats["history"][-20:]

    save_stats(stats)
    return stats


def get_stats() -> dict:
    """Get current stats."""
    return load_stats()
