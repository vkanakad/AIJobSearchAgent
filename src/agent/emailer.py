import smtplib
from email.message import EmailMessage
from typing import List, Dict
import os


def send_email_with_excel(smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str, to_email: str, subject: str, body: str, attachment_path: str):
    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    # attach excel
    with open(attachment_path, "rb") as f:
        data = f.read()
    maintype = "application"
    subtype = "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=os.path.basename(attachment_path))

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as s:
        s.starttls()
        s.login(smtp_user, smtp_password)
        s.send_message(msg)
