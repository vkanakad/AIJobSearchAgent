import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    email_to: str = os.getenv("EMAIL_TO", "")

    resume_path: str = os.getenv("RESUME_PATH", "resume.txt")
    keywords: str = os.getenv("KEYWORDS", "")
    location_filter: str = os.getenv("LOCATION_FILTER", "Austin,Remote")
    sponsorship_keywords: str = os.getenv("SPONSORSHIP_KEYWORDS", "visa,sponsorship,H-1B,H1B,sponsor")
    similarity_threshold: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.12"))
    max_results: int = int(os.getenv("MAX_RESULTS", "50"))

    daily_run_time: str = os.getenv("DAILY_RUN_TIME", "09:00")


cfg = Config()
