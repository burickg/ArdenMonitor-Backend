from fastapi import FastAPI, Header, HTTPException
from datetime import datetime
from db import Base, engine, SessionLocal
from models import Site, Node

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Arden Monitor Backend")

def _auth(secret: str | None):
    if secret is None:
        raise HTTPException(status_code=401, detail="Missing agent secret")

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
        raise HTTPException(status_code=400, detail="Missing required fields")

    db = SessionLocal()
    try:
        # 1️⃣ Find or create site
        site = db.query(Site).filter(Site.name == site_name).first()
        if not site:
            site = Site(name=site_name)
            db.add(site)
            db.commit()
            db.refresh(site)

        # 2️⃣ Find or create node
        node = db.query(Node).filter(Node.agent_id == agent_id).first()
        if not node:
            node = Node(
                agent_id=agent_id,
                node_name=node_name or agent_id,
                site_id=site.id,
                status="green"
            )
            db.add(node)

        # 3️⃣ Update heartbeat
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
