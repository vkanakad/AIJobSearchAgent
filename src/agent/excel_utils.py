from typing import List, Dict
import pandas as pd
from datetime import datetime


def jobs_to_excel(jobs: List[Dict], path: str) -> str:
    if not jobs:
        df = pd.DataFrame([], columns=["title", "company", "location", "remote", "url", "similarity", "sponsorship", "source", "date_found"]) 
    else:
        rows = []
        for j in jobs:
            rows.append({
                "title": j.get("title"),
                "company": j.get("company"),
                "location": j.get("location"),
                "remote": j.get("remote"),
                "url": j.get("url"),
                "similarity": j.get("similarity", None),
                "sponsorship": j.get("sponsorship", False),
                "source": j.get("source"),
                "date_found": datetime.utcnow().isoformat(),
            })
        df = pd.DataFrame(rows)
    df.to_excel(path, index=False)
    return path
