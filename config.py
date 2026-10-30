"""Central settings, read from environment variables (.env supported)."""
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # keeps tests runnable without python-dotenv
    pass


def _float(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _int(name: str, default: str) -> int:
    return int(os.getenv(name, default))


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

MIN_CONFIDENCE = _float("MIN_CONFIDENCE", "0.7")   # drop weaker findings
MAX_COMMENTS = _int("MAX_COMMENTS", "8")           # cap comments per review
MAX_DIFF_CHARS = _int("MAX_DIFF_CHARS", "30000")   # cap diff size sent to LLM
MAX_FILES = _int("MAX_FILES", "20")

PRICE_PER_MTOK_INPUT = _float("PRICE_PER_MTOK_INPUT", "3.0")
PRICE_PER_MTOK_OUTPUT = _float("PRICE_PER_MTOK_OUTPUT", "15.0")
