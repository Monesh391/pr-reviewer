"""Run ruff (static analysis) on changed Python files; keep only new-line hits."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from models import Finding


def lint_python(contents: dict, added: dict) -> list:
    """contents: {path: source}. added: {path: set of added line numbers}."""
    findings = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        for path, source in contents.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")
        cmd = [
            sys.executable, "-m", "ruff", "check", "--isolated", "--no-cache",
            "--output-format", "json", "--select", "F,B,S", "--ignore", "S101",
            str(root),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            items = json.loads(proc.stdout or "[]")
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            return []
        for item in items:
            try:
                rel = Path(item["filename"]).resolve().relative_to(root).as_posix()
                line = int(item["location"]["row"])
            except (KeyError, ValueError, TypeError):
                continue
            if line not in added.get(rel, set()):
                continue
            findings.append(
                Finding(
                    path=rel,
                    line=line,
                    severity="medium",
                    confidence=1.0,
                    message=f"[{item.get('code')}] {item.get('message')}",
                    source="ruff",
                )
            )
    return findings
