"""Helpers for working with GitHub unified-diff patches."""
import re

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

SKIP_SUFFIXES = (
    ".lock", ".min.js", ".min.css", ".map", ".md", ".txt", ".svg", ".png",
    ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".ipynb", ".csv", ".json",
)
SKIP_NAMES = {"package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock"}
SKIP_DIRS = ("node_modules/", "vendor/", "dist/", "build/", ".github/")


def iter_patch(patch: str):
    """Yield (kind, new_line_no, text). kind: hunk | add | ctx | del | meta."""
    new_no = 0
    for raw in patch.splitlines():
        m = HUNK_RE.match(raw)
        if m:
            new_no = int(m.group(1))
            yield ("hunk", None, raw)
        elif raw.startswith("+"):
            yield ("add", new_no, raw[1:])
            new_no += 1
        elif raw.startswith("-"):
            yield ("del", None, raw[1:])
        elif raw.startswith("\\"):
            yield ("meta", None, raw)
        else:
            yield ("ctx", new_no, raw[1:] if raw.startswith(" ") else raw)
            new_no += 1


def valid_lines(patch: str) -> set:
    """Line numbers (new file) GitHub lets us comment on: added + context."""
    return {n for kind, n, _ in iter_patch(patch) if kind in ("add", "ctx")}


def added_lines(patch: str) -> set:
    """Line numbers (new file) that were actually added or changed."""
    return {n for kind, n, _ in iter_patch(patch) if kind == "add"}


def number_patch(patch: str) -> str:
    """Prefix each new-file line with 'L<number>|' so the LLM can cite lines."""
    out = []
    for kind, n, text in iter_patch(patch):
        if kind in ("add", "ctx"):
            marker = "+" if kind == "add" else " "
            out.append(f"L{n}|{marker}{text}")
        elif kind == "del":
            out.append(f"   |-{text}")
        else:
            out.append(f"   |{text}")
    return "\n".join(out)


def should_review(filename: str) -> bool:
    """Skip lockfiles, docs, images, vendored and generated files."""
    base = filename.rsplit("/", 1)[-1]
    if base in SKIP_NAMES:
        return False
    if filename.lower().endswith(SKIP_SUFFIXES):
        return False
    return not any(filename.startswith(d) or f"/{d}" in filename for d in SKIP_DIRS)


def limit_files(files: list, max_chars: int, max_files: int):
    """Keep files while the total patch size stays under max_chars."""
    included, total = [], 0
    for f in files:
        size = len(f.get("patch", ""))
        if len(included) >= max_files or total + size > max_chars:
            continue
        included.append(f)
        total += size
    return included, len(files) - len(included)
