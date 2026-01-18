"""Entry point for the agent.

Usage:
    python -m src.main --once
    python -m src.main   # runs (sleeps) with APScheduler at DAILY_RUN_TIME
"""
import argparse
import os
from src.agent.config import cfg
from src.agent.search import fetch_jobs
from src.agent.matcher import match_jobs
from src.agent.excel_utils import jobs_to_excel
from src.agent.emailer import send_email_with_excel
from datetime import datetime
import tempfile
from apscheduler.schedulers.blocking import BlockingScheduler


def detect_sponsorship(job: dict, sponsorship_keywords: list) -> bool:
    text = (job.get("title", "") or "") + "\n" + (job.get("description", "") or "")
    text_lower = text.lower()
    for k in sponsorship_keywords:
        if k.lower() in text_lower:
            return True
    return False


def run_once():
    print("Fetching jobs...")
    jobs = fetch_jobs(cfg.keywords)
    print(f"Fetched {len(jobs)} jobs from connectors")

    with open(cfg.resume_path, "r", encoding="utf-8") as f:
        resume_text = f.read()

    matched = match_jobs(resume_text, jobs, top_k=cfg.max_results, threshold=cfg.similarity_threshold)
    sponsorship_list = [s.strip() for s in cfg.sponsorship_keywords.split(",") if s.strip()]
    for j in matched:
        j["sponsorship"] = detect_sponsorship(j, sponsorship_list)

    # filter by location (Austin or Remote)
    loc_filters = [l.strip().lower() for l in cfg.location_filter.split(",") if l.strip()]
    filtered = []
    for j in matched:
        loc = (j.get("location") or "").lower()
        is_remote = bool(j.get("remote"))
        if "remote" in loc_filters and (is_remote or "remote" in loc):
            filtered.append(j)
            continue
        for lf in loc_filters:
            if lf != "remote" and lf in loc:
                filtered.append(j)
                break

    print(f"{len(filtered)} jobs match resume + location filters")

    if not filtered:
        print("No jobs to send today.")
        return

    fname = os.path.join(os.getcwd(), f"jobs_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.xlsx")
    jobs_to_excel(filtered, fname)

    subject = f"Daily Job Matches - {datetime.utcnow().date().isoformat()}"
    body = f"Attached are {len(filtered)} job matches (generated {datetime.utcnow().isoformat()})."
    send_email_with_excel(cfg.smtp_host, cfg.smtp_port, cfg.smtp_user, cfg.smtp_password, cfg.email_to, subject, body, fname)
    print("Email sent with attachment:", fname)


def schedule_daily():
    # schedule at DAILY_RUN_TIME (HH:MM)
    hour, minute = [int(x) for x in cfg.daily_run_time.split(":")]
    scheduler = BlockingScheduler()
    scheduler.add_job(run_once, 'cron', hour=hour, minute=minute)
    print(f"Scheduled daily run at {cfg.daily_run_time}. Press Ctrl+C to exit.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()
    if args.once:
        run_once()
    else:
        schedule_daily()


if __name__ == "__main__":
    main()
