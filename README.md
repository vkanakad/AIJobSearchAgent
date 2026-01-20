# AIJobSearchAgent

Lightweight agent to find job postings that match a resume, filter by location and visa sponsorship, and export results to Excel for daily delivery.

This repository fetches jobs from public connectors (Remotive, ArbeitNow) and SerpAPI (if configured), matches them to your resume using TF‑IDF cosine similarity, and writes timestamped outputs including raw SerpAPI dumps and matched results. It can email the Excel automatically (SMTP credentials required).

**Key features**
- Fetch jobs from Remotive and ArbeitNow; SerpAPI if `SERPAPI_KEY` is provided.
- Match jobs to resume text using TF‑IDF + cosine similarity.
- Preserve SerpAPI raw JSON keys in exported Excel (nested values serialized as JSON strings).
- Timestamped outputs under `outputs/<MMDDYY_HHMMSS>/` for reproducible runs.
- CLI entrypoint with `--once` and `--no-email` flags for safe testing.

## Quick start

1. Install Python 3.10+ (this repo was tested with Python 3.14).
2. Create and activate a virtualenv, then install requirements:

```powershell
python -m pip install -r requirements.txt
```

3. Create a `.env` file in the repo root (or set env vars). Minimum recommended variables:

```
RESUME_PATH=resume.txt
KEYWORDS=software engineer,backend,python,java
LOCATION_FILTER=Austin,Remote
SPONSORSHIP_KEYWORDS=visa,sponsorship,H-1B,H1B,sponsor
SIMILARITY_THRESHOLD=0.12
MAX_RESULTS=50
DAILY_RUN_TIME=09:00

# Optional (for SerpAPI)
SERPAPI_KEY=your_serpapi_key_here

# Optional (for emailing results)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your@email
SMTP_PASSWORD=yourpassword
EMAIL_TO=vinay04c8@gmail.com
```

4. Put your resume text at the path specified by `RESUME_PATH` (use `scripts/convert_resume.py` to extract text from a PDF).

## Important commands

- Run a single end-to-end run (exports files and sends email if SMTP configured):

```powershell
$env:PYTHONPATH = (Get-Item -Path .).FullName
python -m src.main --once
```

- Run once without sending email (safe for testing):

```powershell
$env:PYTHONPATH = (Get-Item -Path .).FullName
python -m src.main --once --no-email
```

- Process existing SerpAPI JSON files saved in the repo root (merge, filter by location & explicit no-sponsorship phrases, write CSV/XLSX):

```powershell
python .\scripts\process_serp_jsons.py
```

- Convert a specific SerpAPI JSON (example file) into Excel preserving JSON keys:

```powershell
$env:PYTHONPATH = (Get-Item -Path .).FullName
python .\scripts\export_preserve.py
```

- Run the preview pipeline (fetch connectors, run matcher, write `jobs_all.json` and `matched_jobs.json`):

```powershell
python .\scripts\run_match_preview.py 0.05
```

## Outputs

- All generated files are written to a timestamped folder under `outputs/<MMDDYY_HHMMSS>/`.
- Typical artifacts in a run folder:
  - `serp_raw.json` — raw SerpAPI rows preserved
  - `serp_raw_<TS>.xlsx` — SerpAPI-preserved columns Excel
  - `jobs_<TS>.xlsx` — normalized matched results (used for emailing)
  - `matched_serp_columns_<TS>.xlsx` — matched results mapped to SerpAPI columns
  - Other script outputs: `matched_jobs_links.csv`, `matched_jobs_with_companies.csv`, etc.

To open the most recent outputs folder in PowerShell:

```powershell
(Get-ChildItem -Path .\outputs -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
```

## Expectations & notes

- The sponsorship heuristic uses simple substring matching of tokens in `SPONSORSHIP_KEYWORDS`. The `process_serp_jsons.py` script excludes jobs only if the description explicitly contains negative phrases like "no visa sponsorship" or "will not sponsor".
- Location filtering is a substring match on the job `location` field—freeform entries may require tuning of `LOCATION_FILTER`.
- The SerpAPI integration is optional and will be used if `SERPAPI_KEY` is present. The search will be called once with an OR-joined query when multiple keywords are configured.
- Email sending requires valid SMTP settings; use `--no-email` when testing locally.

## Developer notes

- `src/agent/io_utils.py` centralizes timestamped output folder creation. Scripts under `scripts/` call this helper to place outputs in consistent folders.
- `src/agent/excel_utils.py` preserves JSON keys as columns and serializes nested values as JSON strings to keep Excel columns aligned with original JSON.

## Next improvements (suggested)

- Expand commonly used nested fields into dedicated columns (e.g., `apply_options[0].link`).
- Add `--out-dir` to accept an absolute path without creating an extra timestamp subfolder (currently it creates a timestamped child of the base).
- Add unit tests and CI validation for the connectors and exporters.

If you want, I can implement any of the suggested improvements next (expand nested fields or change out-dir semantics).
# Agentic Job Finder

This project finds jobs matching your resume (Austin, TX or remote) and emails a daily Excel sheet of matches that indicate if a job likely offers visa sponsorship.

Quick start

1. Create a Python virtualenv and install dependencies:

```powershell
python -m venv venv; .\venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill SMTP + settings. Place your resume text in `resume.txt`.

3. Run once to test:

```powershell
python -m src.main --once
```

4. To run daily on Windows, create a Task Scheduler task that runs the same command daily, or run `python -m src.main` as a long-running process (not recommended for laptops).

Notes
- Uses Remotive (remote) and ArbeitNow (location) public APIs. You can add more connectors in `src/agent/search.py`.
- Sponsorship detection is keyword-based; it may miss or false-positive results.

Files
- `src/agent/` : core logic
- `src/main.py` : runner and scheduler
- `.env.example` : configuration example

If you want, I can also add a GitHub Actions workflow to run this daily in the cloud — tell me which cloud/email provider you prefer.

**GitHub Actions**

You can run the agent in GitHub Actions daily (already scaffolded in `.github/workflows/daily.yml`).

- **Required repository secrets:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`.
- **Optional/Recommended:** `KEYWORDS`, `LOCATION_FILTER`, `SPONSORSHIP_KEYWORDS`, `SIMILARITY_THRESHOLD`, `MAX_RESULTS`.
- **SerpAPI (optional):** to fetch Google Jobs / LinkedIn-like results via SerpAPI set `SERPAPI_KEY` as a repo secret. Note: SerpAPI is a paid third-party service with quotas; only set this if you have an API key.

Add secrets via the GitHub UI: Repository → Settings → Secrets and variables → Actions → New repository secret.

Or use the GitHub CLI (recommended):

```powershell
gh auth login
gh secret set SMTP_HOST --body "smtp.example.com" --repo vkanakad/AIJobSearchAgent
gh secret set SMTP_USER --body "you@example.com" --repo vkanakad/AIJobSearchAgent
gh secret set SMTP_PASSWORD --body "your-smtp-password-or-app-password" --repo vkanakad/AIJobSearchAgent
gh secret set EMAIL_TO --body "vinay04c8@gmail.com" --repo vkanakad/AIJobSearchAgent
# Optional: SerpAPI key (if you want Google Jobs results via SerpAPI)
gh secret set SERPAPI_KEY --body "your_serpapi_key_here" --repo vkanakad/AIJobSearchAgent
```

When `SERPAPI_KEY` is present the workflow will attempt to fetch Google Jobs via SerpAPI and include those results in the daily export.