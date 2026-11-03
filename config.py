
"""Central settings, read from environment variables (.env supported)."""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _float(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


# Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

# Review settings
MIN_CONFIDENCE = _float("MIN_CONFIDENCE", "0.7")
MAX_COMMENTS = _int("MAX_COMMENTS", "8")
MAX_DIFF_CHARS = _int("MAX_DIFF_CHARS", "30000")
MAX_FILES = _int("MAX_FILES", "20")

# Gemini pricing: configure using the current model's actual pricing.
PRICE_PER_MTOK_INPUT = _float("PRICE_PER_MTOK_INPUT", "0")
PRICE_PER_MTOK_OUTPUT = _float("PRICE_PER_MTOK_OUTPUT", "0")
