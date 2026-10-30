# AI Pull Request Reviewer

A GitHub App that automatically reviews pull requests. When a PR is opened or
updated, it reads the diff, runs static analysis, asks an LLM to find real bugs
and security issues, filters weak findings, and posts inline review comments.

## How it works

```
GitHub PR event --> webhook (FastAPI) --> fetch diff + repo conventions
        --> ruff static analysis --> LLM review (numbered diff, JSON output)
        --> validate lines, drop low confidence, dedupe, cap
        --> inline review comments + summary (tokens, cost, latency)
```

Key design choices:
- **Line-number-annotated diffs** so the model can cite exact lines, and every
  finding is validated against lines GitHub actually allows comments on.
- **Confidence threshold + comment cap** to keep false alarms low.
- **Repo conventions**: reads `.pr-reviewer.md` or `CONTRIBUTING.md` from the repo.
- **Background processing** so the webhook answers GitHub within 10 seconds.
- **Per-review stats** (`reviews.jsonl`): tokens, cost, latency.

## Setup

```
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env         # Mac/Linux: cp .env.example .env
```

### Create the GitHub App
GitHub > Settings > Developer settings > GitHub Apps > New GitHub App
- Webhook URL: `<your public URL>/webhook` (ngrok URL while developing)
- Webhook secret: same as `GITHUB_WEBHOOK_SECRET` in `.env`
- Permissions: Pull requests = Read & write; Contents = Read-only
- Subscribe to events: Pull request
- Copy the App ID into `.env`, generate a private key, save it as `private-key.pem`
- Install the app on a test repository

Get an Anthropic API key and put it in `.env` as `ANTHROPIC_API_KEY`.

### Run locally
```
uvicorn app:app --reload --port 8000
ngrok http 8000
```
Open a pull request on your test repo and wait a few seconds.

## Tests
```
pytest -q
```
Tests run offline (the LLM is faked), and CI runs them on every push.

## Evaluation (your resume numbers)

**1. Synthetic benchmark** (10 cases with known bugs and clean code):
```
python -m evaluation.run_eval
```
Prints recall (bugs found), precision, false-alarm rate on clean code, average
cost and latency. Add more cases in `evaluation/cases.py` (aim for 30+).

**2. Real pull requests** (the "50+ PRs" claim):
```
python -m evaluation.collect_prs owner/repo 10     # repeat for several repos
python -m evaluation.run_eval --real               # writes real_pr_findings.csv
# open the CSV, mark each finding tp (real issue) or fp (false alarm)
python -m evaluation.summarize_labels              # prints precision
```

### Results (fill in after you run it)
| Metric | Value |
|---|---|
| Synthetic recall | |
| Synthetic precision | |
| False-alarm rate on clean code | |
| Real-PR precision (N PRs labeled) | |
| Avg cost per review | |
| Avg latency | |

## Deploy
```
docker build -t pr-reviewer .
docker run -p 8000:8000 --env-file .env pr-reviewer
```
On Render / Railway / Fly.io: deploy from this repo, set the env vars from
`.env.example` (use `GITHUB_PRIVATE_KEY` with `\n` for newlines instead of the
file), then set the GitHub App webhook URL to `https://<your-app>/webhook`.

## Resume bullet (fill in your numbers)
> Built an AI pull-request reviewer (GitHub App, FastAPI, Claude API, ruff) that
> posts inline review comments; evaluated on N real PRs with X% precision and
> Y% recall on seeded bugs at $Z per review; shipped with Docker and GitHub
> Actions CI.

## Project layout
| File | Purpose |
|---|---|
| `app.py` | Webhook server, signature check |
| `pipeline.py` | Full flow for one PR, comment formatting |
| `reviewer.py` | Prompt, LLM call, validation and filtering |
| `linter.py` | ruff static analysis on changed lines |
| `diff_utils.py` | Diff parsing, line numbering, file filtering |
| `github_client.py` | GitHub API calls |
| `evaluation/` | Benchmark cases, scoring, real-PR evaluation |
| `tests/` | Offline unit tests |
