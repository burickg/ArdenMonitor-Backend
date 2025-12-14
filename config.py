import os

DATABASE_URL = os.getenv("DATABASE_URL")

AGENT_SHARED_SECRET = os.getenv("AGENT_SHARED_SECRET", "change-me")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "alerts@arden.ai")
