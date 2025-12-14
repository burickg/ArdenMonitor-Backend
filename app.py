from fastapi import FastAPI, Header, HTTPException
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
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

def _auth_agent(secret: str | None):
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
    _auth_agent(x_agent_secret)

    agent_id = payload.get("agent_id")
    node_name = payload.get("node_name")
    site_name = payload.get("site_name")

    if not agent_id or not site_name:
        raise HTTPException(status_code=400, detail="Missing agent_id or site_name")

    db: Session = SessionLocal()
    try:
        # ---- Site ----
        site = db.query(Site).filter(Site.name == site_name).first()
        if not site:
            site = Site(name=site_name)
            db.add(site)
            db.commit()
            db.refresh(site)

            recipient = Recipient(
                site_id=site.id,
                email=DEFAULT_ALERT_EMAIL
            )
            db.add(recipient)
            db.commit()

        # ---- Node ----
        node = db.query(Node).filter(Node.agent_id == agent_id).first()
        if not node:
            node = Node(
                agent_id=agent_id,
                node_name=node_name or agent_id,
                site_id=site.id,
                status="green"
            )
            db.add(node)

        node.last_seen = datetime.utcnow()
        node.status = "green"

        db.commit()

        return {"ok": True}

    finally:
        db.close()

# =========================
# METRICS INGEST (CPU / RAM / DISK)
# =========================

@app.post("/ingest/metrics")
def ingest_metrics(
    payload: dict,
    x_agent_secret: str | None = Header(default=None)
):
    _auth_agent(x_agent_secret)

    agent_id = payload.get("agent_id")
    cpu = payload.get("cpu")
    ram = payload.get("ram")
    disk_free_pct = payload.get("disk_free_pct")

    if not agent_id:
        raise HTTPException(status_code=400, detail="Missing agent_id")

    db: Session = SessionLocal()
    try:
        node = db.query(Node).filter(Node.agent_id == agent_id).first()
        if not node:
            raise HTTPException(status_code=404, detail="Unknown agent_id")

        if cpu is not None:
            node.cpu = float(cpu)
        if ram is not None:
            node.ram = float(ram)
        if disk_free_pct is not None:
            node.disk_free_pct = float(disk_free_pct)

        node.metrics_at = datetime.utcnow()
        db.commit()

        return {"ok": True}

    finally:
        db.close()

# =========================
# OFFLINE + METRIC ALERTS
# =========================

@app.post("/alerts/check")
def check_alerts():
    db: Session = SessionLocal()
    now = datetime.utcnow()

    try:
        nodes = db.query(Node).all()

        for node in nodes:
            if not node.last_seen:
                continue

            seconds_since_seen = (now - node.last_seen).total_seconds()

            # ---- OFFLINE ALERT ----
            if seconds_since_seen > OFFLINE_AFTER_SECONDS and node.status != "offline":
                node.status = "offline"
                db.commit()

                site = node.site
                emails = [r.email for r in site.recipients]

                send_email(
                    emails,
                    f"[ARDEN ALERT] {node.node_name} OFFLINE",
                    (
                        f"Node: {node.node_name}\n"
                        f"Site: {site.name}\n"
                        f"Last Seen: {node.last_seen.isoformat()} UTC\n"
                        f"Offline For: {int(seconds_since_seen)} seconds\n"
                        f"Time: {now.isoformat()} UTC"
                    )
                )

            # ---- DISK ALERT ----
            if node.disk_free_pct is not None and node.disk_free_pct < 15:
                site = node.site
                emails = [r.email for r in site.recipients]

                send_email(
                    emails,
                    f"[ARDEN ALERT] {node.node_name} LOW DISK",
                    (
                        f"Node: {node.node_name}\n"
                        f"Site: {site.name}\n"
                        f"Disk Free: {node.disk_free_pct:.1f}%\n"
                        f"Time: {now.isoformat()} UTC"
                    )
                )

        return {"ok": True}

    finally:
        db.close()
