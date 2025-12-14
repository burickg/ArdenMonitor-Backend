from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

class Site(Base):
    __tablename__ = "sites"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    nodes = relationship("Node", back_populates="site")
    recipients = relationship("Recipient", back_populates="site")

class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String, unique=True, index=True)
    node_name = Column(String)
    site_id = Column(Integer, ForeignKey("sites.id"))

    last_seen = Column(DateTime, nullable=True)
    status = Column(String, default="unknown")  # green/offline/unknown

    # Latest metrics (simple v1: store “current state”)
    cpu = Column(Float, nullable=True)
    ram = Column(Float, nullable=True)
    disk_free_pct = Column(Float, nullable=True)
    metrics_at = Column(DateTime, nullable=True)

    # Anti-spam: last time we alerted for each condition
    last_offline_alert_at = Column(DateTime, nullable=True)
    last_disk_alert_at = Column(DateTime, nullable=True)

    site = relationship("Site", back_populates="nodes")

class Recipient(Base):
    __tablename__ = "recipients"

    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id"))
    email = Column(String)

    site = relationship("Site", back_populates="recipients")
