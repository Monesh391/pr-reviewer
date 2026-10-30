"""Plain data classes shared across modules."""
from dataclasses import dataclass, field


@dataclass
class Finding:
    path: str
    line: int
    severity: str          # high | medium | low
    confidence: float      # 0.0 - 1.0
    message: str
    suggestion: str = ""
    source: str = "llm"    # llm | ruff


@dataclass
class ReviewResult:
    summary: str = ""
    findings: list = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    cost_usd: float = 0.0
    skipped_files: int = 0
