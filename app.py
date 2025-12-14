from fastapi import FastAPI, Header, HTTPException
from datetime import datetime, timedelta
from db import Base, engine, SessionLocal
from models import Site, Node, Recipient
from emailer import send_email

# =========================
# CONFIG
# =========================

OFFLINE_AFTER_SECONDS = 90
DEFAULT_ALERT_EMAIL = "office@jetsonsliving.com"

# =========================
# INIT
# =========================

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Arden Monitor Backend")

# =========================
# AUTH
# =========================

def _auth(secret: str | None):
    if secret is None:
        raise HTTPException(status_code=401, detail="Missing agent secret")

# =========================
# HEALTH CHECK
# =========================

@app.get("/healthz")
def healthz():
    return {"ok": True}

# =========================
# HEARTBEAT (AUTO-PROVISION)
# =========================

@app.post("/ingest/heartbeat")
def ingest_heartbeat(
    payload: dict,
    x_agent_secret: str | None = Header(default=None)
):
    _auth(x_agent_secret)

    agent_id = payload.get("agent_id")
    node_name = payload.get("node_name")
    site_name = payload.get("site_name")

    if not agent_id or not site_name:
        raise HTTPException(status_code=400, detail="Missing agent_id or site_name")

    db = SessionLocal()
    try:
        # -------------------------
        # Find or create SITE
        # -------------------------
        site = db.query(Site).filter(Site.name == site_name).first()
        if not site:
            site = Site(name=site_name)
            db.add(site)
            db.commit()
            db.refresh(site)

            # Auto-add default alert recipient
            recipient = Recipient(
                site_id=site.id,
                email=DEFAULT_ALERT_EMAIL
            )
            db.add(recipient)
            db.commit()

        # -------------------------
        # Find or create NODE
        # -------------------------
        node = db.query(Node).filter(Node.agent_id == agent_id).first()
        if not node:
            node = Node(
                agent_id=agent_id,
                node_name=node_name or agent_id,
                site_id=site.id,
                status="green"
            )
            db.add(node)

        # -------------------------
        # Update heartbeat
        # -------------------------
        node.last_seen = datetime.utcnow()
        node.status = "green"

        db.commit()

        return {
            "ok": True,
            "site": site.name,
            "node": node.node_name
        }

    finally:
        db.close()

# =========================
# OFFLINE DETECTION + ALERT
# =========================

@app.post("/alerts/check")
def check_for_offline_nodes():
    db = SessionLocal()
    now = datetime.utcnow()

    try:
        nodes = db.query(Node).all()

        for node in nodes:
            if not node.last_seen:
                continue

            seconds_since_seen = (now - node.last_seen).total_seconds()

            if seconds_since_seen > OFFLINE_AFTER_SECONDS and node.status != "offline":
                # Mark offline
                node.status = "offline"
                db.commit()

                site = node.site
                emails = [r.email for r in site.recipients]

                subject = f"[ARDEN ALERT] {node.node_name} OFFLINE"
                body = (
                    f"Arden Monitor Alert\n\n"
                    f"Node: {node.node_name}\n"
                    f"Site: {site.name}\n"
                    f"Last Seen: {node.last_seen.isoformat()} UTC\n"
                    f"Offline For: {int(seconds_since_seen)} seconds\n"
                    f"\nTime: {now.isoformat()} UTC"
                )

                send_email(emails, subject, body)

        return {"ok": True}

    finally:
        db.close()
