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