"""Job connectors and fetcher.

Connects to public job APIs (Remotive for remote, ArbeitNow for location).
"""
import json
import time
from typing import List, Dict, Union
import requests
from src.agent.config import cfg
import logging

_LOG = logging.getLogger(__name__)


def fetch_remotive(keywords: str = "") -> List[Dict]:
    # Remotive: remote jobs only
    print(f"Fetching {keywords}")
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


def fetch_jobs(keywords: Union[str, List[str]] = "") -> List[Dict]:
    results = []
    # Normalize keywords into a list (OR semantics)
    kw_list: List[str] = []
    if isinstance(keywords, list):
        kw_list = [k.strip() for k in keywords if k and str(k).strip()]
    elif isinstance(keywords, str):
        if keywords.strip() == "":
            kw_list = []
        elif "," in keywords:
            kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        else:
            kw_list = [keywords.strip()]

    # Determine a default non-remote location from config
    loc = None
    try:
        loc_filters = [l.strip() for l in cfg.location_filter.split(',') if l.strip()]
        for lf in loc_filters:
            if lf.lower() != 'remote':
                loc = lf
                break
    except Exception:
        loc = None

    # If SerpAPI key configured, run SerpAPI for each keyword (OR semantics)
    try:
        key = cfg.serpapi_key if hasattr(cfg, 'serpapi_key') else None
        if key:
            # If multiple keywords provided, build a single OR-joined query
            # and call SerpAPI once to reduce API calls and let the search
            # engine handle OR semantics.
            try:
                if kw_list:
                    combined = " OR ".join([k for k in kw_list if k])
                    _LOG.debug("Fetching SerpAPI with combined OR query: %s", combined)
                    results.extend(fetch_serpapi(key, combined, location=loc))
                else:
                    results.extend(fetch_serpapi(key, "", location=loc))
            except Exception as e:
                _LOG.warning("SerpAPI fetch failed: %s", e)
    except Exception:
        pass

    # Remotive: run per-keyword if provided (OR semantics), otherwise once with no filter
    try:
        if kw_list:
            for kw in kw_list:
                try:
                    results.extend(fetch_remotive(kw))
                except Exception:
                    continue
        else:
            try:
                results.extend(fetch_remotive(""))
            except Exception:
                pass
    except Exception:
        pass

    # ArbeitNow: fetch once (no keyword support in this connector)
    try:
        results.extend(fetch_arbeitnow())
    except Exception:
        pass
    # deduplicate by url
    seen = set()
    unique = []
    for j in results:
        # build a stable dedup key: prefer URL, otherwise use title+company
        try:
            u = j.get("url")
        except Exception:
            # malformed entry, skip
            continue
        if not u:
            # ensure both title and company are strings (fallback to empty)
            title = j.get("title") or ""
            company = j.get("company") or ""
            u = f"{title}::{company}"
        # normalize to string
        try:
            u = str(u)
        except Exception:
            continue
        if u in seen:
            continue
        seen.add(u)
        unique.append(j)
    return unique


def fetch_serpapi(api_key: str, keywords: str = "", location: str = None) -> List[Dict]:
    """Fetch Google Jobs results via SerpAPI (commercial API).

    Requires a SerpAPI key. Returns list of job dicts similar to other connectors.
    """
    jobs = []
    url = "https://serpapi.com/search.json"
    params = {"engine": "google_jobs", "api_key": api_key, "google_domain": "google.com"}
    if keywords:
        params["q"] = keywords
    if location:
        params["location"] = location

    def _call(p):
        r = requests.get(url, params=p, timeout=30)
        r.raise_for_status()
        return r.json()

    data = _call(params)

    # SerpAPI may return jobs under 'jobs_results' or 'job_results'
    entries = data.get("jobs_results") or data.get("job_results") or []

    curr_time = time.time()

    with open(f"jobs_results-{curr_time}.json", "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=4)

    # If no entries returned, try fallback query variants (remove commas, shorten)
    if not entries:
        _LOG.debug("SerpAPI returned no jobs; error=%s", data.get('error'))
        if keywords and ',' in keywords:
            p2 = params.copy()
            p2['q'] = keywords.replace(',', ' ')
            try:
                data2 = _call(p2)
                entries = data2.get("jobs_results") or data2.get("job_results") or []
            except Exception:
                entries = []
    if not entries and keywords:
        tokens = keywords.split()
        if len(tokens) > 2:
            p3 = params.copy()
            p3['q'] = ' '.join(tokens[:2])
            try:
                data3 = _call(p3)
                entries = data3.get("jobs_results") or data3.get("job_results") or []
            except Exception:
                entries = []
    for j in entries:
        # Preserve original SerpAPI fields: return a shallow copy of the
        # original entry and add a `source` marker. Also ensure common
        # normalized fields are present for downstream consumers.
        job = dict(j)
        # normalize common fields if missing
        job.setdefault("title", j.get("title") or j.get("position") or j.get("job_title"))
        # keep company_name if present; also set company for compatibility
        if "company_name" in j:
            job.setdefault("company_name", j.get("company_name"))
        if isinstance(j.get("company"), dict) and "name" in j.get("company"):
            job.setdefault("company_name", job.get("company_name") or j.get("company").get("name"))
        # unify url field
        url_link = j.get("link") or j.get("url") or j.get("apply_link") or j.get("share_link")
        if url_link:
            job.setdefault("url", url_link)
            job.setdefault("link", url_link)
        job.setdefault("location", j.get("location") or j.get("formatted_location"))
        job.setdefault("description", j.get("description") or j.get("snippet") or j.get("summary") or "")
        job["source"] = "serpapi"
        jobs.append(job)
    return jobs
