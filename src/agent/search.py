"""Job connectors and fetcher.

Connects to public job APIs (Remotive for remote, ArbeitNow for location).
"""
from typing import List, Dict
import requests


def fetch_remotive(keywords: str = "") -> List[Dict]:
    # Remotive: remote jobs only
    url = "https://remotive.com/api/remote-jobs"
    params = {}
    if keywords:
        params["search"] = keywords
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    jobs = []
    for j in data.get("jobs", []):
        jobs.append({
            "source": "remotive",
            "title": j.get("title"),
            "company": j.get("company_name"),
            "location": j.get("candidate_required_location") or j.get("location"),
            "remote": True,
            "url": j.get("url"),
            "description": j.get("description") or "",
        })
    return jobs


def fetch_arbeitnow(page_limit: int = 5) -> List[Dict]:
    # ArbeitNow public job board API (can include locations)
    jobs = []
    base = "https://www.arbeitnow.com/api/job-board-api"
    url = base
    for _ in range(page_limit):
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        for j in data.get("data", []):
            jobs.append({
                "source": "arbeitnow",
                "title": j.get("title"),
                "company": j.get("company_name"),
                "location": j.get("location"),
                "remote": bool(j.get("remote")),
                "url": j.get("url"),
                "description": j.get("description") or "",
            })
        # pagination
        url = data.get("next")
        if not url:
            break
    return jobs


def fetch_jobs(keywords: str = "") -> List[Dict]:
    results = []
    try:
        results.extend(fetch_remotive(keywords))
    except Exception:
        pass
    try:
        results.extend(fetch_arbeitnow())
    except Exception:
        pass
    # deduplicate by url
    seen = set()
    unique = []
    for j in results:
        u = j.get("url") or (j.get("title") + j.get("company", ""))
        if u in seen:
            continue
        seen.add(u)
        unique.append(j)
    return unique
