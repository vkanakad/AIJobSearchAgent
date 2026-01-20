"""Entry point for the agent.

Usage:
    python -m src.main --once
    python -m src.main   # runs (sleeps) with APScheduler at DAILY_RUN_TIME
"""
import argparse
import os
from pathlib import Path
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

    # determine output folder (allow override via attribute set in main)
    from src.agent.io_utils import get_timestamped_outdir, ensure_outputs_root
    ROOT = Path(__file__).resolve().parents[1]
    ensure_outputs_root()
    out_base = getattr(run_once, "out_dir_arg", None)
    if out_base:
        OUT_DIR = get_timestamped_outdir(base=out_base)
    else:
        OUT_DIR = get_timestamped_outdir(base=str(ROOT / "outputs"))
    serp_rows = [j for j in jobs if j.get("source") == "serpapi"]
    if serp_rows:
        # write raw JSON
        import json
        (OUT_DIR / "serp_raw.json").write_text(json.dumps(serp_rows, indent=2), encoding="utf-8")
        # write preserved-column Excel using jobs_to_excel
        serp_xls = str(OUT_DIR / f"serp_raw_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.xlsx")
        jobs_to_excel(serp_rows, serp_xls)
        print(f"Wrote raw SerpAPI JSON and Excel to: {OUT_DIR}")

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

    # write normalized matched results into timestamped outputs folder
    fname = str(OUT_DIR / f"jobs_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.xlsx")
    jobs_to_excel(filtered, fname)

    # Also create a version of matched results that uses the same columns
    # as the SerpAPI raw export so spreadsheets align.
    if serp_rows:
        # collect serp column order
        serp_cols = []
        seen = set()
        for r in serp_rows:
            for k in r.keys():
                if k not in seen:
                    seen.add(k)
                    serp_cols.append(k)
        # map each filtered job into serp-shaped dicts
        mapped = []
        for j in filtered:
            row = {}
            for k in serp_cols:
                # prefer existing key, else try common fallbacks
                val = j.get(k)
                if val is None:
                    # fallback mappings
                    if k == "company_name":
                        val = j.get("company") or j.get("company_name")
                    if k == "url" or k == "link" or k == "share_link":
                        val = j.get("url") or j.get("link") or j.get("share_link")
                    if k == "job_id":
                        val = j.get("job_id") or j.get("id")
                row[k] = val
            mapped.append(row)
        mapped_xls = str(OUT_DIR / f"matched_serp_columns_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.xlsx")
        jobs_to_excel(mapped, mapped_xls)
        print(f"Wrote matched results with Serp columns: {mapped_xls}")

    print(f"Wrote outputs to: {OUT_DIR}")

    # email unless caller asked not to
    no_email = False
    try:
        # main() may set an attribute for no-email testing
        no_email = getattr(run_once, "no_email_flag", False)
    except Exception:
        no_email = False

    if no_email:
        print("Skipping email send (--no-email)")
        return

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
    parser.add_argument("--no-email", action="store_true", help="Run once but do not send email (useful for testing)")
    parser.add_argument("--out-dir", type=str, default=None, help="Optional base output directory (overrides default outputs folder)")
    args = parser.parse_args()
    if args.once:
        # allow skipping email when testing
        if args.no_email:
            setattr(run_once, "no_email_flag", True)
        # optionally pass an out-dir through environment or arg
        if args.out_dir:
            setattr(run_once, "out_dir_arg", args.out_dir)
        run_once()
    else:
        schedule_daily()


if __name__ == "__main__":
    main()
