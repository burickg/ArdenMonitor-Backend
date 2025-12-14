import smtplib
from email.message import EmailMessage
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM

def send_email(to_list, subject, body):
    if not to_list or not SMTP_HOST:
        return

    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.starttls()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
