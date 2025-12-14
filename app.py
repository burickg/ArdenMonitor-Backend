from fastapi import FastAPI
from db import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Arden Monitor Backend")

@app.get("/healthz")
def healthz():
    return {"ok": True}
