"""Configuration loader for environment variables and project settings."""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Try to load .env from same directory as exe
if getattr(sys, "frozen", False):
    # Running as compiled exe
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).parent

env_path = base_dir / ".env"
load_dotenv(env_path)

# --- LLM API (Groq - Free, unlimited) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Aliases for compatibility
GLM_API_KEY = GROQ_API_KEY
GLM_MODEL = GROQ_MODEL

# --- Browser ---
CHROME_DEBUG_PORT = int(os.getenv("CHROME_DEBUG_PORT", "9222"))
CDP_ENDPOINT = f"http://127.0.0.1:{CHROME_DEBUG_PORT}"

# --- Quiz ---
TARGET_URL = os.getenv("TARGET_URL", "")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
RETRY_DELAY = 1  # seconds between retries

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def setup_logging() -> logging.Logger:
    """Configure and return the project logger."""
    logger = logging.getLogger("mcgrawhill_bot")
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def validate_config():
    """Ensure required environment variables are set."""
    missing = []
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in your keys."
        )
