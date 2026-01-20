from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
import json


def _serialize_value(v: Any) -> Any:
    # Convert complex types to JSON strings for spreadsheet readability
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return v
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return str(v)


def jobs_to_excel(jobs: List[Dict], path: str) -> str:
    """Write `jobs` (list of dicts) to an Excel file at `path`.

    This exporter preserves keys from the job dicts as columns. Nested values
    (lists/dicts) are JSON-serialized into cells so the spreadsheet mirrors
    the original JSON structure.
    """
    # ensure we have a consistent column order: union of all keys, stable sort
    if not jobs:
        cols = ["title", "company", "location", "remote", "url", "similarity", "sponsorship", "source", "date_found"]
        df = pd.DataFrame([], columns=cols)
        df.to_excel(path, index=False)
        return path

    # collect all keys that appear across job dicts
    colset = []
    seen = set()
    for j in jobs:
        if isinstance(j, dict):
            for k in j.keys():
                if k not in seen:
                    seen.add(k)
                    colset.append(k)

    # append a canonical date_found column at the end if not present
    if "date_found" not in seen:
        colset.append("date_found")

    rows = []
    for j in jobs:
        row = {}
        for k in colset:
            if k == "date_found":
                row[k] = datetime.utcnow().isoformat()
            else:
                val = j.get(k)
                row[k] = _serialize_value(val)
        rows.append(row)

    df = pd.DataFrame(rows, columns=colset)
    df.to_excel(path, index=False)
    return path
