"""Hand-made test cases with known bugs.

Lines ending in '  # BUG' mark the real bug. The marker is stripped before the
code is shown to the model, and the line number becomes the answer key.
Cases with no marker are clean code: any finding there is a false alarm.
Add more cases to make your evaluation stronger.
"""

MARK = "  # BUG"

RAW_CASES = [
    {"id": "sql-injection", "filename": "db.py", "code": '''import sqlite3


def find_user(conn: sqlite3.Connection, name: str):
    cur = conn.cursor()
    query = f"SELECT id, email FROM users WHERE name = '{name}'"  # BUG
    cur.execute(query)
    return cur.fetchone()
'''},
    {"id": "off-by-one", "filename": "report.py", "code": '''def total_price(items):
    total = 0
    for i in range(len(items) + 1):  # BUG
        total += items[i]["price"]
    return total
'''},
    {"id": "mutable-default", "filename": "tags.py", "code": '''def add_tag(tag, tags=[]):  # BUG
    tags.append(tag)
    return tags
'''},
    {"id": "hardcoded-secret", "filename": "client.py", "code": '''import requests


API_KEY = "FAKE_STRIPE_SECRET_FOR_TESTING_ONLY"  # BUG


def fetch_orders():
    resp = requests.get(
        "https://api.shop.example/v1/orders",
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=10,
    )
    return resp.json()
'''},
    {"id": "swallowed-exception", "filename": "loader.py", "code": '''import json


def load_config(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:  # BUG
        pass
'''},
    {"id": "divide-by-zero", "filename": "stats.py", "code": '''def average(values):
    """Return the mean of a list of numbers."""
    return sum(values) / len(values)  # BUG


def summarize(scores):
    return {"mean": average(scores), "count": len(scores)}
'''},
    {"id": "path-traversal", "filename": "files.py", "code": '''import os

UPLOAD_DIR = "/srv/uploads"


def read_upload(filename):
    path = os.path.join(UPLOAD_DIR, filename)  # BUG
    with open(path, "rb") as f:
        return f.read()
'''},
    {"id": "clean-clamp", "filename": "mathutil.py", "code": '''def clamp(value, low, high):
    if low > high:
        raise ValueError("low must be <= high")
    return max(low, min(value, high))
'''},
    {"id": "clean-safe-query", "filename": "db_safe.py", "code": '''import sqlite3


def find_user(conn: sqlite3.Connection, name: str):
    cur = conn.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = ?", (name,))
    return cur.fetchone()
'''},
    {"id": "clean-dataclass", "filename": "geometry.py", "code": '''from dataclasses import dataclass


@dataclass
class Point:
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
'''},
]


def build_cases() -> list:
    cases = []
    for raw in RAW_CASES:
        bug_lines, clean = [], []
        for number, line in enumerate(raw["code"].splitlines(), start=1):
            if line.endswith(MARK):
                bug_lines.append(number)
                line = line[: -len(MARK)]
            clean.append(line)
        patch = f"@@ -0,0 +1,{len(clean)} @@\n" + "\n".join("+" + l for l in clean)
        cases.append({
            "id": raw["id"],
            "filename": raw["filename"],
            "code": "\n".join(clean) + "\n",
            "patch": patch,
            "bug_lines": bug_lines,
        })
    return cases
